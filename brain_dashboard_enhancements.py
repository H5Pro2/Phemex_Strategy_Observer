from __future__ import annotations

from typing import Any

import brain_runtime as br


# ==================================================
# brain_dashboard_enhancements.py
# ==================================================
# BRAIN / REPLAY DASHBOARD SUMMARY EXTENSION
# ==================================================

_ORIGINAL_BUILD_BRAIN_DECISION = br.build_brain_decision
_ORIGINAL_APPLY_ECONOMIC_GATE = br.apply_economic_gate_to_brain_decision


# --------------------------------------------------
# SAFE FORMAT
# --------------------------------------------------
def _num(value: Any, digits: int = 2) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "-"


def _pct(value: Any) -> str:
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return "-"


def _text(value: Any, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else fallback


# --------------------------------------------------
# DASHBOARD SUMMARY
# --------------------------------------------------
def _build_dashboard_summary(decision: dict[str, Any]) -> dict[str, Any]:
    candidate = decision.get("candidate") if isinstance(decision.get("candidate"), dict) else None
    replay = decision.get("replay_rule_weight") if isinstance(decision.get("replay_rule_weight"), dict) else {}
    breakdown = decision.get("score_breakdown") if isinstance(decision.get("score_breakdown"), dict) else {}
    match = decision.get("memory_match") if isinstance(decision.get("memory_match"), dict) else {}
    gate = decision.get("economic_gate") if isinstance(decision.get("economic_gate"), dict) else {}
    features = candidate.get("features", {}) if isinstance(candidate, dict) and isinstance(candidate.get("features"), dict) else {}

    entry_method = _text((candidate or {}).get("entry_method") or features.get("entry_method"))
    fallback_active = "fallback" in entry_method.lower()
    replay_adjustment = int(br._safe_float(replay.get("adjustment", breakdown.get("replay_adjustment", 0)), 0.0))
    memory_adjustment = int(br._safe_float(breakdown.get("memory_adjustment", 0), 0.0))
    quality_penalty = int(br._safe_float(breakdown.get("quality_penalty", 0), 0.0))
    final_score = int(br._safe_float(breakdown.get("final_score", decision.get("agent_bias_score", 50)), 50.0))
    min_score = int(br._safe_float(breakdown.get("min_score", 0), 0.0))
    replay_quality = _text(replay.get("quality") or breakdown.get("replay_rule_quality"))
    safe_edge = replay.get("safe_edge_score")
    gate_state = "WAIT"
    if gate:
        gate_state = "OK" if bool(gate.get("trade_allowed", False)) else "BLOCK"

    return {
        "version": "brain-dashboard-v1",
        "decision": _text(decision.get("decision", "WAIT")),
        "bias": _text(decision.get("agent_bias") or breakdown.get("direction")),
        "candidate_reason": _text(decision.get("candidate_reason") or breakdown.get("candidate_reason")),
        "entry_method": entry_method,
        "entry_context": "Fallback" if fallback_active else "Box" if "box" in entry_method.lower() else "Direkt" if entry_method != "-" else "-",
        "fallback_active": fallback_active,
        "zone_type": _text(features.get("zone_type")),
        "score": final_score,
        "min_score": min_score,
        "memory_count": int(br._safe_float(match.get("count"), 0.0)),
        "memory_win_rate": match.get("win_rate"),
        "memory_avg_r": match.get("avg_r"),
        "memory_adjustment": memory_adjustment,
        "replay_quality": replay_quality,
        "replay_adjustment": replay_adjustment,
        "replay_safe_edge_score": safe_edge,
        "replay_count": replay.get("count"),
        "replay_reason": _text(replay.get("reason")),
        "quality_penalty": quality_penalty,
        "economic_gate": gate_state,
        "economic_gate_reason": _text(gate.get("reason")),
        "summary_line": (
            f"Entry {entry_method} | Replay {replay_quality} {replay_adjustment:+d} | "
            f"Memory {int(br._safe_float(match.get('count'), 0.0))} | Score {final_score}/{min_score or '-'} | Gate {gate_state}"
        ),
        "detail_line": (
            f"Winrate {_pct(match.get('win_rate'))} | AvgR {_num(match.get('avg_r'), 3)} | "
            f"Edge {_num(safe_edge, 4)} | Memory {memory_adjustment:+d} | Replay {replay_adjustment:+d} | Daten -{quality_penalty}"
        ),
    }


# --------------------------------------------------
# REPORT UPDATE
# --------------------------------------------------
def _apply_dashboard_summary_to_reports(decision: dict[str, Any]) -> dict[str, Any]:
    summary = _build_dashboard_summary(decision)
    result = dict(decision)
    result["dashboard_summary"] = summary

    brain = dict(result.get("brain") or {})
    if brain:
        brain["reads"] = f"{brain.get('reads', '')} | Dashboard {summary['summary_line']}"
        brain["message"] = f"{brain.get('message', '')} {summary['detail_line']}"
        details = dict(brain.get("details") or {})
        details["dashboard_summary"] = summary
        brain["details"] = details
        result["brain"] = brain

    ceo = dict(result.get("ceo") or {})
    if ceo:
        ceo["reads"] = f"{ceo.get('reads', '')} | {summary['summary_line']}"
        details = dict(ceo.get("details") or {})
        details["dashboard_summary"] = summary
        ceo["details"] = details
        result["ceo"] = ceo

    candidate = dict(result.get("candidate") or {}) if isinstance(result.get("candidate"), dict) else None
    if candidate is not None:
        features = dict(candidate.get("features") or {})
        features["brain_dashboard_summary"] = summary
        features["brain_entry_context"] = summary["entry_context"]
        features["brain_fallback_active"] = summary["fallback_active"]
        features["brain_replay_safe_edge_score"] = summary["replay_safe_edge_score"]
        candidate["features"] = features
        result["candidate"] = candidate

    return result


# --------------------------------------------------
# PATCHED PUBLIC FUNCTIONS
# --------------------------------------------------
def build_brain_decision(*args, **kwargs) -> dict[str, Any]:
    decision = _ORIGINAL_BUILD_BRAIN_DECISION(*args, **kwargs)
    return _apply_dashboard_summary_to_reports(decision)


def apply_economic_gate_to_brain_decision(brain_decision: dict[str, Any], value_result: dict[str, Any] | None) -> dict[str, Any]:
    decision = _ORIGINAL_APPLY_ECONOMIC_GATE(brain_decision, value_result)
    return _apply_dashboard_summary_to_reports(decision)


# --------------------------------------------------
# INSTALLATION
# --------------------------------------------------
def install() -> None:
    br.build_brain_decision = build_brain_decision
    br.apply_economic_gate_to_brain_decision = apply_economic_gate_to_brain_decision


def apply_brain_dashboard_enhancement_patch() -> None:
    install()
