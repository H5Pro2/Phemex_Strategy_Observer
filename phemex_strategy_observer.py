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

try:
    import winreg
except ImportError:  # pragma: no cover - Windows-only detail.
    winreg = None

from trade_value_gate import TradeValueGate
from indikator import build_indicator_response
from agent_runtime import build_agent_board, refresh_risk_agent_report
from brain_runtime import apply_economic_gate_to_brain_decision, build_brain_decision, refresh_llm_layer_after_economic_gate
from llm_roles import default_role_team_response, estimate_llm_usage


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
AGENT_DEFAULT_COLORS = {
    "agent_bos_choch_color": "#2dd4bf",
    "agent_box_color": "#22c55e",
    "agent_support_resistance_color": "#60a5fa",
    "agent_swing_labels_color": "#a78bfa",
    "agent_hma_color": "#f59e0b",
    "agent_sma_color": "#38bdf8",
    "agent_triple_ema_color": "#facc15",
    "agent_macd_color": "#fb7185",
    "agent_mfi_color": "#c084fc",
    "agent_rsi_color": "#818cf8",
    "agent_vwap_color": "#14b8a6",
    "agent_breakout_fakeout_color": "#f472b6",
    "agent_volume_color": "#94a3b8",
    "agent_volatility_regime_color": "#fb923c",
    "agent_risk_color": "#f87171",
}
DEFAULT_LLM_ROLE_PROMPT_EXTRAS = {
    "llm_role_market_structure_prompt_extra": "Bewerte nur die Marktstruktur. Achte besonders auf Trendkontext, frische BOS/CHoCH Signale, HH/LL Sequenz, Range-Gefahr und ob der Kandidat nahe an relevanten Strukturzonen liegt. Bei unklarer Range oder widersprüchlicher Struktur eher WAIT statt APPROVE.",
    "llm_role_momentum_prompt_extra": "Bewerte nur Momentum und technische Bestätigung. Achte auf RSI/MFI, MACD, EMA/HMA/VWAP Lage, Volumenimpuls und Divergenzen. APPROVE nur, wenn Momentum die geplante Richtung nachvollziehbar unterstützt; bei spätem oder erschöpftem Move eher WAIT.",
    "llm_role_risk_officer_prompt_extra": "Bewerte Risiko strikt. Prüfe RR, SL-Distanz, Fee/R, Volatilität, offene Trades, Positionsgröße und Overtrading. Setze hard_block=true, wenn Kosten, Stop-Abstand, offene Exponierung oder Volatilität den Trade ungünstig machen.",
    "llm_role_skeptic_prompt_extra": "Suche zuerst aktiv Gründe gegen den Trade. Markiere schwache Annahmen, Datenlücken, Fallback-Setups, zu wenig Live-Historie, Seitwärtsphasen und Widersprüche zwischen Signalquellen. Nur APPROVE, wenn keine wesentlichen Gegenargumente bleiben.",
    "llm_role_execution_prompt_extra": "Bewerte Ausführung und Timing. Prüfe, ob Limit oder Market sinnvoll ist, ob der Entry zu spät kommt, ob der Preis dem Ziel schon zu nahe ist und ob der geplante Entry noch ein gutes Chance/Risiko-Verhältnis bietet.",
    "llm_role_judge_prompt_extra": "Entscheide konservativ als CEO/Judge. Risk Officer und Skeptic Hard-Blocks haben Vorrang. Bei Rollen-Konflikt, schwacher Datenlage oder fehlender klarer Übereinstimmung WAIT. APPROVE nur, wenn Struktur, Momentum, Risiko und Ausführung zusammenpassen.",
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
    trade_size_mode: str = "asset"
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
    LIVE_MEMORY_SOURCE = "paper_trade_close"

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.memory = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"version": 2, "source": "live_paper", "completed_trades": [], "buckets": {}}
        data = json.loads(self.path.read_text(encoding="utf-8"))
        data.setdefault("version", 2)
        data.setdefault("source", "live_paper")
        data.setdefault("completed_trades", [])
        data.setdefault("buckets", {})
        return data

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
            "source": self.LIVE_MEMORY_SOURCE,
            "learned_from": "paper_broker",
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
            "source": self.memory.get("source", "live_paper"),
            "mode": "live_paper_only",
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

    def _trade_payload(self, trade: VirtualTrade) -> dict[str, Any]:
        payload = asdict(trade)
        payload["lifecycle"] = self._trade_lifecycle(trade)
        return payload

    def _trade_lifecycle(self, trade: VirtualTrade) -> dict[str, Any]:
        closed_state = "waiting"
        closed_label = "Exit offen"
        closed_timestamp = None
        if trade.status in ("tp", "sl", "expired"):
            closed_state = "done"
            closed_label = "Take Profit" if trade.status == "tp" else "Stop Loss" if trade.status == "sl" else "Expired"
            closed_timestamp = trade.closed_at

        steps = [
            {"key": "created", "label": "Pending erstellt", "state": "done", "timestamp": trade.created_at},
            {
                "key": "filled",
                "label": "Entry gefüllt" if trade.filled_at else "Wartet auf Entry",
                "state": "done" if trade.filled_at else ("skipped" if trade.status == "expired" else "active"),
                "timestamp": trade.filled_at,
            },
            {"key": "closed", "label": closed_label, "state": closed_state, "timestamp": closed_timestamp},
        ]

        stage_order = {"pending": 1, "open": 2, "tp": 3, "sl": 3, "expired": 3}
        stage_label = {
            "pending": "Pending -> wartet auf Entry",
            "open": "Open -> TP/SL aktiv",
            "tp": "Closed -> Take Profit",
            "sl": "Closed -> Stop Loss",
            "expired": "Closed -> Expired",
        }.get(trade.status, str(trade.status))
        if trade.status == "pending":
            detail = f"Entry {trade.setup.entry} bis Ablauf {trade.expires_at}"
        elif trade.status == "open":
            detail = f"Gefüllt {trade.filled_at} | TP {trade.setup.take_profit} | SL {trade.setup.stop_loss}"
        elif trade.status in ("tp", "sl"):
            detail = f"Exit {trade.exit_price} | R {trade.result_r}"
        else:
            detail = f"Ablauf {trade.closed_at or trade.expires_at}"
        return {
            "current_stage": trade.status,
            "stage_label": stage_label,
            "stage_detail": detail,
            "stage_order": stage_order.get(trade.status, 0),
            "steps": steps,
        }

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
            "trades": [self._trade_payload(trade) for trade in self.trades[-100:]],
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


# --------------------------------------------------
# ASSET LIST FILE
# --------------------------------------------------
def normalize_asset_symbol(value: Any) -> str:
    text = str(value or "").strip().upper().replace(".P", "")
    text = text.split(":", 1)[0]
    return "".join(char for char in text if char.isalnum() or char in ("_", "-"))


def default_asset_symbols(config: dict[str, Any] | None = None) -> list[str]:
    result: list[str] = []
    source_symbols = []
    if isinstance(config, dict):
        source_symbols.extend(config.get("symbols", []) or [])
    source_symbols.extend(item.get("symbol") for item in WATCHLIST_ASSETS if isinstance(item, dict))
    for item in source_symbols:
        symbol = normalize_asset_symbol(item)
        if symbol and symbol not in result:
            result.append(symbol)
    return result or ["BTCUSDT"]


def asset_list_path(config: dict[str, Any], config_path: Path | None = None) -> Path:
    raw_path = Path(str(config.get("asset_list_path", "assets.txt")))
    if raw_path.is_absolute():
        return raw_path
    base_path = config_path.parent if config_path else Path(str(config.get("_config_path", "."))).parent
    return base_path / raw_path


def read_asset_list_file(path: Path, fallback_symbols: list[str]) -> list[str]:
    if not path.exists():
        path.write_text("\n".join(fallback_symbols) + "\n", encoding="utf-8")
    result: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        clean = line.split("#", 1)[0].strip()
        if not clean:
            continue
        symbol = normalize_asset_symbol(clean)
        if symbol and symbol not in result:
            result.append(symbol)
    return result or fallback_symbols


