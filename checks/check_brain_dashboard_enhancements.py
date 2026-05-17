from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from brain_dashboard_enhancements import _build_dashboard_summary


# ==================================================
# check_brain_dashboard_enhancements.py
# ==================================================
# LOCAL BRAIN DASHBOARD SUMMARY CHECK
# ==================================================


# --------------------------------------------------
# CHECKS
# --------------------------------------------------
def main() -> None:
    decision = {
        "decision": "LONG",
        "agent_bias": "LONG",
        "candidate_reason": "candidate_ok",
        "candidate": {
            "entry_method": "brain_agent_fallback_market_context",
            "features": {
                "zone_type": "candle_fallback_range",
            },
        },
        "memory_match": {
            "count": 8,
            "win_rate": 0.625,
            "avg_r": 0.42,
        },
        "replay_rule_weight": {
            "quality": "GOOD",
            "adjustment": 6,
            "count": 12,
            "safe_edge_score": 0.184,
            "reason": "Robuste Replay-Regel angewendet",
        },
        "score_breakdown": {
            "final_score": 72,
            "min_score": 58,
            "memory_adjustment": 3,
            "replay_adjustment": 6,
            "quality_penalty": 2,
        },
        "economic_gate": {
            "trade_allowed": True,
            "rr": 1.5,
            "reason": "ok",
        },
    }
    summary = _build_dashboard_summary(decision)
    if summary["entry_context"] != "Fallback":
        raise AssertionError("Entry-Fallback wurde nicht erkannt")
    if summary["replay_adjustment"] != 6:
        raise AssertionError("Replay-Adjustment wurde nicht uebernommen")
    if summary["economic_gate"] != "OK":
        raise AssertionError("Economic Gate wurde nicht korrekt dargestellt")
    if "Replay GOOD +6" not in summary["summary_line"]:
        raise AssertionError("Summary-Line enthaelt Replay-Zusammenfassung nicht")
    print("Brain dashboard enhancement checks OK")


if __name__ == "__main__":
    main()
