# ==================================================
# bot.py
# Pipeline:
# OHLC
# -> Exit / Pending Handling
# -> Dummy Entry Slot
# -> TradeValueGate
# -> Order / Pending Entry
# ==================================================
import queue
import threading
import time

from config import Config
from csv_feed import CSVFeed
from trade_stats import TradeStats
from bot_engine.exit_engine import ExitEngine
from bot_engine.mcm_core_engine import build_tension_state_from_window, build_visual_market_state
from bot_engine.strukture_engine import StructureEngine
from bot_gates.trade_value_gate import TradeValueGate

from place_orders import place_order, consume_cancelled, get_active_order_snapshot, is_order_active
from debug_reader import dbr_debug
from ph_ohlcv import _build_candle_state
from bot_gate_funktions import evaluate_entry_decision
from MCM_Brain_Modell import apply_outcome_stimulus, create_mcm_brain, create_mcm_runtime, mark_runtime_episode_event, step_mcm_runtime, step_mcm_runtime_idle
from memory_state import apply_memory_state, read_memory_state, save_memory_state


DEBUG = True
STRUCTURE_ENGINE = StructureEngine()
# --------------------------------------------------


class Bot:
    # --------------------------------------------------
    def __init__(self, filepath: str):

        self.feed = CSVFeed(filepath)
        self.exit_engine = ExitEngine()
        self.value_gate = TradeValueGate()
        self.stats = TradeStats(
            path="debug/trade_stats.json",
            csv_path="debug/trade_equity.csv",
            reset=True,
        )

        self.position = None
        self.pending_entry = None
        self.processed = 0
        self.current_timestamp = None

        self.mcm_brain = create_mcm_brain() if bool(getattr(Config, "MCM_ENABLED", True)) else None
        self.mcm_last_state = None
        self.mcm_last_action = None
        self.mcm_last_attractor = None
        self.mcm_snapshot = None
        self.mcm_pause_left = 0
        self.field_density = 0.0
        self.field_stability = 0.0
        self.regulatory_load = 0.0
        self.action_capacity = 0.0
        self.recovery_need = 0.0
        self.survival_pressure = 0.0

        self.focus_point = None
        self.focus_confidence = 0.0
        self.target_lock = 0.0
        self.target_drift = 0.0

        self.entry_expectation = 0.0
        self.target_expectation = 0.0
        self.approach_pressure = 0.0
        self.pressure_release = 0.0
        self.experience_regulation = 0.0
        self.reflection_maturity = 0.0
        self.load_bearing_capacity = 0.0
        self.protective_width_regulation = 0.0
        self.protective_courage = 0.0

        self.signature_memory = {}
        self.last_signature_key = None
        self.last_signature_outcome = None
        self.last_signature_context = None

        self.context_clusters = {}
        self.context_cluster_seq = 0
        self.last_context_cluster_id = None
        self.last_context_cluster_key = None

        self.inhibition_level = 0.0
        self.habituation_level = 0.0
        self.competition_bias = 0.0
        self.observation_mode = False
        self.last_signal_relevance = 0.0

        self.tension_state = {}
        self.visual_market_state = {}
        self.structure_perception_state = {}
        self.outer_market_state = {}
        self.perception_state = {}
        self.outer_visual_perception_state = {}
        self.inner_field_perception_state = {}
        self.processing_state = {}
        self.expectation_state = {}
        self.felt_state = {}
        self.thought_state = {}
        self.meta_regulation_state = {}
        self.last_outcome_decomposition = {}

        self.mcm_runtime_snapshot = {}
        self.mcm_runtime_decision_state = {}
        self.mcm_runtime_brain_snapshot = {}
        self.mcm_runtime_market_ticks = 0
        self.mcm_episode_seq = 0
        self.mcm_decision_episode = {}
        self.mcm_decision_episode_internal = {}
        self.mcm_experience_space = {}
        self.mcm_last_observe_timestamp = None
        self.mcm_runtime = None

        self._memory_state_payload = read_memory_state()
        self._memory_state_mcm_loaded = False
        apply_memory_state(self, self._memory_state_payload)
        self._memory_state_mcm_loaded = isinstance(self.mcm_brain, dict)
        self.mcm_runtime = create_mcm_runtime(self)

        self._runtime_thread = None
        self._runtime_thread_lock = threading.Lock()
        self._runtime_stop_event = threading.Event()
        self._market_packet_queue = queue.Queue()
        self._runtime_seeded = bool(self.mcm_runtime is not None and self.mcm_runtime.has_impulse())
        self._memory_state_dirty = False
        self._memory_state_last_save_ts = 0.0

        live_mode = str(getattr(Config, "MODE", "LIVE")).upper() == "LIVE"
        snapshot = None

        if live_mode and bool(getattr(Config, "AKTIV_ORDER", False)):
            snapshot = get_active_order_snapshot()

        if snapshot:
            entry_raw = snapshot.get("entry")
            tp_raw = snapshot.get("tp")
            sl_raw = snapshot.get("sl")

            try:
                entry = float(entry_raw)
            except Exception:
                entry = None

            try:
                tp_value = float(tp_raw) if tp_raw is not None else None
            except Exception:
                tp_value = None

            try:
                sl_value = float(sl_raw) if sl_raw is not None else None
            except Exception:
                sl_value = None

            if entry is not None and tp_value is not None and sl_value is not None:
                print("RESTART RECOVERY → ACTIVE ORDER FOUND")

                risk = abs(entry - sl_value)

                self.position = {
                    "side": snapshot.get("side"),
                    "entry": entry,
                    "tp": tp_value,
                    "sl": sl_value,
                    "mfe": 0.0,
                    "mae": 0.0,
                    "risk": risk,
                    "order_id": snapshot.get("id"),
                    "entry_ts": snapshot.get("entry_ts"),
                    "entry_index": None,
                    "last_checked_ts": snapshot.get("entry_ts"),
                    "meta": {},
                }
    # ==================================================
    # ENTSCHEIDUNGSBAHN
    # ==================================================
    def _handle_decision_tendency(self, entry_result: dict):

        result = dict(entry_result or {})
        decision_tendency = str(result.get("decision_tendency", "") or "").strip().lower()

        if decision_tendency == "act":
            return False

        if decision_tendency == "observe":
            event_name = "observed_only"
        elif decision_tendency == "replan":
            event_name = "replanned"
        else:
            event_name = "withheld"

        state_before = self._build_regulation_state_snapshot()
        state_after = self._build_regulation_state_snapshot()
        state_delta = self._build_regulation_state_delta(
            state_before,
            state_after,
        )

        non_action_context = _build_entry_attempt_context(
            self,
            result,
        )
        self.stats.on_attempt(
            status=event_name,
            context=non_action_context,
        )

        mark_runtime_episode_event(
            self,
            event_name,
            {
                "decision_tendency": str(decision_tendency or "hold"),
                "proposed_decision": str(result.get("proposed_decision", "WAIT") or "WAIT"),
                "reason": str(result.get("rejection_reason", "runtime_non_action") or "runtime_non_action"),
                "meta_regulation_state": dict(result.get("meta_regulation_state", {}) or {}),
                "expectation_state": dict(result.get("expectation_state", {}) or {}),
                "state_before": dict(state_before or {}),
                "state_after": dict(state_after or {}),
                "state_delta": dict(state_delta or {}),
            },
        )
        return True                 
    # ==================================================
    # HANDLUNGSBAHN
    # ==================================================
    def _handle_active_position(self, window, last, live_mode: bool):

        if self.position is None:
            return False

        entry_price = float(self.position.get("entry", 0.0) or 0.0)
        side = str(self.position.get("side", "")).upper().strip()
        risk_value = abs(float(self.position.get("risk", 0.0) or 0.0))

        self.current_timestamp = window[-1]["timestamp"]

        high = float(last["high"])
        low = float(last["low"])

        if side == "LONG":
            favorable = max(0.0, high - entry_price)
            adverse = max(0.0, entry_price - low)
        else:
            favorable = max(0.0, entry_price - low)
            adverse = max(0.0, high - entry_price)

        self.position["mfe"] = max(float(self.position.get("mfe", 0.0) or 0.0), favorable)
        self.position["mae"] = max(float(self.position.get("mae", 0.0) or 0.0), adverse)

        bars_open = 0
        entry_index = self.position.get("entry_index")
        if isinstance(entry_index, int):
            bars_open = max(0, int(self.processed) - int(entry_index))

        rr_value = 0.0
        if risk_value > 0.0:
            if side == "LONG":
                rr_value = max(
                    0.0,
                    float(self.position.get("tp", 0.0) or 0.0) - entry_price,
                ) / risk_value
            else:
                rr_value = max(
                    0.0,
                    entry_price - float(self.position.get("tp", 0.0) or 0.0),
                ) / risk_value

        fill_ratio = 0.0
        if risk_value > 0.0:
            fill_ratio = max(0.0, min(2.0, favorable / risk_value))

        meta_regulation_state = dict(getattr(self, "meta_regulation_state", {}) or {})
        runtime_state = dict(getattr(self, "mcm_runtime_decision_state", {}) or {})
        position_state_before = self._build_regulation_state_snapshot()
        position_state_after = self._build_regulation_state_snapshot()
        position_state_delta = self._build_regulation_state_delta(
            position_state_before,
            position_state_after,
        )

        pressure_to_capacity = 0.0
        if float(getattr(self, "action_capacity", 0.0) or 0.0) > 0.0:
            pressure_to_capacity = float(getattr(self, "regulatory_load", 0.0) or 0.0) / max(0.05, float(getattr(self, "action_capacity", 0.0) or 0.0))

        mark_runtime_episode_event(
            self,
            "position_update",
            {
                "position": dict(self.position or {}),
                "entry": float(self.position.get("entry", 0.0) or 0.0),
                "tp": float(self.position.get("tp", 0.0) or 0.0),
                "sl": float(self.position.get("sl", 0.0) or 0.0),
                "risk": float(risk_value),
                "rr": float(rr_value),
                "mfe": float(self.position.get("mfe", 0.0) or 0.0),
                "mae": float(self.position.get("mae", 0.0) or 0.0),
                "bars_open": int(bars_open),
                "fill_ratio": float(fill_ratio),
                "regulatory_load": float(getattr(self, "regulatory_load", 0.0) or 0.0),
                "action_capacity": float(getattr(self, "action_capacity", 0.0) or 0.0),
                "recovery_need": float(getattr(self, "recovery_need", 0.0) or 0.0),
                "survival_pressure": float(getattr(self, "survival_pressure", 0.0) or 0.0),
                "pressure_to_capacity": float(pressure_to_capacity),
                "regulated_courage": float(meta_regulation_state.get("regulated_courage", 0.0) or 0.0),
                "courage_gap": float(meta_regulation_state.get("courage_gap", 0.0) or 0.0),
                "decision_tendency": str(runtime_state.get("decision_tendency", "hold") or "hold"),
                "proposed_decision": str(runtime_state.get("proposed_decision", "WAIT") or "WAIT"),
                "pre_action_phase": str(meta_regulation_state.get("pre_action_phase", "hold") or "hold"),
                "dominant_tension_cause": str(meta_regulation_state.get("dominant_tension_cause", "-") or "-"),
                "reason": "position_watch",
                "state_before": dict(position_state_before or {}),
                "state_after": dict(position_state_after or {}),
                "state_delta": dict(position_state_delta or {}),
            },
        )

        exit_signal = self.exit_engine.process(
            window,
            self.position,
            "exit_trading_debug.csv",
        )
        if exit_signal is None:
            return True

        reason = exit_signal.get("reason")
        if reason is None:
            return True

        position_context = dict(self.position.get("meta", {}) or {})
        resolved_position = dict(self.position or {})
        state_before = self._build_regulation_state_snapshot()

        if live_mode and Config.AKTIV_ORDER:
            oid = self.position.get("order_id")
            if oid is not None and consume_cancelled(oid):
                apply_outcome_stimulus(self, "cancel", self.position)
                self.stats.on_attempt(
                    status="cancelled",
                    context=position_context,
                )
                mark_runtime_episode_event(
                    self,
                    "cancelled",
                    {
                        "position": dict(resolved_position or {}),
                        "reason": "exchange_cancel",
                    },
                )
                self.stats.on_cancel(
                    order_id=oid,
                    cause="exchange_cancel",
                    exploration_trade=False,
                    outcome_decomposition=dict(getattr(self, "last_outcome_decomposition", {}) or {}),
                    context=position_context,
                )
                self._mark_memory_state_dirty()
                self.position = None
                return True

        apply_outcome_stimulus(self, reason, self.position)
        state_after = self._build_regulation_state_snapshot()
        state_delta = self._build_regulation_state_delta(
            state_before,
            state_after,
        )
        self._save_memory_state()

        if str(reason).lower() == "sl_hit":
            self.mcm_pause_left = int(getattr(Config, "MCM_SL_PAUSE_STEPS", 3) or 3)

        self.stats.on_exit(
            entry=self.position.get("entry"),
            tp=self.position.get("tp"),
            sl=self.position.get("sl"),
            reason=reason,
            side=self.position.get("side"),
            amount=Config.ORDER_SIZE if live_mode else 1.0,
            exploration_trade=False,
            outcome_decomposition=dict(getattr(self, "last_outcome_decomposition", {}) or {}),
            context=position_context,
        )
        mark_runtime_episode_event(
            self,
            "resolved",
            {
                "position": dict(resolved_position or {}),
                "reason": str(reason or "-"),
                "state_before": dict(state_before or {}),
                "state_after": dict(state_after or {}),
                "state_delta": dict(state_delta or {}),
            },
        )

        self.position = None
        return True
    # --------------------------------------------------
    def _handle_pending_entry(self, window, last, live_mode: bool):

        if self.pending_entry is None or self.position is not None:
            return False

        pending_meta = dict(self.pending_entry.get("meta", {}) or {})
        side = self.pending_entry["side"]
        entry_price = self.pending_entry["entry"]
        tp_price = self.pending_entry["tp"]
        sl_price = self.pending_entry["sl"]
        created = self.pending_entry["created_index"]
        max_wait = self.pending_entry["max_wait_bars"]

        high = float(last["high"])
        low = float(last["low"])
        trade_plan = dict(pending_meta.get("trade_plan", {}) or {})
        entry_validity_band = dict(trade_plan.get("entry_validity_band", {}) or {})

        validity_lower = entry_validity_band.get("lower")
        validity_upper = entry_validity_band.get("upper")

        try:
            validity_lower = float(validity_lower) if validity_lower is not None else None
        except Exception:
            validity_lower = None

        try:
            validity_upper = float(validity_upper) if validity_upper is not None else None
        except Exception:
            validity_upper = None

        entry_touched = low <= entry_price <= high
        validity_touched = False

        if validity_lower is not None and validity_upper is not None:
            validity_touched = high >= validity_lower and low <= validity_upper

        bars_open = max(0, int(self.processed) - int(created))
        pending_risk = abs(float(entry_price) - float(sl_price))
        rr_value = 0.0
        if pending_risk > 0.0:
            if side == "LONG":
                rr_value = max(
                    0.0,
                    float(tp_price) - float(entry_price),
                ) / pending_risk
            else:
                rr_value = max(
                    0.0,
                    float(entry_price) - float(tp_price),
                ) / pending_risk

        distance_to_entry = 0.0
        if low <= entry_price <= high:
            distance_to_entry = 0.0
        elif entry_price < low:
            distance_to_entry = low - entry_price
        elif entry_price > high:
            distance_to_entry = entry_price - high

        fill_ratio = 0.0
        if pending_risk > 0.0:
            fill_ratio = max(0.0, min(2.0, 1.0 - (distance_to_entry / max(pending_risk, 1e-9))))

        meta_regulation_state = dict(getattr(self, "meta_regulation_state", {}) or {})
        runtime_state = dict(getattr(self, "mcm_runtime_decision_state", {}) or {})
        pending_state_before = self._build_regulation_state_snapshot()
        pending_state_after = self._build_regulation_state_snapshot()
        pending_state_delta = self._build_regulation_state_delta(
            pending_state_before,
            pending_state_after,
        )

        pressure_to_capacity = 0.0
        if float(getattr(self, "action_capacity", 0.0) or 0.0) > 0.0:
            pressure_to_capacity = float(getattr(self, "regulatory_load", 0.0) or 0.0) / max(0.05, float(getattr(self, "action_capacity", 0.0) or 0.0))

        mark_runtime_episode_event(
            self,
            "pending_update",
            {
                "pending_entry": dict(self.pending_entry or {}),
                "entry": float(entry_price),
                "tp": float(tp_price),
                "sl": float(sl_price),
                "risk": float(pending_risk),
                "rr": float(rr_value),
                "mfe": 0.0,
                "mae": 0.0,
                "bars_open": int(bars_open),
                "fill_ratio": float(fill_ratio),
                "regulatory_load": float(getattr(self, "regulatory_load", 0.0) or 0.0),
                "action_capacity": float(getattr(self, "action_capacity", 0.0) or 0.0),
                "recovery_need": float(getattr(self, "recovery_need", 0.0) or 0.0),
                "survival_pressure": float(getattr(self, "survival_pressure", 0.0) or 0.0),
                "pressure_to_capacity": float(pressure_to_capacity),
                "regulated_courage": float(meta_regulation_state.get("regulated_courage", 0.0) or 0.0),
                "courage_gap": float(meta_regulation_state.get("courage_gap", 0.0) or 0.0),
                "decision_tendency": str(runtime_state.get("decision_tendency", "hold") or "hold"),
                "proposed_decision": str(runtime_state.get("proposed_decision", "WAIT") or "WAIT"),
                "pre_action_phase": str(meta_regulation_state.get("pre_action_phase", "hold") or "hold"),
                "dominant_tension_cause": str(meta_regulation_state.get("dominant_tension_cause", "-") or "-"),
                "reason": "pending_watch",
                "state_before": dict(pending_state_before or {}),
                "state_after": dict(pending_state_after or {}),
                "state_delta": dict(pending_state_delta or {}),
            },
        )

        if live_mode:
            return True

        fill_price = float(entry_price)

        if (not entry_touched) and validity_touched:
            fill_price = float(min(max(entry_price, low), high))

        if side in ("LONG", "SHORT") and (entry_touched or validity_touched):

            risk = abs(fill_price - sl_price)
            fill_state_before = self._build_regulation_state_snapshot()

            self.position = {
                "side": side,
                "entry": float(fill_price),
                "tp": tp_price,
                "sl": sl_price,
                "mfe": 0.0,
                "mae": 0.0,
                "risk": float(risk),
                "order_id": None,
                "entry_ts": last.get("timestamp"),
                "entry_index": self.processed,
                "last_checked_ts": last.get("timestamp"),
                "meta": pending_meta,
            }

            fill_state_after = self._build_regulation_state_snapshot()
            fill_state_delta = self._build_regulation_state_delta(
                fill_state_before,
                fill_state_after,
            )

            self.pending_entry = None
            self.stats.on_attempt(
                status="filled",
                context=pending_meta,
            )
            mark_runtime_episode_event(
                self,
                "filled",
                {
                    "position": dict(self.position or {}),
                    "reason": "backtest_fill",
                    "state_before": dict(fill_state_before or {}),
                    "state_after": dict(fill_state_after or {}),
                    "state_delta": dict(fill_state_delta or {}),
                },
            )
            self._save_memory_state()
            return True

        if (self.processed - created) > max_wait:

            pending_snapshot = dict(self.pending_entry or {})
            timeout_state_before = self._build_regulation_state_snapshot()
            apply_outcome_stimulus(self, "timeout", self.pending_entry)
            timeout_state_after = self._build_regulation_state_snapshot()
            timeout_state_delta = self._build_regulation_state_delta(
                timeout_state_before,
                timeout_state_after,
            )
            self.stats.on_attempt(
                status="timeout",
                context=pending_meta,
            )
            mark_runtime_episode_event(
                self,
                "timeout",
                {
                    "pending_entry": dict(pending_snapshot or {}),
                    "reason": "backtest_timeout",
                    "state_before": dict(timeout_state_before or {}),
                    "state_after": dict(timeout_state_after or {}),
                    "state_delta": dict(timeout_state_delta or {}),
                },
            )
            self.stats.on_cancel(
                order_id=None,
                cause="backtest_timeout",
                exploration_trade=False,
                outcome_decomposition=dict(getattr(self, "last_outcome_decomposition", {}) or {}),
                context=pending_meta,
            )

            self._save_memory_state()
            self.pending_entry = None
            return True

        return True
    # --------------------------------------------------
    def _handle_entry_attempt(self, window, candle_state, last, live_mode: bool, external_order_active: bool):

        if self.position is not None or self.pending_entry is not None:
            return False

        if external_order_active:
            return True

        if int(getattr(self, "mcm_pause_left", 0) or 0) > 0:
            self.mcm_pause_left -= 1

        entry_result = evaluate_entry_decision(
            self,
            window,
            candle_state,
        )

        if entry_result is None:
            return True

        if self._handle_decision_tendency(entry_result):
            return True

        value_check = self.value_gate.evaluate(entry_result)

        if DEBUG:
            dbr_debug(f"VALUE_GATE: {value_check}", "value_check_debug.csv")

        if not value_check.get("trade_allowed", False):
            blocked_context = _build_entry_attempt_context(
                self,
                entry_result,
            )

            self.stats.on_attempt(
                status="blocked_value_gate",
                context=blocked_context,
            )
            mark_runtime_episode_event(
                self,
                "blocked_value_gate",
                {
                    "trade_plan": dict((blocked_context.get("trade_plan", {}) or {})),
                    "reason": str(value_check.get("reason") or "blocked_value_gate"),
                },
            )
            apply_outcome_stimulus(
                self,
                value_check.get("reason"),
                entry_result,
            )
            self._save_memory_state()
            return True

        side = str(entry_result.get("decision", "")).upper().strip()
        entry_price = float(entry_result.get("entry_price", 0.0) or 0.0)
        tp_price = float(entry_result.get("tp_price", 0.0) or 0.0)
        sl_price = float(entry_result.get("sl_price", 0.0) or 0.0)
        risk = abs(entry_price - sl_price)

        if side not in ("LONG", "SHORT"):
            return True

        if entry_price <= 0.0 or tp_price <= 0.0 or sl_price <= 0.0 or risk <= 0.0:
            return True

        order_side = "sell" if side == "SHORT" else "buy"

        order_id = None
        is_memory_trade = False
        rr_exec_min = float(getattr(Config, "RR_EXECUTION_MIN", 1.2) or 1.2)

        if live_mode and Config.AKTIV_ORDER and float(entry_result.get("rr_value", 0.0) or 0.0) < rr_exec_min:
            is_memory_trade = True

        if live_mode and Config.AKTIV_ORDER and not is_memory_trade:
            order_id = place_order(
                order_type=order_side,
                price=entry_price,
                amount=Config.ORDER_SIZE,
                open_orders=None,
                tp=tp_price,
                sl=sl_price,
                params={
                    "_entry_reference": entry_price,
                    "_entry_distance": abs(entry_price - float(last.get("close", entry_price) or entry_price)),
                    "_risk_reference": risk,
                    "_entry_validity_band": dict(entry_result.get("entry_validity_band", {}) or {}),
                },
            )

            if order_id is None:
                return True

        attempt_meta = _build_entry_attempt_context(
            self,
            entry_result,
        )

        self.pending_entry = {
            "side": side,
            "entry": entry_price,
            "tp": tp_price,
            "sl": sl_price,
            "risk": float(risk),
            "order_id": order_id,
            "created_index": self.processed,
            "max_wait_bars": int(getattr(Config, "PENDING_ENTRY_MAX_WAIT_BARS", 20) or 20),
            "meta": attempt_meta,
        }
        self.stats.on_attempt(
            status="submitted",
            context=attempt_meta,
        )
        mark_runtime_episode_event(
            self,
            "submitted",
            {
                "trade_plan": dict((attempt_meta.get("trade_plan", {}) or {})),
                "reason": str(side or "-").lower(),
            },
        )

        self._save_memory_state()
        return True
    # ==================================================
    # MCM RUNTIME
    # ==================================================
    def start_runtime_thread(self):

        if self._runtime_thread is not None and self._runtime_thread.is_alive():
            return self._runtime_thread

        with self._runtime_thread_lock:
            if self._runtime_thread is not None and self._runtime_thread.is_alive():
                return self._runtime_thread

            self._runtime_stop_event.clear()
            self._runtime_thread = threading.Thread(
                target=self._runtime_loop,
                daemon=True,
            )
            self._runtime_thread.start()

        return self._runtime_thread
    # --------------------------------------------------
    def stop_runtime_thread(self):

        self._runtime_stop_event.set()

        thread = self._runtime_thread
        if thread is not None and thread.is_alive():
            thread.join()

        self._save_memory_state(force=True)
        return thread
    # --------------------------------------------------
    def wait_until_runtime_idle(self):

        self._market_packet_queue.join()
    # --------------------------------------------------
    def _build_market_packet(self, window):

        return self._build_market_perception_packet(window)
    # --------------------------------------------------
    def _build_regulation_state_delta(self, state_before: dict, state_after: dict) -> dict:

        before = dict(state_before or {})
        after = dict(state_after or {})

        return {
            "tension": {
                "energy": float(after.get("tension", {}).get("energy", 0.0) - before.get("tension", {}).get("energy", 0.0)),
                "coherence": float(after.get("tension", {}).get("coherence", 0.0) - before.get("tension", {}).get("coherence", 0.0)),
                "stability": float(after.get("tension", {}).get("stability", 0.0) - before.get("tension", {}).get("stability", 0.0)),
                "momentum": float(after.get("tension", {}).get("momentum", 0.0) - before.get("tension", {}).get("momentum", 0.0)),
                "perceived_pressure": float(after.get("tension", {}).get("perceived_pressure", 0.0) - before.get("tension", {}).get("perceived_pressure", 0.0)),
                "volume_pressure": float(after.get("tension", {}).get("volume_pressure", 0.0) - before.get("tension", {}).get("volume_pressure", 0.0)),
            },
            "field": {
                "regulatory_load": float(after.get("field", {}).get("regulatory_load", 0.0) - before.get("field", {}).get("regulatory_load", 0.0)),
                "action_capacity": float(after.get("field", {}).get("action_capacity", 0.0) - before.get("field", {}).get("action_capacity", 0.0)),
                "recovery_need": float(after.get("field", {}).get("recovery_need", 0.0) - before.get("field", {}).get("recovery_need", 0.0)),
                "survival_pressure": float(after.get("field", {}).get("survival_pressure", 0.0) - before.get("field", {}).get("survival_pressure", 0.0)),
                "pressure_to_capacity": float(after.get("field", {}).get("pressure_to_capacity", 0.0) - before.get("field", {}).get("pressure_to_capacity", 0.0)),
            },
            "experience": {
                "approach_pressure": float(after.get("experience", {}).get("approach_pressure", 0.0) - before.get("experience", {}).get("approach_pressure", 0.0)),
                "pressure_release": float(after.get("experience", {}).get("pressure_release", 0.0) - before.get("experience", {}).get("pressure_release", 0.0)),
                "experience_regulation": float(after.get("experience", {}).get("experience_regulation", 0.0) - before.get("experience", {}).get("experience_regulation", 0.0)),
                "reflection_maturity": float(after.get("experience", {}).get("reflection_maturity", 0.0) - before.get("experience", {}).get("reflection_maturity", 0.0)),
                "load_bearing_capacity": float(after.get("experience", {}).get("load_bearing_capacity", 0.0) - before.get("experience", {}).get("load_bearing_capacity", 0.0)),
                "protective_courage": float(after.get("experience", {}).get("protective_courage", 0.0) - before.get("experience", {}).get("protective_courage", 0.0)),
            },
        }
    # --------------------------------------------------
    def publish_market_window(self, window):

        packet = self._build_market_packet(window)
        if packet is None:
            return None

        self._market_packet_queue.put(dict(packet))
        return dict(packet)
    # --------------------------------------------------
    def _runtime_loop(self):

        while True:
            if self._runtime_stop_event.is_set() and self._market_packet_queue.empty():
                break

            idle_sleep = self._runtime_idle_sleep_seconds()

            try:
                packet = self._market_packet_queue.get(timeout=idle_sleep)
            except queue.Empty:
                if self._runtime_seeded:
                    self._step_runtime_idle(
                        cycles=self._runtime_idle_cycles(),
                    )
                self._flush_memory_state_if_due()
                continue

            try:
                self._process_market_packet(packet)

                market_cycles = self._runtime_market_followup_cycles()
                if self._runtime_seeded and market_cycles > 0:
                    self._step_runtime_idle(
                        cycles=market_cycles,
                    )

                self._flush_memory_state_if_due()
            finally:
                self._market_packet_queue.task_done()
    # --------------------------------------------------
    def _runtime_dynamic_load(self):

        dynamic_load = max(
            float(getattr(self, "focus_confidence", 0.0) or 0.0),
            float(getattr(self, "target_lock", 0.0) or 0.0),
            float(getattr(self, "last_signal_relevance", 0.0) or 0.0),
            abs(float(getattr(self, "competition_bias", 0.0) or 0.0)),
        )

        if self.position is not None:
            dynamic_load = max(dynamic_load, 1.0)
        elif self.pending_entry is not None:
            dynamic_load = max(dynamic_load, 0.82)
        elif bool(getattr(self, "observation_mode", False)):
            dynamic_load = max(dynamic_load, 0.68)

        return float(max(0.0, min(1.0, float(dynamic_load))))
    # --------------------------------------------------
    def _runtime_idle_sleep_seconds(self):

        min_sleep = max(
            0.01,
            float(
                getattr(
                    Config,
                    "MCM_INNER_IDLE_SLEEP_MIN_SECONDS",
                    getattr(Config, "MCM_RUNTIME_IDLE_SLEEP_MIN_SECONDS", 0.05),
                ) or 0.05
            ),
        )
        max_sleep = max(
            min_sleep,
            float(
                getattr(
                    Config,
                    "MCM_INNER_IDLE_SLEEP_MAX_SECONDS",
                    getattr(Config, "MCM_RUNTIME_IDLE_SLEEP_MAX_SECONDS", 0.35),
                ) or 0.35
            ),
        )

        queue_depth = int(self._market_packet_queue.qsize() or 0)
        if queue_depth > 0:
            return float(min_sleep)

        dynamic_load = self._runtime_dynamic_load()
        sleep_span = max_sleep - min_sleep
        return float(max_sleep - (sleep_span * dynamic_load))
    # --------------------------------------------------
    def _runtime_idle_cycles(self):

        base_cycles = max(
            1,
            int(
                getattr(
                    Config,
                    "MCM_INNER_IDLE_BASE_TICKS",
                    getattr(Config, "MCM_RUNTIME_IDLE_TICKS", 1),
                ) or 1
            ),
        )
        max_cycles = max(
            base_cycles,
            int(
                getattr(
                    Config,
                    "MCM_INNER_IDLE_MAX_TICKS",
                    getattr(Config, "MCM_RUNTIME_IDLE_TICKS_MAX", base_cycles),
                ) or base_cycles
            ),
        )

        dynamic_load = self._runtime_dynamic_load()

        cycle_boost = 0

        if self.position is not None:
            cycle_boost += 2
        elif self.pending_entry is not None:
            cycle_boost += 1

        if bool(getattr(self, "observation_mode", False)):
            cycle_boost += 1

        cycle_boost += int(round(dynamic_load * max(0, max_cycles - base_cycles)))
        return int(min(max_cycles, base_cycles + cycle_boost))
    # --------------------------------------------------
    def _step_runtime_idle(self, cycles=None):

        self._ensure_memory_state_loaded()

        idle_cycles = cycles
        if idle_cycles is None:
            idle_cycles = self._runtime_idle_cycles()

        return step_mcm_runtime_idle(
            bot=self,
            cycles=max(1, int(idle_cycles or 1)),
        )
    # --------------------------------------------------
    def _seed_runtime_window(self, window, candle_state=None, visual_market_state=None, structure_perception_state=None):

        self._ensure_memory_state_loaded()

        perception_packet = self._build_market_perception_packet(window)
        if perception_packet is None:
            return None

        local_window = [dict(item or {}) for item in list(perception_packet.get("window", []) or []) if isinstance(item, dict)]
        if not local_window:
            return None

        resolved_candle_state = dict(perception_packet.get("candle_state", {}) or {})
        resolved_visual_market_state = dict(perception_packet.get("visual_market_state", {}) or {})
        resolved_structure_perception_state = dict(perception_packet.get("structure_perception_state", {}) or {})
        resolved_tension_state = dict(perception_packet.get("tension_state", {}) or {})

        if candle_state is not None:
            resolved_candle_state = dict(candle_state or {})

        if visual_market_state is not None:
            resolved_visual_market_state = dict(visual_market_state or {})

        if structure_perception_state is not None:
            resolved_structure_perception_state = dict(structure_perception_state or {})

        self.current_timestamp = perception_packet.get("timestamp", local_window[-1].get("timestamp"))
        self.tension_state = dict(resolved_tension_state or {})
        self.visual_market_state = dict(resolved_visual_market_state or {})
        self.structure_perception_state = dict(resolved_structure_perception_state or {})
        self.outer_market_state = dict(perception_packet.get("outer_market_state", {}) or {})

        runtime_result = step_mcm_runtime(
            local_window,
            dict(resolved_candle_state or {}),
            bot=self,
            tension_state=dict(resolved_tension_state or {}),
            visual_market_state=dict(resolved_visual_market_state or {}),
            structure_perception_state=dict(resolved_structure_perception_state or {}),
        )
        self._runtime_seeded = True

        action_result = self._run_runtime_action_cycle(
            local_window,
            dict(resolved_candle_state or {}),
        )
        if action_result is None:
            return runtime_result

        return action_result
    # --------------------------------------------------
    def _build_runtime_action_context(self, window):

        if not window:
            return None

        local_window = [dict(item or {}) for item in list(window or []) if isinstance(item, dict)]
        if not local_window:
            return None

        live_mode = str(getattr(Config, "MODE", "LIVE")).upper() == "LIVE"
        external_order_active = False

        if live_mode and self.position is None and is_order_active():
            external_order_active = True
            if DEBUG:
                dbr_debug("RUNTIME: ORDER_ACTIVE_WATCH", "live_backtest_debug.csv")

        last = local_window[-1]
        timestamp = last.get("timestamp")

        return {
            "window": local_window,
            "last": last,
            "timestamp": timestamp,
            "live_mode": bool(live_mode),
            "external_order_active": bool(external_order_active),
            "outer_market_state": dict(getattr(self, "outer_market_state", {}) or {}),
        }
    # --------------------------------------------------
    def _prepare_runtime_action_context(self, action_context):

        context = dict(action_context or {})
        window = [dict(item or {}) for item in list(context.get("window", []) or []) if isinstance(item, dict)]

        if not window:
            return None

        if self.position and self.position.get("entry_ts") is None:
            ts = context.get("timestamp", window[-1].get("timestamp"))
            self.position["entry_ts"] = ts
            self.position["last_checked_ts"] = ts

        self.current_timestamp = context.get("timestamp", window[-1].get("timestamp"))
        self.stats.data["current_timestamp"] = self.current_timestamp
        return {
            "window": window,
            "last": dict(context.get("last", window[-1]) or window[-1]),
            "live_mode": bool(context.get("live_mode", False)),
            "external_order_active": bool(context.get("external_order_active", False)),
            "outer_market_state": dict(context.get("outer_market_state", {}) or {}),
        }
    # --------------------------------------------------
    def _run_position_execution_path(self, action_context):

        context = dict(action_context or {})
        return self._handle_active_position(
            context.get("window", []),
            context.get("last", {}),
            bool(context.get("live_mode", False)),
        )
    # --------------------------------------------------
    def _run_pending_execution_path(self, action_context):

        context = dict(action_context or {})
        return self._handle_pending_entry(
            context.get("window", []),
            context.get("last", {}),
            bool(context.get("live_mode", False)),
        )
    # --------------------------------------------------
    def _run_decision_execution_path(self, action_context, candle_state):

        context = dict(action_context or {})
        return self._handle_entry_attempt(
            context.get("window", []),
            dict(candle_state or {}),
            context.get("last", {}),
            bool(context.get("live_mode", False)),
            bool(context.get("external_order_active", False)),
        )
    # --------------------------------------------------
    def _run_runtime_action_cycle(self, window, candle_state):

        self._ensure_memory_state_loaded()

        action_context = self._build_runtime_action_context(window)
        if action_context is None:
            return None

        prepared_context = self._prepare_runtime_action_context(action_context)
        if prepared_context is None:
            return None

        if self._run_position_execution_path(prepared_context):
            return True

        if self._run_pending_execution_path(prepared_context):
            return True

        if self._run_decision_execution_path(prepared_context, candle_state):
            return True

        return True
    # --------------------------------------------------
    def _runtime_market_followup_cycles(self):

        configured_cycles = max(
            1,
            int(
                getattr(
                    Config,
                    "MCM_RUNTIME_TICKS_PER_WINDOW",
                    getattr(Config, "MCM_INNER_TICKS_PER_WORLD_TICK", 1),
                ) or 1
            ),
        )

        followup_cycles = max(0, configured_cycles - 1)
        if followup_cycles <= 0:
            return 0

        dynamic_load = self._runtime_dynamic_load()
        scaled_cycles = int(round(dynamic_load * followup_cycles))
        return int(max(0, min(followup_cycles, scaled_cycles if followup_cycles > 1 else followup_cycles)))
    # ==================================================
    # MARKET PACKET BUILDERS
    # ==================================================
    def _normalize_market_window(self, window):

        if not window:
            return []

        return [dict(item or {}) for item in list(window or []) if isinstance(item, dict)]
    # --------------------------------------------------
    def _build_candle_state_packet(self, window):

        local_window = self._normalize_market_window(window)
        if not local_window:
            return {}

        last = local_window[-1]
        prev_close = local_window[-2].get("close") if len(local_window) > 1 else None
        return dict(_build_candle_state(last, prev_close=prev_close) or {})
    # --------------------------------------------------
    def _build_tension_state_packet(self, window):

        local_window = self._normalize_market_window(window)
        if not local_window:
            return {}

        return dict(build_tension_state_from_window(local_window) or {})
    # --------------------------------------------------
    def _build_visual_market_state_packet(self, window):

        local_window = self._normalize_market_window(window)
        if not local_window:
            return {}

        return dict(build_visual_market_state(local_window) or {})
    # --------------------------------------------------
    def _build_structure_perception_packet(self, window):

        local_window = self._normalize_market_window(window)
        if not local_window:
            return {}

        return dict(STRUCTURE_ENGINE.build_structure_perception_state(local_window) or {})
    # --------------------------------------------------
    def _build_market_perception_packet(self, window):

        local_window = self._normalize_market_window(window)
        if not local_window:
            return None

        last = local_window[-1]
        candle_state = self._build_candle_state_packet(local_window)
        tension_state = self._build_tension_state_packet(local_window)
        visual_market_state = self._build_visual_market_state_packet(local_window)
        structure_perception_state = self._build_structure_perception_packet(local_window)
        outer_market_state = {
            "timestamp": last.get("timestamp"),
            "candle_state": dict(candle_state or {}),
            "tension_state": dict(tension_state or {}),
            "visual_market_state": dict(visual_market_state or {}),
            "structure_perception_state": dict(structure_perception_state or {}),
        }

        return {
            "timestamp": last.get("timestamp"),
            "window": local_window,
            "candle_state": dict(candle_state or {}),
            "tension_state": dict(tension_state or {}),
            "visual_market_state": dict(visual_market_state or {}),
            "structure_perception_state": dict(structure_perception_state or {}),
            "outer_market_state": dict(outer_market_state or {}),
        }    
    # ==================================================
    # MEMORY STATE
    # ==================================================
    def _ensure_memory_state_loaded(self):

        if self._memory_state_mcm_loaded:
            return

        if not isinstance(self.mcm_brain, dict):
            return

        apply_memory_state(self, self._memory_state_payload)

        if getattr(self, "mcm_runtime", None) is not None:
            self.mcm_runtime.restore_from_bot()

        self._memory_state_mcm_loaded = True
    # --------------------------------------------------
    def _mark_memory_state_dirty(self):

        self._memory_state_dirty = True
        return True
    # --------------------------------------------------
    def _flush_memory_state_if_due(self, force: bool = False):

        if not bool(getattr(self, "_memory_state_dirty", False)) and not bool(force):
            return None

        now_ts = float(time.time())
        cooldown = max(
            0.0,
            float(getattr(Config, "MCM_MEMORY_SAVE_COOLDOWN_SECONDS", 1.25) or 1.25),
        )

        if not force and (now_ts - float(getattr(self, "_memory_state_last_save_ts", 0.0) or 0.0)) < cooldown:
            return None

        return self._save_memory_state(force=True)
    # --------------------------------------------------
    def _save_memory_state(self, force: bool = False):

        if not bool(force) and not bool(getattr(self, "_memory_state_dirty", False)):
            return None

        payload = save_memory_state(
            self,
            include_runtime_state=bool(getattr(Config, "MCM_SAVE_RUNTIME_STATE", False)),
        )

        if payload is None:
            return None

        self._memory_state_payload = payload
        self._memory_state_mcm_loaded = isinstance(self.mcm_brain, dict)
        self._memory_state_dirty = False
        self._memory_state_last_save_ts = float(time.time())
        return payload           
    # --------------------------------------------------
    def _build_regulation_state_snapshot(self) -> dict:

        if self is None:
            return {
                "tension": {
                    "energy": 0.0,
                    "coherence": 0.0,
                    "stability": 0.0,
                    "momentum": 0.0,
                    "perceived_pressure": 0.0,
                    "volume_pressure": 0.0,
                },
                "field": {
                    "regulatory_load": 0.0,
                    "action_capacity": 0.0,
                    "recovery_need": 0.0,
                    "survival_pressure": 0.0,
                    "pressure_to_capacity": 0.0,
                },
                "experience": {
                    "approach_pressure": 0.0,
                    "pressure_release": 0.0,
                    "experience_regulation": 0.0,
                    "reflection_maturity": 0.0,
                    "load_bearing_capacity": 0.0,
                    "protective_courage": 0.0,
                },
            }

        tension_state = dict(getattr(self, "tension_state", {}) or {})
        regulatory_load = float(getattr(self, "regulatory_load", 0.0) or 0.0)
        action_capacity = float(getattr(self, "action_capacity", 0.0) or 0.0)

        pressure_to_capacity = 0.0
        if action_capacity > 0.0:
            pressure_to_capacity = regulatory_load / max(0.05, action_capacity)

        return {
            "tension": {
                "energy": float(tension_state.get("energy", 0.0) or 0.0),
                "coherence": float(tension_state.get("coherence", 0.0) or 0.0),
                "stability": float(tension_state.get("stability", 0.0) or 0.0),
                "momentum": float(tension_state.get("momentum", 0.0) or 0.0),
                "perceived_pressure": float(tension_state.get("perceived_pressure", 0.0) or 0.0),
                "volume_pressure": float(tension_state.get("volume_pressure", 0.0) or 0.0),
            },
            "field": {
                "regulatory_load": float(regulatory_load),
                "action_capacity": float(action_capacity),
                "recovery_need": float(getattr(self, "recovery_need", 0.0) or 0.0),
                "survival_pressure": float(getattr(self, "survival_pressure", 0.0) or 0.0),
                "pressure_to_capacity": float(pressure_to_capacity),
            },
            "experience": {
                "approach_pressure": float(getattr(self, "approach_pressure", 0.0) or 0.0),
                "pressure_release": float(getattr(self, "pressure_release", 0.0) or 0.0),
                "experience_regulation": float(getattr(self, "experience_regulation", 0.0) or 0.0),
                "reflection_maturity": float(getattr(self, "reflection_maturity", 0.0) or 0.0),
                "load_bearing_capacity": float(getattr(self, "load_bearing_capacity", 0.0) or 0.0),
                "protective_courage": float(getattr(self, "protective_courage", 0.0) or 0.0),
            },
        }    
    # ==================================================
    # INTERNE PIPELINE (NUR WINDOW → LOGIK)
    # ==================================================
    def _process_market_packet(self, packet):

        item = dict(packet or {})
        window = [dict(entry or {}) for entry in list(item.get("window", []) or []) if isinstance(entry, dict)]

        if not window:
            return None

        candle_state = dict(item.get("candle_state", {}) or {})
        tension_state = dict(item.get("tension_state", {}) or {})
        visual_market_state = dict(item.get("visual_market_state", {}) or {})
        structure_perception_state = dict(item.get("structure_perception_state", {}) or {})

        # --------------------------------------------------
        # FALLBACK: Wahrnehmung immer aus window erzeugen
        # --------------------------------------------------
        if not candle_state:
            last = window[-1]
            prev_close = window[-2].get("close") if len(window) > 1 else None
            candle_state = _build_candle_state(last, prev_close=prev_close)

        if not tension_state:
            tension_state = build_tension_state_from_window(window)

        if not visual_market_state:
            visual_market_state = build_visual_market_state(window)

        if not structure_perception_state:
            structure_perception_state = STRUCTURE_ENGINE.build_structure_perception_state(window)

        self.tension_state = dict(tension_state or {})
        self.visual_market_state = dict(visual_market_state or {})
        self.structure_perception_state = dict(structure_perception_state or {})
        self.outer_market_state = dict(item.get("outer_market_state", {}) or {})

        if not candle_state:
            last = window[-1]
            prev_close = window[-2].get("close") if len(window) > 1 else None
            candle_state = _build_candle_state(last, prev_close=prev_close)

        if not self._runtime_seeded:
            result = self._seed_runtime_window(
                window,
                candle_state=candle_state,
                visual_market_state=visual_market_state,
                structure_perception_state=structure_perception_state,
            )
        else:
            result = self._process_runtime_packet(
                window,
                candle_state,
                visual_market_state=visual_market_state,
                structure_perception_state=structure_perception_state,
            )

        self.processed += 1
        return result
    # --------------------------------------------------
    def _process_runtime_packet(self, window, candle_state, visual_market_state=None, structure_perception_state=None):

        step_mcm_runtime(
            window,
            candle_state,
            bot=self,
            visual_market_state=dict(visual_market_state or {}),
            structure_perception_state=dict(structure_perception_state or {}),
        )

        return self._run_runtime_action_cycle(
            window,
            candle_state,
        )
    # --------------------------------------------------
    def _process_window(self, window):

        packet = self._build_market_packet(window)
        if packet is None:
            return None

        result = self._process_market_packet(packet)

        market_cycles = self._runtime_market_followup_cycles()
        if self._runtime_seeded and market_cycles > 0:
            self._step_runtime_idle(
                cycles=market_cycles,
            )

        self._flush_memory_state_if_due()
        return result
    # ==================================================
    # MODUS 1: ROW-MODUS (internes Rolling)
    # ==================================================
    def run_rows(self, window_size: int = 2, delay_seconds: float = 0.0):
        buffer = []
        self.processed = 0

        for row in self.feed.rows(delay_seconds=delay_seconds):
            buffer.append(row)

            if len(buffer) < window_size:
                continue

            if len(buffer) > window_size:
                buffer.pop(0)

            self._process_window(buffer)
    # ==================================================
    # MODUS 2: WINDOW-MODUS (direkt vom Feed)
    # ==================================================
    def run_window(self, size: int, delay_seconds: float = 0.0):
        if not hasattr(self, "processed"):
            self.processed = 0

        processed = 0

        for window in self.feed.window(size, delay_seconds=delay_seconds):
            self._process_window(window)
            processed += 1

        return processed
