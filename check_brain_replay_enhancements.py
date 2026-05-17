from __future__ import annotations

import brain_runtime as br
from brain_replay_enhancements import apply_brain_replay_enhancement_patch


# ==================================================
# check_brain_replay_enhancements.py
# ==================================================
# LOCAL BRAIN / REPLAY ENHANCEMENT CHECK
# ==================================================


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def _assert_true(label: str, value: bool) -> None:
    if not value:
        raise AssertionError(label)


def _board() -> dict:
    return {
        "symbol": "BTCUSDT",
        "timeframe_seconds": 300,
        "reports": [
            {"agent_name": "BOS / CHoCH Agent", "role": "structure", "signal": "LONG", "score": 82, "details": {"quality_profile": {"quality": "STRONG"}}},
            {"agent_name": "MACD Agent", "role": "momentum", "signal": "LONG", "score": 78, "details": {"quality_profile": {"quality": "OK"}}},
            {"agent_name": "Volume Agent", "role": "context", "signal": "NEUTRAL", "score": 55, "details": {"quality_profile": {"quality": "OK"}}},
            {"agent_name": "Risk Agent", "role": "risk", "signal": "NEUTRAL", "score": 70, "details": {"quality_profile": {"quality": "OK"}}},
        ],
    }


# --------------------------------------------------
# CHECKS
# --------------------------------------------------
def check_pattern_key() -> str:
    apply_brain_replay_enhancement_patch()
    key_one = br._pattern_key(_board())
    key_two = br._pattern_key(_board())
    _assert_true("Pattern-Key muss stabil sein", key_one == key_two)
    _assert_true("Pattern-Key muss v2 nutzen", key_one.startswith("v2:"))
    _assert_true("Pattern-Key muss Symbol enthalten", "symbol=BTCUSDT" in key_one)
    return key_one


def check_replay_weight(pattern_key: str) -> None:
    apply_brain_replay_enhancement_patch()
    config = {
        "replay_rule_weight_enabled": True,
        "replay_rule_scope": "asset",
        "replay_rule_weight_min_count": 5,
        "replay_rule_good_bonus": 6,
        "replay_rule_bad_penalty": -10,
        "replay_rule_max_abs_adjustment": 12,
        "replay_rule_weight_rules": [
            {
                "scope": "asset",
                "symbol": "BTCUSDT",
                "pattern_key": pattern_key,
                "quality": "GOOD",
                "count": 12,
                "win_rate": 0.66,
                "avg_r": 0.42,
                "profit_factor": 1.6,
            }
        ],
    }
    result = br._replay_rule_weight(pattern_key, config, "BTCUSDT")
    _assert_true("Replay-Regel muss matchen", bool(result.get("matched")))
    _assert_true("Replay-Regel muss positiven Bonus liefern", int(result.get("adjustment", 0)) > 0)
    _assert_true("Replay-Regel muss safe_edge_score liefern", "safe_edge_score" in result)


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main() -> None:
    pattern_key = check_pattern_key()
    check_replay_weight(pattern_key)
    print("Brain replay enhancement checks OK")


if __name__ == "__main__":
    main()
