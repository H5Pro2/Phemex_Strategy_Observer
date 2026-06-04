from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


def check_brain_requires_ceo_quality() -> None:
    apply_brain_replay_enhancement_patch()
    board = _board()
    board["ceo"] = {
        "agent_name": "CEO Agent",
        "signal": "LONG",
        "score": 52,
        "blocking": False,
        "details": {
            "decision": "LONG_BIAS",
            "decision_grade": "C",
            "final_quality_score": 52,
            "role_alignment_score": 40,
        },
    }
    candles = [
        {"timestamp": 1, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0, "volume": 10},
        {"timestamp": 2, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.5, "volume": 10},
    ]
    result = br.build_brain_decision(
        "BTCUSDT",
        300,
        candles,
        board,
        {"boxes": [{"direction": "rising", "top": 100.0, "bottom": 99.0, "start_timestamp": 1}]},
        {},
        {},
        {
            "brain_min_score": 58,
            "brain_min_score_gap": 18,
            "brain_min_agent_alignment": 2,
            "brain_require_ceo_quality_for_trade": True,
            "brain_ceo_min_final_quality": 55,
            "brain_ceo_min_alignment_score": 45,
        },
    )
    _assert_true("Brain muss bei schwacher CEO-Qualitaet warten", result["decision"] == "WAIT")
    _assert_true("CEO-Gate muss im Score-Breakdown stehen", "ceo_trade_gate" in result.get("score_breakdown", {}))


def check_brain_value_precheck_blocks_negative_net() -> None:
    apply_brain_replay_enhancement_patch()
    board = _board()
    board["ceo"] = {
        "agent_name": "CEO Agent",
        "signal": "LONG",
        "score": 80,
        "blocking": False,
        "details": {
            "decision": "LONG_BIAS",
            "decision_grade": "B",
            "final_quality_score": 80,
            "role_alignment_score": 72,
        },
    }
    candles = [
        {"timestamp": 1, "open": 100.0, "high": 100.2, "low": 99.9, "close": 100.0, "volume": 10},
        {"timestamp": 2, "open": 100.0, "high": 100.2, "low": 99.9, "close": 100.05, "volume": 10},
    ]
    result = br.build_brain_decision(
        "BTCUSDT",
        300,
        candles,
        board,
        {"boxes": [{"direction": "rising", "top": 100.05, "bottom": 100.0, "start_timestamp": 1}]},
        {},
        {},
        {
            "brain_min_score": 58,
            "brain_min_score_gap": 18,
            "brain_min_agent_alignment": 2,
            "brain_require_ceo_quality_for_trade": True,
            "brain_precheck_trade_value": True,
            "reward_risk": 1.5,
            "trade_size_mode": "asset",
            "trade_size_asset": 10.0,
            "estimated_taker_fee_rate": 0.0006,
            "min_net_profit_fraction": 0.001,
        },
    )
    _assert_true("Brain Value-Precheck muss Kandidat blocken", result["decision"] == "WAIT")
    _assert_true("Candidate Reason muss Value-Precheck nennen", str(result.get("candidate_reason", "")).startswith("brain_value_precheck_"))


# --------------------------------------------------
# MAIN
# --------------------------------------------------
def main() -> None:
    pattern_key = check_pattern_key()
    check_replay_weight(pattern_key)
    check_brain_requires_ceo_quality()
    check_brain_value_precheck_blocks_negative_net()
    print("Brain replay enhancement checks OK")


if __name__ == "__main__":
    main()