# --------------------------------------------------
# ATTEMPT CONTEXT
# --------------------------------------------------
def _build_entry_attempt_context(bot, entry_result: dict) -> dict:

    result = dict(entry_result or {})
    action_capacity = float(result.get("action_capacity", 0.0) or 0.0)
    pressure_to_capacity = 0.0
    regulation_snapshot = bot._build_regulation_state_snapshot() if bot is not None else {
        "tension": {
            "energy": 0.0,
            "coherence": 0.0,
            "stability": 0.0,
            "momentum": 0.0,
            "perceived_pressure": 0.0,
            "volume_pressure": 0.0,
        },
        "field": {
            "regulatory_load": 0.0,
            "action_capacity": 0.0,
            "recovery_need": 0.0,
            "survival_pressure": 0.0,
            "pressure_to_capacity": 0.0,
        },
        "experience": {
            "approach_pressure": 0.0,
            "pressure_release": 0.0,
            "experience_regulation": 0.0,
            "reflection_maturity": 0.0,
            "load_bearing_capacity": 0.0,
            "protective_courage": 0.0,
        },
    }

    if action_capacity > 0.0:
        pressure_to_capacity = float(result.get("regulatory_load", 0.0) or 0.0) / max(0.05, action_capacity)

    return {
        "state": {
            "energy": float(result.get("energy", 0.0) or 0.0),
            "coherence": float(result.get("coherence", 0.0) or 0.0),
            "asymmetry": int(result.get("asymmetry", 0) or 0),
            "coh_zone": float(result.get("coh_zone", 0.0) or 0.0),
            "self_state": str(result.get("self_state", "stable") or "stable"),
            "attractor": str(result.get("attractor", "neutral") or "neutral"),
        },
        "focus": {
            "focus_point": float(getattr(bot, "focus_point", 0.0) or 0.0) if bot is not None else 0.0,
            "focus_confidence": float(result.get("focus", {}).get("focus_confidence", getattr(bot, "focus_confidence", 0.0) if bot is not None else 0.0) or 0.0),
            "target_lock": float(getattr(bot, "target_lock", 0.0) or 0.0) if bot is not None else 0.0,
            "target_drift": float(getattr(bot, "target_drift", 0.0) or 0.0) if bot is not None else 0.0,
        },
        "experience": {
            "entry_expectation": float(getattr(bot, "entry_expectation", 0.0) or 0.0) if bot is not None else 0.0,
            "target_expectation": float(getattr(bot, "target_expectation", 0.0) or 0.0) if bot is not None else 0.0,
            "approach_pressure": float(getattr(bot, "approach_pressure", 0.0) or 0.0) if bot is not None else 0.0,
            "pressure_release": float(getattr(bot, "pressure_release", 0.0) or 0.0) if bot is not None else 0.0,
            "experience_regulation": float(getattr(bot, "experience_regulation", 0.0) or 0.0) if bot is not None else 0.0,
            "reflection_maturity": float(getattr(bot, "reflection_maturity", 0.0) or 0.0) if bot is not None else 0.0,
            "load_bearing_capacity": float(getattr(bot, "load_bearing_capacity", 0.0) or 0.0) if bot is not None else 0.0,
            "protective_width_regulation": float(getattr(bot, "protective_width_regulation", 0.0) or 0.0) if bot is not None else 0.0,
            "protective_courage": float(getattr(bot, "protective_courage", 0.0) or 0.0) if bot is not None else 0.0,
        },
        "field_state": {
            "field_density": float(result.get("field_density", 0.0) or 0.0),
            "field_stability": float(result.get("field_stability", 0.0) or 0.0),
            "regulatory_load": float(result.get("regulatory_load", 0.0) or 0.0),
            "action_capacity": float(action_capacity),
            "recovery_need": float(result.get("recovery_need", 0.0) or 0.0),
            "survival_pressure": float(result.get("survival_pressure", 0.0) or 0.0),
            "pressure_to_capacity": float(pressure_to_capacity),
        },
        "regulation_snapshot": dict(regulation_snapshot or {}),
        "vision": dict(result.get("vision", {}) or {}),
        "filtered_vision": dict(result.get("filtered_vision", {}) or {}),
        "world_state": dict(result.get("world_state", {}) or {}),
        "structure_perception_state": dict(result.get("structure_perception_state", {}) or {}),
        "outer_visual_perception_state": dict(result.get("outer_visual_perception_state", {}) or {}),
        "inner_field_perception_state": dict(result.get("inner_field_perception_state", {}) or {}),
        "perception_state": dict(result.get("perception_state", {}) or {}),
        "processing_state": dict(result.get("processing_state", {}) or {}),
        "felt_state": dict(result.get("felt_state", {}) or {}),
        "thought_state": dict(result.get("thought_state", {}) or {}),
        "meta_regulation_state": dict(result.get("meta_regulation_state", {}) or {}),
        "expectation_state": dict(result.get("expectation_state", {}) or {}),
        "state_signature": dict(result.get("state_signature", {}) or {}),
        "trade_plan": {
            "decision": str(result.get("decision", "WAIT") or "WAIT"),
            "entry_price": float(result.get("entry_price", 0.0) or 0.0),
            "sl_price": float(result.get("sl_price", 0.0) or 0.0),
            "tp_price": float(result.get("tp_price", 0.0) or 0.0),
            "rr_value": float(result.get("rr_value", 0.0) or 0.0),
            "risk_model_score": float(result.get("risk_model_score", 0.0) or 0.0),
            "reward_model_score": float(result.get("reward_model_score", 0.0) or 0.0),
            "entry_validity_band": dict(result.get("entry_validity_band", {}) or {}),
        },
        "signal": {
            "signature_bias": float(result.get("signature_bias", 0.0) or 0.0),
            "signature_block": bool(result.get("signature_block", False)),
            "signature_quality": float(result.get("signature_quality", 0.0) or 0.0),
            "signature_distance": float(result.get("signature_distance", 0.0) or 0.0),
            "context_cluster_id": str(result.get("context_cluster_id", "-") or "-"),
            "context_cluster_bias": float(result.get("context_cluster_bias", 0.0) or 0.0),
            "context_cluster_quality": float(result.get("context_cluster_quality", 0.0) or 0.0),
            "context_cluster_distance": float(result.get("context_cluster_distance", 0.0) or 0.0),
            "context_cluster_block": bool(result.get("context_cluster_block", False)),
            "inhibition_level": float(result.get("inhibition_level", 0.0) or 0.0),
            "habituation_level": float(result.get("habituation_level", 0.0) or 0.0),
            "competition_bias": float(result.get("competition_bias", 0.0) or 0.0),
            "observation_mode": bool(result.get("observation_mode", False)),
            "long_score": float(result.get("long_score", 0.0) or 0.0),
            "short_score": float(result.get("short_score", 0.0) or 0.0),
        },
    }