def apply_asset_file_to_config(config: dict[str, Any], config_path: Path | None = None) -> None:
    config.setdefault("asset_list_path", "assets.txt")
    path = asset_list_path(config, config_path)
    fallback = default_asset_symbols(config)
    assets = read_asset_list_file(path, fallback)
    config["asset_list_path"] = str(config.get("asset_list_path", "assets.txt"))
    config["asset_list"] = assets
    config["watchlist_assets"] = [{"label": symbol, "symbol": symbol} for symbol in assets]
    active_symbols: list[str] = []
    for symbol in config.get("symbols", []) or []:
        clean = normalize_asset_symbol(symbol)
        if clean and clean not in active_symbols:
            active_symbols.append(clean)
    if not active_symbols:
        active_symbols = assets[:1]
    if config.get("observer_asset_mode") == "single":
        active_symbols = active_symbols[:1]
    config["symbols"] = active_symbols


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    config["base_url"] = os.getenv("PHEMEX_BASE_URL", config.get("base_url", "https://api.phemex.com"))
    config["_config_path"] = str(path)
    config.setdefault("paper_trading_enabled", True)
    config.setdefault("observer_enabled", False)
    config["observer_enabled"] = False
    config.setdefault("observer_asset_mode", "single")
    config.setdefault("max_open_trades_total", 3)
    config.setdefault("max_open_trades_per_asset", 1)
    config.setdefault("pause_entry_search_while_order_active", True)
    config.setdefault("block_same_direction_correlated_trades", True)
    config.setdefault("stop_loss_mode", "structure")
    config.setdefault("stop_loss_percent", 0.25)
    config.setdefault("stop_loss_buffer_percent", 0.0)
    config.setdefault("stop_loss_atr_period", 14)
    config.setdefault("stop_loss_atr_multiplier", 1.5)
    config.setdefault("risk_unit", 1.0)
    config.setdefault("min_rr", 0.0)
    config.setdefault("min_tp_distance_fraction", 0.0)
    config.setdefault("max_sl_distance_fraction", 0.0)
    config.setdefault("max_sl_distance_fraction_by_symbol", {})
    config.setdefault("estimated_taker_fee_rate", 0.0006)
    config.setdefault("max_fee_to_risk_fraction", 0.25)
    config.setdefault("min_net_profit_fraction", 0.001)
    config.setdefault("min_net_profit_fraction_by_symbol", {})
    config.setdefault("poll_seconds", 30)
    config.setdefault("phemex_poll_seconds", config.get("poll_seconds", 30))
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
    config.setdefault("take_profit_mode", "reward_risk")
    config.setdefault("allow_reward_risk_fallback_tp", True)
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
    apply_asset_file_to_config(config, path)
    config.setdefault("trade_size_mode", "asset")
    config.setdefault("trade_size_usd", 0.0)
    config.setdefault("trade_size_asset", 0.0)
    config.setdefault("trade_sizes_by_symbol", {})
    if (
        not config.get("trade_sizes_by_symbol")
        and config.get("trade_size_mode") == "usd"
        and float(config.get("trade_size_usd") or 0.0) == 100.0
        and float(config.get("trade_size_asset") or 0.0) == 0.001
    ):
        config["trade_size_mode"] = "asset"
        config["trade_size_usd"] = 0.0
        config["trade_size_asset"] = 0.0
    config.setdefault("account_balance_currency", "USDT")
    config.setdefault("status_path", "data/runtime_status.json")
    config.setdefault("web_host", "127.0.0.1")
    config.setdefault("web_port", 8787)
    config.setdefault("ui_theme", "dark")
    config.setdefault("ui_language", "de")
    config.setdefault("indicator_enabled", True)
    config.setdefault("indicator_show_bos_choch", True)
    config.setdefault("indicator_show_boxes", True)
    config.setdefault("indicator_show_swing_labels", True)
    config.setdefault("indicator_show_hma", False)
    config.setdefault("indicator_show_sma", True)
    config.setdefault("indicator_show_triple_ema", False)
    config.setdefault("indicator_show_mfi", True)
    config.setdefault("indicator_show_macd", True)
    config.setdefault("indicator_show_support_resistance", True)
    config.setdefault("indicator_swing_size", 5)
    config.setdefault("indicator_hhll_range", 50)
    config.setdefault("indicator_hma_period", 20)
    config.setdefault("indicator_sma_period", 50)
    config.setdefault("indicator_triple_ema_period", 20)
    config.setdefault("indicator_triple_ema_slow_period", 50)
    config.setdefault("indicator_mfi_period", 14)
    config.setdefault("indicator_macd_fast_period", 12)
    config.setdefault("indicator_macd_slow_period", 26)
    config.setdefault("indicator_macd_signal_period", 9)
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
    config.setdefault("indicator_macd_lookback_days", 0)
    config.setdefault("indicator_lookback_days", legacy_indicator_lookback_days)
    config.setdefault("indicator_bos_confirmation", "Wicks")
    config.setdefault("chart_candle_up_color", "#047857")
    config.setdefault("chart_candle_down_color", "#b42318")
    config.setdefault("chart_candle_no_change_color", "#667085")
    config.setdefault("chart_candle_wick_up_color", config.get("chart_candle_up_color", "#047857"))
    config.setdefault("chart_candle_wick_down_color", config.get("chart_candle_down_color", "#b42318"))
    config.setdefault("chart_candle_wick_no_change_color", config.get("chart_candle_no_change_color", "#667085"))
    config.setdefault("chart_candle_border_up_color", config.get("chart_candle_up_color", "#047857"))
    config.setdefault("chart_candle_border_down_color", config.get("chart_candle_down_color", "#b42318"))
    config.setdefault("chart_candle_border_no_change_color", config.get("chart_candle_no_change_color", "#667085"))
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
    config.setdefault("indicator_macd_color", "#0ea5e9")
    config.setdefault("indicator_macd_signal_color", "#f97316")
    config.setdefault("indicator_macd_histogram_color", "#64748b")
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
    config.setdefault("agent_macd_enabled", True)
    config.setdefault("agent_macd_weight", 1.0)
    config.setdefault("agent_macd_min_score", 0)
    config.setdefault("agent_macd_blocking", False)
    config.setdefault("agent_mfi_enabled", True)
    config.setdefault("agent_mfi_period", 14)
    config.setdefault("agent_mfi_weight", 1.0)
    config.setdefault("agent_mfi_min_score", 0)
    config.setdefault("agent_mfi_blocking", False)
    config.setdefault("agent_rsi_enabled", True)
    config.setdefault("agent_rsi_period", 14)
    config.setdefault("agent_rsi_weight", 1.0)
    config.setdefault("agent_rsi_min_score", 0)
    config.setdefault("agent_rsi_blocking", False)
    config.setdefault("agent_vwap_enabled", True)
    config.setdefault("agent_vwap_lookback_candles", 96)
    config.setdefault("agent_vwap_weight", 1.0)
    config.setdefault("agent_vwap_min_score", 0)
    config.setdefault("agent_vwap_blocking", False)
    config.setdefault("agent_breakout_fakeout_enabled", True)
    config.setdefault("agent_breakout_fakeout_lookback", 20)
    config.setdefault("agent_breakout_fakeout_weight", 1.0)
    config.setdefault("agent_breakout_fakeout_min_score", 0)
    config.setdefault("agent_breakout_fakeout_blocking", False)
    config.setdefault("agent_volume_enabled", True)
    config.setdefault("agent_volume_period", 20)
    config.setdefault("agent_volume_weight", 1.0)
    config.setdefault("agent_volume_min_score", 0)
    config.setdefault("agent_volume_blocking", False)
    config.setdefault("agent_volatility_regime_enabled", True)
    config.setdefault("agent_volatility_atr_period", 14)
    config.setdefault("agent_volatility_lookback", 50)
    config.setdefault("agent_volatility_regime_weight", 1.0)
    config.setdefault("agent_volatility_regime_min_score", 0)
    config.setdefault("agent_volatility_regime_blocking", False)
    config.setdefault("agent_risk_enabled", True)
    config.setdefault("agent_risk_weight", 1.0)
    config.setdefault("agent_risk_min_score", 0)
    config.setdefault("agent_risk_blocking", False)
    for key, color in AGENT_DEFAULT_COLORS.items():
        config.setdefault(key, color)
    config.setdefault("trade_decision_mode", "brain")
    config.setdefault("brain_enabled", True)
    config.setdefault("brain_min_score", 58)
    config.setdefault("brain_min_score_gap", 18)
    config.setdefault("brain_min_agent_alignment", 2)
    config.setdefault("brain_memory_min_count", 3)
    config.setdefault("brain_entry_box_offset", 0.35)
    config.setdefault("brain_target_lookback_candles", 36)
    config.setdefault("brain_stop_lookback_candles", 8)
    config.setdefault("brain_allow_rr_target_fallback", False)
    config.setdefault("brain_cap_target_to_max_rr", True)
    config.setdefault("brain_max_target_rr", float(config.get("reward_risk", 1.5)))
    config.setdefault("brain_llm_layer_enabled", True)
    config.setdefault("llm_role_team_enabled", True)
    config.setdefault("llm_provider", "ollama")
    config.setdefault("openai_enabled", False)
    config.setdefault("openai_model", "gpt-4.1-mini")
    config.setdefault("openai_timeout_seconds", 30)
    config["llm_role_timeout_seconds"] = int(config.get("phemex_poll_seconds", config.get("poll_seconds", 30)))
    config.setdefault("llm_role_temperature", 0.0)
    config.setdefault("llm_role_required_for_trade", False)
    config.setdefault("llm_role_market_structure_enabled", True)
    config.setdefault("llm_role_momentum_enabled", True)
    config.setdefault("llm_role_risk_officer_enabled", True)
    config.setdefault("llm_role_skeptic_enabled", True)
    config.setdefault("llm_role_execution_enabled", True)
    for key, default_prompt in DEFAULT_LLM_ROLE_PROMPT_EXTRAS.items():
        if not str(config.get(key, "")).strip():
            config[key] = default_prompt
    config.setdefault("ollama_enabled", True)
    config.setdefault("ollama_base_url", "http://127.0.0.1:11434")
    config.setdefault("ollama_model", "qwen2.5:3b")
    config.setdefault("ollama_timeout_seconds", 120)
    config.setdefault("ollama_max_prompt_chars", 2000)
    config.setdefault("ollama_temperature", 0.0)
    config.setdefault("ollama_block_hint_enabled", False)
    config.setdefault("replay_rule_weight_enabled", False)
    config.setdefault("replay_rule_weight_rules", [])
    config.setdefault("replay_rule_scope", "asset")
    config.setdefault("replay_rule_weight_min_count", 5)
    config.setdefault("replay_rule_good_bonus", 6)
    config.setdefault("replay_rule_bad_penalty", -10)
    config.setdefault("replay_rule_max_abs_adjustment", 12)
    config.setdefault("replay_pnl_enabled", True)
    config.setdefault("replay_pnl_currency", str(config.get("account_balance_currency", "USDT")))
    config.setdefault("replay_history_max_runs", 120)
    config.setdefault("replay_max_steps", 750)
    config.setdefault("replay_kline_limit_max", 1000)
    config.setdefault("replay_frame_display_limit", 120)
    config.setdefault("replay_response_frame_limit", 160)
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
        "stop_loss_atr_period",
        "stop_loss_atr_multiplier",
        "risk_unit",
        "min_rr",
        "min_tp_distance_fraction",
        "max_sl_distance_fraction",
        "max_sl_distance_fraction_by_symbol",
        "estimated_taker_fee_rate",
        "max_fee_to_risk_fraction",
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
        "ui_language",
        "indicator_enabled",
        "indicator_show_bos_choch",
        "indicator_show_boxes",
        "indicator_show_swing_labels",
        "indicator_show_hma",
        "indicator_show_sma",
        "indicator_show_triple_ema",
        "indicator_show_mfi",
        "indicator_show_macd",
        "indicator_show_support_resistance",
        "indicator_swing_size",
        "indicator_hhll_range",
        "indicator_hma_period",
        "indicator_sma_period",
        "indicator_triple_ema_period",
        "indicator_triple_ema_slow_period",
        "indicator_mfi_period",
        "indicator_macd_fast_period",
        "indicator_macd_slow_period",
        "indicator_macd_signal_period",
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
        "indicator_macd_lookback_days",
        "indicator_lookback_days",
        "indicator_bos_confirmation",
        "chart_candle_up_color",
        "chart_candle_down_color",
        "chart_candle_no_change_color",
        "chart_candle_wick_up_color",
        "chart_candle_wick_down_color",
        "chart_candle_wick_no_change_color",
        "chart_candle_border_up_color",
        "chart_candle_border_down_color",
        "chart_candle_border_no_change_color",
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
        "indicator_macd_color",
        "indicator_macd_signal_color",
        "indicator_macd_histogram_color",
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
        "agent_macd_enabled",
        "agent_macd_weight",
        "agent_macd_min_score",
        "agent_macd_blocking",
        "agent_mfi_enabled",
        "agent_mfi_period",
        "agent_mfi_weight",
        "agent_mfi_min_score",
        "agent_mfi_blocking",
        "agent_rsi_enabled",
        "agent_rsi_period",
        "agent_rsi_weight",
        "agent_rsi_min_score",
        "agent_rsi_blocking",
        "agent_vwap_enabled",
        "agent_vwap_lookback_candles",
        "agent_vwap_weight",
        "agent_vwap_min_score",
        "agent_vwap_blocking",
        "agent_breakout_fakeout_enabled",
        "agent_breakout_fakeout_lookback",
        "agent_breakout_fakeout_weight",
        "agent_breakout_fakeout_min_score",
        "agent_breakout_fakeout_blocking",
        "agent_volume_enabled",
        "agent_volume_period",
        "agent_volume_weight",
        "agent_volume_min_score",
        "agent_volume_blocking",
        "agent_volatility_regime_enabled",
        "agent_volatility_atr_period",
        "agent_volatility_lookback",
        "agent_volatility_regime_weight",
        "agent_volatility_regime_min_score",
        "agent_volatility_regime_blocking",
        "agent_risk_enabled",
        "agent_risk_weight",
        "agent_risk_min_score",
        "agent_risk_blocking",
        "agent_bos_choch_color",
        "agent_box_color",
        "agent_support_resistance_color",
        "agent_swing_labels_color",
        "agent_hma_color",
        "agent_sma_color",
        "agent_triple_ema_color",
        "agent_macd_color",
        "agent_mfi_color",
        "agent_rsi_color",
        "agent_vwap_color",
        "agent_breakout_fakeout_color",
        "agent_volume_color",
        "agent_volatility_regime_color",
        "agent_risk_color",
        "trade_decision_mode",
        "brain_enabled",
        "brain_min_score",
        "brain_min_score_gap",
        "brain_min_agent_alignment",
        "brain_memory_min_count",
        "brain_entry_box_offset",
        "brain_target_lookback_candles",
        "brain_stop_lookback_candles",
        "brain_allow_rr_target_fallback",
        "brain_cap_target_to_max_rr",
        "brain_max_target_rr",
        "brain_llm_layer_enabled",
        "llm_role_team_enabled",
        "llm_provider",
        "openai_enabled",
        "openai_model",
        "openai_timeout_seconds",
        "llm_role_timeout_seconds",
        "llm_role_temperature",
        "llm_role_required_for_trade",
        "llm_role_market_structure_enabled",
        "llm_role_momentum_enabled",
        "llm_role_risk_officer_enabled",
        "llm_role_skeptic_enabled",
        "llm_role_execution_enabled",
        "llm_role_market_structure_prompt_extra",
        "llm_role_momentum_prompt_extra",
        "llm_role_risk_officer_prompt_extra",
        "llm_role_skeptic_prompt_extra",
        "llm_role_execution_prompt_extra",
        "llm_role_judge_prompt_extra",
        "ollama_enabled",
        "ollama_base_url",
        "ollama_model",
        "ollama_timeout_seconds",
        "ollama_max_prompt_chars",
        "ollama_temperature",
        "ollama_block_hint_enabled",
        "replay_rule_weight_enabled",
        "replay_rule_weight_rules",
        "replay_rule_scope",
        "replay_rule_weight_min_count",
        "replay_rule_good_bonus",
        "replay_rule_bad_penalty",
        "replay_rule_max_abs_adjustment",
        "replay_pnl_enabled",
        "replay_pnl_currency",
        "replay_history_max_runs",
        "replay_max_steps",
        "replay_kline_limit_max",
        "replay_frame_display_limit",
        "replay_response_frame_limit",
        "asset_list_path",
        "asset_list",
    ]
    result = {key: config.get(key) for key in keys}
    result["watchlist_assets"] = config.get("watchlist_assets", WATCHLIST_ASSETS)
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
        "stop_loss_atr_period",
        "stop_loss_atr_multiplier",
        "risk_unit",
        "min_rr",
        "min_tp_distance_fraction",
        "max_sl_distance_fraction",
        "max_sl_distance_fraction_by_symbol",
        "estimated_taker_fee_rate",
        "max_fee_to_risk_fraction",
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
        "ui_language",
        "indicator_enabled",
        "indicator_show_bos_choch",
        "indicator_show_boxes",
        "indicator_show_swing_labels",
        "indicator_show_hma",
        "indicator_show_sma",
        "indicator_show_triple_ema",
        "indicator_show_mfi",
        "indicator_show_macd",
        "indicator_show_support_resistance",
        "indicator_swing_size",
        "indicator_hhll_range",
        "indicator_hma_period",
        "indicator_sma_period",
        "indicator_triple_ema_period",
        "indicator_triple_ema_slow_period",
        "indicator_mfi_period",
        "indicator_macd_fast_period",
        "indicator_macd_slow_period",
        "indicator_macd_signal_period",
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
        "indicator_macd_lookback_days",
        "indicator_lookback_days",
        "indicator_bos_confirmation",
        "chart_candle_up_color",
        "chart_candle_down_color",
        "chart_candle_no_change_color",
        "chart_candle_wick_up_color",
        "chart_candle_wick_down_color",
        "chart_candle_wick_no_change_color",
        "chart_candle_border_up_color",
        "chart_candle_border_down_color",
        "chart_candle_border_no_change_color",
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
        "indicator_macd_color",
        "indicator_macd_signal_color",
        "indicator_macd_histogram_color",
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
        "agent_macd_enabled",
        "agent_macd_weight",
        "agent_macd_min_score",
        "agent_macd_blocking",
        "agent_mfi_enabled",
        "agent_mfi_period",
        "agent_mfi_weight",
        "agent_mfi_min_score",
        "agent_mfi_blocking",
        "agent_rsi_enabled",
        "agent_rsi_period",
        "agent_rsi_weight",
        "agent_rsi_min_score",
        "agent_rsi_blocking",
        "agent_vwap_enabled",
        "agent_vwap_lookback_candles",
        "agent_vwap_weight",
        "agent_vwap_min_score",
        "agent_vwap_blocking",
        "agent_breakout_fakeout_enabled",
        "agent_breakout_fakeout_lookback",
        "agent_breakout_fakeout_weight",
        "agent_breakout_fakeout_min_score",
        "agent_breakout_fakeout_blocking",
        "agent_volume_enabled",
        "agent_volume_period",
        "agent_volume_weight",
        "agent_volume_min_score",
        "agent_volume_blocking",
        "agent_volatility_regime_enabled",
        "agent_volatility_atr_period",
        "agent_volatility_lookback",
        "agent_volatility_regime_weight",
        "agent_volatility_regime_min_score",
        "agent_volatility_regime_blocking",
        "agent_risk_enabled",
        "agent_risk_weight",
        "agent_risk_min_score",
        "agent_risk_blocking",
        "agent_bos_choch_color",
        "agent_box_color",
        "agent_support_resistance_color",
        "agent_swing_labels_color",
        "agent_hma_color",
        "agent_sma_color",
        "agent_triple_ema_color",
        "agent_macd_color",
        "agent_mfi_color",
        "agent_rsi_color",
        "agent_vwap_color",
        "agent_breakout_fakeout_color",
        "agent_volume_color",
        "agent_volatility_regime_color",
        "agent_risk_color",
        "trade_decision_mode",
        "brain_enabled",
        "brain_min_score",
        "brain_min_score_gap",
        "brain_min_agent_alignment",
        "brain_memory_min_count",
        "brain_entry_box_offset",
        "brain_target_lookback_candles",
        "brain_stop_lookback_candles",
        "brain_allow_rr_target_fallback",
        "brain_cap_target_to_max_rr",
        "brain_max_target_rr",
        "brain_llm_layer_enabled",
        "llm_role_team_enabled",
        "llm_provider",
        "openai_enabled",
        "openai_model",
        "openai_timeout_seconds",
        "llm_role_timeout_seconds",
        "llm_role_temperature",
        "llm_role_required_for_trade",
        "llm_role_market_structure_enabled",
        "llm_role_momentum_enabled",
        "llm_role_risk_officer_enabled",
        "llm_role_skeptic_enabled",
        "llm_role_execution_enabled",
        "llm_role_market_structure_prompt_extra",
        "llm_role_momentum_prompt_extra",
        "llm_role_risk_officer_prompt_extra",
        "llm_role_skeptic_prompt_extra",
        "llm_role_execution_prompt_extra",
        "llm_role_judge_prompt_extra",
        "ollama_enabled",
        "ollama_base_url",
        "ollama_model",
        "ollama_timeout_seconds",
        "ollama_max_prompt_chars",
        "ollama_temperature",
        "ollama_block_hint_enabled",
        "replay_rule_weight_enabled",
        "replay_rule_weight_rules",
        "replay_rule_scope",
        "replay_rule_weight_min_count",
        "replay_rule_good_bonus",
        "replay_rule_bad_penalty",
        "replay_rule_max_abs_adjustment",
    }
    color_keys = {
        "chart_candle_up_color",
        "chart_candle_down_color",
        "chart_candle_no_change_color",
        "chart_candle_wick_up_color",
        "chart_candle_wick_down_color",
        "chart_candle_wick_no_change_color",
        "chart_candle_border_up_color",
        "chart_candle_border_down_color",
        "chart_candle_border_no_change_color",
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
        "indicator_macd_color",
        "indicator_macd_signal_color",
        "indicator_macd_histogram_color",
        "indicator_sr_source",
        "indicator_sr_support_color",
        "indicator_sr_resistance_color",
        "agent_bos_choch_color",
        "agent_box_color",
        "agent_support_resistance_color",
        "agent_swing_labels_color",
        "agent_hma_color",
        "agent_sma_color",
        "agent_triple_ema_color",
        "agent_macd_color",
        "agent_mfi_color",
        "agent_rsi_color",
        "agent_vwap_color",
        "agent_breakout_fakeout_color",
        "agent_volume_color",
        "agent_volatility_regime_color",
        "agent_risk_color",
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
            elif key == "ui_language":
                value = str(value).lower()
                if value not in ("de", "en"):
                    raise ValueError("ui_language must be de or en")
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
            elif key in ("use_trend_filter", "block_same_direction_correlated_trades", "single_timeframe_mode", "daily_bias_blocks_against_direction", "allow_reward_risk_fallback_tp", "indicator_enabled", "indicator_show_bos_choch", "indicator_show_boxes", "indicator_show_swing_labels", "indicator_show_hma", "indicator_show_sma", "indicator_show_triple_ema", "indicator_show_mfi", "indicator_show_macd", "indicator_show_support_resistance", "agent_show_offline_agents", "agent_bos_choch_enabled", "agent_bos_choch_blocking", "agent_box_enabled", "agent_box_blocking", "agent_support_resistance_enabled", "agent_support_resistance_blocking", "agent_swing_labels_enabled", "agent_swing_labels_blocking", "agent_hma_enabled", "agent_hma_blocking", "agent_sma_enabled", "agent_sma_blocking", "agent_triple_ema_enabled", "agent_triple_ema_blocking", "agent_macd_enabled", "agent_macd_blocking", "agent_mfi_enabled", "agent_mfi_blocking", "agent_rsi_enabled", "agent_rsi_blocking", "agent_vwap_enabled", "agent_vwap_blocking", "agent_breakout_fakeout_enabled", "agent_breakout_fakeout_blocking", "agent_volume_enabled", "agent_volume_blocking", "agent_volatility_regime_enabled", "agent_volatility_regime_blocking", "agent_risk_enabled", "agent_risk_blocking", "brain_enabled", "brain_allow_rr_target_fallback", "brain_cap_target_to_max_rr", "brain_llm_layer_enabled", "llm_role_team_enabled", "llm_role_required_for_trade", "openai_enabled", "llm_role_market_structure_enabled", "llm_role_momentum_enabled", "llm_role_risk_officer_enabled", "llm_role_skeptic_enabled", "llm_role_execution_enabled", "ollama_enabled", "ollama_block_hint_enabled", "replay_rule_weight_enabled"):
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
                if value not in ("structure", "atr", "fixed_percent"):
                    raise ValueError("stop_loss_mode must be structure, atr, or fixed_percent")
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
            elif key == "llm_provider":
                value = str(value).strip().lower()
                if value not in ("openai", "ollama"):
                    raise ValueError("llm_provider must be openai or ollama")
                clean[key] = value
            elif key == "openai_model":
                value = str(value).strip()
                if not value:
                    raise ValueError("openai_model must not be empty")
                clean[key] = value
            elif key in DEFAULT_LLM_ROLE_PROMPT_EXTRAS:
                prompt = str(value or "").strip()
                clean[key] = (prompt or DEFAULT_LLM_ROLE_PROMPT_EXTRAS[key])[:1600]
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
            elif key in ("indicator_lookback_days", "indicator_bos_choch_lookback_days", "indicator_boxes_lookback_days", "indicator_swing_labels_lookback_days", "indicator_hma_lookback_days", "indicator_sma_lookback_days", "indicator_triple_ema_lookback_days", "indicator_mfi_lookback_days", "indicator_macd_lookback_days"):
                value = int(value)
                if value < 0:
                    raise ValueError(f"{key} must be non-negative")
                clean[key] = value
            elif key in ("signal_timeframe_seconds", "confirmation_timeframe_seconds", "poll_seconds", "phemex_poll_seconds", "system_loop_seconds", "kline_limit", "trend_ema_period", "max_open_trades_total", "max_open_trades_per_asset", "structure_lookback_candles", "structure_pivot_strength", "entry_search_confirmation_candles", "supply_demand_max_base_candles", "supply_demand_max_zone_retests", "swing_lookback_candles", "swing_pivot_strength", "swing_reaction_lookback_candles", "indicator_swing_size", "indicator_hhll_range", "indicator_hma_period", "indicator_sma_period", "indicator_triple_ema_period", "indicator_triple_ema_slow_period", "indicator_mfi_period", "indicator_macd_fast_period", "indicator_macd_slow_period", "indicator_macd_signal_period", "indicator_sr_pivot_period", "indicator_sr_max_pivots", "indicator_sr_channel_width_percent", "indicator_sr_max_levels", "indicator_sr_min_strength", "indicator_box_extend_candles", "agent_bos_choch_min_score", "agent_box_min_score", "agent_swing_labels_min_score", "agent_hma_min_score", "agent_sma_period", "agent_sma_min_score", "agent_triple_ema_min_score", "agent_macd_min_score", "agent_mfi_period", "agent_mfi_min_score", "agent_rsi_period", "agent_rsi_min_score", "agent_vwap_lookback_candles", "agent_vwap_min_score", "agent_breakout_fakeout_lookback", "agent_breakout_fakeout_min_score", "agent_volume_period", "agent_volume_min_score", "agent_volatility_atr_period", "agent_volatility_lookback", "agent_volatility_regime_min_score", "agent_risk_min_score", "brain_min_score", "brain_min_score_gap", "brain_min_agent_alignment", "brain_memory_min_count", "brain_target_lookback_candles", "brain_stop_lookback_candles", "stop_loss_atr_period", "openai_timeout_seconds", "llm_role_timeout_seconds", "ollama_timeout_seconds", "ollama_max_prompt_chars", "replay_rule_weight_min_count", "replay_rule_good_bonus", "replay_rule_bad_penalty", "replay_rule_max_abs_adjustment", "replay_history_max_runs", "replay_max_steps", "replay_kline_limit_max", "replay_frame_display_limit", "replay_response_frame_limit"):
                value = int(value)
                if key == "replay_rule_bad_penalty":
                    if value > 0:
                        raise ValueError("replay_rule_bad_penalty must be zero or negative")
                elif value < 0 or key not in ("agent_bos_choch_min_score", "agent_box_min_score", "agent_support_resistance_min_score", "agent_swing_labels_min_score", "agent_hma_min_score", "agent_sma_min_score", "agent_triple_ema_min_score", "agent_macd_min_score", "agent_mfi_min_score", "agent_rsi_min_score", "agent_vwap_min_score", "agent_breakout_fakeout_min_score", "agent_volume_min_score", "agent_volatility_regime_min_score", "agent_risk_min_score") and value <= 0:
                    raise ValueError(f"{key} must be positive")
                clean[key] = value
            elif key in ("agent_bos_choch_weight", "agent_box_weight", "agent_support_resistance_weight", "agent_swing_labels_weight", "agent_hma_weight", "agent_sma_weight", "agent_triple_ema_weight", "agent_macd_weight", "agent_mfi_weight", "agent_rsi_weight", "agent_vwap_weight", "agent_breakout_fakeout_weight", "agent_volume_weight", "agent_volatility_regime_weight", "agent_risk_weight", "stop_loss_atr_multiplier", "brain_entry_box_offset", "brain_max_target_rr", "llm_role_temperature", "ollama_temperature", "max_fee_to_risk_fraction"):
                value = float(value)
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f"{key} must be a non-negative number")
                clean[key] = value
            elif key == "replay_rule_weight_rules":
                if not isinstance(value, list):
                    raise ValueError("replay_rule_weight_rules must be a list")
                clean_rules: list[dict[str, Any]] = []
                for rule in value[:50]:
                    if not isinstance(rule, dict):
                        continue
                    key_value = str(rule.get("key", "")).strip()
                    if not key_value:
                        continue
                    quality = str(rule.get("quality", "WATCH")).upper()
                    if quality not in ("GOOD", "BAD", "WATCH"):
                        quality = "WATCH"
                    clean_rules.append({
                        "key": key_value,
                        "quality": quality,
                        "count": int(rule.get("count") or 0),
                        "win_rate": rule.get("win_rate"),
                        "avg_r": rule.get("avg_r"),
                        "sum_r": rule.get("sum_r"),
                    })
                clean[key] = clean_rules
            elif key in ("min_net_profit_fraction_by_symbol", "max_sl_distance_fraction_by_symbol"):
                if not isinstance(value, dict):
                    raise ValueError(f"{key} must be an object")
                clean_values: dict[str, float] = {}
                for raw_symbol, raw_fraction in value.items():
                    symbol = str(raw_symbol).replace(".P", "").split(":", 1)[0].strip().upper()
                    if not symbol:
                        continue
                    fraction = float(raw_fraction)
                    if not math.isfinite(fraction) or fraction < 0:
                        raise ValueError(f"{key} for {symbol} must be a non-negative number")
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
    clean["llm_role_timeout_seconds"] = int(clean.get("phemex_poll_seconds", clean.get("poll_seconds", config.get("phemex_poll_seconds", config.get("poll_seconds", 30)))))

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


