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


class BotPendingFillPersistenceTests(unittest.TestCase):
    def test_backtest_pending_fill_persists_meta_and_filled_attempt_record(self):
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

            bot_module.Config.MODE = "BACKTEST"
            bot_module.Config.AKTIV_ORDER = False
            bot_module.read_memory_state = lambda *args, **kwargs: {}

            try:
                bot = bot_module.Bot(filepath=str(data_path))
                bot.stats = TradeStats(
                    path=str(stats_path),
                    csv_path=str(csv_path),
                    attempt_path=str(attempt_path),
                    outcome_path=str(outcome_path),
                    reset=True,
                )
                bot.processed = 7
                bot.pending_entry = {
                    "side": "LONG",
                    "entry": 105.0,
                    "tp": 108.0,
                    "sl": 103.5,
                    "risk": 1.5,
                    "created_index": 4,
                    "max_wait_bars": 4,
                    "meta": {
                        "structure_perception_state": {
                            "structure_quality": 0.79,
                            "zone_proximity": 0.83,
                        },
                        "felt_state": {
                            "pressure": 0.34,
                        },
                        "thought_state": {
                            "maturity": 0.51,
                        },
                        "meta_regulation_state": {
                            "decision": "LONG",
                            "allow_plan": True,
                        },
                        "expectation_state": {
                            "entry_expectation": 0.59,
                        },
                        "trade_plan": {
                            "entry_validity_band": {
                                "lower": 104.2,
                                "upper": 104.8,
                            }
                        },
                    },
                }

                window = [
                    {"timestamp": 1, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10.0},
                    {"timestamp": 2, "open": 104.4, "high": 104.6, "low": 104.1, "close": 104.5, "volume": 11.0},
                ]
                bot._process_window(window)
            finally:
                bot_module.Config.MODE = original_mode
                bot_module.Config.AKTIV_ORDER = original_aktiv_order
                bot_module.read_memory_state = original_read_memory_state

            saved = json.loads(stats_path.read_text(encoding="utf-8"))
            records = [
                json.loads(line)
                for line in attempt_path.read_text(encoding="utf-8").splitlines()
                if str(line).strip()
            ]

            self.assertIsNone(bot.pending_entry)
            self.assertIsInstance(bot.position, dict)
            self.assertAlmostEqual(float(bot.position.get("entry", 0.0)), 104.6, places=6)
            self.assertAlmostEqual(float(bot.position.get("risk", 0.0)), 1.1, places=6)
            self.assertEqual(((bot.position.get("meta") or {}).get("meta_regulation_state") or {}).get("decision"), "LONG")

            self.assertEqual(int(saved.get("attempts", 0)), 1)
            self.assertEqual(int(saved.get("attempts_filled", 0)), 1)
            self.assertEqual(int(saved.get("attempt_structure_zone", 0)), 1)
            self.assertEqual(saved.get("current_timestamp"), 2)
            self.assertNotIn("attempt_records", saved)

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].get("event"), "attempt")
            self.assertEqual(records[0].get("status"), "filled")
            self.assertEqual(records[0].get("timestamp"), 2)
            self.assertEqual(records[0].get("structure_bucket"), "zone")
            self.assertAlmostEqual(float(records[0].get("structure_quality", 0.0)), 0.79, places=6)
            self.assertEqual((((records[0].get("context") or {}).get("meta_regulation_state") or {}).get("decision")), "LONG")
            self.assertEqual((((records[0].get("context") or {}).get("expectation_state") or {}).get("entry_expectation")), 0.59)


if __name__ == "__main__":
    unittest.main()