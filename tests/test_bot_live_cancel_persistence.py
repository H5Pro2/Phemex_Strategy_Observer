import json
import sys
import tempfile
import types
import importlib
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

api_stub = types.ModuleType("api")
api_stub.API_KEY = ""
api_stub.API_SECRET = ""
sys.modules.setdefault("api", api_stub)

bot_engine_pkg = types.ModuleType("bot_engine")
sys.modules.setdefault("bot_engine", bot_engine_pkg)
sys.modules["bot_engine.exit_engine"] = importlib.import_module("exit_engine")
sys.modules["bot_engine.mcm_core_engine"] = importlib.import_module("mcm_core_engine")
sys.modules["bot_engine.strukture_engine"] = importlib.import_module("strukture_engine")
setattr(bot_engine_pkg, "exit_engine", sys.modules["bot_engine.exit_engine"])
setattr(bot_engine_pkg, "mcm_core_engine", sys.modules["bot_engine.mcm_core_engine"])
setattr(bot_engine_pkg, "strukture_engine", sys.modules["bot_engine.strukture_engine"])

bot_gates_pkg = types.ModuleType("bot_gates")
sys.modules.setdefault("bot_gates", bot_gates_pkg)
sys.modules["bot_gates.trade_value_gate"] = importlib.import_module("trade_value_gate")
setattr(bot_gates_pkg, "trade_value_gate", sys.modules["bot_gates.trade_value_gate"])

import bot as bot_module
from trade_stats import TradeStats


class BotLiveCancelPersistenceTests(unittest.TestCase):
    def test_live_cancel_passes_meta_and_outcome_decomposition_to_stats(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = Path(tmp) / "trade_stats.json"
            csv_path = Path(tmp) / "trade_equity.csv"
            attempt_path = Path(tmp) / "attempt_records.jsonl"
            outcome_path = Path(tmp) / "outcome_records.jsonl"
            data_path = Path(tmp) / "dummy.csv"
            data_path.write_text("timestamp_ms,open,high,low,close,volume\n", encoding="utf-8")

            original_mode = bot_module.Config.MODE
            original_aktiv_order = bot_module.Config.AKTIV_ORDER
            original_read_memory_state = bot_module.read_memory_state
            original_get_snapshot = bot_module.get_active_order_snapshot
            original_apply = bot_module.apply_outcome_stimulus
            original_consume = bot_module.consume_cancelled

            bot_module.Config.MODE = "LIVE"
            bot_module.Config.AKTIV_ORDER = True
            bot_module.read_memory_state = lambda *args, **kwargs: {}
            bot_module.get_active_order_snapshot = lambda *args, **kwargs: None

            try:
                bot = bot_module.Bot(filepath=str(data_path))
                bot.stats = TradeStats(
                    path=str(stats_path),
                    csv_path=str(csv_path),
                    attempt_path=str(attempt_path),
                    outcome_path=str(outcome_path),
                    reset=True,
                )
                bot.position = {
                    "side": "LONG",
                    "entry": 105.0,
                    "tp": 108.0,
                    "sl": 103.0,
                    "mfe": 0.0,
                    "mae": 0.0,
                    "risk": 2.0,
                    "order_id": "oid-1",
                    "entry_ts": 1,
                    "entry_index": 0,
                    "last_checked_ts": 1,
                    "meta": {
                        "structure_perception_state": {
                            "structure_quality": 0.82,
                            "zone_proximity": 0.88,
                        },
                        "felt_state": {
                            "pressure": 0.29,
                        },
                        "thought_state": {
                            "maturity": 0.57,
                        },
                        "meta_regulation_state": {
                            "decision": "LONG",
                        },
                        "expectation_state": {
                            "entry_expectation": 0.61,
                        },
                    },
                }

                bot.exit_engine.process = lambda window, position, txt: {"reason": "sl_hit"}

                saved_calls = []

                def fake_apply_outcome_stimulus(bot_obj, reason, position=None):
                    bot_obj.last_outcome_decomposition = {
                        "reason": str(reason),
                        "execution_quality": 0.22,
                        "plan_quality": 0.41,
                    }
                    return {"reason": reason}

                def fake_save_memory_state():
                    saved_calls.append(True)
                    return {"saved": True}

                bot_module.apply_outcome_stimulus = fake_apply_outcome_stimulus
                bot_module.consume_cancelled = lambda order_id: str(order_id) == "oid-1"
                bot._save_memory_state = fake_save_memory_state

                window = [
                    {"timestamp": 1, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10.0},
                    {"timestamp": 2, "open": 105.0, "high": 106.0, "low": 104.2, "close": 105.4, "volume": 11.0},
                ]
                bot._process_window(window)
            finally:
                bot_module.Config.MODE = original_mode
                bot_module.Config.AKTIV_ORDER = original_aktiv_order
                bot_module.read_memory_state = original_read_memory_state
                bot_module.get_active_order_snapshot = original_get_snapshot
                bot_module.apply_outcome_stimulus = original_apply
                bot_module.consume_cancelled = original_consume

            saved = json.loads(stats_path.read_text(encoding="utf-8"))
            attempt_records = [
                json.loads(line)
                for line in attempt_path.read_text(encoding="utf-8").splitlines()
                if str(line).strip()
            ]
            outcome_records = [
                json.loads(line)
                for line in outcome_path.read_text(encoding="utf-8").splitlines()
                if str(line).strip()
            ]

            self.assertIsNone(bot.position)
            self.assertEqual(saved_calls, [True])
            self.assertEqual(saved.get("last_outcome_decomposition"), {
                "reason": "cancel",
                "execution_quality": 0.22,
                "plan_quality": 0.41,
            })
            self.assertEqual(int(saved.get("cancels", 0)), 1)
            self.assertEqual(int(saved.get("attempts", 0)), 1)
            self.assertEqual(int(saved.get("attempts_cancelled", 0)), 1)
            self.assertEqual(saved.get("current_timestamp"), 2)

            self.assertEqual(len(attempt_records), 1)
            self.assertEqual(attempt_records[0].get("event"), "attempt")
            self.assertEqual(attempt_records[0].get("status"), "cancelled")
            self.assertEqual(attempt_records[0].get("timestamp"), 2)
            self.assertAlmostEqual(float(attempt_records[0].get("structure_quality", 0.0)), 0.82, places=6)
            self.assertEqual(
                (((attempt_records[0].get("context") or {}).get("meta_regulation_state") or {}).get("decision")),
                "LONG",
            )

            self.assertEqual(len(outcome_records), 1)
            self.assertEqual(outcome_records[0].get("event"), "cancel")
            self.assertEqual(outcome_records[0].get("reason"), "cancel")
            self.assertEqual(outcome_records[0].get("timestamp"), 2)
            self.assertEqual(outcome_records[0].get("cause"), "exchange_cancel")
            self.assertEqual(outcome_records[0].get("outcome_decomposition"), {
                "reason": "cancel",
                "execution_quality": 0.22,
                "plan_quality": 0.41,
            })
            self.assertEqual(
                (((outcome_records[0].get("context") or {}).get("meta_regulation_state") or {}).get("decision")),
                "LONG",
            )


if __name__ == "__main__":
    unittest.main()