def openai_error_payload(response: requests.Response) -> dict[str, Any]:
    status_code = int(response.status_code)
    message = response.text.strip()[:500] if response.text else f"HTTP {status_code}"
    error_type = ""
    error_code = ""
    try:
        data = response.json()
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message") or message)
            error_type = str(error.get("type") or "")
            error_code = str(error.get("code") or "")
    except ValueError:
        pass

    status = "http_error"
    user_reason = f"OpenAI Test fehlgeschlagen: HTTP {status_code}. {message}"
    if status_code in (401, 403):
        status = "auth_failed"
        user_reason = f"OpenAI Key wurde abgelehnt: {message}"
    elif status_code == 429 and (error_code == "insufficient_quota" or "quota" in message.lower()):
        status = "insufficient_quota"
        user_reason = "Kein OpenAI API-Guthaben oder Projekt-Budget verfügbar. Bitte Billing/Guthaben in der OpenAI Platform prüfen."
    elif status_code == 429:
        status = "rate_limited"
        user_reason = f"OpenAI Rate Limit erreicht: {message}"

    return {
        "ok": False,
        "reason": user_reason,
        "status": status,
        "http_status": status_code,
        "api_message": message,
        "api_error_type": error_type,
        "api_error_code": error_code,
        "popup": status in {"insufficient_quota", "auth_failed", "rate_limited", "http_error"},
    }


def strategy_path(config: dict[str, Any]) -> Path:
    return Path(str(config["_config_path"])).with_name("strategy.md")


def read_strategy_markdown(config: dict[str, Any]) -> dict[str, Any]:
    path = strategy_path(config)
    if not path.exists():
        path.write_text(
            "# Strategie-Regelwerk\n\n"
            "## Setup\n\n"
            "Die höhere Zeiteinheit sucht Supply- und Demand-Zonen aus Base + impulsivem Abgang. "
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
    openai_key = values.get("OPENAI_API_KEY", "")
    return {
        "base_url": values.get("PHEMEX_BASE_URL", config.get("base_url", "https://api.phemex.com")),
        "api_key_present": bool(api_key),
        "api_key_preview": f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "",
        "api_secret_present": bool(secret),
        "api_secret_preview": f"{secret[:4]}...{secret[-4:]}" if len(secret) > 8 else "",
        "openai_key_present": bool(openai_key),
        "openai_key_preview": f"{openai_key[:7]}...{openai_key[-4:]}" if len(openai_key) > 12 else "",
    }


def save_env_settings(config: dict[str, Any], updates: dict[str, Any], client: PhemexClient) -> dict[str, Any]:
    current = read_env_settings(config)
    base_url = str(updates.get("base_url") or current["base_url"]).strip()
    api_key = str(updates.get("api_key") or "").strip()
    api_secret = str(updates.get("api_secret") or "").strip()
    openai_key = str(updates.get("openai_api_key") or "").strip()

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
    if openai_key:
        existing["OPENAI_API_KEY"] = openai_key
    existing["PHEMEX_BASE_URL"] = base_url

    ordered = ["PHEMEX_BASE_URL", "PHEMEX_API_KEY", "PHEMEX_API_SECRET", "OPENAI_API_KEY"]
    remaining = [key for key in existing.keys() if key not in ordered]
    path.write_text("\n".join(f"{key}={existing.get(key, '')}" for key in ordered + remaining) + "\n", encoding="utf-8")

    os.environ["PHEMEX_BASE_URL"] = base_url
    if existing.get("PHEMEX_API_KEY"):
        os.environ["PHEMEX_API_KEY"] = existing["PHEMEX_API_KEY"]
    if existing.get("PHEMEX_API_SECRET"):
        os.environ["PHEMEX_API_SECRET"] = existing["PHEMEX_API_SECRET"]
    if existing.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = existing["OPENAI_API_KEY"]
    config["base_url"] = base_url
    client.base_url = base_url.rstrip("/")
    client.api_key = env_secret("PHEMEX_API_KEY")
    client.api_secret = env_secret("PHEMEX_API_SECRET")
    return read_env_settings(config)


def test_openai_connection(config: dict[str, Any]) -> dict[str, Any]:
    key = env_secret("OPENAI_API_KEY")
    if not key:
        return {"ok": False, "reason": "OPENAI_API_KEY fehlt.", "status": "missing_key", "popup": True}
    try:
        model = str(config.get("openai_model", "gpt-4.1-mini"))
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "model": model,
                "temperature": 0,
                "max_tokens": 8,
                "messages": [
                    {"role": "system", "content": "Antworte kurz."},
                    {"role": "user", "content": "Sag OK."},
                ],
            },
            timeout=10,
        )
        if response.status_code == 200:
            return {"ok": True, "reason": f"OpenAI Verbindung erfolgreich ({model}).", "status": "ok", "popup": False}
        return openai_error_payload(response)
    except requests.RequestException as exc:
        return {"ok": False, "reason": f"OpenAI nicht erreichbar: {type(exc).__name__}.", "status": "network_error", "popup": True}


