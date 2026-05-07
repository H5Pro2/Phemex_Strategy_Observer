from __future__ import annotations

import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
import os
import subprocess
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from dotenv import load_dotenv

from trade_value_gate import TradeValueGate
from indikator import build_indicator_response
from agent_runtime import build_agent_board
from brain_runtime import apply_economic_gate_to_brain_decision, build_brain_decision, refresh_llm_layer_after_economic_gate


Side = Literal["long", "short"]
Status = Literal["pending", "open", "tp", "sl", "expired"]
WATCHLIST_ASSETS = [
    {"label": "XRPUSDT", "symbol": "XRPUSDT"},
    {"label": "KASUSDT", "symbol": "KASUSDT"},
    {"label": "PTUSDT", "symbol": "PTUSDT"},
    {"label": "BTCUSDT", "symbol": "BTCUSDT"},
    {"label": "ETHUSDT", "symbol": "ETHUSDT"},
    {"label": "SOLUSDT", "symbol": "SOLUSDT"},
    {"label": "LINKUSDT", "symbol": "LINKUSDT"},
    {"label": "BCHUSDT", "symbol": "BCHUSDT"},
    {"label": "BNBUSDT", "symbol": "BNBUSDT"},
    {"label": "PAXGUSDT", "symbol": "PAXGUSDT"},
]
CORRELATION_GROUPS = {
    "crypto_major": {"BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "BCHUSDT", "BNBUSDT", "XRPUSDT"},
    "crypto_alt": {"KASUSDT", "PTUSDT"},
    "metals": {"PAXGUSDT"},
}


@dataclass(frozen=True)
class Candle:
    timestamp: int
    interval: int
    last_close: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float

    @property
    def body(self) -> float:
        return abs(self.close - self.open)

    @property
    def range(self) -> float:
        return max(self.high - self.low, 0.0)

    @property
    def upper_wick(self) -> float:
        return self.high - max(self.open, self.close)

    @property
    def lower_wick(self) -> float:
        return min(self.open, self.close) - self.low

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


@dataclass
class Setup:
    symbol: str
    side: Side
    signal_timeframe_seconds: int
    confirmation_timeframe_seconds: int
    signal_candle_time: int
    confirmation_candle_time: int
    entry: float
    stop_loss: float
    take_profit: float
    reward_risk: float
    fvg_low: float
    fvg_high: float
    features: dict[str, Any]
    trade_size_mode: str = "usd"
    planned_notional_usd: float | None = None
    planned_quantity_asset: float | None = None
    confidence: float = 0.5
    similar_trades: int = 0
    historical_win_rate: float | None = None


@dataclass
class VirtualTrade:
    id: str
    setup: Setup
    status: Status
    created_at: int
    expires_at: int
    filled_at: int | None = None
    closed_at: int | None = None
    exit_price: float | None = None
    result_r: float | None = None


class PhemexClient:
    def __init__(self, base_url: str, api_key: str | None = None, api_secret: str | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()

    def get_klines(self, symbol: str, resolution: int, limit: int = 500) -> list[Candle]:
        path = "/exchange/public/md/v2/kline/last"
        requested_symbol = symbol.strip().upper().replace(".P", "")
        ph_symbol = requested_symbol.split(":", 1)[0]
        quote = requested_symbol.split(":", 1)[1] if ":" in requested_symbol else "USDT"
        futures_symbol = f"{ph_symbol}:{quote}"
        api_symbol = ph_symbol
        params = {"symbol": api_symbol, "resolution": resolution, "limit": limit}

        try:
            response = self.session.get(f"{self.base_url}{path}", params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(f"Phemex kline error for {futures_symbol} via {api_symbol}: {payload}")

            rows = payload.get("data", {}).get("rows", [])
            candles = [
                Candle(
                    timestamp=int(row[0]),
                    interval=int(row[1]),
                    last_close=float(row[2]),
                    open=float(row[3]),
                    high=float(row[4]),
                    low=float(row[5]),
                    close=float(row[6]),
                    volume=float(row[7]),
                    turnover=float(row[8]),
                )
                for row in rows
            ]
            return sorted(candles, key=lambda candle: candle.timestamp)
        except Exception as exc:
            raise RuntimeError(f"Phemex kline request failed for {futures_symbol} via {api_symbol}: {exc}") from exc

    def get_futures_account(self, currency: str = "USDT") -> dict[str, Any]:
        payload = self._signed_get("/g-accounts/positions", {"currency": currency})
        account = payload.get("data", {}).get("account")
        if not account:
            raise RuntimeError(f"No futures account returned for {currency}: {payload}")
        return account

    def _signed_get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self.api_key or not self.api_secret:
            raise RuntimeError("Phemex API key/secret missing in .env")

        query = urlencode(params)
        expiry = str(int(time.time()) + 60)
        body = ""
        signed = f"{path}{query}{expiry}{body}"
        signature = hmac.new(self.api_secret.encode("utf-8"), signed.encode("utf-8"), hashlib.sha256).hexdigest()
        headers = {
            "x-phemex-access-token": self.api_key,
            "x-phemex-request-expiry": expiry,
            "x-phemex-request-signature": signature,
        }
        url = f"{self.base_url}{path}?{query}" if query else f"{self.base_url}{path}"
        response = self.session.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"Phemex signed request error: {payload}")
        return payload


class MemoryAgent:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 1, "completed_trades": [], "buckets": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def save(self) -> None:
        self.path.write_text(json.dumps(self.memory, indent=2), encoding="utf-8")

    def score_setup(self, setup: Setup) -> Setup:
        key = self._bucket_key(setup.features)
        bucket = self.memory.get("buckets", {}).get(key)
        if not bucket or bucket["count"] < 3:
            brain_score = float(setup.features.get("brain_score", 50.0)) if isinstance(setup.features, dict) else 50.0
            setup.confidence = round(max(float(getattr(setup, "confidence", 0.5)), min(0.95, brain_score / 100.0)), 3)
            setup.similar_trades = 0 if not bucket else bucket["count"]
            setup.historical_win_rate = None
            return setup

        win_rate = bucket["wins"] / bucket["count"]
        avg_r = bucket["sum_r"] / bucket["count"]
        score = 0.2 + (win_rate * 0.55) + (max(min(avg_r, 2.0), -1.0) + 1.0) * 0.25 / 3.0
        setup.confidence = round(max(0.05, min(score, 0.95)), 3)
        setup.similar_trades = bucket["count"]
        setup.historical_win_rate = round(win_rate, 3)
        return setup

    def record_trade(self, trade: VirtualTrade) -> None:
        if trade.result_r is None:
            return
        setup_data = asdict(trade.setup)
        record = {
            "id": trade.id,
            "symbol": trade.setup.symbol,
            "side": trade.setup.side,
            "closed_at": trade.closed_at,
            "status": trade.status,
            "result_r": trade.result_r,
            "setup": setup_data,
        }
        self.memory.setdefault("completed_trades", []).append(record)

        key = self._bucket_key(trade.setup.features)
        bucket = self.memory.setdefault("buckets", {}).setdefault(
            key, {"count": 0, "wins": 0, "losses": 0, "sum_r": 0.0}
        )
        bucket["count"] += 1
        bucket["wins"] += 1 if trade.result_r > 0 else 0
        bucket["losses"] += 1 if trade.result_r <= 0 else 0
        bucket["sum_r"] += trade.result_r
        self.save()

    def summary(self) -> dict[str, Any]:
        buckets = self.memory.get("buckets", {})
        top_buckets = []
        for key, bucket in buckets.items():
            count = bucket.get("count", 0)
            if not count:
                continue
            top_buckets.append(
                {
                    "key": key,
                    "count": count,
                    "win_rate": round(bucket.get("wins", 0) / count, 3),
                    "avg_r": round(bucket.get("sum_r", 0.0) / count, 3),
                }
            )
        top_buckets.sort(key=lambda item: (item["count"], item["avg_r"]), reverse=True)
        return {
            "completed_trades": len(self.memory.get("completed_trades", [])),
            "bucket_count": len(buckets),
            "top_buckets": top_buckets[:20],
            "recent_completed": self.memory.get("completed_trades", [])[-20:],
        }

    def _bucket_key(self, features: dict[str, Any]) -> str:
        if features.get("strategy") == "agent_brain_ceo":
            parts = [
                f"symbol={features.get('symbol')}",
                f"side={features.get('side')}",
                "strategy=agent_brain_ceo",
                f"tf={features.get('signal_tf')}/{features.get('confirm_tf')}",
                f"pattern={features.get('brain_pattern_key', 'na')}",
                f"entry={features.get('entry_method', 'na')}",
                f"zone={features.get('zone_type', 'na')}",
                f"offset={self._bucket_number(features.get('brain_entry_offset_in_box'), [0.25, 0.5, 0.75])}",
                f"rr={self._bucket_number(features.get('brain_rr_before_gate'), [1.0, 1.5, 2.0, 3.0])}",
            ]
            return "|".join(parts)

        parts = [
            f"symbol={features.get('symbol')}",
            f"side={features.get('side')}",
            f"strategy={features.get('strategy', 'legacy')}",
            f"tf={features.get('signal_tf')}/{features.get('confirm_tf')}",
            f"zone={features.get('zone_type', 'na')}",
            f"zone_size={self._bucket_number(features.get('zone_size_pct'), [0.001, 0.003, 0.006, 0.012])}",
            f"impulse={self._bucket_number(features.get('impulse_range_multiple'), [1.2, 1.6, 2.2, 3.0])}",
            f"entry={features.get('entry_method', 'na')}",
            f"entry_zone={self._bucket_number(features.get('entry_zone_size_pct'), [0.0005, 0.0015, 0.003, 0.006])}",
            f"trend={features.get('trend_alignment')}",
            f"session={features.get('session')}",
        ]
        return "|".join(parts)

    @staticmethod
    def _bucket_number(value: Any, thresholds: list[float]) -> str:
        if value is None:
            return "na"
        value = float(value)
        for threshold in thresholds:
            if value < threshold:
                return f"<{threshold}"
        return f">={thresholds[-1]}"



class PaperBroker:
    def __init__(self, config: dict[str, Any], memory: MemoryAgent) -> None:
        self.config = config
        self.memory = memory
        self.path = Path(config["state_path"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.trades: list[VirtualTrade] = self._load()

    def _load(self) -> list[VirtualTrade]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        trades = []
        for item in raw.get("trades", []):
            setup = Setup(**item["setup"])
            trades.append(VirtualTrade(setup=setup, **{k: v for k, v in item.items() if k != "setup"}))
        return trades

    def save(self) -> None:
        payload = {"trades": [asdict(trade) for trade in self.trades]}
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def add_setup(self, setup: Setup) -> VirtualTrade | None:
        trade_id = f"{setup.symbol}-{setup.side}-{setup.signal_candle_time}-{setup.confirmation_candle_time}"
        if any(trade.id == trade_id for trade in self.trades):
            return None
        allowed, _reason = self.can_accept_setup(setup)
        if not allowed:
            return None
        expires_at = setup.confirmation_candle_time + int(self.config["order_expiry_confirmation_candles"]) * setup.confirmation_timeframe_seconds
        trade = VirtualTrade(
            id=trade_id,
            setup=setup,
            status="pending",
            created_at=int(time.time()),
            expires_at=expires_at,
        )
        self.trades.append(trade)
        self.save()
        return trade

    def can_accept_setup(self, setup: Setup) -> tuple[bool, str | None]:
        active = [trade for trade in self.trades if trade.status in ("pending", "open")]
        if len(active) >= int(self.config.get("max_open_trades_total", 3)):
            return False, "max_open_trades_total"

        same_asset = [trade for trade in active if trade.setup.symbol == setup.symbol]
        if len(same_asset) >= int(self.config.get("max_open_trades_per_asset", 1)):
            return False, "max_open_trades_per_asset"

        if self.config.get("block_same_direction_correlated_trades", True):
            group = correlation_group(setup.symbol)
            if group:
                for trade in active:
                    if trade.setup.side == setup.side and correlation_group(trade.setup.symbol) == group:
                        return False, f"correlated_{group}_{setup.side}"
        return True, None

    def update(self, symbol: str, candles: list[Candle]) -> list[VirtualTrade]:
        changed: list[VirtualTrade] = []
        for trade in self.trades:
            if trade.setup.symbol != symbol or trade.status in ("tp", "sl", "expired"):
                continue

            relevant = [c for c in candles if c.timestamp >= trade.setup.confirmation_candle_time]
            for candle in relevant:
                if trade.status == "pending":
                    if candle.timestamp > trade.expires_at:
                        trade.status = "expired"
                        trade.closed_at = candle.timestamp
                        changed.append(trade)
                        break
                    if self._touches(candle, trade.setup.entry):
                        trade.status = "open"
                        trade.filled_at = candle.timestamp
                        changed.append(trade)

                if trade.status == "open":
                    exit_status, exit_price = self._check_exit(trade.setup, candle)
                    if exit_status:
                        trade.status = exit_status
                        trade.closed_at = candle.timestamp
                        trade.exit_price = exit_price
                        trade.result_r = self._result_r(trade.setup, exit_price)
                        self.memory.record_trade(trade)
                        changed.append(trade)
                        break
        if changed:
            self.save()
        return changed

    @staticmethod
    def _touches(candle: Candle, price: float) -> bool:
        return candle.low <= price <= candle.high

    @staticmethod
    def _check_exit(setup: Setup, candle: Candle) -> tuple[Status | None, float | None]:
        if setup.side == "long":
            hit_sl = candle.low <= setup.stop_loss
            hit_tp = candle.high >= setup.take_profit
            if hit_sl:
                return "sl", setup.stop_loss
            if hit_tp:
                return "tp", setup.take_profit
        else:
            hit_sl = candle.high >= setup.stop_loss
            hit_tp = candle.low <= setup.take_profit
            if hit_sl:
                return "sl", setup.stop_loss
            if hit_tp:
                return "tp", setup.take_profit
        return None, None

    @staticmethod
    def _result_r(setup: Setup, exit_price: float) -> float:
        risk = abs(setup.entry - setup.stop_loss)
        if risk == 0:
            return 0.0
        pnl = (exit_price - setup.entry) if setup.side == "long" else (setup.entry - exit_price)
        return round(pnl / risk, 4)

    def performance(self) -> dict[str, Any]:
        closed = [t for t in self.trades if t.result_r is not None]
        wins = [t for t in closed if t.result_r and t.result_r > 0]
        sum_r = sum(t.result_r or 0.0 for t in closed)
        equity = float(self.config["paper_equity"]) * (1 + float(self.config["risk_per_trade_fraction"]) * sum_r)
        profit_fraction = (equity / float(self.config["paper_equity"])) - 1
        return {
            "closed": len(closed),
            "wins": len(wins),
            "losses": len(closed) - len(wins),
            "win_rate": round(len(wins) / len(closed), 3) if closed else None,
            "sum_r": round(sum_r, 3),
            "paper_equity": round(equity, 2),
            "profit_fraction": round(profit_fraction, 4),
            "live_unlock_ready": profit_fraction >= float(self.config["profit_unlock_threshold_fraction"]),
        }

    def snapshot(self) -> dict[str, Any]:
        per_symbol: dict[str, dict[str, Any]] = {}
        for trade in self.trades:
            symbol_stats = per_symbol.setdefault(
                trade.setup.symbol,
                {"total": 0, "open": 0, "pending": 0, "closed": 0, "wins": 0, "losses": 0, "sum_r": 0.0},
            )
            symbol_stats["total"] += 1
            if trade.status in ("open", "pending"):
                symbol_stats[trade.status] += 1
            if trade.result_r is not None:
                symbol_stats["closed"] += 1
                symbol_stats["sum_r"] += trade.result_r
                if trade.result_r > 0:
                    symbol_stats["wins"] += 1
                else:
                    symbol_stats["losses"] += 1
        for stats in per_symbol.values():
            stats["win_rate"] = round(stats["wins"] / stats["closed"], 3) if stats["closed"] else None
            stats["sum_r"] = round(stats["sum_r"], 3)
        return {
            "performance": self.performance(),
            "trades": [asdict(trade) for trade in self.trades[-100:]],
            "open_trades": sum(1 for trade in self.trades if trade.status == "open"),
            "pending_trades": sum(1 for trade in self.trades if trade.status == "pending"),
            "per_symbol": per_symbol,
        }


class StatusStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.status = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def update(self, patch: dict[str, Any]) -> None:
        with self.lock:
            self.status.update(patch)
            self.path.write_text(json.dumps(self.status, indent=2), encoding="utf-8")

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return json.loads(json.dumps(self.status))


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    config["base_url"] = os.getenv("PHEMEX_BASE_URL", config.get("base_url", "https://api.phemex.com"))
    config["_config_path"] = str(path)
    config.setdefault("paper_trading_enabled", True)
    config.setdefault("observer_enabled", False)
    config.setdefault("observer_asset_mode", "single")
    config.setdefault("max_open_trades_total", 3)
    config.setdefault("max_open_trades_per_asset", 1)
    config.setdefault("block_same_direction_correlated_trades", True)
    config.setdefault("stop_loss_mode", "structure")
    config.setdefault("stop_loss_percent", 0.25)
    config.setdefault("stop_loss_buffer_percent", 0.0)
    config.setdefault("risk_unit", 1.0)
    config.setdefault("min_rr", 0.0)
    config.setdefault("min_tp_distance_fraction", 0.0)
    config.setdefault("max_sl_distance_fraction", 0.0)
    config.setdefault("estimated_taker_fee_rate", 0.0006)
    config.setdefault("min_net_profit_fraction", 0.001)
    config.setdefault("min_net_profit_fraction_by_symbol", {})
    config.setdefault("poll_seconds", 20)
    config.setdefault("phemex_poll_seconds", config.get("poll_seconds", 20))
    config.setdefault("system_loop_seconds", 1)
    config.setdefault("single_timeframe_mode", True)
    if config.get("single_timeframe_mode", True):
        config["confirmation_timeframe_seconds"] = int(config.get("signal_timeframe_seconds", 300))
    config.setdefault("trend_filter_mode", "day_candle")
    config.setdefault("trend_ema_source", "trade_timeframe")
    config.setdefault("daily_bias_min_body_fraction", 0.0)
    config.setdefault("daily_bias_blocks_against_direction", False)
    config.setdefault("structure_lookback_candles", 80)
    config.setdefault("structure_pivot_strength", 2)
    config.setdefault("swing_lookback_candles", config.get("structure_lookback_candles", 80))
    config.setdefault("swing_pivot_strength", config.get("structure_pivot_strength", 2))
    config.setdefault("swing_min_distance_fraction", 0.0001)
    config.setdefault("swing_zone_padding_fraction", 0.0005)
    config.setdefault("swing_reaction_lookback_candles", 5)
    config.setdefault("dip_rejection_wick_ratio", 0.25)
    config.setdefault("dip_rejection_body_ratio", 0.2)
    config.setdefault("take_profit_mode", "target_swing")
    config.setdefault("allow_reward_risk_fallback_tp", False)
    config.setdefault("sweep_rejection_mode", "close")
    config.setdefault("entry_search_confirmation_candles", 20)
    config.setdefault("supply_demand_max_base_candles", 6)
    config.setdefault("supply_demand_max_zone_retests", 1)
    config.setdefault("supply_demand_impulse_range_multiple", 1.15)
    config.setdefault("supply_demand_entry_tolerance_fraction", 0.001)
    config.setdefault("supply_demand_zone_padding_fraction", 0.05)
    config.setdefault("supply_demand_rejection_wick_ratio", 0.35)
    if config.get("observer_asset_mode") == "single" and len(config.get("symbols", [])) > 1:
        config["symbols"] = config["symbols"][:1]
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    config.setdefault("trade_size_mode", "usd")
    config.setdefault("trade_size_usd", 100.0)
    config.setdefault("trade_size_asset", 0.001)
    config.setdefault("trade_sizes_by_symbol", {})
    config.setdefault("account_balance_currency", "USDT")
    config.setdefault("status_path", "data/runtime_status.json")
    config.setdefault("web_host", "127.0.0.1")
    config.setdefault("web_port", 8787)
    config.setdefault("ui_theme", "dark")
    config.setdefault("indicator_enabled", True)
    config.setdefault("indicator_show_bos_choch", True)
    config.setdefault("indicator_show_boxes", True)
    config.setdefault("indicator_show_swing_labels", True)
    config.setdefault("indicator_show_hma", False)
    config.setdefault("indicator_show_sma", True)
    config.setdefault("indicator_show_triple_ema", False)
    config.setdefault("indicator_show_mfi", True)
    config.setdefault("indicator_show_support_resistance", True)
    config.setdefault("indicator_swing_size", 5)
    config.setdefault("indicator_hhll_range", 50)
    config.setdefault("indicator_hma_period", 20)
    config.setdefault("indicator_sma_period", 50)
    config.setdefault("indicator_triple_ema_period", 20)
    config.setdefault("indicator_triple_ema_slow_period", 50)
    config.setdefault("indicator_mfi_period", 14)
    config.setdefault("indicator_sr_pivot_period", 10)
    config.setdefault("indicator_sr_source", "High/Low")
    config.setdefault("indicator_sr_max_pivots", 20)
    config.setdefault("indicator_sr_channel_width_percent", 10)
    config.setdefault("indicator_sr_max_levels", 5)
    config.setdefault("indicator_sr_min_strength", 2)
    config.setdefault("indicator_box_extend_candles", 4)
    legacy_indicator_lookback_days = int(config.get("indicator_lookback_days", 3))
    config.setdefault("indicator_bos_choch_lookback_days", legacy_indicator_lookback_days)
    config.setdefault("indicator_boxes_lookback_days", legacy_indicator_lookback_days)
    config.setdefault("indicator_swing_labels_lookback_days", legacy_indicator_lookback_days)
    config.setdefault("indicator_hma_lookback_days", 0)
    config.setdefault("indicator_sma_lookback_days", 0)
    config.setdefault("indicator_triple_ema_lookback_days", 0)
    config.setdefault("indicator_mfi_lookback_days", 0)
    config.setdefault("indicator_lookback_days", legacy_indicator_lookback_days)
    config.setdefault("indicator_bos_confirmation", "Wicks")
    config.setdefault("chart_candle_up_color", "#047857")
    config.setdefault("chart_candle_down_color", "#b42318")
    config.setdefault("chart_candle_no_change_color", "#667085")
    config.setdefault("chart_grid_color", "#d9e0ea")
    config.setdefault("chart_background_color", "#ffffff")
    config.setdefault("indicator_rising_color", "#047857")
    config.setdefault("indicator_falling_color", "#b42318")
    config.setdefault("indicator_bos_rising_color", config.get("indicator_rising_color", "#047857"))
    config.setdefault("indicator_bos_falling_color", config.get("indicator_falling_color", "#b42318"))
    config.setdefault("indicator_swing_rising_color", config.get("indicator_rising_color", "#047857"))
    config.setdefault("indicator_swing_falling_color", config.get("indicator_falling_color", "#b42318"))
    config.setdefault("indicator_box_high_color", "#b42318")
    config.setdefault("indicator_box_low_color", "#047857")
    config.setdefault("indicator_hma_color", "#7c3aed")
    config.setdefault("indicator_sma_color", "#06b6d4")
    config.setdefault("indicator_triple_ema_color", "#d97706")
    config.setdefault("indicator_triple_ema_slow_color", "#2563eb")
    config.setdefault("indicator_mfi_color", "#db2777")
    config.setdefault("indicator_sr_support_color", "#22c55e")
    config.setdefault("indicator_sr_resistance_color", "#ef4444")
    config.setdefault("agent_view_enabled", True)
    config.setdefault("agent_show_offline_agents", True)
    config.setdefault("agent_bos_choch_enabled", True)
    config.setdefault("agent_bos_choch_weight", 1.0)
    config.setdefault("agent_bos_choch_min_score", 0)
    config.setdefault("agent_bos_choch_blocking", False)
    config.setdefault("agent_box_enabled", True)
    config.setdefault("agent_box_weight", 1.0)
    config.setdefault("agent_box_min_score", 0)
    config.setdefault("agent_box_blocking", False)
    config.setdefault("agent_support_resistance_enabled", True)
    config.setdefault("agent_support_resistance_weight", 1.0)
    config.setdefault("agent_support_resistance_min_score", 0)
    config.setdefault("agent_support_resistance_blocking", False)
    config.setdefault("agent_swing_labels_enabled", True)
    config.setdefault("agent_swing_labels_weight", 1.0)
    config.setdefault("agent_swing_labels_min_score", 0)
    config.setdefault("agent_swing_labels_blocking", False)
    config.setdefault("agent_hma_enabled", True)
    config.setdefault("agent_hma_weight", 1.0)
    config.setdefault("agent_hma_min_score", 0)
    config.setdefault("agent_hma_blocking", False)
    config.setdefault("agent_sma_enabled", True)
    config.setdefault("agent_sma_period", 50)
    config.setdefault("agent_sma_weight", 1.0)
    config.setdefault("agent_sma_min_score", 0)
    config.setdefault("agent_sma_blocking", False)
    config.setdefault("agent_triple_ema_enabled", True)
    config.setdefault("agent_triple_ema_weight", 1.0)
    config.setdefault("agent_triple_ema_min_score", 0)
    config.setdefault("agent_triple_ema_blocking", False)
    config.setdefault("agent_mfi_enabled", True)
    config.setdefault("agent_mfi_period", 14)
    config.setdefault("agent_mfi_weight", 1.0)
    config.setdefault("agent_mfi_min_score", 0)
    config.setdefault("agent_mfi_blocking", False)
    config.setdefault("agent_volume_enabled", True)
    config.setdefault("agent_volume_period", 20)
    config.setdefault("agent_volume_weight", 1.0)
    config.setdefault("agent_volume_min_score", 0)
    config.setdefault("agent_volume_blocking", False)
    config.setdefault("agent_risk_enabled", True)
    config.setdefault("agent_risk_weight", 1.0)
    config.setdefault("agent_risk_min_score", 0)
    config.setdefault("agent_risk_blocking", False)
    config.setdefault("trade_decision_mode", "brain")
    config.setdefault("brain_enabled", True)
    config.setdefault("brain_min_score", 58)
    config.setdefault("brain_min_score_gap", 18)
    config.setdefault("brain_min_agent_alignment", 2)
    config.setdefault("brain_memory_min_count", 3)
    config.setdefault("brain_entry_box_offset", 0.35)
    config.setdefault("brain_require_box_for_trade", True)
    config.setdefault("brain_target_lookback_candles", 120)
    config.setdefault("brain_stop_lookback_candles", 8)
    config.setdefault("brain_allow_rr_target_fallback", False)
    config.setdefault("brain_llm_layer_enabled", True)
    config.setdefault("ollama_enabled", True)
    config.setdefault("ollama_base_url", "http://127.0.0.1:11434")
    config.setdefault("ollama_model", "qwen2.5:3b")
    config.setdefault("ollama_timeout_seconds", 60)
    config.setdefault("ollama_max_prompt_chars", 4000)
    config.setdefault("ollama_temperature", 0.0)
    config.setdefault("ollama_block_hint_enabled", False)
    if config.get("live_trading_enabled", False):
        raise RuntimeError("Live trading is locked in this observer. Set live_trading_enabled=false.")
    return config


def public_config(config: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "symbols",
        "signal_timeframe_seconds",
        "confirmation_timeframe_seconds",
        "single_timeframe_mode",
        "poll_seconds",
        "phemex_poll_seconds",
        "system_loop_seconds",
        "kline_limit",
        "reward_risk",
        "entry_mode",
        "paper_trading_enabled",
        "observer_enabled",
        "observer_asset_mode",
        "max_open_trades_total",
        "max_open_trades_per_asset",
        "block_same_direction_correlated_trades",
        "stop_loss_mode",
        "stop_loss_percent",
        "stop_loss_buffer_percent",
        "risk_unit",
        "min_rr",
        "min_tp_distance_fraction",
        "max_sl_distance_fraction",
        "estimated_taker_fee_rate",
        "min_net_profit_fraction",
        "min_net_profit_fraction_by_symbol",
        "trade_size_mode",
        "trade_size_usd",
        "trade_size_asset",
        "trade_sizes_by_symbol",
        "account_balance_currency",
        "profit_unlock_threshold_fraction",
        "structure_lookback_candles",
        "structure_pivot_strength",
        "use_trend_filter",
        "trend_filter_mode",
        "trend_ema_source",
        "trend_ema_period",
        "daily_bias_min_body_fraction",
        "daily_bias_blocks_against_direction",
        "swing_lookback_candles",
        "swing_pivot_strength",
        "swing_min_distance_fraction",
        "swing_zone_padding_fraction",
        "swing_reaction_lookback_candles",
        "dip_rejection_wick_ratio",
        "dip_rejection_body_ratio",
        "take_profit_mode",
        "allow_reward_risk_fallback_tp",
        "sweep_rejection_mode",
        "entry_search_confirmation_candles",
        "supply_demand_max_base_candles",
        "supply_demand_max_zone_retests",
        "supply_demand_impulse_range_multiple",
        "supply_demand_entry_tolerance_fraction",
        "supply_demand_zone_padding_fraction",
        "supply_demand_rejection_wick_ratio",
        "ui_theme",
        "indicator_enabled",
        "indicator_show_bos_choch",
        "indicator_show_boxes",
        "indicator_show_swing_labels",
        "indicator_show_hma",
        "indicator_show_sma",
        "indicator_show_triple_ema",
        "indicator_show_mfi",
        "indicator_show_support_resistance",
        "indicator_swing_size",
        "indicator_hhll_range",
        "indicator_hma_period",
        "indicator_sma_period",
        "indicator_triple_ema_period",
        "indicator_triple_ema_slow_period",
        "indicator_mfi_period",
        "indicator_sr_pivot_period",
        "indicator_sr_max_pivots",
        "indicator_sr_channel_width_percent",
        "indicator_sr_max_levels",
        "indicator_sr_min_strength",
        "indicator_box_extend_candles",
        "indicator_bos_choch_lookback_days",
        "indicator_boxes_lookback_days",
        "indicator_swing_labels_lookback_days",
        "indicator_hma_lookback_days",
        "indicator_sma_lookback_days",
        "indicator_triple_ema_lookback_days",
        "indicator_mfi_lookback_days",
        "indicator_lookback_days",
        "indicator_bos_confirmation",
        "chart_candle_up_color",
        "chart_candle_down_color",
        "chart_candle_no_change_color",
        "chart_grid_color",
        "chart_background_color",
        "indicator_rising_color",
        "indicator_falling_color",
        "indicator_bos_rising_color",
        "indicator_bos_falling_color",
        "indicator_swing_rising_color",
        "indicator_swing_falling_color",
        "indicator_box_high_color",
        "indicator_box_low_color",
        "indicator_hma_color",
        "indicator_sma_color",
        "indicator_triple_ema_color",
        "indicator_triple_ema_slow_color",
        "indicator_mfi_color",
        "indicator_sr_source",
        "indicator_sr_support_color",
        "indicator_sr_resistance_color",
        "agent_view_enabled",
        "agent_show_offline_agents",
        "agent_bos_choch_enabled",
        "agent_bos_choch_weight",
        "agent_bos_choch_min_score",
        "agent_bos_choch_blocking",
        "agent_box_enabled",
        "agent_box_weight",
        "agent_box_min_score",
        "agent_box_blocking",
        "agent_support_resistance_enabled",
        "agent_support_resistance_weight",
        "agent_support_resistance_min_score",
        "agent_support_resistance_blocking",
        "agent_swing_labels_enabled",
        "agent_swing_labels_weight",
        "agent_swing_labels_min_score",
        "agent_swing_labels_blocking",
        "agent_hma_enabled",
        "agent_hma_weight",
        "agent_hma_min_score",
        "agent_hma_blocking",
        "agent_sma_enabled",
        "agent_sma_period",
        "agent_sma_weight",
        "agent_sma_min_score",
        "agent_sma_blocking",
        "agent_triple_ema_enabled",
        "agent_triple_ema_weight",
        "agent_triple_ema_min_score",
        "agent_triple_ema_blocking",
        "agent_mfi_enabled",
        "agent_mfi_period",
        "agent_mfi_weight",
        "agent_mfi_min_score",
        "agent_mfi_blocking",
        "agent_volume_enabled",
        "agent_volume_period",
        "agent_volume_weight",
        "agent_volume_min_score",
        "agent_volume_blocking",
        "agent_risk_enabled",
        "agent_risk_weight",
        "agent_risk_min_score",
        "agent_risk_blocking",
        "trade_decision_mode",
        "brain_enabled",
        "brain_min_score",
        "brain_min_score_gap",
        "brain_min_agent_alignment",
        "brain_memory_min_count",
        "brain_entry_box_offset",
        "brain_require_box_for_trade",
        "brain_target_lookback_candles",
        "brain_stop_lookback_candles",
        "brain_allow_rr_target_fallback",
        "brain_llm_layer_enabled",
        "ollama_enabled",
        "ollama_base_url",
        "ollama_model",
        "ollama_timeout_seconds",
        "ollama_max_prompt_chars",
        "ollama_temperature",
        "ollama_block_hint_enabled",
    ]
    result = {key: config.get(key) for key in keys}
    result["watchlist_assets"] = WATCHLIST_ASSETS
    return result


def update_config_file(config: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "paper_trading_enabled": bool,
        "observer_enabled": bool,
        "trade_size_mode": str,
        "trade_size_usd": float,
        "trade_size_asset": float,
        "profit_unlock_threshold_fraction": float,
    }
    extra_allowed = {
        "symbols",
        "signal_timeframe_seconds",
        "confirmation_timeframe_seconds",
        "single_timeframe_mode",
        "poll_seconds",
        "phemex_poll_seconds",
        "system_loop_seconds",
        "kline_limit",
        "reward_risk",
        "entry_mode",
        "min_sweep_percent_of_prev_range",
        "min_displacement_body_percent_of_range",
        "use_trend_filter",
        "trend_filter_mode",
        "trend_ema_source",
        "daily_bias_min_body_fraction",
        "daily_bias_blocks_against_direction",
        "trend_ema_period",
        "single_timeframe_mode",
        "swing_lookback_candles",
        "swing_pivot_strength",
        "swing_min_distance_fraction",
        "swing_zone_padding_fraction",
        "swing_reaction_lookback_candles",
        "dip_rejection_wick_ratio",
        "dip_rejection_body_ratio",
        "take_profit_mode",
        "allow_reward_risk_fallback_tp",
        "observer_asset_mode",
        "max_open_trades_total",
        "max_open_trades_per_asset",
        "block_same_direction_correlated_trades",
        "stop_loss_mode",
        "stop_loss_percent",
        "stop_loss_buffer_percent",
        "risk_unit",
        "min_rr",
        "min_tp_distance_fraction",
        "max_sl_distance_fraction",
        "estimated_taker_fee_rate",
        "min_net_profit_fraction",
        "min_net_profit_fraction_by_symbol",
        "structure_lookback_candles",
        "structure_pivot_strength",
        "sweep_rejection_mode",
        "entry_search_confirmation_candles",
        "supply_demand_max_base_candles",
        "supply_demand_max_zone_retests",
        "supply_demand_impulse_range_multiple",
        "supply_demand_entry_tolerance_fraction",
        "supply_demand_zone_padding_fraction",
        "supply_demand_rejection_wick_ratio",
        "ui_theme",
        "indicator_enabled",
        "indicator_show_bos_choch",
        "indicator_show_boxes",
        "indicator_show_swing_labels",
        "indicator_show_hma",
        "indicator_show_sma",
        "indicator_show_triple_ema",
        "indicator_show_mfi",
        "indicator_show_support_resistance",
        "indicator_swing_size",
        "indicator_hhll_range",
        "indicator_hma_period",
        "indicator_sma_period",
        "indicator_triple_ema_period",
        "indicator_triple_ema_slow_period",
        "indicator_mfi_period",
        "indicator_sr_pivot_period",
        "indicator_sr_max_pivots",
        "indicator_sr_channel_width_percent",
        "indicator_sr_max_levels",
        "indicator_sr_min_strength",
        "indicator_box_extend_candles",
        "indicator_bos_choch_lookback_days",
        "indicator_boxes_lookback_days",
        "indicator_swing_labels_lookback_days",
        "indicator_hma_lookback_days",
        "indicator_sma_lookback_days",
        "indicator_triple_ema_lookback_days",
        "indicator_mfi_lookback_days",
        "indicator_lookback_days",
        "indicator_bos_confirmation",
        "chart_candle_up_color",
        "chart_candle_down_color",
        "chart_candle_no_change_color",
        "chart_grid_color",
        "chart_background_color",
        "indicator_rising_color",
        "indicator_falling_color",
        "indicator_bos_rising_color",
        "indicator_bos_falling_color",
        "indicator_swing_rising_color",
        "indicator_swing_falling_color",
        "indicator_box_high_color",
        "indicator_box_low_color",
        "indicator_hma_color",
        "indicator_sma_color",
        "indicator_triple_ema_color",
        "indicator_triple_ema_slow_color",
        "indicator_mfi_color",
        "indicator_sr_source",
        "indicator_sr_support_color",
        "indicator_sr_resistance_color",
        "agent_view_enabled",
        "agent_show_offline_agents",
        "agent_bos_choch_enabled",
        "agent_bos_choch_weight",
        "agent_bos_choch_min_score",
        "agent_bos_choch_blocking",
        "agent_box_enabled",
        "agent_box_weight",
        "agent_box_min_score",
        "agent_box_blocking",
        "agent_support_resistance_enabled",
        "agent_support_resistance_weight",
        "agent_support_resistance_min_score",
        "agent_support_resistance_blocking",
        "agent_swing_labels_enabled",
        "agent_swing_labels_weight",
        "agent_swing_labels_min_score",
        "agent_swing_labels_blocking",
        "agent_hma_enabled",
        "agent_hma_weight",
        "agent_hma_min_score",
        "agent_hma_blocking",
        "agent_sma_enabled",
        "agent_sma_period",
        "agent_sma_weight",
        "agent_sma_min_score",
        "agent_sma_blocking",
        "agent_triple_ema_enabled",
        "agent_triple_ema_weight",
        "agent_triple_ema_min_score",
        "agent_triple_ema_blocking",
        "agent_mfi_enabled",
        "agent_mfi_period",
        "agent_mfi_weight",
        "agent_mfi_min_score",
        "agent_mfi_blocking",
        "agent_volume_enabled",
        "agent_volume_period",
        "agent_volume_weight",
        "agent_volume_min_score",
        "agent_volume_blocking",
        "agent_risk_enabled",
        "agent_risk_weight",
        "agent_risk_min_score",
        "agent_risk_blocking",
        "trade_decision_mode",
        "brain_enabled",
        "brain_min_score",
        "brain_min_score_gap",
        "brain_min_agent_alignment",
        "brain_memory_min_count",
        "brain_entry_box_offset",
        "brain_require_box_for_trade",
        "brain_target_lookback_candles",
        "brain_stop_lookback_candles",
        "brain_allow_rr_target_fallback",
        "brain_llm_layer_enabled",
        "ollama_enabled",
        "ollama_base_url",
        "ollama_model",
        "ollama_timeout_seconds",
        "ollama_max_prompt_chars",
        "ollama_temperature",
        "ollama_block_hint_enabled",
    }
    color_keys = {
        "chart_candle_up_color",
        "chart_candle_down_color",
        "chart_candle_no_change_color",
        "chart_grid_color",
        "chart_background_color",
        "indicator_rising_color",
        "indicator_falling_color",
        "indicator_bos_rising_color",
        "indicator_bos_falling_color",
        "indicator_swing_rising_color",
        "indicator_swing_falling_color",
        "indicator_box_high_color",
        "indicator_box_low_color",
        "indicator_hma_color",
        "indicator_sma_color",
        "indicator_triple_ema_color",
        "indicator_triple_ema_slow_color",
        "indicator_mfi_color",
        "indicator_sr_source",
        "indicator_sr_support_color",
        "indicator_sr_resistance_color",
    }

    def clean_hex_color(name: str, raw: Any) -> str:
        value = str(raw).strip()
        valid = value.startswith("#") and len(value) == 7 and all(char in "0123456789abcdefABCDEF" for char in value[1:])
        if not valid:
            raise ValueError(f"{name} must be a #RRGGBB color")
        return value.lower()

    clean: dict[str, Any] = {}
    for key, converter in allowed.items():
        if key not in updates:
            continue
        value = updates[key]
        if key == "trade_size_mode":
            value = str(value).lower()
            if value not in ("usd", "asset"):
                raise ValueError("trade_size_mode must be usd or asset")
        elif key in ("paper_trading_enabled", "observer_enabled"):
            value = bool(value)
        else:
            value = converter(value)
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{key} must be a non-negative number")
        clean[key] = value

    for key in extra_allowed:
        if key in updates and key not in clean:
            value = updates[key]
            if key == "symbols":
                if not isinstance(value, list) or not value:
                    raise ValueError("symbols must be a non-empty list")
                clean[key] = [str(symbol).replace(".P", "").split(":", 1)[0].strip().upper() for symbol in value if str(symbol).strip()]
            elif key == "observer_asset_mode":
                value = str(value).lower()
                if value not in ("single", "multi"):
                    raise ValueError("observer_asset_mode must be single or multi")
                clean[key] = value
            elif key == "ui_theme":
                value = str(value).lower()
                if value not in ("light", "dark"):
                    raise ValueError("ui_theme must be light or dark")
                clean[key] = value
            elif key == "indicator_sr_source":
                value = str(value)
                if value not in ("High/Low", "Close/Open"):
                    raise ValueError("indicator_sr_source must be High/Low or Close/Open")
                clean[key] = value
            elif key == "trend_filter_mode":
                value = str(value).lower()
                if value not in ("day_candle", "ema", "none"):
                    raise ValueError("trend_filter_mode must be day_candle, ema, or none")
                clean[key] = value
            elif key == "trend_ema_source":
                value = str(value).lower()
                if value not in ("trade_timeframe", "daily"):
                    raise ValueError("trend_ema_source must be trade_timeframe or daily")
                clean[key] = value
            elif key == "take_profit_mode":
                value = str(value).lower()
                if value not in ("target_swing", "reward_risk"):
                    raise ValueError("take_profit_mode must be target_swing or reward_risk")
                clean[key] = value
            elif key in ("use_trend_filter", "block_same_direction_correlated_trades", "single_timeframe_mode", "daily_bias_blocks_against_direction", "allow_reward_risk_fallback_tp", "indicator_enabled", "indicator_show_bos_choch", "indicator_show_boxes", "indicator_show_swing_labels", "indicator_show_hma", "indicator_show_sma", "indicator_show_triple_ema", "indicator_show_mfi", "indicator_show_support_resistance", "agent_show_offline_agents", "agent_bos_choch_enabled", "agent_bos_choch_blocking", "agent_box_enabled", "agent_box_blocking", "agent_support_resistance_enabled", "agent_support_resistance_blocking", "agent_swing_labels_enabled", "agent_swing_labels_blocking", "agent_hma_enabled", "agent_hma_blocking", "agent_sma_enabled", "agent_sma_blocking", "agent_triple_ema_enabled", "agent_triple_ema_blocking", "agent_mfi_enabled", "agent_mfi_blocking", "agent_volume_enabled", "agent_volume_blocking", "agent_risk_enabled", "agent_risk_blocking", "brain_enabled", "brain_require_box_for_trade", "brain_allow_rr_target_fallback", "brain_llm_layer_enabled", "ollama_enabled", "ollama_block_hint_enabled"):
                clean[key] = bool(value)
            elif key == "trade_decision_mode":
                value = str(value).lower()
                if value != "brain":
                    raise ValueError("trade_decision_mode must stay brain")
                clean[key] = value
            elif key == "entry_mode":
                value = str(value).lower()
                if value not in ("edge", "mid", "conservative"):
                    raise ValueError("entry_mode must be edge, mid, or conservative")
                clean[key] = value
            elif key == "stop_loss_mode":
                value = str(value).lower()
                if value not in ("structure", "fixed_percent"):
                    raise ValueError("stop_loss_mode must be structure or fixed_percent")
                clean[key] = value
            elif key == "ollama_base_url":
                value = str(value).strip().rstrip("/")
                if not value.startswith(("http://", "https://")):
                    raise ValueError("ollama_base_url must start with http:// or https://")
                clean[key] = value
            elif key == "ollama_model":
                value = str(value).strip()
                if not value:
                    raise ValueError("ollama_model must not be empty")
                clean[key] = value
            elif key == "sweep_rejection_mode":
                value = str(value).lower()
                if value not in ("close", "wick"):
                    raise ValueError("sweep_rejection_mode must be close or wick")
                clean[key] = value
            elif key == "indicator_bos_confirmation":
                value = str(value)
                if value not in ("Candle Close", "Wicks"):
                    raise ValueError("indicator_bos_confirmation must be Candle Close or Wicks")
                clean[key] = value
            elif key in color_keys:
                clean[key] = clean_hex_color(key, value)
            elif key in ("indicator_lookback_days", "indicator_bos_choch_lookback_days", "indicator_boxes_lookback_days", "indicator_swing_labels_lookback_days", "indicator_hma_lookback_days", "indicator_sma_lookback_days", "indicator_triple_ema_lookback_days", "indicator_mfi_lookback_days"):
                value = int(value)
                if value < 0:
                    raise ValueError(f"{key} must be non-negative")
                clean[key] = value
            elif key in ("signal_timeframe_seconds", "confirmation_timeframe_seconds", "poll_seconds", "phemex_poll_seconds", "system_loop_seconds", "kline_limit", "trend_ema_period", "max_open_trades_total", "max_open_trades_per_asset", "structure_lookback_candles", "structure_pivot_strength", "entry_search_confirmation_candles", "supply_demand_max_base_candles", "supply_demand_max_zone_retests", "swing_lookback_candles", "swing_pivot_strength", "swing_reaction_lookback_candles", "indicator_swing_size", "indicator_hhll_range", "indicator_hma_period", "indicator_sma_period", "indicator_triple_ema_period", "indicator_triple_ema_slow_period", "indicator_mfi_period", "indicator_sr_pivot_period", "indicator_sr_max_pivots", "indicator_sr_channel_width_percent", "indicator_sr_max_levels", "indicator_sr_min_strength", "indicator_box_extend_candles", "agent_bos_choch_min_score", "agent_box_min_score", "agent_swing_labels_min_score", "agent_hma_min_score", "agent_sma_period", "agent_sma_min_score", "agent_triple_ema_min_score", "agent_mfi_period", "agent_mfi_min_score", "agent_volume_period", "agent_volume_min_score", "agent_risk_min_score", "brain_min_score", "brain_min_score_gap", "brain_min_agent_alignment", "brain_memory_min_count", "brain_target_lookback_candles", "brain_stop_lookback_candles", "ollama_timeout_seconds", "ollama_max_prompt_chars"):
                value = int(value)
                if value < 0 or key not in ("agent_bos_choch_min_score", "agent_box_min_score", "agent_support_resistance_min_score", "agent_swing_labels_min_score", "agent_hma_min_score", "agent_sma_min_score", "agent_triple_ema_min_score", "agent_mfi_min_score", "agent_volume_min_score", "agent_risk_min_score") and value <= 0:
                    raise ValueError(f"{key} must be positive")
                clean[key] = value
            elif key in ("agent_bos_choch_weight", "agent_box_weight", "agent_support_resistance_weight", "agent_swing_labels_weight", "agent_hma_weight", "agent_sma_weight", "agent_triple_ema_weight", "agent_mfi_weight", "agent_volume_weight", "agent_risk_weight", "brain_entry_box_offset", "ollama_temperature"):
                value = float(value)
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"{key} must be a non-negative number")
                clean[key] = value
            elif key == "min_net_profit_fraction_by_symbol":
                if not isinstance(value, dict):
                    raise ValueError("min_net_profit_fraction_by_symbol must be an object")
                clean_values: dict[str, float] = {}
                for raw_symbol, raw_fraction in value.items():
                    symbol = str(raw_symbol).replace(".P", "").split(":", 1)[0].strip().upper()
                    if not symbol:
                        continue
                    fraction = float(raw_fraction)
                    if not math.isfinite(fraction) or fraction < 0:
                        raise ValueError(f"min_net_profit_fraction for {symbol} must be a non-negative number")
                    clean_values[symbol] = fraction
                clean[key] = clean_values
            else:
                value = float(value)
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"{key} must be a non-negative number")
                clean[key] = value

    if "trade_sizes_by_symbol" in updates:
        raw_sizes = updates.get("trade_sizes_by_symbol") or {}
        if not isinstance(raw_sizes, dict):
            raise ValueError("trade_sizes_by_symbol must be an object")
        clean_sizes: dict[str, Any] = {}
        for raw_symbol, raw_value in raw_sizes.items():
            symbol = str(raw_symbol).replace(".P", "").strip().upper()
            if not isinstance(raw_value, dict):
                continue
            mode = str(raw_value.get("mode", config.get("trade_size_mode", "usd"))).lower()
            if mode not in ("usd", "asset"):
                raise ValueError(f"invalid mode for {symbol}")
            usd = float(raw_value.get("usd", config.get("trade_size_usd", 0.0)) or 0.0)
            asset = float(raw_value.get("asset", config.get("trade_size_asset", 0.0)) or 0.0)
            if usd < 0 or asset < 0:
                raise ValueError(f"trade size for {symbol} must be non-negative")
            clean_sizes[symbol] = {"mode": mode, "usd": usd, "asset": asset}
        clean["trade_sizes_by_symbol"] = clean_sizes

    if clean.get("observer_asset_mode", config.get("observer_asset_mode")) == "single" and len(clean.get("symbols", config.get("symbols", []))) > 1:
        clean["symbols"] = clean.get("symbols", config.get("symbols", []))[:1]

    if clean.get("single_timeframe_mode", config.get("single_timeframe_mode", True)):
        clean["confirmation_timeframe_seconds"] = int(clean.get("signal_timeframe_seconds", config.get("signal_timeframe_seconds", 300)))

    config.update(clean)
    path = Path(str(config["_config_path"]))
    saved = json.loads(path.read_text(encoding="utf-8"))
    saved.update(clean)
    path.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    return public_config(config)


def env_secret(name: str) -> str | None:
    value = os.getenv(name)
    if not value:
        return None
    value = value.strip()
    if not value or value.startswith("put_"):
        return None
    return value


def strategy_path(config: dict[str, Any]) -> Path:
    return Path(str(config["_config_path"])).with_name("strategy.md")


def read_strategy_markdown(config: dict[str, Any]) -> dict[str, Any]:
    path = strategy_path(config)
    if not path.exists():
        path.write_text(
            "# Strategie-Regelwerk\n\n"
            "## Setup\n\n"
            "Die hoehere Zeiteinheit sucht Supply- und Demand-Zonen aus Base + impulsivem Abgang. "
            "Der Einstieg entsteht erst auf der kleineren Zeiteinheit durch Break-Retest, Struktur-Pullback, optionales FVG oder klare Zonen-Rejection.\n",
            encoding="utf-8",
        )
    return {"path": str(path), "content": path.read_text(encoding="utf-8")}


def open_setup_file(config: dict[str, Any], target: str) -> dict[str, Any]:
    target = target.lower()
    if target == "env":
        path = Path(str(config["_config_path"])).with_name(".env")
    elif target == "config":
        path = Path(str(config["_config_path"]))
    else:
        raise ValueError("target must be env or config")

    if not path.exists() and target == "env":
        example = path.with_name(".env.example")
        path.write_text(example.read_text(encoding="utf-8") if example.exists() else "", encoding="utf-8")
    if not path.exists():
        raise FileNotFoundError(str(path))

    os.startfile(str(path))
    return {"opened": str(path)}


def env_path(config: dict[str, Any]) -> Path:
    return Path(str(config["_config_path"])).with_name(".env")


def read_env_settings(config: dict[str, Any]) -> dict[str, Any]:
    path = env_path(config)
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" not in line or line.strip().startswith("#"):
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    api_key = values.get("PHEMEX_API_KEY", "")
    secret = values.get("PHEMEX_API_SECRET", "")
    return {
        "base_url": values.get("PHEMEX_BASE_URL", config.get("base_url", "https://api.phemex.com")),
        "api_key_present": bool(api_key),
        "api_key_preview": f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "",
        "api_secret_present": bool(secret),
        "api_secret_preview": f"{secret[:4]}...{secret[-4:]}" if len(secret) > 8 else "",
    }


def save_env_settings(config: dict[str, Any], updates: dict[str, Any], client: PhemexClient) -> dict[str, Any]:
    current = read_env_settings(config)
    base_url = str(updates.get("base_url") or current["base_url"]).strip()
    api_key = str(updates.get("api_key") or "").strip()
    api_secret = str(updates.get("api_secret") or "").strip()

    existing: dict[str, str] = {}
    path = env_path(config)
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                existing[key.strip()] = value.strip().strip('"').strip("'")

    if api_key:
        existing["PHEMEX_API_KEY"] = api_key
    if api_secret:
        existing["PHEMEX_API_SECRET"] = api_secret
    existing["PHEMEX_BASE_URL"] = base_url

    ordered = ["PHEMEX_BASE_URL", "PHEMEX_API_KEY", "PHEMEX_API_SECRET"]
    path.write_text("\n".join(f"{key}={existing.get(key, '')}" for key in ordered) + "\n", encoding="utf-8")

    os.environ["PHEMEX_BASE_URL"] = base_url
    if existing.get("PHEMEX_API_KEY"):
        os.environ["PHEMEX_API_KEY"] = existing["PHEMEX_API_KEY"]
    if existing.get("PHEMEX_API_SECRET"):
        os.environ["PHEMEX_API_SECRET"] = existing["PHEMEX_API_SECRET"]
    config["base_url"] = base_url
    client.base_url = base_url.rstrip("/")
    client.api_key = env_secret("PHEMEX_API_KEY")
    client.api_secret = env_secret("PHEMEX_API_SECRET")
    return read_env_settings(config)


def reset_persistent_data(config: dict[str, Any], memory: MemoryAgent, broker: PaperBroker, symbol: str | None = None) -> dict[str, Any]:
    if symbol:
        broker.trades = [trade for trade in broker.trades if trade.setup.symbol != symbol]
        broker.save()

        memory.memory["completed_trades"] = [
            trade for trade in memory.memory.get("completed_trades", [])
            if trade.get("symbol") != symbol and trade.get("setup", {}).get("symbol") != symbol
        ]
        memory.memory["buckets"] = {
            key: bucket
            for key, bucket in memory.memory.get("buckets", {}).items()
            if f"symbol={symbol}" not in key
        }
        memory.save()
        return {"reset": True, "symbol": symbol}

    for path_key in ("memory_path", "state_path"):
        path = Path(str(config[path_key]))
        if path.exists():
            path.unlink()
    memory.memory = {"version": 1, "completed_trades": [], "buckets": {}}
    memory.save()
    broker.trades = []
    broker.save()
    return {"reset": True}


def format_time(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def format_timeframe(seconds: int | float | str) -> str:
    value = int(seconds)
    labels = {60: "1m", 300: "5m", 900: "15m", 1800: "30m", 3600: "1h", 14400: "4h"}
    return labels.get(value, f"{value}s")


def print_signal(trade: VirtualTrade) -> None:
    setup = trade.setup
    print(
        "\nSIGNAL "
        f"{setup.symbol} {setup.side.upper()} "
        f"entry={setup.entry} sl={setup.stop_loss} tp={setup.take_profit} "
        f"confidence={setup.confidence} similar={setup.similar_trades} "
        f"signal={format_time(setup.signal_candle_time)} confirm={format_time(setup.confirmation_candle_time)}"
    )
    print(f"features={json.dumps(setup.features, sort_keys=True)}")


def fetch_account_snapshot(client: PhemexClient, config: dict[str, Any]) -> dict[str, Any]:
    try:
        raw_account = client.get_futures_account(str(config.get("account_balance_currency", "USDT")))
        balance = float(raw_account.get("accountBalanceRv", 0.0))
        used = float(raw_account.get("totalUsedBalanceRv", 0.0))
        return {
            "status": "ok",
            "currency": raw_account.get("currency", config.get("account_balance_currency", "USDT")),
            "account_balance": balance,
            "total_used_balance": used,
            "available_balance_estimate": round(balance - used, 8),
            "raw": raw_account,
        }
    except Exception as exc:
        return {
            "status": "unavailable",
            "currency": config.get("account_balance_currency", "USDT"),
            "error": f"{type(exc).__name__}: {exc}",
        }


def correlation_group(symbol: str) -> str | None:
    for group, symbols in CORRELATION_GROUPS.items():
        if symbol in symbols:
            return group
    return None



class MarketDataCache:
    # --------------------------------------------------
    # INIT
    # --------------------------------------------------
    def __init__(self, config: dict[str, Any]) -> None:
        self.lock = threading.Lock()
        self.account: dict[str, Any] = {
            "status": "unknown",
            "currency": config.get("account_balance_currency", "USDT"),
            "account_balance": None,
            "available_balance_estimate": None,
        }
        self.symbols: dict[str, dict[str, Any]] = {}
        self.last_fetch_started_at: int | None = None
        self.last_fetch_finished_at: int | None = None
        self.last_fetch_duration_seconds: float | None = None
        self.last_fetch_errors: list[dict[str, Any]] = []

    # --------------------------------------------------
    # FETCH STATUS
    # --------------------------------------------------
    def start_fetch(self) -> int:
        now = int(time.time())
        with self.lock:
            self.last_fetch_started_at = now
        return now

    def finish_fetch(self, started_at: int, errors: list[dict[str, Any]]) -> None:
        now = int(time.time())
        with self.lock:
            self.last_fetch_finished_at = now
            self.last_fetch_duration_seconds = round(time.time() - started_at, 3)
            self.last_fetch_errors = list(errors)

    # --------------------------------------------------
    # ACCOUNT CACHE
    # --------------------------------------------------
    def update_account(self, account: dict[str, Any]) -> None:
        with self.lock:
            self.account = json.loads(json.dumps(account))

    # --------------------------------------------------
    # SYMBOL CACHE
    # --------------------------------------------------
    def update_symbol(self, symbol: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.symbols[symbol] = payload

    # --------------------------------------------------
    # SNAPSHOT
    # --------------------------------------------------
    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            symbols: dict[str, dict[str, Any]] = {}
            for symbol, payload in self.symbols.items():
                symbols[symbol] = {
                    **payload,
                    "signal_candles": list(payload.get("signal_candles", [])),
                    "confirm_candles": list(payload.get("confirm_candles", [])),
                    "daily_ema_candles": list(payload.get("daily_ema_candles", [])),
                }
            return {
                "account": json.loads(json.dumps(self.account)),
                "symbols": symbols,
                "last_fetch_started_at": self.last_fetch_started_at,
                "last_fetch_finished_at": self.last_fetch_finished_at,
                "last_fetch_duration_seconds": self.last_fetch_duration_seconds,
                "last_fetch_errors": list(self.last_fetch_errors),
            }


# --------------------------------------------------
# MARKET DATA FETCH LOOP
# --------------------------------------------------
def fetch_market_data_once(client: PhemexClient, config: dict[str, Any], market_cache: MarketDataCache) -> None:
    started_at = market_cache.start_fetch()
    errors: list[dict[str, Any]] = []

    account = fetch_account_snapshot(client, config)
    market_cache.update_account(account)

    if not config.get("observer_enabled", False):
        market_cache.finish_fetch(started_at, errors)
        return

    for symbol in config.get("symbols", []):
        signal_candles: list[Candle] = []
        confirm_candles: list[Candle] = []
        daily_ema_candles: list[Candle] = []
        daily_ema_error: str | None = None
        market_error: str | None = None
        try:
            signal_candles = client.get_klines(symbol, int(config["signal_timeframe_seconds"]), int(config["kline_limit"]))
            if config.get("single_timeframe_mode", True):
                confirm_candles = signal_candles
            else:
                confirm_candles = client.get_klines(symbol, int(config["confirmation_timeframe_seconds"]), int(config["kline_limit"]))

            if (
                str(config.get("trend_filter_mode", "day_candle")).lower() == "ema"
                and str(config.get("trend_ema_source", "trade_timeframe")).lower() == "daily"
            ):
                daily_limit = max(int(config.get("trend_ema_period", 50)) + 5, 20)
                daily_ema_candles = client.get_klines(symbol, 86400, min(daily_limit, 500))
        except Exception as exc:
            error_text = f"{type(exc).__name__}: {exc}"
            if not signal_candles:
                market_error = error_text
                errors.append({"symbol": symbol, "error": error_text})
            else:
                daily_ema_error = error_text
                if not confirm_candles and config.get("single_timeframe_mode", True):
                    confirm_candles = signal_candles

        market_cache.update_symbol(
            symbol,
            {
                "signal_candles": signal_candles,
                "confirm_candles": confirm_candles,
                "daily_ema_candles": daily_ema_candles,
                "daily_ema_error": daily_ema_error,
                "market_error": market_error,
                "fetched_at": int(time.time()),
                "fetched_at_utc": format_time(int(time.time())),
            },
        )

    market_cache.finish_fetch(started_at, errors)


# --------------------------------------------------
# BRAIN SCAN CONTEXT
# --------------------------------------------------
def day_candle_context(candles: list[Candle], config: dict[str, Any]) -> dict[str, Any]:
    if not candles:
        return {"direction": "neutral", "reason": "no_candles"}
    latest = candles[-1]
    latest_date = datetime.fromtimestamp(latest.timestamp, tz=timezone.utc).date()
    day_candles = [
        candle for candle in candles
        if datetime.fromtimestamp(candle.timestamp, tz=timezone.utc).date() == latest_date
    ]
    if not day_candles:
        return {"direction": "neutral", "reason": "no_day_candles"}

    day_open = float(day_candles[0].open)
    day_high = max(float(candle.high) for candle in day_candles)
    day_low = min(float(candle.low) for candle in day_candles)
    day_close = float(day_candles[-1].close)
    day_range = max(day_high - day_low, 1e-12)
    body_fraction = abs(day_close - day_open) / day_range
    min_body_fraction = float(config.get("daily_bias_min_body_fraction", 0.0))
    if body_fraction < min_body_fraction:
        direction = "neutral"
        reason = "body_too_small"
    elif day_close > day_open:
        direction = "long"
        reason = "close_above_open"
    elif day_close < day_open:
        direction = "short"
        reason = "close_below_open"
    else:
        direction = "neutral"
        reason = "close_equals_open"
    return {
        "direction": direction,
        "reason": reason,
        "open": round(day_open, 8),
        "high": round(day_high, 8),
        "low": round(day_low, 8),
        "close": round(day_close, 8),
        "body_fraction": round(body_fraction, 6),
        "candles": len(day_candles),
        "date_utc": latest_date.isoformat(),
    }


def build_brain_scan_context(
    symbol: str,
    signal_candles: list[Candle],
    confirm_candles: list[Candle],
    market_error: str | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    current = signal_candles[-1] if signal_candles else None
    return {
        "symbol": symbol,
        "setup_found": False,
        "reason": market_error or "agent_brain_waiting",
        "strategy": "agent_brain_ceo",
        "structure_mode": "agent_brain_ceo",
        "pipeline": "agents_brain_ceo_gate",
        "signal_candle_time": current.timestamp if current else None,
        "signal_candles": len(signal_candles),
        "confirmation_candles": len(confirm_candles),
        "day_candle": day_candle_context(signal_candles, config),
    }


def update_scan_with_brain_decision(scan: dict[str, Any], brain_decision: dict[str, Any]) -> None:
    candidate = brain_decision.get("candidate") or {}
    brain = brain_decision.get("brain") or {}
    decision = str(brain_decision.get("decision", "WAIT"))
    features = candidate.get("features") or {}
    scan["setup_found"] = bool(candidate)
    scan["reason"] = str(brain.get("message") or decision)
    scan["side"] = str(candidate.get("side", ""))
    scan["entry_method"] = candidate.get("entry_method")
    scan["entry"] = candidate.get("entry_price")
    scan["stop_loss"] = candidate.get("sl_price")
    scan["take_profit"] = candidate.get("tp_price")
    scan["entry_zone_low"] = candidate.get("entry_zone_low")
    scan["entry_zone_high"] = candidate.get("entry_zone_high")
    scan["zone_low"] = candidate.get("entry_zone_low")
    scan["zone_high"] = candidate.get("entry_zone_high")
    scan["zone_type"] = features.get("zone_type") if candidate else None
    scan["brain_decision"] = decision


def brain_gate_input_from_setup(setup: Setup) -> dict[str, Any]:
    return {
        "symbol": setup.symbol,
        "decision": setup.side.upper(),
        "entry_price": setup.entry,
        "tp_price": setup.take_profit,
        "sl_price": setup.stop_loss,
        "planned_notional_usd": setup.planned_notional_usd,
        "planned_quantity_asset": setup.planned_quantity_asset,
    }


# --------------------------------------------------
# BRAIN SETUP FACTORY
# --------------------------------------------------
def create_setup_from_brain_candidate(candidate: dict[str, Any], config: dict[str, Any]) -> Setup:
    symbol = str(candidate["symbol"])
    entry = float(candidate["entry_price"])
    sizes = config.get("trade_sizes_by_symbol", {}) or {}
    size = sizes.get(symbol, {}) if isinstance(sizes, dict) else {}
    mode = str(size.get("mode", config.get("trade_size_mode", "usd"))).lower()
    usd = float(size.get("usd", config.get("trade_size_usd", 0.0)))
    asset = float(size.get("asset", config.get("trade_size_asset", 0.0)))
    planned_notional = round(usd, 8) if mode == "usd" and usd > 0 else None
    planned_quantity = round(asset, 8) if mode == "asset" and asset > 0 else None
    if planned_quantity is None and planned_notional is not None and entry > 0:
        planned_quantity = round(planned_notional / entry, 8)
    if planned_notional is None and planned_quantity is not None and entry > 0:
        planned_notional = round(planned_quantity * entry, 8)

    return Setup(
        symbol=symbol,
        side=str(candidate["side"]),
        signal_timeframe_seconds=int(config.get("signal_timeframe_seconds", 300)),
        confirmation_timeframe_seconds=int(config.get("signal_timeframe_seconds", 300)),
        signal_candle_time=int(candidate["signal_candle_time"]),
        confirmation_candle_time=int(candidate["confirmation_candle_time"]),
        entry=round(entry, 8),
        stop_loss=round(float(candidate["sl_price"]), 8),
        take_profit=round(float(candidate["tp_price"]), 8),
        reward_risk=float(config.get("reward_risk", 1.5)),
        fvg_low=round(float(candidate.get("entry_zone_low", entry)), 8),
        fvg_high=round(float(candidate.get("entry_zone_high", entry)), 8),
        features=dict(candidate.get("features") or {}),
        trade_size_mode=mode,
        planned_notional_usd=planned_notional,
        planned_quantity_asset=planned_quantity,
        confidence=float(candidate.get("confidence", 0.5)),
    )


# --------------------------------------------------
# SYSTEM PROCESSING LOOP
# --------------------------------------------------
def process_cached_once(
    broker: PaperBroker,
    memory: MemoryAgent,
    status_store: StatusStore,
    config: dict[str, Any],
    market_cache: MarketDataCache,
) -> None:
    market = market_cache.snapshot()
    cycle: dict[str, Any] = {
        "started_at": int(time.time()),
        "symbols": {},
        "signals": [],
        "events": [],
        "agents": {},
        "errors": list(market.get("last_fetch_errors", [])),
        "market_data": {
            "last_fetch_started_at": market.get("last_fetch_started_at"),
            "last_fetch_finished_at": market.get("last_fetch_finished_at"),
            "last_fetch_finished_utc": format_time(market["last_fetch_finished_at"]) if market.get("last_fetch_finished_at") else None,
            "last_fetch_duration_seconds": market.get("last_fetch_duration_seconds"),
            "phemex_poll_seconds": int(config.get("phemex_poll_seconds", config.get("poll_seconds", 20))),
            "system_loop_seconds": int(config.get("system_loop_seconds", 1)),
        },
    }
    account = market.get("account") or {
        "status": "unknown",
        "currency": config.get("account_balance_currency", "USDT"),
        "account_balance": None,
        "available_balance_estimate": None,
    }

    if not config.get("observer_enabled", False):
        now = int(time.time())
        snapshot = {
            "bot": {
                "mode": "observer",
                "live_trading_enabled": False,
                "scanner_status": "stopped",
                "last_update": now,
                "last_update_utc": format_time(now),
            },
            "config": {
                **public_config(config),
            },
            "account": account,
            "cycle": {**cycle, "finished_at": now, "duration_seconds": 0, "skipped": "observer stopped"},
            "paper": broker.snapshot(),
            "memory": memory.summary(),
        }
        status_store.update(snapshot)
        return

    value_gate = TradeValueGate(config)
    for symbol in config["symbols"]:
        cached_symbol = market.get("symbols", {}).get(symbol, {})
        signal_candles: list[Candle] = list(cached_symbol.get("signal_candles", []))
        confirm_candles: list[Candle] = list(cached_symbol.get("confirm_candles", []))
        daily_ema_candles: list[Candle] = list(cached_symbol.get("daily_ema_candles", []))
        daily_ema_error: str | None = cached_symbol.get("daily_ema_error")
        market_error: str | None = cached_symbol.get("market_error")

        if not signal_candles:
            reason = market_error or "market_data_not_ready"
            cycle["symbols"][symbol] = {
                "last_signal_candle": None,
                "last_confirmation_candle": None,
                "signal_candles": 0,
                "confirmation_candles": 0,
                "daily_ema_candles": len(daily_ema_candles),
                "daily_ema_error": daily_ema_error,
                "market_error": reason,
                "fetched_at": cached_symbol.get("fetched_at"),
                "fetched_at_utc": cached_symbol.get("fetched_at_utc"),
            }
            cycle["events"].append({"type": "no_setup", "reason": reason, "symbol": symbol})
            continue

        if not confirm_candles and config.get("single_timeframe_mode", True):
            confirm_candles = signal_candles

        cycle["symbols"][symbol] = {
            "last_signal_candle": asdict(signal_candles[-1]) if signal_candles else None,
            "last_confirmation_candle": asdict(confirm_candles[-1]) if confirm_candles else None,
            "signal_candles": len(signal_candles),
            "confirmation_candles": len(confirm_candles),
            "daily_ema_candles": len(daily_ema_candles),
            "daily_ema_error": daily_ema_error,
            "market_error": market_error,
            "fetched_at": cached_symbol.get("fetched_at"),
            "fetched_at_utc": cached_symbol.get("fetched_at_utc"),
        }

        scan_explanation = build_brain_scan_context(symbol, signal_candles, confirm_candles, market_error, config)
        cycle["symbols"][symbol]["scan"] = scan_explanation
        indicator_context = build_indicator_response(
            symbol=symbol,
            resolution=int(config.get("signal_timeframe_seconds", 300)),
            candles=signal_candles,
            swing_size=int(config.get("indicator_swing_size", 5)),
            hhll_range=int(config.get("indicator_hhll_range", 50)),
            bos_confirmation=str(config.get("indicator_bos_confirmation", "Wicks")),
            bos_choch_lookback_days=int(config.get("indicator_bos_choch_lookback_days", config.get("indicator_lookback_days", 3))),
            boxes_lookback_days=int(config.get("indicator_boxes_lookback_days", config.get("indicator_lookback_days", 3))),
            swing_labels_lookback_days=int(config.get("indicator_swing_labels_lookback_days", config.get("indicator_lookback_days", 3))),
            hma_lookback_days=int(config.get("indicator_hma_lookback_days", 0)),
            sma_lookback_days=int(config.get("indicator_sma_lookback_days", 0)),
            triple_ema_lookback_days=int(config.get("indicator_triple_ema_lookback_days", 0)),
            mfi_lookback_days=int(config.get("indicator_mfi_lookback_days", 0)),
            show_swing_labels=bool(config.get("indicator_show_swing_labels", True)),
            show_bos_choch=bool(config.get("indicator_show_bos_choch", True)),
            show_boxes=bool(config.get("indicator_show_boxes", True)),
            show_hma=bool(config.get("indicator_show_hma", False)),
            show_sma=bool(config.get("indicator_show_sma", True)),
            show_triple_ema=bool(config.get("indicator_show_triple_ema", False)),
            show_mfi=bool(config.get("indicator_show_mfi", True)),
            show_support_resistance=bool(config.get("indicator_show_support_resistance", True)),
            hma_period=int(config.get("indicator_hma_period", 20)),
            sma_period=int(config.get("indicator_sma_period", 50)),
            triple_ema_period=int(config.get("indicator_triple_ema_period", 20)),
            triple_ema_slow_period=int(config.get("indicator_triple_ema_slow_period", 50)),
            mfi_period=int(config.get("indicator_mfi_period", 14)),
            sr_pivot_period=int(config.get("indicator_sr_pivot_period", 10)),
            sr_source=str(config.get("indicator_sr_source", "High/Low")),
            sr_max_pivots=int(config.get("indicator_sr_max_pivots", 20)),
            sr_channel_width_percent=int(config.get("indicator_sr_channel_width_percent", 10)),
            sr_max_levels=int(config.get("indicator_sr_max_levels", 5)),
            sr_min_strength=int(config.get("indicator_sr_min_strength", 2)),
            box_extend_candles=int(config.get("indicator_box_extend_candles", 4)),
            hma_color=str(config.get("indicator_hma_color", "#7c3aed")),
            sma_color=str(config.get("indicator_sma_color", "#06b6d4")),
            triple_ema_color=str(config.get("indicator_triple_ema_color", "#d97706")),
            triple_ema_slow_color=str(config.get("indicator_triple_ema_slow_color", "#2563eb")),
            mfi_color=str(config.get("indicator_mfi_color", "#db2777")),
            sr_support_color=str(config.get("indicator_sr_support_color", "#22c55e")),
            sr_resistance_color=str(config.get("indicator_sr_resistance_color", "#ef4444")),
        )
        agent_board = build_agent_board(
            symbol=symbol,
            timeframe_seconds=int(config.get("signal_timeframe_seconds", 300)),
            candles=signal_candles,
            indicator_data=indicator_context,
            scan=scan_explanation,
            config=config,
        )
        brain_decision = build_brain_decision(
            symbol=symbol,
            timeframe_seconds=int(config.get("signal_timeframe_seconds", 300)),
            candles=signal_candles,
            agent_board=agent_board,
            indicator_data=indicator_context,
            scan=scan_explanation,
            memory_state=memory.memory,
            config=config,
        )
        agent_board["brain"] = brain_decision.get("brain")
        agent_board["ceo"] = brain_decision.get("ceo", agent_board.get("ceo"))
        agent_board["trade_plan"] = brain_decision.get("candidate")
        agent_board["memory_match"] = brain_decision.get("memory_match")
        agent_board["llm_layer"] = brain_decision.get("llm_layer")
        cycle["symbols"][symbol]["agents"] = agent_board
        cycle["agents"][symbol] = agent_board
        cycle["symbols"][symbol]["brain"] = brain_decision
        cycle.setdefault("brains", {})[symbol] = brain_decision
        update_scan_with_brain_decision(scan_explanation, brain_decision)

        setup = None
        candidate = brain_decision.get("candidate")
        if candidate:
            setup = create_setup_from_brain_candidate(candidate, config)
            setup = memory.score_setup(setup)

        if setup:
            value_result = value_gate.evaluate(brain_gate_input_from_setup(setup))
            brain_decision = apply_economic_gate_to_brain_decision(brain_decision, value_result)
            brain_decision["llm_layer"] = refresh_llm_layer_after_economic_gate(agent_board, scan_explanation, brain_decision, config)
            agent_board["ceo"] = brain_decision.get("ceo", agent_board.get("ceo"))
            agent_board["economic_gate"] = value_result
            agent_board["llm_layer"] = brain_decision.get("llm_layer")
            cycle["symbols"][symbol]["agents"] = agent_board
            cycle["agents"][symbol] = agent_board
            cycle["symbols"][symbol]["brain"] = brain_decision
            cycle["brains"][symbol] = brain_decision
            if not value_result.get("trade_allowed", False):
                cycle["events"].append({"type": "blocked", "reason": "value_gate", "value_result": value_result, "setup": asdict(setup), "brain": brain_decision})
            else:
                setup.features["value_gate"] = value_result
                setup.features["ceo_decision"] = brain_decision.get("ceo")
                if config.get("paper_trading_enabled", True):
                    allowed, block_reason = broker.can_accept_setup(setup)
                    if not allowed:
                        event = {"type": "blocked", "reason": block_reason, "setup": asdict(setup), "brain": brain_decision}
                        cycle["events"].append(event)
                    else:
                        trade = broker.add_setup(setup)
                        if trade:
                            print_signal(trade)
                            cycle["signals"].append(asdict(trade))
                else:
                    print_signal(VirtualTrade(id=f"signal-only-{setup.symbol}-{setup.confirmation_candle_time}", setup=setup, status="expired", created_at=int(time.time()), expires_at=setup.confirmation_candle_time))
                    cycle["signals"].append({"paper_trade_created": False, "setup": asdict(setup), "brain": brain_decision})
        else:
            cycle["events"].append({"type": "no_setup", "reason": brain_decision.get("decision", scan_explanation.get("reason")), "symbol": symbol, "scan": scan_explanation, "brain": brain_decision})

        changes = broker.update(symbol, confirm_candles) if config.get("paper_trading_enabled", True) else []
        for trade in changes:
            if trade.status == "open":
                print(f"FILLED {trade.id} at {trade.setup.entry} on {format_time(trade.filled_at or 0)}")
                cycle["events"].append({"type": "filled", "trade": asdict(trade)})
            elif trade.status in ("tp", "sl"):
                print(f"CLOSED {trade.id} status={trade.status.upper()} result_r={trade.result_r} on {format_time(trade.closed_at or 0)}")
                cycle["events"].append({"type": "closed", "trade": asdict(trade)})
            elif trade.status == "expired":
                print(f"EXPIRED {trade.id} on {format_time(trade.closed_at or 0)}")
                cycle["events"].append({"type": "expired", "trade": asdict(trade)})

    cycle["finished_at"] = int(time.time())
    cycle["duration_seconds"] = cycle["finished_at"] - cycle["started_at"]
    snapshot = {
        "bot": {
            "mode": "observer",
            "live_trading_enabled": False,
            "scanner_status": "running",
            "last_update": cycle["finished_at"],
            "last_update_utc": format_time(cycle["finished_at"]),
        },
        "config": {
            **public_config(config),
        },
        "account": account,
        "cycle": cycle,
        "paper": broker.snapshot(),
        "memory": memory.summary(),
    }
    status_store.update(snapshot)
    print(f"PERFORMANCE {json.dumps(broker.performance(), sort_keys=True)}")


# --------------------------------------------------
# BACKWARD-COMPATIBLE SINGLE CYCLE
# --------------------------------------------------
def run_once(
    client: PhemexClient,
    broker: PaperBroker,
    memory: MemoryAgent,
    status_store: StatusStore,
    config: dict[str, Any],
) -> None:
    market_cache = MarketDataCache(config)
    fetch_market_data_once(client, config, market_cache)
    process_cached_once(broker, memory, status_store, config, market_cache)


# --------------------------------------------------
# INDEPENDENT LOOP RUNNER
# --------------------------------------------------
def run_market_fetch_loop(client: PhemexClient, config: dict[str, Any], market_cache: MarketDataCache, stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        started = time.time()
        try:
            fetch_market_data_once(client, config, market_cache)
        except Exception as exc:
            print(f"MARKET FETCH ERROR {type(exc).__name__}: {exc}")
        interval = max(1, int(config.get("phemex_poll_seconds", config.get("poll_seconds", 20))))
        sleep_seconds = max(0.1, interval - (time.time() - started))
        stop_event.wait(sleep_seconds)


DASHBOARD_TEMPLATE_PATH = Path(__file__).with_name("dashboard.html")


def load_dashboard_html() -> str:
    return DASHBOARD_TEMPLATE_PATH.read_text(encoding="utf-8")




def start_dashboard(status_store: StatusStore, config: dict[str, Any], client: PhemexClient, memory: MemoryAgent, broker: PaperBroker, host: str, port: int) -> ThreadingHTTPServer:
    class DashboardHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            parsed_url = urlparse(self.path)
            request_path = parsed_url.path
            query = parse_qs(parsed_url.query)
            if request_path == "/" or request_path == "/index.html":
                self._send(200, "text/html; charset=utf-8", load_dashboard_html().encode("utf-8"))
                return
            if request_path in ("/files/arrow_up.png", "/files/arrow_down.png"):
                asset_path = Path(str(config["_config_path"])).with_name("files") / Path(request_path).name
                if not asset_path.exists():
                    asset_path = Path(__file__).with_name("files") / Path(request_path).name
                if asset_path.exists():
                    self._send(200, "image/png", asset_path.read_bytes())
                else:
                    self._send(404, "text/plain; charset=utf-8", b"not found")
                return
            if request_path == "/api/chart-data":
                try:
                    active_symbols = [str(symbol).replace(".P", "").split(":", 1)[0].strip().upper() for symbol in config.get("symbols", []) if str(symbol).strip()]
                    requested_symbol = str(query.get("symbol", [active_symbols[0] if active_symbols else "BTCUSDT"])[0]).replace(".P", "").split(":", 1)[0].strip().upper()
                    if config.get("observer_asset_mode", "single") == "single":
                        symbol = active_symbols[0] if active_symbols else requested_symbol
                    else:
                        symbol = requested_symbol if requested_symbol in active_symbols else (active_symbols[0] if active_symbols else requested_symbol)
                    resolution = int(query.get("resolution", [config.get("confirmation_timeframe_seconds", 60)])[0])
                    config_limit = int(config.get("kline_limit", 500))
                    limit = max(50, min(int(query.get("limit", [config_limit])[0]), 1000))
                    try:
                        candles = client.get_klines(symbol, resolution, limit)
                    except Exception:
                        limit = max(50, min(config_limit, 1000))
                        candles = client.get_klines(symbol, resolution, limit)
                    body = {
                        "symbol": symbol,
                        "chart_symbol": f"{symbol}:USDT",
                        "resolution": resolution,
                        "limit": limit,
                        "candles": [asdict(candle) for candle in candles],
                    }
                    self._send(200, "application/json; charset=utf-8", json.dumps(body).encode("utf-8"))
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(500, "application/json; charset=utf-8", body)
                return
            if request_path == "/api/indicator-data":
                try:
                    active_symbols = [str(symbol).replace(".P", "").split(":", 1)[0].strip().upper() for symbol in config.get("symbols", []) if str(symbol).strip()]
                    requested_symbol = str(query.get("symbol", [active_symbols[0] if active_symbols else "BTCUSDT"])[0]).replace(".P", "").split(":", 1)[0].strip().upper()
                    if config.get("observer_asset_mode", "single") == "single":
                        symbol = active_symbols[0] if active_symbols else requested_symbol
                    else:
                        symbol = requested_symbol if requested_symbol in active_symbols else (active_symbols[0] if active_symbols else requested_symbol)
                    resolution = int(query.get("resolution", [config.get("confirmation_timeframe_seconds", 60)])[0])
                    config_limit = int(config.get("kline_limit", 500))
                    limit = max(50, min(int(query.get("limit", [config_limit])[0]), 1000))
                    def indicator_query_bool(name: str, default: bool) -> bool:
                        raw = str(query.get(name, [str(default)])[0]).strip().lower()
                        return raw in ("1", "true", "yes", "on")

                    swing_size = max(1, min(int(query.get("swing_size", [config.get("indicator_swing_size", 5)])[0]), 50))
                    hhll_range = max(1, min(int(query.get("hhll_range", [config.get("indicator_hhll_range", 50)])[0]), 500))
                    hma_period = max(1, min(int(query.get("hma_period", [config.get("indicator_hma_period", 20)])[0]), 500))
                    sma_period = max(1, min(int(query.get("sma_period", [config.get("indicator_sma_period", 50)])[0]), 500))
                    triple_ema_period = max(1, min(int(query.get("triple_ema_period", [config.get("indicator_triple_ema_period", 20)])[0]), 500))
                    triple_ema_slow_period = max(1, min(int(query.get("triple_ema_slow_period", [config.get("indicator_triple_ema_slow_period", 50)])[0]), 500))
                    mfi_period = max(1, min(int(query.get("mfi_period", [config.get("indicator_mfi_period", 14)])[0]), 500))
                    box_extend_candles = max(2, min(int(query.get("box_extend_candles", [config.get("indicator_box_extend_candles", 4)])[0]), 100))
                    legacy_lookback_days = int(config.get("indicator_lookback_days", 3))
                    bos_choch_lookback_days = max(0, min(int(query.get("bos_choch_lookback_days", [config.get("indicator_bos_choch_lookback_days", legacy_lookback_days)])[0]), 365))
                    boxes_lookback_days = max(0, min(int(query.get("boxes_lookback_days", [config.get("indicator_boxes_lookback_days", legacy_lookback_days)])[0]), 365))
                    swing_labels_lookback_days = max(0, min(int(query.get("swing_labels_lookback_days", [config.get("indicator_swing_labels_lookback_days", legacy_lookback_days)])[0]), 365))
                    hma_lookback_days = max(0, min(int(query.get("hma_lookback_days", [config.get("indicator_hma_lookback_days", 0)])[0]), 365))
                    sma_lookback_days = max(0, min(int(query.get("sma_lookback_days", [config.get("indicator_sma_lookback_days", 0)])[0]), 365))
                    triple_ema_lookback_days = max(0, min(int(query.get("triple_ema_lookback_days", [config.get("indicator_triple_ema_lookback_days", 0)])[0]), 365))
                    mfi_lookback_days = max(0, min(int(query.get("mfi_lookback_days", [config.get("indicator_mfi_lookback_days", 0)])[0]), 365))
                    sr_pivot_period = max(4, min(int(query.get("sr_pivot_period", [config.get("indicator_sr_pivot_period", 10)])[0]), 30))
                    sr_source = str(query.get("sr_source", [config.get("indicator_sr_source", "High/Low")])[0])
                    if sr_source not in ("High/Low", "Close/Open"):
                        sr_source = "High/Low"
                    sr_max_pivots = max(5, min(int(query.get("sr_max_pivots", [config.get("indicator_sr_max_pivots", 20)])[0]), 100))
                    sr_channel_width_percent = max(1, min(int(query.get("sr_channel_width_percent", [config.get("indicator_sr_channel_width_percent", 10)])[0]), 100))
                    sr_max_levels = max(1, min(int(query.get("sr_max_levels", [config.get("indicator_sr_max_levels", 5)])[0]), 10))
                    sr_min_strength = max(1, min(int(query.get("sr_min_strength", [config.get("indicator_sr_min_strength", 2)])[0]), 10))
                    bos_confirmation = str(query.get("bos_confirmation", [config.get("indicator_bos_confirmation", "Wicks")])[0])
                    if bos_confirmation not in ("Candle Close", "Wicks"):
                        bos_confirmation = "Wicks"
                    show_swing_labels = indicator_query_bool("show_swing_labels", bool(config.get("indicator_show_swing_labels", True)))
                    show_bos_choch = indicator_query_bool("show_bos_choch", bool(config.get("indicator_show_bos_choch", True)))
                    show_boxes = indicator_query_bool("show_boxes", bool(config.get("indicator_show_boxes", True)))
                    show_hma = indicator_query_bool("show_hma", bool(config.get("indicator_show_hma", False)))
                    show_sma = indicator_query_bool("show_sma", bool(config.get("indicator_show_sma", True)))
                    show_triple_ema = indicator_query_bool("show_triple_ema", bool(config.get("indicator_show_triple_ema", False)))
                    show_mfi = indicator_query_bool("show_mfi", bool(config.get("indicator_show_mfi", True)))
                    show_support_resistance = indicator_query_bool("show_support_resistance", bool(config.get("indicator_show_support_resistance", True)))
                    hma_color = str(query.get("hma_color", [config.get("indicator_hma_color", "#7c3aed")])[0])
                    sma_color = str(query.get("sma_color", [config.get("indicator_sma_color", "#06b6d4")])[0])
                    triple_ema_color = str(query.get("triple_ema_color", [config.get("indicator_triple_ema_color", "#d97706")])[0])
                    triple_ema_slow_color = str(query.get("triple_ema_slow_color", [config.get("indicator_triple_ema_slow_color", "#2563eb")])[0])
                    mfi_color = str(query.get("mfi_color", [config.get("indicator_mfi_color", "#db2777")])[0])
                    sr_support_color = str(query.get("sr_support_color", [config.get("indicator_sr_support_color", "#22c55e")])[0])
                    sr_resistance_color = str(query.get("sr_resistance_color", [config.get("indicator_sr_resistance_color", "#ef4444")])[0])
                    try:
                        candles = client.get_klines(symbol, resolution, limit)
                    except Exception:
                        limit = max(50, min(config_limit, 1000))
                        candles = client.get_klines(symbol, resolution, limit)
                    body = build_indicator_response(
                        symbol=symbol,
                        resolution=resolution,
                        candles=candles,
                        swing_size=swing_size,
                        hhll_range=hhll_range,
                        bos_confirmation=bos_confirmation,
                        bos_choch_lookback_days=bos_choch_lookback_days,
                        boxes_lookback_days=boxes_lookback_days,
                        swing_labels_lookback_days=swing_labels_lookback_days,
                        hma_lookback_days=hma_lookback_days,
                        sma_lookback_days=sma_lookback_days,
                        triple_ema_lookback_days=triple_ema_lookback_days,
                        mfi_lookback_days=mfi_lookback_days,
                        show_swing_labels=show_swing_labels,
                        show_bos_choch=show_bos_choch,
                        show_boxes=show_boxes,
                        show_hma=show_hma,
                        show_sma=show_sma,
                        show_triple_ema=show_triple_ema,
                        show_mfi=show_mfi,
                        show_support_resistance=show_support_resistance,
                        hma_period=hma_period,
                        sma_period=sma_period,
                        triple_ema_period=triple_ema_period,
                        triple_ema_slow_period=triple_ema_slow_period,
                        mfi_period=mfi_period,
                        sr_pivot_period=sr_pivot_period,
                        sr_source=sr_source,
                        sr_max_pivots=sr_max_pivots,
                        sr_channel_width_percent=sr_channel_width_percent,
                        sr_max_levels=sr_max_levels,
                        sr_min_strength=sr_min_strength,
                        box_extend_candles=box_extend_candles,
                        hma_color=hma_color,
                        sma_color=sma_color,
                        triple_ema_color=triple_ema_color,
                        triple_ema_slow_color=triple_ema_slow_color,
                        mfi_color=mfi_color,
                        sr_support_color=sr_support_color,
                        sr_resistance_color=sr_resistance_color,
                    )
                    body["limit"] = limit
                    self._send(200, "application/json; charset=utf-8", json.dumps(body).encode("utf-8"))
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(500, "application/json; charset=utf-8", body)
                return
            if request_path == "/api/status":
                payload = json.dumps(status_store.snapshot()).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/settings":
                payload = json.dumps(public_config(config)).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/env-settings":
                payload = json.dumps(read_env_settings(config)).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/config-json":
                path = Path(str(config["_config_path"]))
                payload = path.read_text(encoding="utf-8").encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/strategy-md":
                try:
                    payload = json.dumps(read_strategy_markdown(config)).encode("utf-8")
                    self._send(200, "application/json; charset=utf-8", payload)
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(404, "application/json; charset=utf-8", body)
                return
            self._send(404, "text/plain; charset=utf-8", b"not found")

        def do_POST(self) -> None:
            parsed_url = urlparse(self.path)
            request_path = parsed_url.path
            if self.path == "/api/bot-control":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length).decode("utf-8")
                    payload = json.loads(body or "{}")
                    action = str(payload.get("action", "")).lower()
                    if action == "start":
                        settings = update_config_file(config, {"observer_enabled": True})
                        result = {"observer_enabled": True, "config": settings}
                    elif action == "stop":
                        settings = update_config_file(config, {"observer_enabled": False})
                        result = {"observer_enabled": False, "config": settings}
                    elif action == "reset":
                        symbol = payload.get("symbol")
                        reset_symbol = str(symbol).strip().upper() if symbol else None
                        if reset_symbol in ("", "__ALL__", "ALL", "GESAMT"):
                            reset_symbol = None
                        settings = update_config_file(config, {"observer_enabled": False})
                        result = {**reset_persistent_data(config, memory, broker, reset_symbol), "observer_enabled": False, "config": settings}
                    else:
                        raise ValueError("action must be start, stop, or reset")
                    current = status_store.snapshot()
                    if action == "reset" and not result.get("symbol"):
                        current["cycle"] = {"events": [], "symbols": {}, "agents": {}, "brains": {}}
                    current["config"] = public_config(config)
                    current["paper"] = broker.snapshot()
                    current["memory"] = memory.summary()
                    current.setdefault("bot", {})["scanner_status"] = "running" if config.get("observer_enabled") else "stopped"
                    status_store.update(current)
                    self._send(200, "application/json; charset=utf-8", json.dumps(result).encode("utf-8"))
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(400, "application/json; charset=utf-8", body)
                return

            if request_path == "/api/env-settings":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length).decode("utf-8")
                    payload = json.loads(body or "{}")
                    result = save_env_settings(config, payload, client)
                    self._send(200, "application/json; charset=utf-8", json.dumps(result).encode("utf-8"))
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(400, "application/json; charset=utf-8", body)
                return

            if request_path == "/api/config-json":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length).decode("utf-8")
                    payload = json.loads(body or "{}")
                    if not isinstance(payload, dict):
                        raise ValueError("config must be a JSON object")
                    path = Path(str(config["_config_path"]))
                    existing = json.loads(path.read_text(encoding="utf-8"))
                    existing.update(payload)
                    if existing.get("live_trading_enabled", False):
                        raise ValueError("live_trading_enabled must stay false in this observer")
                    path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
                    config.update(load_config(path))
                    current = status_store.snapshot()
                    current["config"] = public_config(config)
                    status_store.update(current)
                    self._send(200, "application/json; charset=utf-8", json.dumps(existing).encode("utf-8"))
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(400, "application/json; charset=utf-8", body)
                return

            if self.path == "/api/open-setup-file":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length).decode("utf-8")
                    payload = json.loads(body or "{}")
                    result = open_setup_file(config, str(payload.get("target", "env")))
                    self._send(200, "application/json; charset=utf-8", json.dumps(result).encode("utf-8"))
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(400, "application/json; charset=utf-8", body)
                return

            if self.path != "/api/settings":
                self._send(404, "text/plain; charset=utf-8", b"not found")
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                body = self.rfile.read(length).decode("utf-8")
                updates = json.loads(body or "{}")
                settings = update_config_file(config, updates)
                current = status_store.snapshot()
                current["config"] = settings
                status_store.update(current)
                self._send(200, "application/json; charset=utf-8", json.dumps(settings).encode("utf-8"))
            except Exception as exc:
                body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                self._send(400, "application/json; charset=utf-8", body)

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer((host, port), DashboardHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--web", action="store_true", help="host the local dashboard while the observer runs")
    args = parser.parse_args()

    load_dotenv()
    config = load_config(Path(args.config))
    memory = MemoryAgent(Path(config["memory_path"]))
    client = PhemexClient(config["base_url"], env_secret("PHEMEX_API_KEY"), env_secret("PHEMEX_API_SECRET"))
    broker = PaperBroker(config, memory)
    status_store = StatusStore(Path(config["status_path"]))
    status_store.update(
        {
            "bot": {
                "mode": "observer",
                "live_trading_enabled": False,
                "scanner_status": "running" if config.get("observer_enabled") else "stopped",
                "last_update": None,
                "last_update_utc": None,
            },
            "config": public_config(config),
            "account": {
                "status": "unknown",
                "currency": config.get("account_balance_currency", "USDT"),
                "account_balance": None,
                "available_balance_estimate": None,
            },
            "cycle": {
                "market_data": {
                    "phemex_poll_seconds": int(config.get("phemex_poll_seconds", config.get("poll_seconds", 20))),
                    "system_loop_seconds": int(config.get("system_loop_seconds", 1)),
                }
            },
            "paper": broker.snapshot(),
            "memory": memory.summary(),
        }
    )

    print("Phemex agent brain observer started. Live trading is disabled.")
    print(f"Symbols: {', '.join(config['symbols'])}")
    print(f"Timeframes: signal={format_timeframe(config['signal_timeframe_seconds'])} confirmation={format_timeframe(config['confirmation_timeframe_seconds'])}")
    print(f"Loops: phemex={int(config.get('phemex_poll_seconds', config.get('poll_seconds', 20)))}s system={int(config.get('system_loop_seconds', 1))}s")
    if args.web:
        start_dashboard(status_store, config, client, memory, broker, str(config["web_host"]), int(config["web_port"]))
        print(f"Dashboard: http://{config['web_host']}:{config['web_port']}")

    if args.once:
        try:
            run_once(client, broker, memory, status_store, config)
        except Exception as exc:
            print(f"ERROR {type(exc).__name__}: {exc}")
        return

    market_cache = MarketDataCache(config)
    stop_event = threading.Event()
    fetch_thread = threading.Thread(target=run_market_fetch_loop, args=(client, config, market_cache, stop_event), daemon=True)
    fetch_thread.start()

    try:
        while True:
            try:
                process_cached_once(broker, memory, status_store, config, market_cache)
            except Exception as exc:
                print(f"SYSTEM LOOP ERROR {type(exc).__name__}: {exc}")
            time.sleep(max(1, int(config.get("system_loop_seconds", 1))))
    except KeyboardInterrupt:
        stop_event.set()
        fetch_thread.join(timeout=3)


if __name__ == "__main__":
    main()
