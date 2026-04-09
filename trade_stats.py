# ==================================================
# trade_stats.py
# ==================================================
# PERSISTENTE TRADE-STATISTIK
# - wird vom Bot bei EXIT aufgerufen
# - speichert aggregierte Werte in JSON
# - keine Abhängigkeit vom Bot-State
# ==================================================

import json
import os
from config import Config

class TradeStats:
    def __init__(
        self,
        path="debug/trade_stats.json",
        csv_path="debug/trade_equity.csv",
        attempt_path="debug/attempt_records.jsonl",
        outcome_path="debug/outcome_records.jsonl",
        reset=True,
    ):
        self.path = path
        self.csv_path = csv_path
        self.attempt_path = attempt_path
        self.outcome_path = outcome_path

        if str(getattr(Config, "MODE", "LIVE")).upper() == "LIVE":
            try:
                from ph_ohlcv import create_exchange, get_account_value

                exchange = create_exchange()
                start_equity = float(get_account_value(exchange, Config.USDT))
            except Exception:
                start_equity = float(getattr(Config, "START_EQUITY", 0.0) or 0.0)
        else:
            start_equity = float(getattr(Config, "START_EQUITY", 0.0) or 0.0)

        self.data = {
            "trades": 0,
            "tp": 0,
            "sl": 0,
            "pnl_netto": start_equity,
            "pnl_tp": 0.0,
            "pnl_sl": 0.0,
            "cancels": 0,
            "attempts": 0,
            "attempts_submitted": 0,
            "attempts_filled": 0,
            "attempts_cancelled": 0,
            "attempts_timeout": 0,
            "attempts_blocked": 0,
            "attempts_skipped": 0,
            "attempts_observed": 0,
            "attempts_replanned": 0,
            "attempts_withheld": 0,
            "attempt_structure_zone": 0,
            "attempt_non_structure_zone": 0,
            "current_timestamp": None,
            "last_outcome_decomposition": {},
            "recent_attempts": [],
            "exploration_trades": 0,
            "exploration_tp": 0,
            "exploration_sl": 0,
            "exploration_cancels": 0,
            "exploration_pnl": 0.0,
            "equity_peak": start_equity,
            "max_drawdown_abs": 0.0,
            "max_drawdown_pct": 0.0,
            "kpi_summary": {},
        }

        if reset:
            # JSON zurücksetzen
            self._save()

            # CSV bei Neustart überschreiben
            if os.path.exists(self.csv_path):
                try:
                    os.remove(self.csv_path)
                except Exception:
                    pass

            if os.path.exists(self.attempt_path):
                try:
                    os.remove(self.attempt_path)
                except Exception:
                    pass

            if os.path.exists(self.outcome_path):
                try:
                    os.remove(self.outcome_path)
                except Exception:
                    pass
        else:
            self._load()


    # ─────────────────────────────────────────────
    def _load(self):
        if not os.path.exists(self.path):
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                self.data.update(obj)
                self.data.pop("attempt_records", None)
                self.data.pop("outcome_records", None)
        except Exception:
            pass
    # ─────────────────────────────────────────────
    def _normalize_record_value(self, value):
        if isinstance(value, dict):
            normalized = {}
            for key, item in value.items():
                if key is None:
                    continue
                normalized[str(key)] = self._normalize_record_value(item)
            return normalized

        if isinstance(value, list):
            return [self._normalize_record_value(item) for item in list(value or [])[:128]]

        if value is None or isinstance(value, (str, int, float, bool)):
            return value

        return str(value)

    # ─────────────────────────────────────────────
    def _append_record_file(self, path: str, record: dict):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(dict(record or {}), ensure_ascii=False) + "\n")
        except Exception:
            pass

    # ─────────────────────────────────────────────
    def _read_record_file(self, path: str, limit: int | None = None) -> list[dict]:
        records = []

        try:
            if not os.path.exists(path):
                return records

            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = str(line or "").strip()
                    if not line:
                        continue

                    try:
                        item = json.loads(line)
                    except Exception:
                        continue

                    if isinstance(item, dict):
                        records.append(item)
        except Exception:
            return []

        if limit is not None:
            return records[-max(1, int(limit or 1)):]

        return records

    # ─────────────────────────────────────────────
    def _structure_band(self, structure_quality: float) -> str:
        quality = float(structure_quality or 0.0)

        if quality >= 0.70:
            return "high"

        if quality >= 0.55:
            return "mid"

        return "low"

    # ─────────────────────────────────────────────
    def _rebuild_kpi_summary(self):
        trades = int(self.data.get("trades", 0) or 0)
        tp = int(self.data.get("tp", 0) or 0)
        sl = int(self.data.get("sl", 0) or 0)
        cancels = int(self.data.get("cancels", 0) or 0)
        attempts = int(self.data.get("attempts", 0) or 0)

        pnl_netto = float(self.data.get("pnl_netto", 0.0) or 0.0)
        pnl_tp = float(self.data.get("pnl_tp", 0.0) or 0.0)
        pnl_sl = float(self.data.get("pnl_sl", 0.0) or 0.0)

        avg_win = (pnl_tp / tp) if tp > 0 else 0.0
        avg_loss = (pnl_sl / sl) if sl > 0 else 0.0
        profit_factor = abs(pnl_tp / pnl_sl) if pnl_sl != 0 else 0.0
        expectancy = (pnl_netto / trades) if trades > 0 else 0.0
        winrate = (tp / trades) if trades > 0 else 0.0

        attempt_feedback = self.get_attempt_feedback()

        outcomes = self._read_record_file(self.outcome_path)

        band_stats = {
            "high": {"count": 0, "tp": 0, "sl": 0, "cancel": 0, "pnl": 0.0},
            "mid": {"count": 0, "tp": 0, "sl": 0, "cancel": 0, "pnl": 0.0},
            "low": {"count": 0, "tp": 0, "sl": 0, "cancel": 0, "pnl": 0.0},
        }

        for item in outcomes:
            record = dict(item or {})
            band = self._structure_band(record.get("structure_quality", 0.0))
            reason = str(record.get("reason", "") or "").strip().lower()

            band_stats[band]["count"] += 1
            band_stats[band]["pnl"] += float(record.get("pnl", 0.0) or 0.0)

            if reason == "tp_hit":
                band_stats[band]["tp"] += 1
            elif reason == "sl_hit":
                band_stats[band]["sl"] += 1
            else:
                band_stats[band]["cancel"] += 1

        for band_name, payload in band_stats.items():
            count = int(payload.get("count", 0) or 0)
            tp_count = int(payload.get("tp", 0) or 0)
            payload["winrate"] = float(tp_count / count) if count > 0 else 0.0
            payload["avg_pnl"] = float(payload.get("pnl", 0.0) or 0.0) / count if count > 0 else 0.0

        self.data["kpi_summary"] = {
            "proof": {
                "winrate": float(winrate),
                "profit_factor": float(profit_factor),
                "expectancy": float(expectancy),
                "avg_win": float(avg_win),
                "avg_loss": float(avg_loss),
                "attempts_per_trade": float(attempts / max(1, trades)),
                "attempt_fill_rate": float(self.data.get("attempts_filled", 0) or 0) / max(1, attempts),
                "attempt_zone_share": float(self.data.get("attempt_structure_zone", 0) or 0) / max(1, attempts),
                "attempt_density": float(attempt_feedback.get("attempt_density", 0.0) or 0.0),
                "context_quality": float(attempt_feedback.get("context_quality", 0.0) or 0.0),
                "overtrade_pressure": float(attempt_feedback.get("overtrade_pressure", 0.0) or 0.0),
                "observe_share": float(attempt_feedback.get("observe_share", 0.0) or 0.0),
                "replan_share": float(attempt_feedback.get("replan_share", 0.0) or 0.0),
                "withheld_share": float(attempt_feedback.get("withheld_share", 0.0) or 0.0),
                "pressure_to_capacity": float(attempt_feedback.get("pressure_to_capacity", 0.0) or 0.0),
                "recovery_need": float(attempt_feedback.get("recovery_need", 0.0) or 0.0),
                "regulated_courage": float(attempt_feedback.get("regulated_courage", 0.0) or 0.0),
                "courage_gap": float(attempt_feedback.get("courage_gap", 0.0) or 0.0),
                "action_inhibition": float(attempt_feedback.get("action_inhibition", 0.0) or 0.0),
                "action_clearance": float(attempt_feedback.get("action_clearance", 0.0) or 0.0),
                "regulation_before_action": float(attempt_feedback.get("regulation_before_action", 0.0) or 0.0),
                "max_drawdown_abs": float(self.data.get("max_drawdown_abs", 0.0) or 0.0),
                "max_drawdown_pct": float(self.data.get("max_drawdown_pct", 0.0) or 0.0),
            },
            "structure_bands": {
                "high": dict(band_stats["high"]),
                "mid": dict(band_stats["mid"]),
                "low": dict(band_stats["low"]),
            },
            "totals": {
                "trades": int(trades),
                "tp": int(tp),
                "sl": int(sl),
                "cancels": int(cancels),
                "attempts": int(attempts),
                "attempts_observed": int(self.data.get("attempts_observed", 0) or 0),
                "attempts_replanned": int(self.data.get("attempts_replanned", 0) or 0),
                "attempts_withheld": int(self.data.get("attempts_withheld", 0) or 0),
                "pnl_netto": float(pnl_netto),
            },
        }

    # ─────────────────────────────────────────────
    def _pick_fields(self, payload: dict, keys: list[str]) -> dict:
        source = dict(payload or {})
        result = {}

        for key in list(keys or []):
            if key not in source:
                continue

            value = source.get(key)
            if value is None:
                continue

            result[str(key)] = value

        return result

    # ─────────────────────────────────────────────
    def _compact_context(self, context: dict) -> dict:
        normalized_context = self._normalize_record_value(context or {})

        compact = {
            "state": self._pick_fields(normalized_context.get("state", {}), [
                "energy",
                "coherence",
                "asymmetry",
                "coh_zone",
                "self_state",
                "attractor",
            ]),
            "focus": self._pick_fields(normalized_context.get("focus", {}), [
                "focus_point",
                "focus_confidence",
                "target_lock",
                "target_drift",
            ]),
            "experience": self._pick_fields(normalized_context.get("experience", {}), [
                "entry_expectation",
                "target_expectation",
                "approach_pressure",
                "pressure_release",
                "experience_regulation",
                "reflection_maturity",
                "load_bearing_capacity",
                "protective_width_regulation",
                "protective_courage",
            ]),
            "field_state": self._pick_fields(normalized_context.get("field_state", {}), [
                "field_density",
                "field_stability",
                "regulatory_load",
                "action_capacity",
                "recovery_need",
                "survival_pressure",
                "pressure_to_capacity",
            ]),
            "regulation_snapshot": self._normalize_record_value(normalized_context.get("regulation_snapshot", {})),
            "state_before": self._normalize_record_value(normalized_context.get("state_before", {})),
            "state_after": self._normalize_record_value(normalized_context.get("state_after", {})),
            "state_delta": self._normalize_record_value(normalized_context.get("state_delta", {})),
            "felt_state": self._pick_fields(normalized_context.get("felt_state", {}), [
                "confidence",
                "urgency",
                "pressure",
                "hesitation",
                "protective_tension",
                "courage_tension",
                "relief_need",
                "regulated_confidence",
            ]),
            "meta_regulation_state": self._pick_fields(normalized_context.get("meta_regulation_state", {}), [
                "decision",
                "observation_priority",
                "uncertainty_load",
                "regulatory_balance",
                "regulated_courage",
                "courage_gap",
                "action_inhibition",
                "action_clearance",
                "pre_action_phase",
                "dominant_tension_cause",
            ]),
            "expectation_state": self._pick_fields(normalized_context.get("expectation_state", {}), [
                "entry_expectation",
                "target_expectation",
                "approach_pressure",
                "pressure_release",
                "experience_regulation",
                "reflection_maturity",
                "load_bearing_capacity",
            ]),
            "trade_plan": self._pick_fields(normalized_context.get("trade_plan", {}), [
                "decision",
                "entry_price",
                "sl_price",
                "tp_price",
                "rr_value",
                "risk_model_score",
                "reward_model_score",
                "entry_validity_band",
            ]),
            "signal": self._pick_fields(normalized_context.get("signal", {}), [
                "signature_bias",
                "signature_block",
                "signature_quality",
                "signature_distance",
                "context_cluster_id",
                "context_cluster_bias",
                "context_cluster_quality",
                "context_cluster_distance",
                "context_cluster_block",
                "inhibition_level",
                "habituation_level",
                "competition_bias",
                "observation_mode",
                "long_score",
                "short_score",
            ]),
        }
        return {key: value for key, value in compact.items() if value}
    # ─────────────────────────────────────────────
    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception:
            pass

    # ─────────────────────────────────────────────
    def _extract_structure_quality(self, context: dict) -> float:
        ctx = dict(context or {})
        world_state = dict(ctx.get("world_state", {}) or {})
        structure = dict(ctx.get("structure_perception_state", {}) or {})
        if not structure and isinstance(world_state.get("structure_perception_state"), dict):
            structure = dict(world_state.get("structure_perception_state", {}) or {})
        if not structure and isinstance(ctx.get("outer_visual_perception_state"), dict):
            structure = dict(ctx.get("outer_visual_perception_state", {}) or {})
        try:
            return float(structure.get("structure_quality", 0.0) or 0.0)
        except Exception:
            return 0.0

    # ─────────────────────────────────────────────
    def _build_attempt_record(self, status_key: str, context: dict, structure_quality: float, structure_bucket: str) -> dict:
        compact_context = self._compact_context(context or {})

        return {
            "event": "attempt",
            "status": str(status_key or "unknown"),
            "timestamp": self.data.get("current_timestamp"),
            "structure_quality": float(structure_quality),
            "structure_bucket": str(structure_bucket),
            "context": compact_context,
        }

    # ─────────────────────────────────────────────
    def get_attempt_feedback(self, window: int = 24) -> dict:
        recent_attempts = list(self.data.get("recent_attempts", []) or [])
        items = recent_attempts[-max(1, int(window or 1)):]

        if not items:
            return {
                "recent_attempt_count": 0,
                "attempt_density": 0.0,
                "fill_ratio": 0.0,
                "blocked_ratio": 0.0,
                "cancel_ratio": 0.0,
                "timeout_ratio": 0.0,
                "zone_ratio": 0.0,
                "mean_structure_quality": 0.0,
                "context_quality": 0.0,
                "overtrade_pressure": 0.0,
                "observe_share": 0.0,
                "replan_share": 0.0,
                "withheld_share": 0.0,
                "pressure_to_capacity": 0.0,
                "recovery_need": 0.0,
                "regulated_courage": 0.0,
                "courage_gap": 0.0,
                "action_inhibition": 0.0,
                "action_clearance": 0.0,
                "regulation_before_action": 0.0,
            }

        total = float(len(items))
        filled = 0.0
        blocked = 0.0
        cancelled = 0.0
        timeout = 0.0
        observed = 0.0
        replanned = 0.0
        withheld = 0.0
        zone = 0.0
        structure_sum = 0.0
        pressure_sum = 0.0
        recovery_sum = 0.0
        regulated_courage_sum = 0.0
        courage_gap_sum = 0.0
        action_inhibition_sum = 0.0
        action_clearance_sum = 0.0
        regulation_before_action_sum = 0.0

        for item in items:
            status = str((item or {}).get("status", "") or "").strip().lower()
            structure_quality = float((item or {}).get("structure_quality", 0.0) or 0.0)
            structure_bucket = str((item or {}).get("structure_bucket", "") or "").strip().lower()
            pressure_to_capacity = float((item or {}).get("pressure_to_capacity", 0.0) or 0.0)
            recovery_need = float((item or {}).get("recovery_need", 0.0) or 0.0)
            regulated_courage = float((item or {}).get("regulated_courage", 0.0) or 0.0)
            courage_gap = float((item or {}).get("courage_gap", 0.0) or 0.0)
            action_inhibition = float((item or {}).get("action_inhibition", 0.0) or 0.0)
            action_clearance = float((item or {}).get("action_clearance", 0.0) or 0.0)
            pre_action_phase = str((item or {}).get("pre_action_phase", "") or "").strip().lower()

            structure_sum += structure_quality
            pressure_sum += pressure_to_capacity
            recovery_sum += recovery_need
            regulated_courage_sum += regulated_courage
            courage_gap_sum += courage_gap
            action_inhibition_sum += action_inhibition
            action_clearance_sum += action_clearance

            if status == "filled":
                filled += 1.0
            elif status in ("blocked", "blocked_value_gate"):
                blocked += 1.0
            elif status == "cancelled":
                cancelled += 1.0
            elif status == "timeout":
                timeout += 1.0
            elif status == "observed_only":
                observed += 1.0
            elif status == "replanned":
                replanned += 1.0
            elif status == "withheld":
                withheld += 1.0

            if structure_bucket == "zone":
                zone += 1.0

            if pre_action_phase in ("regulated", "ready", "stable", "aligned"):
                regulation_before_action_sum += 1.0

        attempt_density = max(0.0, min(1.0, total / max(8.0, float(window) * 0.50)))
        fill_ratio = filled / total
        blocked_ratio = blocked / total
        cancel_ratio = cancelled / total
        timeout_ratio = timeout / total
        observe_share = observed / total
        replan_share = replanned / total
        withheld_share = withheld / total
        zone_ratio = zone / total
        mean_structure_quality = structure_sum / total
        avg_pressure_to_capacity = pressure_sum / total
        avg_recovery_need = recovery_sum / total
        avg_regulated_courage = regulated_courage_sum / total
        avg_courage_gap = courage_gap_sum / total
        avg_action_inhibition = action_inhibition_sum / total
        avg_action_clearance = action_clearance_sum / total
        regulation_before_action = regulation_before_action_sum / total

        context_quality = max(
            0.0,
            min(
                1.0,
                (mean_structure_quality * 0.34)
                + (zone_ratio * 0.16)
                + (fill_ratio * 0.10)
                + (avg_regulated_courage * 0.12)
                + (avg_action_clearance * 0.12)
                + (regulation_before_action * 0.10)
                + (observe_share * 0.04)
                + (replan_share * 0.04)
                - (min(1.0, avg_pressure_to_capacity / 2.0) * 0.08)
                - (avg_recovery_need * 0.06)
                - (avg_courage_gap * 0.06)
                - (avg_action_inhibition * 0.06)
                - (cancel_ratio * 0.04)
                - (timeout_ratio * 0.06),
            ),
        )

        overtrade_pressure = max(
            0.0,
            min(
                1.0,
                (attempt_density * 0.32)
                + ((1.0 - context_quality) * 0.20)
                + (blocked_ratio * 0.10)
                + (cancel_ratio * 0.08)
                + (timeout_ratio * 0.12)
                + (min(1.0, avg_pressure_to_capacity / 2.0) * 0.10)
                + (avg_recovery_need * 0.04)
                + (avg_action_inhibition * 0.04),
            ),
        )

        return {
            "recent_attempt_count": int(total),
            "attempt_density": float(attempt_density),
            "fill_ratio": float(fill_ratio),
            "blocked_ratio": float(blocked_ratio),
            "cancel_ratio": float(cancel_ratio),
            "timeout_ratio": float(timeout_ratio),
            "zone_ratio": float(zone_ratio),
            "mean_structure_quality": float(mean_structure_quality),
            "context_quality": float(context_quality),
            "overtrade_pressure": float(overtrade_pressure),
            "observe_share": float(observe_share),
            "replan_share": float(replan_share),
            "withheld_share": float(withheld_share),
            "pressure_to_capacity": float(avg_pressure_to_capacity),
            "recovery_need": float(avg_recovery_need),
            "regulated_courage": float(avg_regulated_courage),
            "courage_gap": float(avg_courage_gap),
            "action_inhibition": float(avg_action_inhibition),
            "action_clearance": float(avg_action_clearance),
            "regulation_before_action": float(regulation_before_action),
        }

    # ─────────────────────────────────────────────
    def on_attempt(self, *, status: str, context: dict = None): 
        status_key = str(status or "").strip().lower()
        normalized_context = self._normalize_record_value(context or {})
        compact_context = self._compact_context(normalized_context)

        self.data["attempts"] = int(self.data.get("attempts", 0) or 0) + 1
        if status_key == "submitted":
            self.data["attempts_submitted"] = int(self.data.get("attempts_submitted", 0) or 0) + 1
        elif status_key == "filled":
            self.data["attempts_filled"] = int(self.data.get("attempts_filled", 0) or 0) + 1
        elif status_key == "cancelled":
            self.data["attempts_cancelled"] = int(self.data.get("attempts_cancelled", 0) or 0) + 1
        elif status_key == "timeout":
            self.data["attempts_timeout"] = int(self.data.get("attempts_timeout", 0) or 0) + 1
        elif status_key in ("blocked", "blocked_value_gate"):
            self.data["attempts_blocked"] = int(self.data.get("attempts_blocked", 0) or 0) + 1
        elif status_key == "skipped":
            self.data["attempts_skipped"] = int(self.data.get("attempts_skipped", 0) or 0) + 1
        elif status_key == "observed_only":
            self.data["attempts_observed"] = int(self.data.get("attempts_observed", 0) or 0) + 1
        elif status_key == "replanned":
            self.data["attempts_replanned"] = int(self.data.get("attempts_replanned", 0) or 0) + 1
        elif status_key == "withheld":
            self.data["attempts_withheld"] = int(self.data.get("attempts_withheld", 0) or 0) + 1

        structure_quality = self._extract_structure_quality(normalized_context)
        if structure_quality >= 0.55:
            self.data["attempt_structure_zone"] = int(self.data.get("attempt_structure_zone", 0) or 0) + 1
            structure_bucket = "zone"
        else:
            self.data["attempt_non_structure_zone"] = int(self.data.get("attempt_non_structure_zone", 0) or 0) + 1
            structure_bucket = "non_zone"

        attempt_record = self._build_attempt_record(
            status_key,
            normalized_context,
            structure_quality,
            structure_bucket,
        )

        field_state = dict(compact_context.get("field_state", {}) or {})
        meta_regulation_state = dict(compact_context.get("meta_regulation_state", {}) or {})

        recent = list(self.data.get("recent_attempts", []) or [])
        recent.append(
            {
                "status": status_key or "unknown",
                "structure_quality": float(structure_quality),
                "structure_bucket": structure_bucket,
                "pressure_to_capacity": float(field_state.get("pressure_to_capacity", 0.0) or 0.0),
                "recovery_need": float(field_state.get("recovery_need", 0.0) or 0.0),
                "regulated_courage": float(meta_regulation_state.get("regulated_courage", 0.0) or 0.0),
                "courage_gap": float(meta_regulation_state.get("courage_gap", 0.0) or 0.0),
                "action_inhibition": float(meta_regulation_state.get("action_inhibition", 0.0) or 0.0),
                "action_clearance": float(meta_regulation_state.get("action_clearance", 0.0) or 0.0),
                "pre_action_phase": str(meta_regulation_state.get("pre_action_phase", "") or ""),
            }
        )
        self.data["recent_attempts"] = recent[-80:]
        self._append_record_file(self.attempt_path, attempt_record)
        self._rebuild_kpi_summary()
        self._save()

    # ─────────────────────────────────────────────
    def on_exit(
        self,
        *,
        entry: float,
        tp: float,
        sl: float,
        reason: str,
        side: str = None,
        amount: float = 1.0,
        exploration_trade: bool = False,
        outcome_decomposition: dict = None,
        context: dict = None,
    ):
        pnl = 0.0

        side = str(side).upper().strip() if side is not None else "LONG"

        if reason == "tp_hit":
            if side == "LONG":
                pnl = (tp - entry) * float(amount)
            elif side == "SHORT":
                pnl = (entry - tp) * float(amount)
            else:
                return
            self.data["tp"] += 1

            if exploration_trade:
                self.data["exploration_tp"] = int(self.data.get("exploration_tp", 0) or 0) + 1

        elif reason == "sl_hit":
            if side == "LONG":
                pnl = (sl - entry) * float(amount)
            elif side == "SHORT":
                pnl = (entry - sl) * float(amount)
            else:
                return
            self.data["sl"] += 1

            if exploration_trade:
                self.data["exploration_sl"] = int(self.data.get("exploration_sl", 0) or 0) + 1

        else:
            return

        # Fees berücksichtigen
        # pnl = pnl - Config.FEE_PER_TRADE

        # Fees berücksichtigen (prozentual pro Seite + optional fixer Abzug)
        exit_price = tp if reason == "tp_hit" else sl
        fee_rate = getattr(Config, "FEE_RATE", 0.0) or 0.0
        fees = (
            (entry * float(amount) * fee_rate) +
            (exit_price * float(amount) * fee_rate) +
            (Config.FEE_PER_TRADE or 0.0)
        )
        pnl = pnl - fees

        compact_context = self._compact_context(context or {})
        normalized_decomposition = self._normalize_record_value(outcome_decomposition or {})

        self.data["trades"] += 1
        self.data["last_outcome_decomposition"] = dict(normalized_decomposition or {})

        if exploration_trade:
            self.data["exploration_trades"] = int(self.data.get("exploration_trades", 0) or 0) + 1
            self.data["exploration_pnl"] = float(self.data.get("exploration_pnl", 0.0) or 0.0) + float(pnl)

        # GESAMT = Summe aller Trades (Gewinn + Verlust)
        self.data["pnl_netto"] += pnl

        # GEWINN = Summe nur positiver Trades
        if pnl > 0:
            self.data["pnl_tp"] += pnl

        # VERLUST = Summe nur negativer Trades
        if pnl < 0:
            self.data["pnl_sl"] += pnl

        structure_quality = self._extract_structure_quality(compact_context)
        structure_bucket = "zone" if structure_quality >= 0.55 else "non_zone"

        outcome_record = {
            "event": "trade_exit",
            "reason": str(reason or "").strip().lower(),
            "timestamp": self.data.get("current_timestamp"),
            "side": side,
            "entry": float(entry),
            "tp": float(tp),
            "sl": float(sl),
            "amount": float(amount),
            "pnl": float(pnl),
            "structure_quality": float(structure_quality),
            "structure_bucket": structure_bucket,
            "outcome_decomposition": normalized_decomposition,
            "context": compact_context,
        }

        self._append_record_file(self.outcome_path, outcome_record)

        equity_peak = max(
            float(self.data.get("equity_peak", self.data.get("pnl_netto", 0.0)) or self.data.get("pnl_netto", 0.0)),
            float(self.data.get("pnl_netto", 0.0) or 0.0),
        )
        self.data["equity_peak"] = float(equity_peak)

        drawdown_abs = max(0.0, equity_peak - float(self.data.get("pnl_netto", 0.0) or 0.0))
        drawdown_pct = (drawdown_abs / equity_peak) if equity_peak > 0.0 else 0.0

        self.data["max_drawdown_abs"] = float(max(float(self.data.get("max_drawdown_abs", 0.0) or 0.0), drawdown_abs))
        self.data["max_drawdown_pct"] = float(max(float(self.data.get("max_drawdown_pct", 0.0) or 0.0), drawdown_pct))

        self._rebuild_kpi_summary()
        self._save()

        # ---------------- CSV Equity Export ----------------
        try:
            os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)

            write_header = not os.path.exists(self.csv_path)

            with open(self.csv_path, "a", encoding="utf-8") as f:
                if write_header:
                    f.write("trade,pnl_netto,pnl_tp,pnl_sl\n")

                f.write(
                    f"{self.data['trades']},"
                    f"{self.data['pnl_netto']},"
                    f"{self.data['pnl_tp']},"
                    f"{self.data['pnl_sl']}\n"
                )
        except Exception:
            pass

    # ─────────────────────────────────────────────
    # Snapshot mit zusätzlichen Kennzahlen
    # ─────────────────────────────────────────────
    def snapshot(self) -> dict:
        """
        Aktuellen Stand zurückgeben (read-only Kopie)
        """
        data = dict(self.data)

        trades = data.get("trades", 0)
        pnl_tp = data.get("pnl_tp", 0.0)
        pnl_sl = data.get("pnl_sl", 0.0)

        avg_win = (pnl_tp / data.get("tp", 1)) if data.get("tp", 0) > 0 else 0.0
        avg_loss = (pnl_sl / data.get("sl", 1)) if data.get("sl", 0) > 0 else 0.0

        profit_factor = (
            abs(pnl_tp / pnl_sl)
            if pnl_sl != 0
            else 0.0
        )

        expectancy = (
            (data.get("pnl_netto", 0.0) / trades)
            if trades > 0
            else 0.0
        )

        exploration_trades = int(data.get("exploration_trades", 0) or 0)
        exploration_tp = int(data.get("exploration_tp", 0) or 0)
        exploration_sl = int(data.get("exploration_sl", 0) or 0)
        exploration_pnl = float(data.get("exploration_pnl", 0.0) or 0.0)

        exploration_avg = (
            exploration_pnl / exploration_trades
            if exploration_trades > 0
            else 0.0
        )

        self._rebuild_kpi_summary()
        kpi_summary = dict(self.data.get("kpi_summary", {}) or {})
        proof = dict(kpi_summary.get("proof", {}) or {})

        data.pop("attempt_records", None)
        data.pop("outcome_records", None)

        data.update({
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "expectancy": expectancy,
            "exploration_avg": exploration_avg,
            "normal_trades": max(0, trades - exploration_trades),
            "normal_tp": max(0, int(data.get("tp", 0) or 0) - exploration_tp),
            "normal_sl": max(0, int(data.get("sl", 0) or 0) - exploration_sl),
            "normal_cancels": max(0, int(data.get("cancels", 0) or 0) - int(data.get("exploration_cancels", 0) or 0)),
            "attempts_per_trade": (
                float(data.get("attempts", 0) or 0) / max(1, int(trades))
            ),
            "attempt_zone_share": (
                float(data.get("attempt_structure_zone", 0) or 0) / max(1, int(data.get("attempts", 0) or 0))
            ),
            "attempt_fill_rate": (
                float(data.get("attempts_filled", 0) or 0) / max(1, int(data.get("attempts", 0) or 0))
            ),
            "attempt_density": float(proof.get("attempt_density", 0.0) or 0.0),
            "context_quality": float(proof.get("context_quality", 0.0) or 0.0),
            "overtrade_pressure": float(proof.get("overtrade_pressure", 0.0) or 0.0),
            "observe_share": float(proof.get("observe_share", 0.0) or 0.0),
            "replan_share": float(proof.get("replan_share", 0.0) or 0.0),
            "withheld_share": float(proof.get("withheld_share", 0.0) or 0.0),
            "pressure_to_capacity": float(proof.get("pressure_to_capacity", 0.0) or 0.0),
            "recovery_need": float(proof.get("recovery_need", 0.0) or 0.0),
            "regulated_courage": float(proof.get("regulated_courage", 0.0) or 0.0),
            "courage_gap": float(proof.get("courage_gap", 0.0) or 0.0),
            "action_inhibition": float(proof.get("action_inhibition", 0.0) or 0.0),
            "action_clearance": float(proof.get("action_clearance", 0.0) or 0.0),
            "regulation_before_action": float(proof.get("regulation_before_action", 0.0) or 0.0),
            "max_drawdown_abs": float(proof.get("max_drawdown_abs", 0.0) or 0.0),
            "max_drawdown_pct": float(proof.get("max_drawdown_pct", 0.0) or 0.0),
            "kpi_summary": kpi_summary,
        })

        return data
    # ─────────────────────────────────────────────
    def on_cancel(self, *, order_id=None, cause: str = None, exploration_trade: bool = False, outcome_decomposition: dict = None, context: dict = None):
        """
        Order wurde gecancelt bevor ein Trade/Exit stattgefunden hat.
        Keine PnL-Änderung – nur Zählung.
        """
        try:
            normalized_context = self._normalize_record_value(context or {})
            normalized_decomposition = self._normalize_record_value(outcome_decomposition or {})
            structure_quality = self._extract_structure_quality(normalized_context)
            structure_bucket = "zone" if structure_quality >= 0.55 else "non_zone"

            self.data["cancels"] = int(self.data.get("cancels", 0) or 0) + 1
            self.data["last_outcome_decomposition"] = dict(normalized_decomposition or {})
            if exploration_trade:
                self.data["exploration_cancels"] = int(self.data.get("exploration_cancels", 0) or 0) + 1

            compact_context = self._compact_context(normalized_context)
            outcome_record = {
                    "event": "cancel",
                    "reason": "cancel",
                    "timestamp": self.data.get("current_timestamp"),
                    "order_id": None if order_id is None else str(order_id),
                    "cause": None if cause is None else str(cause),
                    "structure_quality": float(structure_quality),
                    "structure_bucket": structure_bucket,
                    "outcome_decomposition": normalized_decomposition,
                    "context": compact_context,
                }

            self._append_record_file(self.outcome_path, outcome_record)
            self._rebuild_kpi_summary()
            self._save()
        except Exception:
            pass