def test_ollama_connection(config: dict[str, Any]) -> dict[str, Any]:
    base_url = str(config.get("ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
    model = str(config.get("ollama_model", "qwen2.5:3b")).strip() or "qwen2.5:3b"
    timeout = max(1.0, min(180.0, float(config.get("ollama_timeout_seconds", 60) or 60)))
    try:
        tags_response = requests.get(f"{base_url}/api/tags", timeout=min(5.0, timeout))
        if tags_response.status_code != 200:
            return {
                "ok": False,
                "reason": f"Ollama erreichbar, aber /api/tags meldet HTTP {tags_response.status_code}.",
                "status": "http_error",
                "base_url": base_url,
                "model": model,
            }
        tags = tags_response.json()
        models = [
            str(item.get("name") or item.get("model") or "")
            for item in (tags.get("models") if isinstance(tags, dict) else []) or []
            if isinstance(item, dict)
        ]
        if models and model not in models:
            return {
                "ok": False,
                "reason": f"Ollama läuft, aber Modell {model} ist nicht geladen. Verfügbar: {', '.join(models[:8])}.",
                "status": "model_missing",
                "base_url": base_url,
                "model": model,
                "available_models": models,
            }
        payload = {
            "model": model,
            "prompt": '{"task":"Antworte nur mit JSON: {\\"ok\\": true}"}',
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        response = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
        if response.status_code != 200:
            return {
                "ok": False,
                "reason": f"Ollama Generate fehlgeschlagen: HTTP {response.status_code}.",
                "status": "generate_failed",
                "base_url": base_url,
                "model": model,
            }
        generated = response.json()
        text = str(generated.get("response", "")).strip()
        try:
            parsed = json.loads(text or "{}")
            if not isinstance(parsed, dict):
                raise ValueError("not an object")
        except ValueError:
            return {
                "ok": False,
                "reason": "Ollama antwortet, aber nicht als gültiges JSON. Modell/Format prüfen.",
                "status": "invalid_json",
                "base_url": base_url,
                "model": model,
                "api_message": text[:300],
            }
        return {"ok": True, "reason": f"Ollama Verbindung erfolgreich ({model}).", "status": "ok", "base_url": base_url, "model": model}
    except requests.ConnectionError:
        return {"ok": False, "reason": f"Ollama ist unter {base_url} nicht erreichbar. Ollama starten oder Base URL prüfen.", "status": "not_running", "base_url": base_url, "model": model}
    except requests.Timeout:
        return {"ok": False, "reason": f"Ollama Test Timeout nach {timeout:g}s. Modell {model} ist eventuell zu langsam oder lädt noch.", "status": "timeout", "base_url": base_url, "model": model}
    except (requests.RequestException, ValueError) as exc:
        return {"ok": False, "reason": f"Ollama Test fehlgeschlagen: {type(exc).__name__}: {exc}", "status": "error", "base_url": base_url, "model": model}


def test_ollama_speed(config: dict[str, Any]) -> dict[str, Any]:
    base_url = str(config.get("ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
    model = str(config.get("ollama_model", "qwen2.5:3b")).strip() or "qwen2.5:3b"
    timeout = max(1.0, min(180.0, float(config.get("ollama_timeout_seconds", 60) or 60)))
    payload = {
        "model": model,
        "prompt": 'Antworte nur mit diesem JSON Objekt: {"decision":"WAIT","reason":"Risiko pruefen"}',
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 40},
    }
    started = time.perf_counter()
    try:
        response = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
        elapsed = time.perf_counter() - started
        if response.status_code != 200:
            error_text = (response.text or "").strip()[:300]
            return {
                "ok": False,
                "status": "generate_failed",
                "reason": f"Ollama Speed-Test fehlgeschlagen: HTTP {response.status_code}. {error_text}".strip(),
                "seconds": round(elapsed, 3),
                "base_url": base_url,
                "model": model,
                "hardware": ollama_hardware_status(config),
            }
        generated = response.json()
        text = str(generated.get("response", "")).strip()
        try:
            parsed = json.loads(text or "{}")
            json_valid = isinstance(parsed, dict)
        except ValueError:
            parsed = None
            json_valid = False
        eval_count = int(generated.get("eval_count") or 0)
        eval_duration_ns = int(generated.get("eval_duration") or 0)
        tokens_per_second = None
        if eval_count > 0 and eval_duration_ns > 0:
            tokens_per_second = round(eval_count / (eval_duration_ns / 1_000_000_000), 2)
        ok = json_valid and elapsed <= timeout
        return {
            "ok": ok,
            "status": "ok" if ok else "invalid_json",
            "reason": (
                f"Ollama Speed-Test OK: {elapsed:.2f}s, JSON gueltig."
                if ok
                else f"Ollama antwortet in {elapsed:.2f}s, aber JSON ist ungueltig."
            ),
            "seconds": round(elapsed, 3),
            "json_valid": json_valid,
            "response": text[:300],
            "parsed": parsed,
            "eval_count": eval_count,
            "tokens_per_second": tokens_per_second,
            "base_url": base_url,
            "model": model,
            "hardware": ollama_hardware_status(config),
        }
    except requests.Timeout:
        elapsed = time.perf_counter() - started
        return {
            "ok": False,
            "status": "timeout",
            "reason": f"Ollama Speed-Test Timeout nach {timeout:g}s.",
            "seconds": round(elapsed, 3),
            "base_url": base_url,
            "model": model,
            "hardware": ollama_hardware_status(config),
        }
    except (requests.RequestException, ValueError) as exc:
        elapsed = time.perf_counter() - started
        return {
            "ok": False,
            "status": "error",
            "reason": f"Ollama Speed-Test fehlgeschlagen: {type(exc).__name__}: {exc}",
            "seconds": round(elapsed, 3),
            "base_url": base_url,
            "model": model,
            "hardware": ollama_hardware_status(config),
        }


def _windows_user_env(name: str) -> str:
    if winreg is None:
        return ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _value_type = winreg.QueryValueEx(key, name)
            return str(value or "")
    except OSError:
        return ""


def _ollama_processes() -> list[dict[str, Any]]:
    command = [
        "powershell",
        "-NoProfile",
        "-Command",
        (
            "Get-CimInstance Win32_Process | "
            "Where-Object { $_.Name -match 'ollama|llama-server' } | "
            "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
        ),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.SubprocessError):
        return []
    text = (result.stdout or "").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return []
    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def ollama_hardware_status(config: dict[str, Any]) -> dict[str, Any]:
    process_library = str(os.environ.get("OLLAMA_LLM_LIBRARY", "") or "")
    user_library = _windows_user_env("OLLAMA_LLM_LIBRARY")
    configured_library = user_library or process_library or "auto"
    ollama_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Ollama" / "lib" / "ollama"
    backends = [name for name in ("vulkan", "rocm_v7_1", "cuda_v12", "cuda_v13") if (ollama_dir / name).exists()]
    processes = _ollama_processes()
    runner = next((proc for proc in processes if str(proc.get("Name", "")).lower() == "llama-server.exe"), None)
    runner_command = str((runner or {}).get("CommandLine") or "")
    runner_active = runner is not None
    no_mmap = "--no-mmap" in runner_command
    if configured_library == "vulkan":
        status = "vulkan_configured"
        detail = "Vulkan ist als Ollama-Backend gesetzt."
    elif configured_library.startswith("cpu"):
        status = "cpu_forced"
        detail = "Ollama wird per OLLAMA_LLM_LIBRARY auf CPU gezwungen."
    elif configured_library == "auto":
        status = "auto"
        detail = "Ollama waehlt das Backend automatisch."
    else:
        status = "custom"
        detail = f"Ollama Backend ist auf {configured_library} gesetzt."
    if runner_active and no_mmap and configured_library == "vulkan":
        detail += " Der aktuelle Runner sieht trotzdem CPU-typisch aus; Ollama neu starten."
    return {
        "provider": str(config.get("llm_provider", "ollama")),
        "model": str(config.get("ollama_model", "")),
        "configured_library": configured_library,
        "process_library": process_library or "-",
        "user_library": user_library or "-",
        "status": status,
        "detail": detail,
        "runner_active": runner_active,
        "runner_pid": (runner or {}).get("ProcessId"),
        "runner_no_mmap": no_mmap,
        "available_backends": backends,
        "ollama_process_count": len(processes),
    }


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


def build_risk_context(
    setup: Setup | None,
    broker: PaperBroker,
    config: dict[str, Any],
    value_result: dict[str, Any] | None = None,
    broker_allowed: bool | None = None,
    broker_reason: str | None = None,
    paper_trade_created: bool | None = None,
) -> dict[str, Any]:
    active = [trade for trade in broker.trades if trade.status in ("pending", "open")]
    symbol = setup.symbol if setup else None
    side = setup.side if setup else None
    group = correlation_group(symbol) if symbol else None
    same_asset = [trade for trade in active if trade.setup.symbol == symbol] if symbol else []
    correlated_same_direction = [
        trade
        for trade in active
        if group and trade.setup.side == side and correlation_group(trade.setup.symbol) == group
    ]
    entry = float(setup.entry) if setup else 0.0
    risk_fraction = abs(float(setup.entry) - float(setup.stop_loss)) / entry if setup and entry > 0 else None
    max_sl_by_symbol = config.get("max_sl_distance_fraction_by_symbol", {}) or {}
    max_sl_fraction = max_sl_by_symbol.get(symbol) if symbol and isinstance(max_sl_by_symbol, dict) else None
    if max_sl_fraction is None:
        max_sl_fraction = config.get("max_sl_distance_fraction", 0.0)
    min_profit_by_symbol = config.get("min_net_profit_fraction_by_symbol", {}) or {}
    min_profit_fraction = min_profit_by_symbol.get(symbol) if symbol and isinstance(min_profit_by_symbol, dict) else None
    if min_profit_fraction is None:
        min_profit_fraction = config.get("min_net_profit_fraction", 0.001)
    return {
        "candidate_present": setup is not None,
        "symbol": symbol,
        "side": side,
        "economic_gate": value_result or {},
        "broker": {
            "allowed": broker_allowed,
            "reason": broker_reason,
            "paper_trade_created": paper_trade_created,
        } if broker_allowed is not None else {},
        "active_trades": {
            "total": len(active),
            "same_asset": len(same_asset),
            "correlation_group": group,
            "correlated_same_direction": len(correlated_same_direction),
            "max_open_trades_total": int(config.get("max_open_trades_total", 3)),
            "max_open_trades_per_asset": int(config.get("max_open_trades_per_asset", 1)),
            "correlation_lock_enabled": bool(config.get("block_same_direction_correlated_trades", True)),
        },
        "sl_distance_fraction": risk_fraction,
        "max_sl_distance_fraction": float(max_sl_fraction or 0.0),
        "min_rr": float(config.get("min_rr", 0.0)),
        "min_net_profit_fraction": float(min_profit_fraction or 0.0),
    }


def refresh_agent_board_risk_context(
    agent_board: dict[str, Any],
    scan: dict[str, Any],
    setup: Setup | None,
    broker: PaperBroker,
    config: dict[str, Any],
    value_result: dict[str, Any] | None = None,
    broker_allowed: bool | None = None,
    broker_reason: str | None = None,
    paper_trade_created: bool | None = None,
) -> dict[str, Any]:
    risk_context = build_risk_context(
        setup=setup,
        broker=broker,
        config=config,
        value_result=value_result,
        broker_allowed=broker_allowed,
        broker_reason=broker_reason,
        paper_trade_created=paper_trade_created,
    )
    refreshed = refresh_risk_agent_report(
        board=agent_board,
        scan=scan,
        config=config,
        risk_context=risk_context,
    )
    refreshed["risk_context"] = risk_context
    return refreshed


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
# REPLAY PREVIEW ENGINE
# --------------------------------------------------
def replay_gate_input_from_candidate(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    setup = create_setup_from_brain_candidate(candidate, config)
    return brain_gate_input_from_setup(setup)


def replay_trade_id(candidate: dict[str, Any]) -> str:
    return "-".join(
        [
            str(candidate.get("symbol", "SYMBOL")),
            str(candidate.get("side", "side")),
            str(candidate.get("signal_candle_time", 0)),
            str(candidate.get("confirmation_candle_time", 0)),
            str(candidate.get("pattern_key", "pattern"))[:24],
        ]
    )


def replay_configured_trade_size(symbol: Any, config: dict[str, Any]) -> dict[str, Any]:
    clean_symbol = normalize_asset_symbol(symbol)
    sizes = config.get("trade_sizes_by_symbol", {}) or {}
    symbol_size: dict[str, Any] = {}
    if isinstance(sizes, dict):
        for key, value in sizes.items():
            if normalize_asset_symbol(key) == clean_symbol and isinstance(value, dict):
                symbol_size = value
                break
    mode = str(symbol_size.get("mode", config.get("trade_size_mode", "usd"))).lower()
    if mode not in ("asset", "usd"):
        mode = str(config.get("trade_size_mode", "usd")).lower()
    usd = float(symbol_size.get("usd", config.get("trade_size_usd", 0.0)) or 0.0)
    asset = float(symbol_size.get("asset", config.get("trade_size_asset", 0.0)) or 0.0)
    return {"symbol": clean_symbol, "mode": mode, "usd": usd, "asset": asset}


def replay_trade_pnl_basis(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    symbol = normalize_asset_symbol(candidate.get("symbol", ""))
    entry = float(candidate.get("entry_price", 0.0) or 0.0)
    stop_loss = float(candidate.get("sl_price", 0.0) or 0.0)
    configured_size = replay_configured_trade_size(symbol, config)
    mode = str(configured_size.get("mode", "usd")).lower()
    usd = float(configured_size.get("usd", 0.0) or 0.0)
    asset = float(configured_size.get("asset", 0.0) or 0.0)
    planned_notional = round(usd, 8) if mode == "usd" and usd > 0 else None
    planned_quantity = round(asset, 8) if mode == "asset" and asset > 0 else None
    if planned_quantity is None and planned_notional is not None and entry > 0:
        planned_quantity = round(planned_notional / entry, 8)
    if planned_notional is None and planned_quantity is not None and entry > 0:
        planned_notional = round(planned_quantity * entry, 8)
    risk_per_unit = abs(entry - stop_loss)
    risk_usd = round(risk_per_unit * planned_quantity, 8) if planned_quantity is not None else None
    return {
        "trade_size_mode": mode,
        "planned_notional_usd": planned_notional,
        "planned_quantity_asset": planned_quantity,
        "risk_usd": risk_usd,
        "fee_rate": float(config.get("estimated_taker_fee_rate", 0.0006)),
        "pnl_currency": str(config.get("replay_pnl_currency", config.get("account_balance_currency", "USDT"))),
    }


def replay_pnl_for_exit(
    *,
    side: str,
    entry: float,
    exit_price: float,
    quantity: float | None,
    notional: float | None,
    fee_rate: float,
    risk_usd: float | None = None,
    result_r: float = 0.0,
) -> dict[str, Any]:
    quantity_number = float(quantity) if quantity is not None and float(quantity) > 0 else None
    if quantity_number is None and notional is not None and float(notional) > 0 and entry > 0:
        quantity_number = float(notional) / entry
    if quantity_number is not None and quantity_number > 0:
        gross_pnl = ((exit_price - entry) if side == "long" else (entry - exit_price)) * quantity_number
        entry_notional = abs(entry * quantity_number)
        exit_notional = abs(exit_price * quantity_number)
        fees = (entry_notional + exit_notional) * float(fee_rate)
    else:
        gross_pnl = float(result_r) * float(risk_usd) if risk_usd is not None else 0.0
        fees = 0.0
    return {
        "gross_pnl_usd": round(gross_pnl, 8),
        "estimated_fees_usd": round(fees, 8),
        "net_pnl_usd": round(gross_pnl - fees, 8),
    }


def replay_candidate_pnl_preview(candidate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    basis = replay_trade_pnl_basis(candidate, config)
    entry = float(candidate.get("entry_price", 0.0) or 0.0)
    tp = float(candidate.get("tp_price", 0.0) or 0.0)
    sl = float(candidate.get("sl_price", 0.0) or 0.0)
    side = str(candidate.get("side", ""))
    quantity = basis.get("planned_quantity_asset")
    notional = basis.get("planned_notional_usd")
    fee_rate = float(basis.get("fee_rate", 0.0) or 0.0)
    risk_usd = basis.get("risk_usd")
    tp_result = replay_pnl_for_exit(side=side, entry=entry, exit_price=tp, quantity=quantity, notional=notional, fee_rate=fee_rate, risk_usd=risk_usd, result_r=1.0)
    sl_result = replay_pnl_for_exit(side=side, entry=entry, exit_price=sl, quantity=quantity, notional=notional, fee_rate=fee_rate, risk_usd=risk_usd, result_r=-1.0)
    return {
        "trade_size_mode": basis.get("trade_size_mode"),
        "asset_quantity": quantity,
        "notional_usd": notional,
        "rr_factor": round(abs(tp - entry) / abs(entry - sl), 6) if entry != sl else None,
        "tp_distance_usd": round(abs(tp - entry), 8),
        "sl_distance_usd": round(abs(entry - sl), 8),
        "tp_gross_usd": tp_result["gross_pnl_usd"],
        "tp_fees_usd": tp_result["estimated_fees_usd"],
        "tp_net_usd": tp_result["net_pnl_usd"],
        "sl_gross_usd": sl_result["gross_pnl_usd"],
        "sl_fees_usd": sl_result["estimated_fees_usd"],
        "sl_net_usd": sl_result["net_pnl_usd"],
        "fee_rate": fee_rate,
        "pnl_formula": "price_distance * asset_quantity - fees",
    }


def apply_replay_trade_pnl(trade: dict[str, Any], exit_price: float) -> None:
    entry = float(trade.get("entry", 0.0) or 0.0)
    quantity = trade.get("planned_quantity_asset")
    notional = trade.get("planned_notional_usd")
    risk_usd = trade.get("risk_usd")
    result_r = float(trade.get("result_r") or 0.0)
    side = str(trade.get("side", ""))
    pnl = replay_pnl_for_exit(
        side=side,
        entry=entry,
        exit_price=float(exit_price),
        quantity=float(quantity) if quantity is not None else None,
        notional=float(notional) if notional is not None else None,
        fee_rate=float(trade.get("fee_rate", 0.0006) or 0.0),
        risk_usd=float(risk_usd) if risk_usd is not None else None,
        result_r=result_r,
    )
    trade.update(pnl)


def replay_trade_from_candidate(candidate: dict[str, Any], config: dict[str, Any], resolution: int) -> dict[str, Any]:
    created_at = int(candidate.get("confirmation_candle_time") or candidate.get("signal_candle_time") or 0)
    expiry_candles = max(1, int(config.get("order_expiry_confirmation_candles", 20)))
    features = candidate.get("features", {}) if isinstance(candidate.get("features"), dict) else {}
    memory_key = "|".join(
        [
            f"symbol={candidate.get('symbol', '')}",
            f"side={candidate.get('side', '')}",
            f"pattern={candidate.get('pattern_key', '')}",
            f"entry={candidate.get('entry_method', '')}",
            f"phase={features.get('market_phase', features.get('trend_alignment', 'na'))}",
            f"volatility={features.get('volatility_bucket', features.get('volatility', 'na'))}",
            f"session={features.get('session', 'na')}",
        ]
    )
    pnl_basis = replay_trade_pnl_basis(candidate, config)
    return {
        "id": replay_trade_id(candidate),
        "symbol": str(candidate.get("symbol", "")),
        "side": str(candidate.get("side", "")),
        "status": "pending",
        "created_at": created_at,
        "expires_at": created_at + expiry_candles * int(resolution),
        "filled_at": None,
        "closed_at": None,
        "entry": float(candidate.get("entry_price", 0.0)),
        "stop_loss": float(candidate.get("sl_price", 0.0)),
        "take_profit": float(candidate.get("tp_price", 0.0)),
        "exit_price": None,
        "result_r": None,
        "trade_size_mode": pnl_basis["trade_size_mode"],
        "planned_notional_usd": pnl_basis["planned_notional_usd"],
        "planned_quantity_asset": pnl_basis["planned_quantity_asset"],
        "risk_usd": pnl_basis["risk_usd"],
        "fee_rate": pnl_basis["fee_rate"],
        "pnl_currency": pnl_basis["pnl_currency"],
        "gross_pnl_usd": None,
        "estimated_fees_usd": None,
        "net_pnl_usd": None,
        "pattern_key": str(candidate.get("pattern_key", "")),
        "entry_method": str(candidate.get("entry_method", "")),
        "memory_key": memory_key,
        "memory_features": {
            "market_phase": features.get("market_phase", features.get("trend_alignment", "na")),
            "volatility": features.get("volatility_bucket", features.get("volatility", "na")),
            "session": features.get("session", "na"),
            "entry_method": str(candidate.get("entry_method", "")),
            "pattern_key": str(candidate.get("pattern_key", "")),
        },
        "llm_role_context": features.get("llm_role_context") if isinstance(features.get("llm_role_context"), dict) else {},
        "llm_role_protocol": features.get("llm_role_protocol") if isinstance(features.get("llm_role_protocol"), dict) else {},
    }


def replay_can_accept_trade(trades: list[dict[str, Any]], candidate_trade: dict[str, Any], config: dict[str, Any]) -> tuple[bool, str | None]:
    active = [trade for trade in trades if trade.get("status") in ("pending", "open")]
    if len(active) >= int(config.get("max_open_trades_total", 3)):
        return False, "max_open_trades_total"

    symbol = str(candidate_trade.get("symbol", ""))
    same_asset = [trade for trade in active if str(trade.get("symbol", "")) == symbol]
    if len(same_asset) >= int(config.get("max_open_trades_per_asset", 1)):
        return False, "max_open_trades_per_asset"

    if config.get("block_same_direction_correlated_trades", True):
        group = correlation_group(symbol)
        side = str(candidate_trade.get("side", ""))
        if group and side:
            for trade in active:
                if str(trade.get("side", "")) == side and correlation_group(str(trade.get("symbol", ""))) == group:
                    return False, f"correlated_{group}_{side}"
    return True, None


def replay_result_r(trade: dict[str, Any], exit_price: float) -> float:
    entry = float(trade.get("entry", 0.0))
    stop_loss = float(trade.get("stop_loss", 0.0))
    risk = abs(entry - stop_loss)
    if risk <= 0:
        return 0.0
    side = str(trade.get("side", ""))
    pnl = (exit_price - entry) if side == "long" else (entry - exit_price)
    return round(pnl / risk, 4)


def compact_replay_frame_candidate(candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(candidate, dict):
        return None
    return {
        "symbol": candidate.get("symbol"),
        "decision": candidate.get("decision"),
        "side": candidate.get("side"),
        "entry_price": candidate.get("entry_price"),
        "sl_price": candidate.get("sl_price"),
        "tp_price": candidate.get("tp_price"),
        "entry_method": candidate.get("entry_method"),
        "pattern_key": candidate.get("pattern_key"),
        "reason": candidate.get("reason"),
    }


def lightweight_replay_trade_summary(trades: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "created": len(trades),
        "pending": sum(1 for trade in trades if trade.get("status") == "pending"),
        "open": sum(1 for trade in trades if trade.get("status") == "open"),
        "closed": sum(1 for trade in trades if trade.get("result_r") is not None),
    }


def close_replay_trade_at_price(trade: dict[str, Any], status: str, timestamp: int, exit_price: float, reason: str) -> dict[str, Any]:
    trade["status"] = status
    trade["closed_at"] = int(timestamp)
    trade["exit_price"] = float(exit_price)
    trade["result_r"] = replay_result_r(trade, float(exit_price)) if status != "expired" else float(trade.get("result_r", 0.0) or 0.0)
    trade["replay_close_reason"] = reason
    apply_replay_trade_pnl(trade, float(exit_price))
    return {
        "trade_id": trade.get("id"),
        "status": status,
        "time": int(timestamp),
        "price": float(exit_price),
        "result_r": trade.get("result_r"),
        "net_pnl_usd": trade.get("net_pnl_usd"),
        "reason": reason,
    }


def expire_replay_trade_flat(trade: dict[str, Any], timestamp: int, reason: str) -> dict[str, Any]:
    trade["status"] = "expired"
    trade["closed_at"] = int(timestamp)
    trade["exit_price"] = None
    trade["result_r"] = 0.0
    trade["replay_close_reason"] = reason
    trade["gross_pnl_usd"] = 0.0
    trade["estimated_fees_usd"] = 0.0
    trade["net_pnl_usd"] = 0.0
    return {
        "trade_id": trade.get("id"),
        "status": "expired",
        "time": int(timestamp),
        "price": None,
        "result_r": 0.0,
        "net_pnl_usd": 0.0,
        "reason": reason,
    }


def finalize_replay_trades(trades: list[dict[str, Any]], candle: Candle | None) -> list[dict[str, Any]]:
    if candle is None:
        return []
    events: list[dict[str, Any]] = []
    for trade in trades:
        if trade.get("result_r") is not None or trade.get("status") in ("tp", "sl", "expired"):
            continue
        if trade.get("status") == "open":
            exit_price = float(candle.close)
            status = "tp" if replay_result_r(trade, exit_price) > 0 else "sl" if replay_result_r(trade, exit_price) < 0 else "expired"
            events.append(close_replay_trade_at_price(trade, status, candle.timestamp, exit_price, "replay_end_mark_to_market"))
        else:
            events.append(expire_replay_trade_flat(trade, candle.timestamp, "replay_end_pending_not_filled"))
    return events


def replay_no_closed_reason(summary: dict[str, Any]) -> str:
    if int(summary.get("frames", 0) or 0) <= 0:
        return "Keine Replay-Frames: zu wenig Kerzendaten oder Warmup zu groß."
    if int(summary.get("candidates", 0) or 0) <= 0:
        return "Brain erzeugt keine Trade-Kandidaten."
    if int(summary.get("gate_allowed", 0) or 0) <= 0:
        return "Economic Gate blockiert alle Kandidaten."
    if int(summary.get("replay_created", 0) or 0) <= 0:
        return "Replay erstellt keine Trades trotz Gate-Freigabe."
    if int(summary.get("replay_opened", 0) or 0) <= 0:
        return "Replay-Trades erreichen den Entry nicht vor Ablauf."
    return "Replay-Trades wurden nicht bis TP/SL geschlossen."


def update_replay_trades(trades: list[dict[str, Any]], candle: Candle) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for trade in trades:
        if trade.get("status") in ("tp", "sl", "expired"):
            continue

        if trade.get("status") == "pending":
            if int(candle.timestamp) > int(trade.get("expires_at", 0)):
                events.append(expire_replay_trade_flat(trade, candle.timestamp, "entry_not_filled_before_expiry"))
                continue
            entry = float(trade.get("entry", 0.0))
            if candle.low <= entry <= candle.high:
                trade["status"] = "open"
                trade["filled_at"] = candle.timestamp
                events.append({"trade_id": trade.get("id"), "status": "open", "time": candle.timestamp, "price": entry})

        if trade.get("status") == "open":
            side = str(trade.get("side", ""))
            stop_loss = float(trade.get("stop_loss", 0.0))
            take_profit = float(trade.get("take_profit", 0.0))
            exit_status: str | None = None
            exit_price: float | None = None
            if side == "long":
                if candle.low <= stop_loss:
                    exit_status, exit_price = "sl", stop_loss
                elif candle.high >= take_profit:
                    exit_status, exit_price = "tp", take_profit
            else:
                if candle.high >= stop_loss:
                    exit_status, exit_price = "sl", stop_loss
                elif candle.low <= take_profit:
                    exit_status, exit_price = "tp", take_profit
            if exit_status and exit_price is not None:
                events.append(close_replay_trade_at_price(trade, exit_status, candle.timestamp, exit_price, "tp_sl_hit"))
    return events


def replay_trade_summary(trades: list[dict[str, Any]]) -> dict[str, Any]:
    closed = [trade for trade in trades if trade.get("result_r") is not None]
    closed.sort(key=lambda trade: int(trade.get("closed_at") or trade.get("created_at") or 0))
    wins = [trade for trade in closed if float(trade.get("result_r") or 0.0) > 0]
    gross_win_r = sum(max(0.0, float(trade.get("result_r") or 0.0)) for trade in closed)
    gross_loss_r = abs(sum(min(0.0, float(trade.get("result_r") or 0.0)) for trade in closed))
    sum_r = sum(float(trade.get("result_r") or 0.0) for trade in closed)
    gross_pnl_usd = sum(float(trade.get("gross_pnl_usd") or 0.0) for trade in closed)
    estimated_fees_usd = sum(float(trade.get("estimated_fees_usd") or 0.0) for trade in closed)
    net_pnl_values = [float(trade.get("net_pnl_usd") or 0.0) for trade in closed]
    net_pnl_usd = sum(net_pnl_values)
    pnl_wins = sum(1 for value in net_pnl_values if value > 0)
    gross_pnl_profit_usd = sum(max(0.0, value) for value in net_pnl_values)
    gross_pnl_loss_usd = abs(sum(min(0.0, value) for value in net_pnl_values))
    avg_win_pnl_usd = gross_pnl_profit_usd / pnl_wins if pnl_wins else None
    pnl_losses = len([value for value in net_pnl_values if value < 0])
    avg_loss_pnl_usd = gross_pnl_loss_usd / pnl_losses if pnl_losses else None
    break_even_win_rate = None
    if avg_win_pnl_usd and avg_loss_pnl_usd and (avg_win_pnl_usd + avg_loss_pnl_usd) > 0:
        break_even_win_rate = avg_loss_pnl_usd / (avg_win_pnl_usd + avg_loss_pnl_usd)

    equity_r = 0.0
    peak_r = 0.0
    max_drawdown_r = 0.0
    equity_usd = 0.0
    peak_usd = 0.0
    max_drawdown_usd = 0.0
    best_pnl_series_usd = 0.0
    worst_pnl_series_usd = 0.0
    current_best_series = 0.0
    current_worst_series = 0.0
    for trade, net_value in zip(closed, net_pnl_values):
        equity_r += float(trade.get("result_r") or 0.0)
        peak_r = max(peak_r, equity_r)
        max_drawdown_r = max(max_drawdown_r, peak_r - equity_r)

        equity_usd += net_value
        peak_usd = max(peak_usd, equity_usd)
        max_drawdown_usd = max(max_drawdown_usd, peak_usd - equity_usd)
        current_best_series = max(net_value, current_best_series + net_value)
        current_worst_series = min(net_value, current_worst_series + net_value)
        best_pnl_series_usd = max(best_pnl_series_usd, current_best_series)
        worst_pnl_series_usd = min(worst_pnl_series_usd, current_worst_series)

    return {
        "created": len(trades),
        "pending": sum(1 for trade in trades if trade.get("status") == "pending"),
        "open": sum(1 for trade in trades if trade.get("status") == "open"),
        "tp": sum(1 for trade in trades if trade.get("status") == "tp"),
        "sl": sum(1 for trade in trades if trade.get("status") == "sl"),
        "expired": sum(1 for trade in trades if trade.get("status") == "expired"),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(closed) - len(wins),
        "win_rate": round(len(wins) / len(closed), 3) if closed else None,
        "sum_r": round(sum_r, 4),
        "expectancy_r": round(sum_r / len(closed), 4) if closed else None,
        "profit_factor": round(gross_win_r / gross_loss_r, 4) if gross_loss_r > 0 else (None if gross_win_r <= 0 else 999.0),
        "max_drawdown_r": round(max_drawdown_r, 4),
        "gross_pnl_usd": round(gross_pnl_usd, 4),
        "estimated_fees_usd": round(estimated_fees_usd, 4),
        "net_pnl_usd": round(net_pnl_usd, 4),
        "pnl_win_rate": round(pnl_wins / len(closed), 4) if closed else None,
        "net_profit_factor_usd": round(gross_pnl_profit_usd / gross_pnl_loss_usd, 4) if gross_pnl_loss_usd > 0 else (None if gross_pnl_profit_usd <= 0 else 999.0),
        "max_drawdown_usd": round(max_drawdown_usd, 4),
        "best_pnl_series_usd": round(best_pnl_series_usd, 4),
        "worst_pnl_series_usd": round(worst_pnl_series_usd, 4),
        "break_even_win_rate": round(break_even_win_rate, 4) if break_even_win_rate is not None else None,
        "net_win_usd": round(gross_pnl_profit_usd, 4),
        "net_loss_usd": round(gross_pnl_loss_usd, 4),
        "avg_net_win_usd": round(avg_win_pnl_usd, 6) if avg_win_pnl_usd is not None else None,
        "avg_net_loss_usd": round(avg_loss_pnl_usd, 6) if avg_loss_pnl_usd is not None else None,
    }



def replay_memory_test_summary(trades: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = config or {}
    rule_min_count = max(3, int(cfg.get("replay_rule_weight_min_count", 5)))
    rule_good_bonus = int(cfg.get("replay_rule_good_bonus", 6))
    rule_bad_penalty = int(cfg.get("replay_rule_bad_penalty", -10))
    rule_max_abs = max(0, int(cfg.get("replay_rule_max_abs_adjustment", 12)))
    rule_good_bonus = max(0, min(rule_max_abs, rule_good_bonus))
    rule_bad_penalty = max(-rule_max_abs, min(0, rule_bad_penalty))
    buckets: dict[str, dict[str, Any]] = {}
    completed = [trade for trade in trades if trade.get("result_r") is not None]
    for trade in completed:
        key = str(trade.get("memory_key") or "unknown")
        bucket = buckets.setdefault(
            key,
            {
                "key": key,
                "count": 0,
                "wins": 0,
                "losses": 0,
                "sum_r": 0.0,
                "entry_methods": {},
                "market_phases": {},
                "volatility": {},
                "sessions": {},
            },
        )
        result_r = float(trade.get("result_r") or 0.0)
        features = trade.get("memory_features", {}) if isinstance(trade.get("memory_features"), dict) else {}
        bucket["count"] += 1
        bucket["wins"] += 1 if result_r > 0 else 0
        bucket["losses"] += 1 if result_r <= 0 else 0
        bucket["sum_r"] += result_r
        for field, target in (
            ("entry_method", "entry_methods"),
            ("market_phase", "market_phases"),
            ("volatility", "volatility"),
            ("session", "sessions"),
        ):
            value = str(features.get(field, "na"))
            bucket[target][value] = int(bucket[target].get(value, 0)) + 1

    bucket_rows: list[dict[str, Any]] = []
    for bucket in buckets.values():
        count = int(bucket["count"])
        bucket_rows.append(
            {
                "key": bucket["key"],
                "count": count,
                "wins": bucket["wins"],
                "losses": bucket["losses"],
                "win_rate": round(bucket["wins"] / count, 3) if count else None,
                "avg_r": round(float(bucket["sum_r"]) / count, 4) if count else None,
                "sum_r": round(float(bucket["sum_r"]), 4),
                "entry_methods": bucket["entry_methods"],
                "market_phases": bucket["market_phases"],
                "volatility": bucket["volatility"],
                "sessions": bucket["sessions"],
            }
        )
    bucket_rows.sort(key=lambda item: (item["count"], item["avg_r"] or 0.0), reverse=True)
    wins = sum(1 for trade in completed if float(trade.get("result_r") or 0.0) > 0)
    memory_test = {
        "mode": "replay_memory_test",
        "isolated_from_live_memory": True,
        "completed_trades": len(completed),
        "bucket_count": len(bucket_rows),
        "win_rate": round(wins / len(completed), 3) if completed else None,
        "sum_r": round(sum(float(trade.get("result_r") or 0.0) for trade in completed), 4),
        "top_buckets": bucket_rows[:20],
        "rule_min_count": rule_min_count,
        "rule_good_bonus": rule_good_bonus,
        "rule_bad_penalty": rule_bad_penalty,
        "rule_max_abs_adjustment": rule_max_abs,
        "rule_small_sample": len(completed) < max(rule_min_count * 3, 20),
    }
    memory_test["preview_rules"] = replay_memory_preview_rules(memory_test)
    return memory_test



def parse_replay_memory_key(key: Any) -> dict[str, str]:
    text = str(key or "")
    result: dict[str, str] = {}
    for name in ("symbol", "side", "entry", "phase", "volatility", "session"):
        marker = f"{name}="
        if marker not in text:
            continue
        start = text.find(marker) + len(marker)
        end = text.find("|", start)
        result[name] = text[start:] if end == -1 else text[start:end]
    pattern_marker = "pattern="
    entry_marker = "|entry="
    if pattern_marker in text:
        start = text.find(pattern_marker) + len(pattern_marker)
        end = text.find(entry_marker, start)
        result["pattern_key"] = text[start:] if end == -1 else text[start:end]
    return result


def replay_rule_action_label(quality: str, eligible: bool) -> str:
    if not eligible:
        return "WATCH"
    value = str(quality or "WATCH").upper()
    if value == "GOOD":
        return "BONUS"
    if value == "BAD":
        return "MALUS"
    return "WATCH"


def replay_memory_preview_rules(memory_test: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    rule_min_count = max(3, int(memory_test.get("rule_min_count") or 5))
    good_bonus = int(memory_test.get("rule_good_bonus") or 0)
    bad_penalty = int(memory_test.get("rule_bad_penalty") or 0)
    for bucket in memory_test.get("top_buckets", []) or []:
        count = int(bucket.get("count") or 0)
        win_rate = bucket.get("win_rate")
        avg_r = bucket.get("avg_r")
        eligible = count >= rule_min_count and win_rate is not None and avg_r is not None
        adjustment = 0
        if not eligible:
            quality = "WATCH"
            action = f"Nicht aktivierbar: mindestens {rule_min_count} Trades pro Pattern nötig."
            safety = "zu wenig Daten"
            priority = 1
        elif float(win_rate) >= 0.6 and float(avg_r) > 0:
            quality = "GOOD"
            adjustment = good_bonus
            action = "Aktivierbar: Brain-Score bekommt einen begrenzten Bonus."
            safety = "aktivierbar"
            priority = 3
        elif float(win_rate) <= 0.4 or float(avg_r) < 0:
            quality = "BAD"
            adjustment = bad_penalty
            action = "Aktivierbar: Brain-Score bekommt einen begrenzten Malus."
            safety = "aktivierbar"
            priority = 3
        else:
            quality = "WATCH"
            action = "Neutral beobachten; kein automatischer Eingriff."
            safety = "neutral"
            priority = 2

        parsed_key = parse_replay_memory_key(bucket.get("key"))
        clean_symbol = str(parsed_key.get("symbol", "")).upper()
        action_label = replay_rule_action_label(quality, bool(eligible and quality in ("GOOD", "BAD")))
        rules.append(
            {
                "quality": quality,
                "priority": priority,
                "key": bucket.get("key"),
                "symbol": clean_symbol,
                "pattern_key": parsed_key.get("pattern_key", ""),
                "scope": "asset",
                "action_label": action_label,
                "count": count,
                "min_count": rule_min_count,
                "eligible": eligible and quality in ("GOOD", "BAD"),
                "adjustment": adjustment,
                "safety": safety,
                "win_rate": win_rate,
                "avg_r": avg_r,
                "sum_r": bucket.get("sum_r"),
                "entry_methods": bucket.get("entry_methods", {}),
                "market_phases": bucket.get("market_phases", {}),
                "volatility": bucket.get("volatility", {}),
                "sessions": bucket.get("sessions", {}),
                "action": action,
            }
        )
    rules.sort(key=lambda item: (item["priority"], bool(item.get("eligible")), item["count"], abs(float(item.get("avg_r") or 0.0))), reverse=True)
    return rules[:20]


# --------------------------------------------------
# REPLAY HISTORY STORAGE
# --------------------------------------------------
def replay_history_path(config: dict[str, Any]) -> Path:
    return Path(str(config.get("replay_history_path", "data/replay_history.json")))


def load_replay_history(config: dict[str, Any]) -> dict[str, Any]:
    path = replay_history_path(config)
    if not path.exists():
        return {"version": 1, "runs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "runs": []}
    if not isinstance(payload, dict):
        return {"version": 1, "runs": []}
    if not isinstance(payload.get("runs"), list):
        payload["runs"] = []
    payload.setdefault("version", 1)
    return payload


def replay_history_trade_results(replay_payload: dict[str, Any]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for trade in replay_payload.get("replay_trades", []) or []:
        if not isinstance(trade, dict):
            continue
        result_r = trade.get("result_r")
        if result_r is None:
            continue
        try:
            result_number = float(result_r)
        except (TypeError, ValueError):
            continue
        results.append(
            {
                "trade_id": trade.get("id"),
                "status": str(trade.get("status", "")).lower(),
                "side": trade.get("side"),
                "created_at": trade.get("created_at"),
                "filled_at": trade.get("filled_at"),
                "closed_at": trade.get("closed_at"),
                "result_r": round(result_number, 6),
                "entry": trade.get("entry"),
                "stop_loss": trade.get("stop_loss"),
                "take_profit": trade.get("take_profit"),
                "trade_size_mode": trade.get("trade_size_mode"),
                "planned_quantity_asset": trade.get("planned_quantity_asset"),
                "planned_notional_usd": trade.get("planned_notional_usd"),
                "risk_usd": trade.get("risk_usd"),
                "gross_pnl_usd": trade.get("gross_pnl_usd"),
                "estimated_fees_usd": trade.get("estimated_fees_usd"),
                "net_pnl_usd": trade.get("net_pnl_usd"),
                "pnl_currency": trade.get("pnl_currency"),
                "pattern_key": trade.get("pattern_key"),
                "entry_method": trade.get("entry_method"),
                "memory_key": trade.get("memory_key"),
                "memory_features": trade.get("memory_features") if isinstance(trade.get("memory_features"), dict) else {},
                "llm_role_protocol": trade.get("llm_role_protocol") if isinstance(trade.get("llm_role_protocol"), dict) else {},
                "llm_role_context": trade.get("llm_role_context") if isinstance(trade.get("llm_role_context"), dict) else {},
            }
        )
    return results


def compact_replay_history_run(replay_payload: dict[str, Any]) -> dict[str, Any]:
    summary = replay_payload.get("summary", {}) or {}
    symbol = str(replay_payload.get("symbol", "UNKNOWN")).upper()
    resolution = int(replay_payload.get("resolution", 0) or 0)
    timestamp = int(time.time())
    return {
        "id": f"{symbol}-{resolution}-{timestamp}",
        "created_at": timestamp,
        "created_at_utc": format_time(timestamp),
        "symbol": symbol,
        "resolution": resolution,
        "limit": replay_payload.get("limit"),
        "warmup": replay_payload.get("warmup"),
        "summary": {
            "frames": summary.get("frames", 0),
            "candidates": summary.get("candidates", 0),
            "gate_allowed": summary.get("gate_allowed", 0),
            "gate_blocked": summary.get("gate_blocked", 0),
            "replay_created": summary.get("replay_created", 0),
            "replay_open": summary.get("replay_open", 0),
            "replay_pending": summary.get("replay_pending", 0),
            "replay_closed": summary.get("replay_closed", 0),
            "replay_tp": summary.get("replay_tp", 0),
            "replay_sl": summary.get("replay_sl", 0),
            "replay_expired": summary.get("replay_expired", 0),
            "replay_win_rate": summary.get("replay_win_rate"),
            "replay_sum_r": summary.get("replay_sum_r"),
            "replay_expectancy_r": summary.get("replay_expectancy_r"),
            "replay_profit_factor": summary.get("replay_profit_factor"),
            "replay_max_drawdown_r": summary.get("replay_max_drawdown_r"),
            "replay_gross_pnl_usd": summary.get("replay_gross_pnl_usd"),
            "replay_estimated_fees_usd": summary.get("replay_estimated_fees_usd"),
            "replay_net_pnl_usd": summary.get("replay_net_pnl_usd"),
            "replay_pnl_win_rate": summary.get("replay_pnl_win_rate"),
            "replay_net_profit_factor_usd": summary.get("replay_net_profit_factor_usd"),
            "replay_max_drawdown_usd": summary.get("replay_max_drawdown_usd"),
            "replay_best_pnl_series_usd": summary.get("replay_best_pnl_series_usd"),
            "replay_worst_pnl_series_usd": summary.get("replay_worst_pnl_series_usd"),
            "replay_break_even_win_rate": summary.get("replay_break_even_win_rate"),
        },
        "trade_results": replay_history_trade_results(replay_payload),
    }


def replay_history_asset_stats(runs: list[dict[str, Any]], config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for run in runs:
        if not isinstance(run, dict):
            continue
        symbol = str(run.get("symbol", "UNKNOWN")).upper()
        item = grouped.setdefault(
            symbol,
            {
                "symbol": symbol,
                "runs": 0,
                "frames": 0,
                "created": 0,
                "closed": 0,
                "tp": 0,
                "sl": 0,
                "expired": 0,
                "pending": 0,
                "open": 0,
                "sum_r": 0.0,
                "wins": 0,
                "losses": 0,
                "gross_profit_r": 0.0,
                "gross_loss_r": 0.0,
                "gross_pnl_usd": 0.0,
                "estimated_fees_usd": 0.0,
                "net_pnl_usd": 0.0,
                "gross_pnl_profit_usd": 0.0,
                "gross_pnl_loss_usd": 0.0,
                "gross_win_usd": 0.0,
                "gross_loss_usd": 0.0,
                "net_win_usd": 0.0,
                "net_loss_usd": 0.0,
                "quantity_sum": 0.0,
                "quantity_count": 0,
                "notional_sum_usd": 0.0,
                "notional_count": 0,
                "rr_sum": 0.0,
                "rr_count": 0,
                "max_drawdown_usd": 0.0,
                "best_pnl_series_usd": 0.0,
                "worst_pnl_series_usd": 0.0,
                "break_even_win_rate": None,
                "last_run_utc": None,
                "configured_asset_quantity": None,
                "configured_notional_usd": None,
                "configured_trade_size_mode": None,
                "display_tp_price": None,
                "display_sl_price": None,
                "display_trade_value_usd": None,
                "latest_trade_timestamp": 0,
            },
        )
        if isinstance(config, dict):
            configured_size = replay_configured_trade_size(symbol, config)
            item["configured_trade_size_mode"] = configured_size.get("mode")
            if configured_size.get("mode") == "asset":
                item["configured_asset_quantity"] = round(float(configured_size.get("asset") or 0.0), 8)
                item["configured_notional_usd"] = None
            else:
                item["configured_asset_quantity"] = None
                item["configured_notional_usd"] = round(float(configured_size.get("usd") or 0.0), 4)
        summary = run.get("summary", {}) if isinstance(run.get("summary"), dict) else {}
        item["runs"] += 1
        item["frames"] += int(summary.get("frames") or 0)
        item["created"] += int(summary.get("replay_created") or 0)
        item["tp"] += int(summary.get("replay_tp") or 0)
        item["sl"] += int(summary.get("replay_sl") or 0)
        item["expired"] += int(summary.get("replay_expired") or 0)
        item["pending"] += int(summary.get("replay_pending") or 0)
        item["open"] += int(summary.get("replay_open") or 0)
        item["closed"] += int(summary.get("replay_closed") or 0)
        item["last_run_utc"] = run.get("created_at_utc") or item["last_run_utc"]
        item["max_drawdown_usd"] = max(float(item.get("max_drawdown_usd") or 0.0), float(summary.get("replay_max_drawdown_usd") or 0.0))
        item["best_pnl_series_usd"] = max(float(item.get("best_pnl_series_usd") or 0.0), float(summary.get("replay_best_pnl_series_usd") or 0.0))
        item["worst_pnl_series_usd"] = min(float(item.get("worst_pnl_series_usd") or 0.0), float(summary.get("replay_worst_pnl_series_usd") or 0.0))
        for trade in run.get("trade_results", []) or []:
            if not isinstance(trade, dict):
                continue
            try:
                result_r = float(trade.get("result_r"))
            except (TypeError, ValueError):
                continue
            item["sum_r"] += result_r
            if result_r > 0:
                item["wins"] += 1
                item["gross_profit_r"] += result_r
            elif result_r < 0:
                item["losses"] += 1
                item["gross_loss_r"] += abs(result_r)
            gross_pnl = float(trade.get("gross_pnl_usd") or 0.0)
            fees = float(trade.get("estimated_fees_usd") or 0.0)
            net_pnl = float(trade.get("net_pnl_usd") or 0.0)
            quantity_value = trade.get("planned_quantity_asset")
            try:
                quantity_number = float(quantity_value) if quantity_value is not None else None
            except (TypeError, ValueError):
                quantity_number = None
            if quantity_number is not None and quantity_number > 0:
                item["quantity_sum"] += quantity_number
                item["quantity_count"] += 1
            notional_value = trade.get("planned_notional_usd")
            try:
                notional_number = float(notional_value) if notional_value is not None else None
            except (TypeError, ValueError):
                notional_number = None
            if notional_number is None:
                entry_value = trade.get("entry")
                try:
                    entry_number = float(entry_value) if entry_value is not None else None
                except (TypeError, ValueError):
                    entry_number = None
                if entry_number is not None and quantity_number is not None and entry_number > 0 and quantity_number > 0:
                    notional_number = entry_number * quantity_number
            if notional_number is not None and notional_number > 0:
                item["notional_sum_usd"] += notional_number
                item["notional_count"] += 1
            try:
                entry_number = float(trade.get("entry"))
                sl_number = float(trade.get("stop_loss"))
                tp_number = float(trade.get("take_profit"))
                risk_distance = abs(entry_number - sl_number)
                reward_distance = abs(tp_number - entry_number)
                if risk_distance > 0 and reward_distance > 0:
                    item["rr_sum"] += reward_distance / risk_distance
                    item["rr_count"] += 1
                trade_timestamp = int(trade.get("closed_at") or trade.get("filled_at") or trade.get("created_at") or 0)
                if trade_timestamp >= int(item.get("latest_trade_timestamp") or 0):
                    item["latest_trade_timestamp"] = trade_timestamp
                    item["display_side"] = str(trade.get("side") or "").upper() or None
                    item["display_tp_price"] = round(tp_number, 2)
                    item["display_sl_price"] = round(sl_number, 2)
                    if notional_number is not None and notional_number > 0:
                        item["display_trade_value_usd"] = round(notional_number, 2)
                    elif entry_number > 0 and quantity_number is not None and quantity_number > 0:
                        item["display_trade_value_usd"] = round(entry_number * quantity_number, 2)
            except (TypeError, ValueError):
                pass
            item["gross_pnl_usd"] += gross_pnl
            item["estimated_fees_usd"] += fees
            item["net_pnl_usd"] += net_pnl
            if gross_pnl > 0:
                item["gross_win_usd"] += gross_pnl
            elif gross_pnl < 0:
                item["gross_loss_usd"] += abs(gross_pnl)
            if net_pnl > 0:
                item["gross_pnl_profit_usd"] += net_pnl
                item["net_win_usd"] += net_pnl
            elif net_pnl < 0:
                item["gross_pnl_loss_usd"] += abs(net_pnl)
                item["net_loss_usd"] += abs(net_pnl)
    result: list[dict[str, Any]] = []
    for item in grouped.values():
        closed = max(0, int(item["wins"]) + int(item["losses"]))
        item["closed"] = max(int(item["closed"]), closed)
        item["win_rate"] = round(item["wins"] / closed, 4) if closed else None
        item["expectancy_r"] = round(item["sum_r"] / closed, 6) if closed else None
        item["profit_factor"] = round(item["gross_profit_r"] / item["gross_loss_r"], 6) if item["gross_loss_r"] > 0 else None
        item["net_profit_factor_usd"] = round(item["gross_pnl_profit_usd"] / item["gross_pnl_loss_usd"], 6) if item["gross_pnl_loss_usd"] > 0 else None
        avg_win_pnl = item["net_win_usd"] / item["wins"] if item["wins"] else None
        avg_loss_pnl = item["net_loss_usd"] / item["losses"] if item["losses"] else None
        item["avg_net_win_usd"] = round(avg_win_pnl, 6) if avg_win_pnl is not None else None
        item["avg_net_loss_usd"] = round(avg_loss_pnl, 6) if avg_loss_pnl is not None else None
        item["avg_asset_quantity"] = round(item["quantity_sum"] / item["quantity_count"], 8) if item["quantity_count"] else None
        item["avg_notional_usd"] = round(item["notional_sum_usd"] / item["notional_count"], 4) if item["notional_count"] else None
        item["display_asset_quantity"] = item.get("configured_asset_quantity") if item.get("configured_asset_quantity") is not None else item.get("avg_asset_quantity")
        item["display_notional_usd"] = item.get("configured_notional_usd") if item.get("configured_notional_usd") is not None else item.get("avg_notional_usd")
        item["avg_rr_factor"] = round(item["rr_sum"] / item["rr_count"], 4) if item["rr_count"] else None
        item["fee_per_trade_usd"] = round(item["estimated_fees_usd"] / closed, 6) if closed else None
        item["display_fee_or_trade_value_usd"] = item.get("fee_per_trade_usd")
        item["net_sl_usd"] = round(item["net_loss_usd"], 4) if item["net_loss_usd"] else 0.0
        item["avg_net_sl_usd"] = round(avg_loss_pnl, 6) if avg_loss_pnl is not None else None
        item["avg_gross_win_usd"] = round(item["gross_win_usd"] / item["wins"], 6) if item["wins"] else None
        item["avg_gross_loss_usd"] = round(item["gross_loss_usd"] / item["losses"], 6) if item["losses"] else None
        item["win_usd"] = round(item["net_win_usd"], 4)
        item["loss_usd"] = round(item["net_loss_usd"], 4)
        item["pnl_formula"] = "Netto PnL = Gewinn - Verlust"
        item["pnl_check_usd"] = round(item["net_win_usd"] - item["net_loss_usd"], 4)
        item["fee_drag_usd"] = round(float(item.get("estimated_fees_usd") or 0.0), 6)
        item["fee_drag_fraction"] = round(float(item.get("estimated_fees_usd") or 0.0) / max(1e-12, abs(float(item.get("gross_pnl_usd") or 0.0))), 6) if float(item.get("gross_pnl_usd") or 0.0) != 0 else None
        item["break_even_win_rate"] = round(avg_loss_pnl / (avg_win_pnl + avg_loss_pnl), 6) if avg_win_pnl and avg_loss_pnl and (avg_win_pnl + avg_loss_pnl) > 0 else None
        be_gap = None
        if item.get("win_rate") is not None and item.get("break_even_win_rate") is not None:
            be_gap = float(item["win_rate"]) - float(item["break_even_win_rate"])
        pf_value = float(item["profit_factor"]) if item.get("profit_factor") is not None else 0.0
        net_pnl_value = float(item.get("net_pnl_usd") or 0.0)
        drawdown_value = float(item.get("max_drawdown_usd") or 0.0)
        closed_bonus = min(10.0, float(item.get("closed") or 0) / 5.0)
        pnl_component = max(-80.0, min(120.0, net_pnl_value))
        pf_component = max(-30.0, min(45.0, (pf_value - 1.0) * 35.0)) if pf_value > 0 else -20.0
        be_component = max(-35.0, min(35.0, (be_gap or 0.0) * 100.0))
        dd_component = min(60.0, drawdown_value * 0.6)
        ranking_score = pnl_component + pf_component + be_component + closed_bonus - dd_component
        item["ranking_score"] = round(ranking_score, 3)
        item["ranking_grade"] = "A" if ranking_score >= 80 else "B" if ranking_score >= 35 else "C" if ranking_score >= 0 else "D"
        if closed < 5:
            item["action"] = "WAIT"
            item["action_label"] = "mehr Daten sammeln"
            item["action_reason"] = "zu wenige abgeschlossene Replay-Trades"
        elif ranking_score >= 35 and net_pnl_value > 0 and (be_gap is None or be_gap >= 0):
            item["action"] = "PRIORITY"
            item["action_label"] = "bevorzugt testen"
            item["action_reason"] = "positiver Score, Net PnL und Break-even-Abstand"
        elif net_pnl_value < 0 and float(item.get("sum_r") or 0.0) > 0 and pf_value > 1.0:
            item["action"] = "FEE_DRAG"
            item["action_label"] = "Gebühren / Größe prüfen"
            item["action_reason"] = "R-Ergebnis positiv, aber Netto nach Gebühren negativ"
        elif ranking_score < 0 or net_pnl_value < 0:
            item["action"] = "AVOID"
            item["action_label"] = "vorsichtig / meiden"
            item["action_reason"] = "negativer Score oder Net PnL"
        else:
            item["action"] = "WATCH"
            item["action_label"] = "beobachten"
            item["action_reason"] = "noch kein klarer Vorteil"
        item["ranking_reason"] = {
            "net_pnl_component": round(pnl_component, 3),
            "profit_factor_component": round(pf_component, 3),
            "break_even_gap_component": round(be_component, 3),
            "closed_bonus": round(closed_bonus, 3),
            "drawdown_penalty": round(dd_component, 3),
            "break_even_gap": round(be_gap, 6) if be_gap is not None else None,
        }
        item["sum_r"] = round(item["sum_r"], 6)
        item["gross_profit_r"] = round(item["gross_profit_r"], 6)
        item["gross_loss_r"] = round(item["gross_loss_r"], 6)
        item["gross_pnl_usd"] = round(item["gross_pnl_usd"], 4)
        item["estimated_fees_usd"] = round(item["estimated_fees_usd"], 4)
        item["net_pnl_usd"] = round(item["net_pnl_usd"], 4)
        item["gross_pnl_profit_usd"] = round(item["gross_pnl_profit_usd"], 4)
        item["gross_pnl_loss_usd"] = round(item["gross_pnl_loss_usd"], 4)
        item["gross_win_usd"] = round(item["gross_win_usd"], 4)
        item["gross_loss_usd"] = round(item["gross_loss_usd"], 4)
        item["net_win_usd"] = round(item["net_win_usd"], 4)
        item["net_loss_usd"] = round(item["net_loss_usd"], 4)
        item["max_drawdown_usd"] = round(item["max_drawdown_usd"], 4)
        item["best_pnl_series_usd"] = round(item["best_pnl_series_usd"], 4)
        item["worst_pnl_series_usd"] = round(item["worst_pnl_series_usd"], 4)
        result.append(item)
    result.sort(
        key=lambda item: (
            float(item.get("ranking_score") or 0.0),
            float(item.get("net_pnl_usd") or 0.0),
            float(item["profit_factor"]) if item.get("profit_factor") is not None else -1.0,
            -float(item.get("max_drawdown_usd") or 0.0),
        ),
        reverse=True,
    )
    for index, item in enumerate(result, start=1):
        item["rank"] = index
    return result


def save_replay_history(config: dict[str, Any], replay_payload: dict[str, Any]) -> dict[str, Any]:
    path = replay_history_path(config)
    path.parent.mkdir(parents=True, exist_ok=True)
    history = load_replay_history(config)
    runs = history.setdefault("runs", [])
    runs.append(compact_replay_history_run(replay_payload))
    max_runs = max(10, int(config.get("replay_history_max_runs", 120)))
    history["runs"] = runs[-max_runs:]
    history["asset_stats"] = replay_history_asset_stats(history["runs"], config)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return history


def replay_history_memory_test(config: dict[str, Any], symbol: str | None = None) -> dict[str, Any]:
    history = load_replay_history(config)
    runs = history.get("runs", []) if isinstance(history.get("runs"), list) else []
    clean_symbol = normalize_asset_symbol(symbol) if symbol else ""
    trades: list[dict[str, Any]] = []
    run_count = 0
    for run in runs:
        if not isinstance(run, dict):
            continue
        run_symbol = normalize_asset_symbol(run.get("symbol"))
        if clean_symbol and run_symbol != clean_symbol:
            continue
        run_count += 1
        for trade in run.get("trade_results", []) or []:
            if not isinstance(trade, dict):
                continue
            item = dict(trade)
            if not item.get("memory_key"):
                pattern = str(item.get("pattern_key") or "unknown")
                entry = str(item.get("entry_method") or "history")
                side = str(item.get("side") or "na")
                item["memory_key"] = "|".join(
                    [
                        f"symbol={run_symbol}",
                        f"side={side}",
                        f"pattern={pattern}",
                        f"entry={entry}",
                        "phase=history",
                        "volatility=history",
                        "session=history",
                    ]
                )
                item["memory_features"] = {"market_phase": "history", "volatility": "history", "session": "history", "entry_method": entry, "pattern_key": pattern}
            trades.append(item)
    memory_test = replay_memory_test_summary(trades, config)
    memory_test["source"] = "replay_history"
    memory_test["history_runs"] = run_count
    memory_test["symbol"] = clean_symbol or "__ALL__"
    return memory_test


def replay_history_memory_by_symbol(config: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    symbols = sorted({normalize_asset_symbol(run.get("symbol")) for run in runs if isinstance(run, dict) and normalize_asset_symbol(run.get("symbol"))})
    return {symbol: replay_history_memory_test(config, symbol) for symbol in symbols}


def public_replay_history(config: dict[str, Any]) -> dict[str, Any]:
    history = load_replay_history(config)
    runs = history.get("runs", []) if isinstance(history.get("runs"), list) else []
    public_runs = runs[-80:]
    return {
        "version": int(history.get("version", 1)),
        "path": str(replay_history_path(config)),
        "runs": public_runs,
        "asset_stats": replay_history_asset_stats(runs, config),
        "memory_test": replay_history_memory_test(config),
        "memory_test_by_symbol": replay_history_memory_by_symbol(config, public_runs),
    }


def clear_replay_history(config: dict[str, Any], symbol: str | None = None) -> dict[str, Any]:
    path = replay_history_path(config)
    history = load_replay_history(config)
    runs = history.get("runs", []) if isinstance(history.get("runs"), list) else []
    clean_symbol = str(symbol or "").replace(".P", "").split(":", 1)[0].strip().upper()
    if clean_symbol:
        kept_runs = [run for run in runs if str(run.get("symbol", "")).upper() != clean_symbol]
    else:
        kept_runs = []
    result = {
        "version": int(history.get("version", 1)),
        "runs": kept_runs,
        "asset_stats": replay_history_asset_stats(kept_runs, config),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return {
        "cleared_symbol": clean_symbol or None,
        "removed": len(runs) - len(kept_runs),
        "history": public_replay_history(config),
    }


def build_replay_preview(
    client: PhemexClient,
    memory: MemoryAgent,
    config: dict[str, Any],
    symbol: str,
    resolution: int,
    limit: int,
    steps: int,
) -> dict[str, Any]:
    clean_symbol = symbol.replace(".P", "").split(":", 1)[0].strip().upper() or str(config.get("symbols", ["BTCUSDT"])[0])
    safe_resolution = max(60, int(resolution))
    max_kline_limit = max(250, min(int(config.get("replay_kline_limit_max", 1000)), 1000))
    max_replay_steps = max(250, min(int(config.get("replay_max_steps", 750)), max_kline_limit))
    requested_steps = max(5, int(steps))
    safe_steps = max(5, min(requested_steps, max_replay_steps))
    warmup = max(
        40,
        int(config.get("indicator_hhll_range", 50)),
        int(config.get("indicator_sma_period", 50)),
        int(config.get("indicator_triple_ema_slow_period", 50)),
        int(config.get("brain_target_lookback_candles", 36)),
    )
    requested_limit = max(80, int(limit))
    needed_limit = safe_steps + warmup + 10
    safe_limit = max(80, min(max(requested_limit, needed_limit), max_kline_limit))
    kline_limit_fallback = False
    try:
        candles = client.get_klines(clean_symbol, safe_resolution, safe_limit)
    except Exception:
        if safe_limit <= 500:
            raise
        safe_limit = 500
        kline_limit_fallback = True
        candles = client.get_klines(clean_symbol, safe_resolution, safe_limit)
    available_replay_steps = max(0, len(candles) - warmup)
    effective_steps = max(0, min(safe_steps, available_replay_steps))
    start_index = max(warmup, len(candles) - effective_steps)
    value_gate = TradeValueGate(config)
    frames: list[dict[str, Any]] = []
    replay_trades: list[dict[str, Any]] = []
    response_frame_limit = max(40, min(int(config.get("replay_response_frame_limit", 160)), 300))
    summary: dict[str, Any] = {
        "frames": 0,
        "brain_long": 0,
        "brain_short": 0,
        "brain_wait": 0,
        "brain_blocked": 0,
        "ceo_long": 0,
        "ceo_short": 0,
        "ceo_wait": 0,
        "ceo_blocked": 0,
        "long_bias": 0,
        "short_bias": 0,
        "wait": 0,
        "blocked": 0,
        "candidates": 0,
        "gate_allowed": 0,
        "gate_blocked": 0,
        "replay_risk_blocked": 0,
        "replay_created": 0,
        "replay_opened": 0,
        "replay_tp": 0,
        "replay_sl": 0,
        "replay_expired": 0,
        "requested_steps": requested_steps,
        "safe_steps": safe_steps,
        "effective_steps": effective_steps,
        "available_candles": len(candles),
        "kline_limit": safe_limit,
        "kline_limit_fallback": kline_limit_fallback,
        "max_replay_steps": max_replay_steps,
        "warmup": warmup,
    }

    for end_index in range(start_index, len(candles)):
        window = candles[: end_index + 1]
        current = window[-1]
        replay_events = update_replay_trades(replay_trades, current)
        for event in replay_events:
            status = str(event.get("status", ""))
            if status == "open":
                summary["replay_opened"] += 1
            elif status == "tp":
                summary["replay_tp"] += 1
            elif status == "sl":
                summary["replay_sl"] += 1
            elif status == "expired":
                summary["replay_expired"] += 1
        scan = build_brain_scan_context(clean_symbol, window, window, None, config)
        indicator_context = build_indicator_response(
            symbol=clean_symbol,
            resolution=safe_resolution,
            candles=window,
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
            macd_lookback_days=int(config.get("indicator_macd_lookback_days", 0)),
            show_swing_labels=bool(config.get("indicator_show_swing_labels", True)),
            show_bos_choch=bool(config.get("indicator_show_bos_choch", True)),
            show_boxes=bool(config.get("indicator_show_boxes", True)),
            show_hma=bool(config.get("indicator_show_hma", False)),
            show_sma=bool(config.get("indicator_show_sma", True)),
            show_triple_ema=bool(config.get("indicator_show_triple_ema", False)),
            show_mfi=bool(config.get("indicator_show_mfi", True)),
            show_macd=bool(config.get("indicator_show_macd", True)),
            show_support_resistance=bool(config.get("indicator_show_support_resistance", True)),
            hma_period=int(config.get("indicator_hma_period", 20)),
            sma_period=int(config.get("indicator_sma_period", 50)),
            triple_ema_period=int(config.get("indicator_triple_ema_period", 20)),
            triple_ema_slow_period=int(config.get("indicator_triple_ema_slow_period", 50)),
            mfi_period=int(config.get("indicator_mfi_period", 14)),
            macd_fast_period=int(config.get("indicator_macd_fast_period", 12)),
            macd_slow_period=int(config.get("indicator_macd_slow_period", 26)),
            macd_signal_period=int(config.get("indicator_macd_signal_period", 9)),
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
            macd_color=str(config.get("indicator_macd_color", "#0ea5e9")),
            macd_signal_color=str(config.get("indicator_macd_signal_color", "#f97316")),
            macd_histogram_color=str(config.get("indicator_macd_histogram_color", "#64748b")),
            sr_support_color=str(config.get("indicator_sr_support_color", "#22c55e")),
            sr_resistance_color=str(config.get("indicator_sr_resistance_color", "#ef4444")),
        )
        agent_board = build_agent_board(
            symbol=clean_symbol,
            timeframe_seconds=safe_resolution,
            candles=window,
            indicator_data=indicator_context,
            scan=scan,
            config=config,
        )
        brain_decision = build_brain_decision(
            symbol=clean_symbol,
            timeframe_seconds=safe_resolution,
            candles=window,
            agent_board=agent_board,
            indicator_data=indicator_context,
            scan=scan,
            memory_state=memory.memory,
            config=config,
        )
        candidate = brain_decision.get("candidate") or None
        gate_result = None
        pnl_preview = replay_candidate_pnl_preview(candidate, config) if isinstance(candidate, dict) else None
        replay_created_trade = None
        if candidate:
            summary["candidates"] += 1
            gate_result = value_gate.evaluate(replay_gate_input_from_candidate(candidate, config))
            brain_decision = apply_economic_gate_to_brain_decision(brain_decision, gate_result)
            candidate = brain_decision.get("candidate") or candidate
            candidate_features = candidate.setdefault("features", {}) if isinstance(candidate, dict) else {}
            llm_gate = llm_role_trade_gate(brain_decision.get("llm_layer"), config)
            candidate_features["llm_role_gate"] = llm_gate
            candidate_features["llm_role_context"] = compact_llm_role_context(brain_decision, gate_result)
            candidate_features["llm_role_protocol"] = compact_llm_role_protocol(brain_decision.get("llm_layer"), llm_gate)
            brain_decision["llm_role_gate"] = llm_gate
            if gate_result.get("trade_allowed"):
                summary["gate_allowed"] += 1
                if not llm_gate.get("allowed", True):
                    summary["replay_risk_blocked"] += 1
                    replay_events.append(
                        {
                            "trade_id": replay_trade_id(candidate),
                            "status": "blocked",
                            "time": int(candidate.get("confirmation_candle_time") or candidate.get("signal_candle_time") or 0),
                            "price": candidate.get("entry_price"),
                            "reason": llm_gate.get("reason", "llm_role_gate"),
                            "llm_role_gate": llm_gate,
                        }
                    )
                else:
                    replay_created_trade = replay_trade_from_candidate(candidate, config, safe_resolution)
                    can_accept_replay, replay_block_reason = replay_can_accept_trade(replay_trades, replay_created_trade, config)
                    if not can_accept_replay:
                        summary["replay_risk_blocked"] += 1
                        replay_events.append(
                            {
                                "trade_id": replay_created_trade.get("id"),
                                "status": "blocked",
                                "time": replay_created_trade.get("created_at"),
                                "price": replay_created_trade.get("entry"),
                                "reason": replay_block_reason,
                            }
                        )
                    elif not any(trade.get("id") == replay_created_trade.get("id") for trade in replay_trades):
                        replay_trades.append(replay_created_trade)
                        summary["replay_created"] += 1
                        replay_events.append(
                            {
                                "trade_id": replay_created_trade.get("id"),
                                "status": "pending",
                                "time": replay_created_trade.get("created_at"),
                                "price": replay_created_trade.get("entry"),
                            }
                        )
            else:
                summary["gate_blocked"] += 1
        decision = str(brain_decision.get("decision", "WAIT")).upper()
        ceo = brain_decision.get("ceo") or {}
        ceo_signal = str(ceo.get("signal", "NEUTRAL")).upper()
        if decision == "LONG":
            summary["brain_long"] += 1
            summary["long_bias"] += 1
        elif decision == "SHORT":
            summary["brain_short"] += 1
            summary["short_bias"] += 1
        elif decision == "BLOCKED":
            summary["brain_blocked"] += 1
            summary["blocked"] += 1
        else:
            summary["brain_wait"] += 1
            summary["wait"] += 1

        if ceo_signal == "LONG":
            summary["ceo_long"] += 1
        elif ceo_signal == "SHORT":
            summary["ceo_short"] += 1
        elif ceo_signal == "BLOCKED":
            summary["ceo_blocked"] += 1
        else:
            summary["ceo_wait"] += 1

        summary["frames"] += 1
        frames.append(
            {
                "index": end_index,
                "timestamp": current.timestamp,
                "time_utc": format_time(current.timestamp),
                "open": current.open,
                "high": current.high,
                "low": current.low,
                "close": current.close,
                "ceo_signal": ceo_signal,
                "ceo_score": ceo.get("score"),
                "decision": decision,
                "brain_score": (brain_decision.get("brain") or {}).get("score"),
                "brain_message": (brain_decision.get("brain") or {}).get("message"),
                "candidate": compact_replay_frame_candidate(candidate),
                "candidate_pnl": pnl_preview,
                "gate": gate_result,
                "llm_role_context": (candidate.get("features") or {}).get("llm_role_context") if isinstance(candidate, dict) else None,
                "llm_role_protocol": (candidate.get("features") or {}).get("llm_role_protocol") if isinstance(candidate, dict) else None,
                "memory_match": brain_decision.get("memory_match"),
                "replay_events": replay_events,
                "replay_trade_created": compact_replay_frame_candidate(replay_created_trade),
                "replay_trade_summary": lightweight_replay_trade_summary(replay_trades),
            }
        )
        if len(frames) > response_frame_limit:
            del frames[0 : len(frames) - response_frame_limit]

    final_events = finalize_replay_trades(replay_trades, candles[-1] if candles else None)
    for event in final_events:
        status = str(event.get("status", ""))
        if status == "tp":
            summary["replay_tp"] += 1
        elif status == "sl":
            summary["replay_sl"] += 1
        elif status == "expired":
            summary["replay_expired"] += 1
    if frames and final_events:
        frames[-1].setdefault("replay_events", []).extend(final_events)
        frames[-1]["replay_trade_summary"] = lightweight_replay_trade_summary(replay_trades)

    final_replay_summary = replay_trade_summary(replay_trades)
    memory_test = replay_memory_test_summary(replay_trades, config)
    summary.update(
        {
            "replay_pending": final_replay_summary["pending"],
            "replay_open": final_replay_summary["open"],
            "replay_closed": final_replay_summary["closed"],
            "replay_win_rate": final_replay_summary["win_rate"],
            "replay_sum_r": final_replay_summary["sum_r"],
            "replay_expectancy_r": final_replay_summary["expectancy_r"],
            "replay_profit_factor": final_replay_summary["profit_factor"],
            "replay_max_drawdown_r": final_replay_summary["max_drawdown_r"],
            "replay_gross_pnl_usd": final_replay_summary["gross_pnl_usd"],
            "replay_estimated_fees_usd": final_replay_summary["estimated_fees_usd"],
            "replay_net_pnl_usd": final_replay_summary["net_pnl_usd"],
            "replay_pnl_win_rate": final_replay_summary["pnl_win_rate"],
            "replay_net_profit_factor_usd": final_replay_summary["net_profit_factor_usd"],
            "replay_max_drawdown_usd": final_replay_summary["max_drawdown_usd"],
            "replay_best_pnl_series_usd": final_replay_summary["best_pnl_series_usd"],
            "replay_worst_pnl_series_usd": final_replay_summary["worst_pnl_series_usd"],
            "replay_break_even_win_rate": final_replay_summary["break_even_win_rate"],
            "memory_test_buckets": memory_test["bucket_count"],
            "memory_test_completed": memory_test["completed_trades"],
            "memory_test_win_rate": memory_test["win_rate"],
            "memory_test_sum_r": memory_test["sum_r"],
            "replay_no_closed_reason": replay_no_closed_reason(summary) if int(final_replay_summary.get("closed", 0) or 0) <= 0 else None,
            "finalized_at_replay_end": len(final_events),
            "frames_returned": len(frames),
            "frames_truncated": summary["frames"] > len(frames),
            "response_frame_limit": response_frame_limit,
        }
    )

    replay_payload = {
        "mode": "replay_preview",
        "symbol": clean_symbol,
        "resolution": safe_resolution,
        "limit": safe_limit,
        "warmup": warmup,
        "summary": summary,
        "frames": frames,
        "replay_trades": replay_trades,
        "memory_test": memory_test,
    }
    replay_payload["history"] = save_replay_history(config, replay_payload)
    return replay_payload


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


def llm_role_trade_gate(llm_layer: dict[str, Any] | None, config: dict[str, Any]) -> dict[str, Any]:
    if not bool(config.get("llm_role_team_enabled", config.get("brain_llm_layer_enabled", False))):
        return {"allowed": True, "reason": "llm_role_team_disabled", "decision": "OFF"}
    layer = llm_layer if isinstance(llm_layer, dict) else {}
    judge = layer.get("judge") if isinstance(layer.get("judge"), dict) else {}
    decision = str(layer.get("decision") or judge.get("decision") or "WAIT").upper()
    verdict = str(layer.get("verdict") or "NO_DATA").upper()
    if decision == "BLOCK" or bool(layer.get("block_hint", False)):
        return {"allowed": False, "reason": "llm_role_judge_block", "decision": decision, "verdict": verdict}
    if bool(config.get("llm_role_required_for_trade", False)) and decision != "APPROVE":
        return {"allowed": False, "reason": "llm_role_approval_required", "decision": decision, "verdict": verdict}
    return {"allowed": True, "reason": "llm_role_gate_passive", "decision": decision, "verdict": verdict}


def compact_llm_role_context(brain_decision: dict[str, Any] | None, value_result: dict[str, Any] | None = None) -> dict[str, Any]:
    brain = brain_decision if isinstance(brain_decision, dict) else {}
    candidate = brain.get("candidate") if isinstance(brain.get("candidate"), dict) else {}
    features = candidate.get("features") if isinstance(candidate.get("features"), dict) else {}
    memory_match = brain.get("memory_match") if isinstance(brain.get("memory_match"), dict) else {}
    score_breakdown = features.get("brain_score_breakdown") if isinstance(features.get("brain_score_breakdown"), dict) else {}
    gate = value_result if isinstance(value_result, dict) else brain.get("economic_gate") if isinstance(brain.get("economic_gate"), dict) else {}
    return {
        "version": 1,
        "symbol": candidate.get("symbol"),
        "decision": brain.get("decision"),
        "candidate_reason": brain.get("candidate_reason"),
        "side": candidate.get("side"),
        "entry_price": candidate.get("entry_price"),
        "sl_price": candidate.get("sl_price"),
        "tp_price": candidate.get("tp_price"),
        "entry_method": candidate.get("entry_method"),
        "target_method": candidate.get("target_method"),
        "score": candidate.get("score"),
        "confidence": candidate.get("confidence"),
        "pattern_key": candidate.get("pattern_key"),
        "memory": {
            "count": memory_match.get("count"),
            "win_rate": memory_match.get("win_rate"),
            "avg_r": memory_match.get("avg_r"),
            "entry_offset_in_box": memory_match.get("entry_offset_in_box"),
        },
        "scores": {
            "long_score": score_breakdown.get("long_score"),
            "short_score": score_breakdown.get("short_score"),
            "long_count": score_breakdown.get("long_count"),
            "short_count": score_breakdown.get("short_count"),
            "conflict": score_breakdown.get("conflict"),
        },
        "economic_gate": {
            "trade_allowed": gate.get("trade_allowed"),
            "reason": gate.get("reason"),
            "rr": gate.get("rr"),
            "fee_to_risk_fraction": gate.get("fee_to_risk_fraction"),
            "risk_usd": gate.get("risk_usd"),
            "net_profit_fraction": gate.get("net_profit_fraction"),
        },
    }


def compact_llm_role_protocol(llm_layer: dict[str, Any] | None, llm_gate: dict[str, Any] | None = None) -> dict[str, Any]:
    layer = llm_layer if isinstance(llm_layer, dict) else {}
    judge = layer.get("judge") if isinstance(layer.get("judge"), dict) else {}
    gate = llm_gate if isinstance(llm_gate, dict) else {}
    roles = []
    for role in layer.get("roles") or []:
        if not isinstance(role, dict):
            continue
        roles.append(
            {
                "role_key": role.get("role_key"),
                "role": role.get("role"),
                "decision": str(role.get("decision", "WAIT")).upper(),
                "confidence": role.get("confidence"),
                "hard_block": bool(role.get("hard_block", False)),
                "reasons": list(role.get("reasons") or [])[:4],
            }
        )
    return {
        "version": 1,
        "enabled": bool(layer.get("enabled", False)),
        "provider": layer.get("provider"),
        "model": layer.get("model"),
        "verdict": layer.get("verdict"),
        "decision": str(layer.get("decision") or judge.get("decision") or "WAIT").upper(),
        "block_hint": bool(layer.get("block_hint", False)),
        "gate": {
            "allowed": gate.get("allowed"),
            "reason": gate.get("reason"),
            "decision": gate.get("decision"),
            "verdict": gate.get("verdict"),
        },
        "judge": {
            "decision": str(judge.get("decision", layer.get("decision", "WAIT"))).upper(),
            "confidence": judge.get("confidence"),
            "summary": judge.get("summary", layer.get("risk_note")),
            "conflict_note": judge.get("conflict_note", layer.get("conflict_note")),
            "advice": judge.get("advice", layer.get("advice")),
        },
        "roles": roles,
    }


def attach_llm_role_trace(setup: Setup, brain_decision: dict[str, Any], value_result: dict[str, Any] | None, llm_gate: dict[str, Any] | None = None) -> None:
    setup.features["llm_role_context"] = compact_llm_role_context(brain_decision, value_result)
    setup.features["llm_role_protocol"] = compact_llm_role_protocol(brain_decision.get("llm_layer"), llm_gate)


def active_order_lock_snapshot(broker: PaperBroker, symbol: str | None = None) -> dict[str, Any]:
    active = [trade for trade in broker.trades if trade.status in ("pending", "open")]
    if symbol:
        symbol_active = [trade for trade in active if trade.setup.symbol == symbol]
    else:
        symbol_active = active
    primary = symbol_active[0] if symbol_active else (active[0] if active else None)
    return {
        "locked": bool(active),
        "scope": "symbol" if symbol_active else ("global" if active else "none"),
        "active_total": len(active),
        "active_symbol": len(symbol_active),
        "order_id": primary.id if primary else None,
        "order_symbol": primary.setup.symbol if primary else None,
        "order_status": primary.status if primary else None,
        "order_side": primary.setup.side if primary else None,
    }


def order_lock_brain_decision(
    symbol: str,
    agent_board: dict[str, Any],
    scan: dict[str, Any],
    config: dict[str, Any],
    lock: dict[str, Any],
) -> dict[str, Any]:
    order_id = lock.get("order_id") or "-"
    message = f"WAIT: Entry-Suche pausiert, aktive Order {order_id} ({lock.get('order_status', '-')}) laeuft."
    brain_report = {
        "agent_name": "Trade Planner",
        "function": "Entry-Suche steuern",
        "signal": "NEUTRAL",
        "score": 0,
        "reads": f"active_order={order_id} | active_total={lock.get('active_total', 0)}",
        "message": message,
        "conflict": False,
        "blocking": True,
        "details": {"active_order_lock": lock},
    }
    ceo_report = {
        "agent_name": "CEO / Judge",
        "function": "Nur neue Kandidaten freigeben, wenn keine aktive Order laeuft",
        "signal": "NEUTRAL",
        "score": 0,
        "reads": f"Entry-Suche gesperrt fuer {symbol}",
        "message": message,
        "conflict": False,
        "blocking": True,
        "details": {"active_order_lock": lock},
    }
    llm_layer = default_role_team_response(
        config,
        "WAIT",
        f"LLM-Rollenteam nicht gestartet: aktive Order {order_id}. Neue LLM-Abfrage erst wieder bei freier Entry-Suche.",
        enabled=bool(config.get("llm_role_team_enabled", config.get("brain_llm_layer_enabled", False))),
    )
    return {
        "decision": "WAIT",
        "scores": {},
        "agent_bias": "NEUTRAL",
        "agent_bias_score": 0,
        "candidate_reason": "active_order_lock",
        "brain": brain_report,
        "ceo": ceo_report,
        "candidate": None,
        "memory_match": {},
        "score_breakdown": {"decision": "WAIT", "candidate_reason": "active_order_lock", "active_order_lock": lock},
        "active_order_lock": lock,
        "llm_layer": llm_layer,
    }


def append_trade_change_events(changes: list[VirtualTrade], cycle: dict[str, Any]) -> None:
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


def compact_llm_analysis_entry(symbol: str, brain_decision: dict[str, Any] | None, config: dict[str, Any], skipped_reason: str | None = None) -> dict[str, Any] | None:
    brain = brain_decision or {}
    layer = brain.get("llm_layer") if isinstance(brain.get("llm_layer"), dict) else {}
    if not layer and not skipped_reason:
        return None
    trace = layer.get("context_trace") if isinstance(layer.get("context_trace"), dict) else {}
    roles = layer.get("roles") if isinstance(layer.get("roles"), list) else []
    judge = layer.get("judge") if isinstance(layer.get("judge"), dict) else {}
    usage = layer.get("usage_estimate") if isinstance(layer.get("usage_estimate"), dict) else None
    if usage is None:
        usage = estimate_llm_usage(trace, roles, judge, config)
    active_order_lock = brain.get("active_order_lock") if isinstance(brain.get("active_order_lock"), dict) else None
    event_type = "skipped" if skipped_reason else ("completed" if roles else "waiting")
    reason = skipped_reason or brain.get("candidate_reason") or layer.get("message") or layer.get("advice") or "-"
    now = int(time.time())
    return {
        "time": now,
        "time_utc": format_time(now),
        "symbol": symbol,
        "type": event_type,
        "reason": reason,
        "provider": layer.get("provider") or str(config.get("llm_provider", "ollama")),
        "model": layer.get("model") or str(config.get("openai_model" if str(config.get("llm_provider", "ollama")).lower() == "openai" else "ollama_model", "qwen2.5:3b")),
        "decision": layer.get("decision") or judge.get("decision") or brain.get("decision") or "-",
        "verdict": layer.get("verdict") or "-",
        "role_count": len(roles),
        "duration_seconds": layer.get("duration_seconds"),
        "role_duration_seconds": layer.get("role_duration_seconds"),
        "judge_duration_seconds": layer.get("judge_duration_seconds"),
        "timing": layer.get("timing") if isinstance(layer.get("timing"), dict) else None,
        "summary": judge.get("summary") or layer.get("risk_note") or layer.get("message") or "-",
        "active_sources": trace.get("active_sources") or [],
        "candidate": trace.get("candidate") or brain.get("candidate"),
        "active_order_lock": active_order_lock,
        "usage_estimate": usage,
    }


def append_llm_analysis_history(history: list[dict[str, Any]], entry: dict[str, Any] | None, max_items: int = 40) -> list[dict[str, Any]]:
    if not entry:
        return history[-max_items:]
    comparable_keys = ("symbol", "type", "reason", "decision", "verdict", "role_count")
    last = history[-1] if history else {}
    same = all(last.get(key) == entry.get(key) for key in comparable_keys)
    last_lock = last.get("active_order_lock") if isinstance(last.get("active_order_lock"), dict) else {}
    entry_lock = entry.get("active_order_lock") if isinstance(entry.get("active_order_lock"), dict) else {}
    if same and last_lock.get("order_id") == entry_lock.get("order_id") and entry.get("type") in {"skipped", "waiting"}:
        updated = dict(last)
        updated["time"] = entry["time"]
        updated["time_utc"] = entry["time_utc"]
        updated["repeat_count"] = int(updated.get("repeat_count", 1)) + 1
        history[-1] = updated
    else:
        item = dict(entry)
        item["repeat_count"] = 1
        history.append(item)
    return history[-max_items:]


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
    previous_status = status_store.snapshot()
    llm_analysis_history = list(previous_status.get("llm_analysis_history", [])) if isinstance(previous_status.get("llm_analysis_history"), list) else []
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
            "llm_analysis_history": llm_analysis_history,
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

        changes = broker.update(symbol, confirm_candles) if config.get("paper_trading_enabled", True) else []
        append_trade_change_events(changes, cycle)

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
            macd_lookback_days=int(config.get("indicator_macd_lookback_days", 0)),
            show_swing_labels=bool(config.get("indicator_show_swing_labels", True)),
            show_bos_choch=bool(config.get("indicator_show_bos_choch", True)),
            show_boxes=bool(config.get("indicator_show_boxes", True)),
            show_hma=bool(config.get("indicator_show_hma", False)),
            show_sma=bool(config.get("indicator_show_sma", True)),
            show_triple_ema=bool(config.get("indicator_show_triple_ema", False)),
            show_mfi=bool(config.get("indicator_show_mfi", True)),
            show_macd=bool(config.get("indicator_show_macd", True)),
            show_support_resistance=bool(config.get("indicator_show_support_resistance", True)),
            hma_period=int(config.get("indicator_hma_period", 20)),
            sma_period=int(config.get("indicator_sma_period", 50)),
            triple_ema_period=int(config.get("indicator_triple_ema_period", 20)),
            triple_ema_slow_period=int(config.get("indicator_triple_ema_slow_period", 50)),
            mfi_period=int(config.get("indicator_mfi_period", 14)),
            macd_fast_period=int(config.get("indicator_macd_fast_period", 12)),
            macd_slow_period=int(config.get("indicator_macd_slow_period", 26)),
            macd_signal_period=int(config.get("indicator_macd_signal_period", 9)),
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
            macd_color=str(config.get("indicator_macd_color", "#0ea5e9")),
            macd_signal_color=str(config.get("indicator_macd_signal_color", "#f97316")),
            macd_histogram_color=str(config.get("indicator_macd_histogram_color", "#64748b")),
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
        order_lock = active_order_lock_snapshot(broker, symbol)
        if bool(config.get("pause_entry_search_while_order_active", True)) and order_lock.get("locked"):
            brain_decision = order_lock_brain_decision(symbol, agent_board, scan_explanation, config, order_lock)
            agent_board = refresh_agent_board_risk_context(
                agent_board,
                scan_explanation,
                None,
                broker,
                config,
                broker_allowed=False,
                broker_reason="active_order_lock",
            )
            agent_board["brain"] = brain_decision.get("brain")
            agent_board["ceo"] = brain_decision.get("ceo", agent_board.get("ceo"))
            agent_board["trade_plan"] = None
            agent_board["memory_match"] = brain_decision.get("memory_match")
            agent_board["llm_layer"] = brain_decision.get("llm_layer")
            agent_board["active_order_lock"] = order_lock
            cycle["symbols"][symbol]["agents"] = agent_board
            cycle["agents"][symbol] = agent_board
            cycle["symbols"][symbol]["brain"] = brain_decision
            cycle["symbols"][symbol]["active_order_lock"] = order_lock
            cycle.setdefault("brains", {})[symbol] = brain_decision
            update_scan_with_brain_decision(scan_explanation, brain_decision)
            llm_analysis_history = append_llm_analysis_history(
                llm_analysis_history,
                compact_llm_analysis_entry(symbol, brain_decision, config, skipped_reason="active_order_lock"),
            )
            cycle["events"].append({"type": "entry_search_paused", "reason": "active_order_lock", "symbol": symbol, "active_order_lock": order_lock})
            continue

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
            agent_board = refresh_agent_board_risk_context(agent_board, scan_explanation, setup, broker, config)
            cycle["symbols"][symbol]["agents"] = agent_board
            cycle["agents"][symbol] = agent_board
            value_result = value_gate.evaluate(brain_gate_input_from_setup(setup))
            brain_decision = apply_economic_gate_to_brain_decision(brain_decision, value_result)
            brain_decision["llm_layer"] = refresh_llm_layer_after_economic_gate(agent_board, scan_explanation, brain_decision, config, indicator_context)
            agent_board["ceo"] = brain_decision.get("ceo", agent_board.get("ceo"))
            agent_board["economic_gate"] = value_result
            agent_board["llm_layer"] = brain_decision.get("llm_layer")
            agent_board = refresh_agent_board_risk_context(agent_board, scan_explanation, setup, broker, config, value_result=value_result)
            cycle["symbols"][symbol]["agents"] = agent_board
            cycle["agents"][symbol] = agent_board
            cycle["symbols"][symbol]["brain"] = brain_decision
            cycle["brains"][symbol] = brain_decision
            if not value_result.get("trade_allowed", False):
                attach_llm_role_trace(setup, brain_decision, value_result, None)
                agent_board = refresh_agent_board_risk_context(agent_board, scan_explanation, setup, broker, config, value_result=value_result, broker_allowed=False, broker_reason="value_gate")
                cycle["symbols"][symbol]["agents"] = agent_board
                cycle["agents"][symbol] = agent_board
                cycle["events"].append({"type": "blocked", "reason": "value_gate", "value_result": value_result, "setup": asdict(setup), "brain": brain_decision})
            else:
                setup.features["value_gate"] = value_result
                setup.features["ceo_decision"] = brain_decision.get("ceo")
                llm_gate = llm_role_trade_gate(brain_decision.get("llm_layer"), config)
                setup.features["llm_role_gate"] = llm_gate
                brain_decision["llm_role_gate"] = llm_gate
                attach_llm_role_trace(setup, brain_decision, value_result, llm_gate)
                if not llm_gate.get("allowed", True):
                    agent_board = refresh_agent_board_risk_context(agent_board, scan_explanation, setup, broker, config, value_result=value_result, broker_allowed=False, broker_reason=str(llm_gate.get("reason", "llm_role_gate")))
                    cycle["symbols"][symbol]["agents"] = agent_board
                    cycle["agents"][symbol] = agent_board
                    cycle["events"].append({"type": "blocked", "reason": llm_gate.get("reason", "llm_role_gate"), "llm_role_gate": llm_gate, "setup": asdict(setup), "brain": brain_decision})
                    continue
                if config.get("paper_trading_enabled", True):
                    allowed, block_reason = broker.can_accept_setup(setup)
                    agent_board = refresh_agent_board_risk_context(agent_board, scan_explanation, setup, broker, config, value_result=value_result, broker_allowed=allowed, broker_reason=block_reason)
                    cycle["symbols"][symbol]["agents"] = agent_board
                    cycle["agents"][symbol] = agent_board
                    if not allowed:
                        event = {"type": "blocked", "reason": block_reason, "setup": asdict(setup), "brain": brain_decision}
                        cycle["events"].append(event)
                    else:
                        trade = broker.add_setup(setup)
                        if trade:
                            agent_board = refresh_agent_board_risk_context(agent_board, scan_explanation, setup, broker, config, value_result=value_result, broker_allowed=True, broker_reason=None, paper_trade_created=True)
                            cycle["symbols"][symbol]["agents"] = agent_board
                            cycle["agents"][symbol] = agent_board
                            print_signal(trade)
                            cycle["signals"].append(asdict(trade))
                else:
                    print_signal(VirtualTrade(id=f"signal-only-{setup.symbol}-{setup.confirmation_candle_time}", setup=setup, status="expired", created_at=int(time.time()), expires_at=setup.confirmation_candle_time))
                    cycle["signals"].append({"paper_trade_created": False, "setup": asdict(setup), "brain": brain_decision})
        else:
            cycle["events"].append({"type": "no_setup", "reason": brain_decision.get("decision", scan_explanation.get("reason")), "symbol": symbol, "scan": scan_explanation, "brain": brain_decision})

        llm_analysis_history = append_llm_analysis_history(
            llm_analysis_history,
            compact_llm_analysis_entry(symbol, brain_decision, config),
        )

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
        "llm_analysis_history": llm_analysis_history,
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






def save_replay_rule_weights(config: dict[str, Any], rules: list[dict[str, Any]], enabled: bool) -> dict[str, Any]:
    if not isinstance(rules, list):
        raise ValueError("rules must be a list")
    min_count = max(3, int(config.get("replay_rule_weight_min_count", 5)))
    max_abs = max(0, int(config.get("replay_rule_max_abs_adjustment", 12)))
    good_bonus = max(0, min(max_abs, int(config.get("replay_rule_good_bonus", 6))))
    bad_penalty = max(-max_abs, min(0, int(config.get("replay_rule_bad_penalty", -10))))
    clean_rules: list[dict[str, Any]] = []
    for rule in rules[:50]:
        if not isinstance(rule, dict):
            continue
        key = str(rule.get("key", "")).strip()
        if not key:
            continue
        count = int(rule.get("count") or 0)
        quality = str(rule.get("quality", "WATCH")).upper()
        if quality not in ("GOOD", "BAD"):
            continue
        if count < min_count:
            continue
        adjustment = good_bonus if quality == "GOOD" else bad_penalty
        parsed_key = parse_replay_memory_key(key)
        symbol = str(rule.get("symbol") or parsed_key.get("symbol") or "").upper()
        pattern_key = str(rule.get("pattern_key") or parsed_key.get("pattern_key") or key)
        scope = str(rule.get("scope") or config.get("replay_rule_scope", "asset")).lower()
        if scope not in ("asset", "global"):
            scope = "asset"
        clean_rules.append(
            {
                "key": key,
                "pattern_key": pattern_key,
                "symbol": symbol,
                "scope": scope,
                "quality": quality,
                "count": count,
                "min_count": min_count,
                "adjustment": adjustment,
                "win_rate": rule.get("win_rate"),
                "avg_r": rule.get("avg_r"),
                "sum_r": rule.get("sum_r"),
            }
        )
    return update_config_file(config, {"replay_rule_weight_enabled": bool(enabled) and bool(clean_rules), "replay_rule_weight_rules": clean_rules, "replay_rule_scope": str(config.get("replay_rule_scope", "asset"))})

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
                    watchlist_symbols = [str(item.get("symbol", "")).replace(".P", "").split(":", 1)[0].strip().upper() for item in WATCHLIST_ASSETS if str(item.get("symbol", "")).strip()]
                    requested_symbol = str(query.get("symbol", [active_symbols[0] if active_symbols else "BTCUSDT"])[0]).replace(".P", "").split(":", 1)[0].strip().upper()
                    allowed_symbols = set(active_symbols) | set(watchlist_symbols)
                    symbol = requested_symbol if requested_symbol in allowed_symbols else (active_symbols[0] if active_symbols else requested_symbol)
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
                    macd_fast_period = max(1, min(int(query.get("macd_fast_period", [config.get("indicator_macd_fast_period", 12)])[0]), 500))
                    macd_slow_period = max(macd_fast_period + 1, min(int(query.get("macd_slow_period", [config.get("indicator_macd_slow_period", 26)])[0]), 500))
                    macd_signal_period = max(1, min(int(query.get("macd_signal_period", [config.get("indicator_macd_signal_period", 9)])[0]), 500))
                    box_extend_candles = max(2, min(int(query.get("box_extend_candles", [config.get("indicator_box_extend_candles", 4)])[0]), 100))
                    legacy_lookback_days = int(config.get("indicator_lookback_days", 3))
                    bos_choch_lookback_days = max(0, min(int(query.get("bos_choch_lookback_days", [config.get("indicator_bos_choch_lookback_days", legacy_lookback_days)])[0]), 365))
                    boxes_lookback_days = max(0, min(int(query.get("boxes_lookback_days", [config.get("indicator_boxes_lookback_days", legacy_lookback_days)])[0]), 365))
                    swing_labels_lookback_days = max(0, min(int(query.get("swing_labels_lookback_days", [config.get("indicator_swing_labels_lookback_days", legacy_lookback_days)])[0]), 365))
                    hma_lookback_days = max(0, min(int(query.get("hma_lookback_days", [config.get("indicator_hma_lookback_days", 0)])[0]), 365))
                    sma_lookback_days = max(0, min(int(query.get("sma_lookback_days", [config.get("indicator_sma_lookback_days", 0)])[0]), 365))
                    triple_ema_lookback_days = max(0, min(int(query.get("triple_ema_lookback_days", [config.get("indicator_triple_ema_lookback_days", 0)])[0]), 365))
                    mfi_lookback_days = max(0, min(int(query.get("mfi_lookback_days", [config.get("indicator_mfi_lookback_days", 0)])[0]), 365))
                    macd_lookback_days = max(0, min(int(query.get("macd_lookback_days", [config.get("indicator_macd_lookback_days", 0)])[0]), 365))
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
                    show_macd = indicator_query_bool("show_macd", bool(config.get("indicator_show_macd", True)))
                    show_support_resistance = indicator_query_bool("show_support_resistance", bool(config.get("indicator_show_support_resistance", True)))
                    hma_color = str(query.get("hma_color", [config.get("indicator_hma_color", "#7c3aed")])[0])
                    sma_color = str(query.get("sma_color", [config.get("indicator_sma_color", "#06b6d4")])[0])
                    triple_ema_color = str(query.get("triple_ema_color", [config.get("indicator_triple_ema_color", "#d97706")])[0])
                    triple_ema_slow_color = str(query.get("triple_ema_slow_color", [config.get("indicator_triple_ema_slow_color", "#2563eb")])[0])
                    mfi_color = str(query.get("mfi_color", [config.get("indicator_mfi_color", "#db2777")])[0])
                    macd_color = str(query.get("macd_color", [config.get("indicator_macd_color", "#0ea5e9")])[0])
                    macd_signal_color = str(query.get("macd_signal_color", [config.get("indicator_macd_signal_color", "#f97316")])[0])
                    macd_histogram_color = str(query.get("macd_histogram_color", [config.get("indicator_macd_histogram_color", "#64748b")])[0])
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
                        macd_lookback_days=macd_lookback_days,
                        show_swing_labels=show_swing_labels,
                        show_bos_choch=show_bos_choch,
                        show_boxes=show_boxes,
                        show_hma=show_hma,
                        show_sma=show_sma,
                        show_triple_ema=show_triple_ema,
                        show_mfi=show_mfi,
                        show_macd=show_macd,
                        show_support_resistance=show_support_resistance,
                        hma_period=hma_period,
                        sma_period=sma_period,
                        triple_ema_period=triple_ema_period,
                        triple_ema_slow_period=triple_ema_slow_period,
                        mfi_period=mfi_period,
                        macd_fast_period=macd_fast_period,
                        macd_slow_period=macd_slow_period,
                        macd_signal_period=macd_signal_period,
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
                        macd_color=macd_color,
                        macd_signal_color=macd_signal_color,
                        macd_histogram_color=macd_histogram_color,
                        sr_support_color=sr_support_color,
                        sr_resistance_color=sr_resistance_color,
                    )
                    body["limit"] = limit
                    self._send(200, "application/json; charset=utf-8", json.dumps(body).encode("utf-8"))
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(500, "application/json; charset=utf-8", body)
                return
            if request_path == "/api/replay-preview":
                try:
                    replay_symbols: list[str] = []
                    for source_symbol in config.get("asset_list", []) or []:
                        clean = normalize_asset_symbol(source_symbol)
                        if clean and clean not in replay_symbols:
                            replay_symbols.append(clean)
                    for asset in config.get("watchlist_assets", []) or []:
                        clean = normalize_asset_symbol(asset.get("symbol") if isinstance(asset, dict) else asset)
                        if clean and clean not in replay_symbols:
                            replay_symbols.append(clean)
                    for source_symbol in config.get("symbols", []) or []:
                        clean = normalize_asset_symbol(source_symbol)
                        if clean and clean not in replay_symbols:
                            replay_symbols.append(clean)
                    if not replay_symbols:
                        replay_symbols = default_asset_symbols(config)
                    requested_symbol = str(query.get("symbol", [replay_symbols[0] if replay_symbols else "BTCUSDT"])[0])
                    symbol = normalize_asset_symbol(requested_symbol) or (replay_symbols[0] if replay_symbols else "BTCUSDT")
                    if replay_symbols and symbol not in replay_symbols:
                        raise ValueError(f"Replay Asset nicht in Asset-Liste: {symbol}")
                    resolution = int(query.get("resolution", [config.get("signal_timeframe_seconds", 300)])[0])
                    limit = int(query.get("limit", [config.get("kline_limit", 500)])[0])
                    steps = int(query.get("steps", [80])[0])
                    body = build_replay_preview(client, memory, config, symbol, resolution, limit, steps)
                    self._send(200, "application/json; charset=utf-8", json.dumps(body).encode("utf-8"))
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(500, "application/json; charset=utf-8", body)
                return
            if request_path == "/api/replay-history":
                payload = json.dumps(public_replay_history(config)).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/status":
                status_payload = status_store.snapshot()
                status_payload["llm_hardware"] = ollama_hardware_status(config)
                payload = json.dumps(status_payload).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/bot-control-ui":
                try:
                    query = parse_qs(parsed_url.query)
                    action = str((query.get("action") or [""])[0]).lower()
                    if action == "start":
                        update_config_file(config, {"observer_enabled": True})
                    elif action == "stop":
                        update_config_file(config, {"observer_enabled": False})
                    else:
                        raise ValueError("action must be start or stop")
                    current = status_store.snapshot()
                    current["config"] = public_config(config)
                    current.setdefault("bot", {})["scanner_status"] = "running" if config.get("observer_enabled") else "stopped"
                    status_store.update(current)
                    self.send_response(303)
                    self.send_header("Location", "/")
                    self.end_headers()
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode("utf-8")
                    self._send(400, "application/json; charset=utf-8", body)
                return
            if request_path == "/api/settings":
                payload = json.dumps(public_config(config)).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/env-settings":
                payload = json.dumps(read_env_settings(config)).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/openai-test":
                payload = json.dumps(test_openai_connection(config)).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/ollama-test":
                payload = json.dumps(test_ollama_connection(config)).encode("utf-8")
                self._send(200, "application/json; charset=utf-8", payload)
                return
            if request_path == "/api/ollama-speed-test":
                payload = json.dumps(test_ollama_speed(config)).encode("utf-8")
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

            if request_path == "/api/replay-history/clear":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length).decode("utf-8")
                    payload = json.loads(body or "{}")
                    raw_symbol = payload.get("symbol")
                    symbol = str(raw_symbol).strip().upper() if raw_symbol is not None else None
                    if symbol in ("", "__ALL__", "ALL", "GESAMT"):
                        symbol = None
                    result = clear_replay_history(config, symbol)
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
                    existing["single_timeframe_mode"] = True
                    existing["confirmation_timeframe_seconds"] = int(existing.get("signal_timeframe_seconds", 300))
                    existing["llm_role_timeout_seconds"] = int(existing.get("phemex_poll_seconds", existing.get("poll_seconds", 30)))
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

            if request_path == "/api/replay-rule-weights":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    body = self.rfile.read(length).decode("utf-8")
                    payload = json.loads(body or "{}")
                    result = save_replay_rule_weights(
                        config,
                        payload.get("rules", []),
                        bool(payload.get("enabled", True)),
                    )
                    current = status_store.snapshot()
                    current["config"] = result
                    status_store.update(current)
                    self._send(200, "application/json; charset=utf-8", json.dumps(result).encode("utf-8"))
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
