import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from trade_stats import TradeStats


class TradeStatsOutcomeDecompositionTests(unittest.TestCase):
    def test_on_exit_persists_last_outcome_decomposition(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = Path(tmp) / "trade_stats.json"
            csv_path = Path(tmp) / "trade_equity.csv"

            stats = TradeStats(
                path=str(stats_path),
                csv_path=str(csv_path),
                reset=True,
            )

            decomposition = {
                "perception_quality": 0.7,
                "felt_quality": 0.6,
                "thought_quality": 0.8,
                "plan_quality": 0.75,
                "execution_quality": 0.72,
                "risk_fit_quality": 0.68,
                "reason": "tp_hit",
            }

            stats.on_exit(
                entry=100.0,
                tp=102.0,
                sl=99.0,
                reason="tp_hit",
                side="LONG",
                amount=1.0,
                outcome_decomposition=decomposition,
            )

            saved = json.loads(stats_path.read_text(encoding="utf-8"))
            self.assertEqual(saved.get("last_outcome_decomposition"), decomposition)

    def test_on_attempt_tracks_structure_zone_and_snapshot_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = Path(tmp) / "trade_stats.json"
            csv_path = Path(tmp) / "trade_equity.csv"

            stats = TradeStats(
                path=str(stats_path),
                csv_path=str(csv_path),
                reset=True,
            )

            stats.on_attempt(
                status="submitted",
                context={
                    "world_state": {
                        "structure_perception_state": {
                            "structure_quality": 0.81,
                        }
                    }
                },
            )
            stats.on_attempt(
                status="filled",
                context={
                    "outer_visual_perception_state": {
                        "structure_quality": 0.20,
                    }
                },
            )

            snap = stats.snapshot()
            self.assertEqual(int(snap.get("attempts", 0)), 2)
            self.assertEqual(int(snap.get("attempts_submitted", 0)), 1)
            self.assertEqual(int(snap.get("attempts_filled", 0)), 1)
            self.assertEqual(int(snap.get("attempt_structure_zone", 0)), 1)
            self.assertEqual(int(snap.get("attempt_non_structure_zone", 0)), 1)
            self.assertAlmostEqual(float(snap.get("attempt_zone_share", -1.0)), 0.5, places=6)
            self.assertEqual(len(snap.get("recent_attempts", [])), 2)

    def test_on_cancel_persists_last_outcome_decomposition(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = Path(tmp) / "trade_stats.json"
            csv_path = Path(tmp) / "trade_equity.csv"

            stats = TradeStats(
                path=str(stats_path),
                csv_path=str(csv_path),
                reset=True,
            )

            decomposition = {
                "perception_quality": 0.4,
                "felt_quality": 0.5,
                "thought_quality": 0.45,
                "plan_quality": 0.3,
                "execution_quality": 0.2,
                "risk_fit_quality": 0.35,
                "reason": "cancel",
            }

            stats.on_cancel(
                order_id="abc123",
                cause="exchange_cancel",
                outcome_decomposition=decomposition,
            )

            saved = json.loads(stats_path.read_text(encoding="utf-8"))
            self.assertEqual(saved.get("last_outcome_decomposition"), decomposition)

    def test_on_attempt_persists_detailed_attempt_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = Path(tmp) / "trade_stats.json"
            csv_path = Path(tmp) / "trade_equity.csv"
            attempt_path = Path(tmp) / "attempt_records.jsonl"
            outcome_path = Path(tmp) / "outcome_records.jsonl"

            stats = TradeStats(
                path=str(stats_path),
                csv_path=str(csv_path),
                attempt_path=str(attempt_path),
                outcome_path=str(outcome_path),
                reset=True,
            )
            stats.data["current_timestamp"] = 1712345678901

            context = {
                "structure_perception_state": {
                    "structure_quality": 0.77,
                    "zone_proximity": 0.84,
                },
                "felt_state": {
                    "pressure": 0.31,
                },
                "thought_state": {
                    "maturity": 0.62,
                },
                "meta_regulation_state": {
                    "decision": "LONG",
                },
                "expectation_state": {
                    "entry_expectation": 0.58,
                },
            }

            stats.on_attempt(
                status="submitted",
                context=context,
            )

            saved = json.loads(stats_path.read_text(encoding="utf-8"))
            records = [
                json.loads(line)
                for line in attempt_path.read_text(encoding="utf-8").splitlines()
                if str(line).strip()
            ]

            self.assertNotIn("attempt_records", saved)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].get("event"), "attempt")
            self.assertEqual(records[0].get("status"), "submitted")
            self.assertEqual(records[0].get("timestamp"), 1712345678901)
            self.assertAlmostEqual(float(records[0].get("structure_quality", 0.0)), 0.77, places=6)
            self.assertEqual(records[0].get("structure_bucket"), "zone")
            self.assertEqual(
                (((records[0].get("context") or {}).get("meta_regulation_state") or {}).get("decision")),
                "LONG",
            )

    def test_on_exit_persists_detailed_outcome_record_with_context(self):
        with tempfile.TemporaryDirectory() as tmp:
            stats_path = Path(tmp) / "trade_stats.json"
            csv_path = Path(tmp) / "trade_equity.csv"
            attempt_path = Path(tmp) / "attempt_records.jsonl"
            outcome_path = Path(tmp) / "outcome_records.jsonl"

            stats = TradeStats(
                path=str(stats_path),
                csv_path=str(csv_path),
                attempt_path=str(attempt_path),
                outcome_path=str(outcome_path),
                reset=True,
            )
            stats.data["current_timestamp"] = 1719999999000

            decomposition = {
                "perception_quality": 0.73,
                "felt_quality": 0.64,
                "thought_quality": 0.79,
                "plan_quality": 0.70,
                "execution_quality": 0.74,
                "risk_fit_quality": 0.69,
                "reason": "tp_hit",
            }
            context = {
                "structure_perception_state": {
                    "structure_quality": 0.82,
                },
                "felt_state": {
                    "pressure": 0.28,
                },
                "thought_state": {
                    "maturity": 0.67,
                },
                "meta_regulation_state": {
                    "decision": "LONG",
                },
                "expectation_state": {
                    "entry_expectation": 0.61,
                },
            }

            stats.on_exit(
                entry=100.0,
                tp=102.0,
                sl=99.0,
                reason="tp_hit",
                side="LONG",
                amount=1.0,
                outcome_decomposition=decomposition,
                context=context,
            )

            saved = json.loads(stats_path.read_text(encoding="utf-8"))
            records = [
                json.loads(line)
                for line in outcome_path.read_text(encoding="utf-8").splitlines()
                if str(line).strip()
            ]

            self.assertNotIn("outcome_records", saved)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].get("event"), "trade_exit")
            self.assertEqual(records[0].get("reason"), "tp_hit")
            self.assertEqual(records[0].get("timestamp"), 1719999999000)
            self.assertEqual(records[0].get("structure_bucket"), "zone")
            self.assertEqual(records[0].get("outcome_decomposition"), decomposition)
            self.assertEqual(
                (((records[0].get("context") or {}).get("meta_regulation_state") or {}).get("decision")),
                "LONG",
            )

if __name__ == "__main__":
    unittest.main()
