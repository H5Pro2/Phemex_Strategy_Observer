from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import llm_roles
from phemex_strategy_observer import compact_llm_role_context, compact_llm_role_protocol, llm_role_trade_gate


def base_context() -> dict:
    return llm_roles.build_role_context(
        {
            "symbol": "BTCUSDT",
            "timeframe_seconds": 3600,
            "reports": [
                {
                    "agent_name": "BOS / CHoCH Agent",
                    "role": "structure",
                    "signal": "LONG",
                    "score": 72,
                    "message": "BOS bestaetigt.",
                }
            ],
            "ceo": {"message": "LONG_BIAS"},
        },
        {"setup_found": True, "side": "long", "reason": "test"},
        {"count": 5, "win_rate": 60.0, "avg_r": 0.4},
        "LONG",
        {
            "symbol": "BTCUSDT",
            "decision": "LONG",
            "entry_price": 100.0,
            "sl_price": 99.0,
            "tp_price": 101.6,
            "features": {"fee_to_risk_fraction": 0.12, "risk_usd": 1.0},
        },
        {"trade_allowed": True, "reason": "ok", "fee_to_risk_fraction": 0.12, "risk_usd": 1.0},
    )


def test_disabled_team_does_not_call_provider() -> None:
    result = llm_roles.evaluate_role_team(base_context(), {"llm_role_team_enabled": False, "llm_provider": "openai"})
    assert result["enabled"] is False
    assert result["decision"] == "WAIT"
    assert result["roles"] == []


def test_judge_blocks_on_risk_hard_block() -> None:
    reports = [
        {"role_key": "risk_officer", "role": "Risk Officer", "decision": "BLOCK", "confidence": 0.9, "hard_block": True},
        {"role_key": "momentum", "role": "Momentum Analyst", "decision": "APPROVE", "confidence": 0.8, "hard_block": False},
    ]
    judge = llm_roles._normalize_judge(  # noqa: SLF001 - local contract check
        {"decision": "APPROVE", "confidence": 0.8, "summary": "ok", "conflict_note": "-", "advice": "go"},
        reports,
    )
    assert judge["decision"] == "BLOCK"


def test_trade_gate_blocks_judge_block() -> None:
    gate = llm_role_trade_gate(
        {"enabled": True, "decision": "BLOCK", "verdict": "BLOCK_HINT", "block_hint": True},
        {"llm_role_team_enabled": True, "llm_role_required_for_trade": False},
    )
    assert gate["allowed"] is False
    assert gate["reason"] == "llm_role_judge_block"


def test_trade_gate_passive_without_required_approval() -> None:
    gate = llm_role_trade_gate(
        {"enabled": True, "decision": "WAIT", "verdict": "NO_DATA"},
        {"llm_role_team_enabled": True, "llm_role_required_for_trade": False},
    )
    assert gate["allowed"] is True


def test_trade_gate_can_require_approval() -> None:
    gate = llm_role_trade_gate(
        {"enabled": True, "decision": "WAIT", "verdict": "NO_DATA"},
        {"llm_role_team_enabled": True, "llm_role_required_for_trade": True},
    )
    assert gate["allowed"] is False
    assert gate["reason"] == "llm_role_approval_required"


def test_role_prompt_extra_reaches_system_prompt() -> None:
    captured = {}
    original = llm_roles._call_llm_json  # noqa: SLF001 - local contract check

    def fake_call(system, user, config):  # noqa: ANN001
        captured["system"] = system
        return {
            "role": "Market Structure Analyst",
            "decision": "WAIT",
            "confidence": 0.5,
            "reasons": ["test"],
            "hard_block": False,
        }

    try:
        llm_roles._call_llm_json = fake_call  # type: ignore[attr-defined]  # noqa: SLF001
        llm_roles._run_role(  # noqa: SLF001
            "market_structure",
            base_context(),
            {"llm_role_market_structure_prompt_extra": "Nur A+ Setups akzeptieren."},
        )
    finally:
        llm_roles._call_llm_json = original  # type: ignore[attr-defined]  # noqa: SLF001
    assert "Nur A+ Setups akzeptieren." in captured["system"]


def test_compact_role_trace_contract() -> None:
    brain = {
        "decision": "LONG",
        "candidate_reason": "candidate_ok",
        "memory_match": {"count": 4, "win_rate": 50.0, "avg_r": 0.2, "entry_offset_in_box": 0.35},
        "candidate": {
            "symbol": "BTCUSDT",
            "side": "long",
            "entry_price": 100,
            "sl_price": 99,
            "tp_price": 101.6,
            "score": 72,
            "confidence": 0.72,
            "pattern_key": "demo",
            "features": {"brain_score_breakdown": {"long_score": 100, "short_score": 20, "long_count": 3, "short_count": 1, "conflict": True}},
        },
        "llm_layer": {
            "enabled": True,
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "decision": "WAIT",
            "verdict": "WARN",
            "roles": [{"role_key": "risk_officer", "role": "Risk Officer", "decision": "BLOCK", "confidence": 0.8, "hard_block": True, "reasons": ["fee"]}],
            "judge": {"decision": "BLOCK", "confidence": 0.8, "summary": "risk", "conflict_note": "-", "advice": "wait"},
        },
    }
    context = compact_llm_role_context(brain, {"trade_allowed": True, "reason": "ok", "rr": 1.6, "fee_to_risk_fraction": 0.1})
    protocol = compact_llm_role_protocol(brain["llm_layer"], {"allowed": False, "reason": "llm_role_judge_block", "decision": "BLOCK", "verdict": "WARN"})
    assert context["version"] == 1
    assert context["symbol"] == "BTCUSDT"
    assert context["scores"]["conflict"] is True
    assert protocol["version"] == 1
    assert protocol["decision"] == "WAIT"
    assert protocol["judge"]["decision"] == "BLOCK"
    assert protocol["roles"][0]["hard_block"] is True


def run() -> None:
    test_disabled_team_does_not_call_provider()
    test_judge_blocks_on_risk_hard_block()
    test_trade_gate_blocks_judge_block()
    test_trade_gate_passive_without_required_approval()
    test_trade_gate_can_require_approval()
    test_role_prompt_extra_reaches_system_prompt()
    test_compact_role_trace_contract()
    print("llm role checks passed")


if __name__ == "__main__":
    run()
