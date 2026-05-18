from __future__ import annotations

from typing import Any

import brain_runtime as br


# ==================================================
# brain_ceo_quality_enhancements.py
# ==================================================
# BRAIN / CEO QUALITY COUPLING EXTENSION
# ==================================================


_ORIGINAL_BUILD_BRAIN_DECISION = br.build_brain_decision


# --------------------------------------------------
# VALUE ACCESS
# --------------------------------------------------
def _safe_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(fallback)


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, int(value)))


# --------------------------------------------------
# CEO REPORT EXTRACTION
# --------------------------------------------------
def _ceo_report_from_board(agent_board: dict[str, Any]) -> dict[str, Any] | None:
    direct = agent_board.get("ceo")
    if isinstance(direct, dict):
        return direct
    for report in agent_board.get("reports") or []:
        if not isinstance(report, dict):
            continue
        name = str(report.get("agent_name") or "").lower()
        if "ceo" in name:
            return report
    return None


def _ceo_quality_gate(agent_board: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    report = _ceo_report_from_board(agent_board)
    if not report:
        return {
            "present": False,
            "enabled": bool(config.get("brain_ceo_quality_gate_enabled", True)),
            "decision_grade": "NO_CEO",
            "final_quality_score": None,
            "role_alignment_score": None,
            "score_adjustment": 0,
            "force_wait": False,
            "force_blocked": False,
            "reason": "Kein CEO-Qualitaetsreport im Agent Board vorhanden.",
        }

    details = report.get("details") if isinstance(report.get("details"), dict) else {}
    decision_grade = str(details.get("decision_grade") or "UNKNOWN").upper()
    final_quality = _safe_int(details.get("final_quality_score", report.get("score", 50)), 50)
    role_alignment = _safe_int(details.get("role_alignment_score", details.get("quality_score", 50)), 50)
    hard_conflict = _safe_bool(details.get("hard_role_conflict", False))
    blocking = bool(report.get("blocking", False))
    enabled = bool(config.get("brain_ceo_quality_gate_enabled", True))
    min_quality = _safe_int(config.get("brain_ceo_min_final_quality", 55), 55)
    min_alignment = _safe_int(config.get("brain_ceo_min_alignment_score", 45), 45)

    score_adjustment = _clamp(int((final_quality - 60) / 3) + int((role_alignment - 55) / 5), -16, 12)
    force_blocked = enabled and (blocking or decision_grade == "BLOCKED")
    force_wait = enabled and (
        force_blocked
        or hard_conflict
        or decision_grade in {"CONFLICT", "NO_PRIMARY_CONFIRMATION"}
        or final_quality < min_quality
        or role_alignment < min_alignment
    )

    if force_blocked:
        reason = "CEO blockiert Brain wegen Blockade im Agent Board."
    elif hard_conflict or decision_grade == "CONFLICT":
        reason = "CEO erkennt harten Rollen-Konflikt zwischen Struktur und Momentum."
    elif decision_grade == "NO_PRIMARY_CONFIRMATION":
        reason = "CEO erkennt zu wenig nutzbare Struktur-/Momentum-Bestaetigung."
    elif final_quality < min_quality:
        reason = f"CEO-Finalqualitaet {final_quality} unter Minimum {min_quality}."
    elif role_alignment < min_alignment:
        reason = f"CEO-Rollen-Ausrichtung {role_alignment} unter Minimum {min_alignment}."
    else:
        reason = "CEO-Qualitaet bestaetigt Brain-Auswertung."

    return {
        "present": True,
        "enabled": enabled,
        "decision_grade": decision_grade,
        "final_quality_score": final_quality,
        "role_alignment_score": role_alignment,
        "score_adjustment": score_adjustment if enabled else 0,
        "force_wait": force_wait and not force_blocked,
        "force_blocked": force_blocked,
        "reason": reason,
        "quality_overview": details.get("quality_overview", {}),
        "primary_aligned": bool(details.get("primary_aligned", False)),
        "context_supports_primary": bool(details.get("context_supports_primary", False)),
        "hard_role_conflict": hard_conflict,
    }


# --------------------------------------------------
# RESULT APPLICATION
# --------------------------------------------------
def _apply_gate_to_result(result: dict[str, Any], gate: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    updated = dict(result)
    breakdown = dict(updated.get("score_breakdown") or {})
    brain = dict(updated.get("brain") or {})
    ceo = dict(updated.get("ceo") or {})
    candidate = updated.get("candidate")

    old_score = _safe_int(brain.get("score", updated.get("agent_bias_score", 50)), 50)
    min_score = _safe_int(breakdown.get("min_score", config.get("brain_min_score", 58)), 58)
    adjusted_score = _clamp(old_score + _safe_int(gate.get("score_adjustment"), 0))

    breakdown["ceo_quality_gate"] = gate
    breakdown["ceo_score_before"] = old_score
    breakdown["ceo_score_after"] = adjusted_score
    breakdown["ceo_score_adjustment"] = gate.get("score_adjustment", 0)

    if gate.get("force_blocked"):
        updated["decision"] = "BLOCKED"
        updated["candidate"] = None
        updated["candidate_reason"] = "ceo_quality_gate_blocked"
        updated["agent_bias"] = "NEUTRAL"
        updated["agent_bias_score"] = 0
        brain["signal"] = "NEUTRAL"
        brain["score"] = 0
        brain["blocking"] = True
        brain["message"] = f"BLOCKED: {gate.get('reason')}"
        ceo["signal"] = "NEUTRAL"
        ceo["score"] = 0
        ceo["blocking"] = True
        ceo["message"] = f"BLOCKED: {gate.get('reason')}"
    elif gate.get("force_wait"):
        updated["decision"] = "WAIT"
        updated["candidate"] = None
        updated["candidate_reason"] = "ceo_quality_gate_wait"
        updated["agent_bias_score"] = min(adjusted_score, min_score - 1)
        brain["score"] = min(adjusted_score, min_score - 1)
        brain["message"] = f"WAIT: {gate.get('reason')}"
        ceo["score"] = min(adjusted_score, min_score - 1)
        ceo["message"] = f"WAIT: {gate.get('reason')}"
    else:
        updated["agent_bias_score"] = adjusted_score
        brain["score"] = adjusted_score
        ceo["score"] = adjusted_score
        if isinstance(candidate, dict):
            candidate = dict(candidate)
            candidate["score"] = adjusted_score
            features = dict(candidate.get("features") or {})
            features["brain_ceo_quality_gate"] = gate
            candidate["features"] = features
            updated["candidate"] = candidate
        brain["message"] = f"{updated.get('decision', 'WAIT')}: {brain.get('message', '')} CEO-Gate: {gate.get('reason')}"
        ceo["message"] = f"{ceo.get('message', '')} CEO-Gate: {gate.get('reason')}"

    brain_details = dict(brain.get("details") or {})
    brain_details["ceo_quality_gate"] = gate
    brain_details["score_breakdown"] = breakdown
    brain["details"] = brain_details

    ceo_details = dict(ceo.get("details") or {})
    ceo_details["ceo_quality_gate"] = gate
    ceo_details["score_breakdown"] = breakdown
    ceo["details"] = ceo_details

    updated["brain"] = brain
    updated["ceo"] = ceo
    updated["score_breakdown"] = breakdown
    updated["ceo_quality_gate"] = gate
    return updated


# --------------------------------------------------
# PATCHED PUBLIC DECISION
# --------------------------------------------------
def _build_brain_decision_with_ceo_quality(
    symbol: str,
    timeframe_seconds: int,
    candles: list[Any],
    agent_board: dict[str, Any],
    indicator_data: dict[str, Any] | None,
    scan: dict[str, Any] | None,
    memory_state: dict[str, Any] | None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or {}
    result = _ORIGINAL_BUILD_BRAIN_DECISION(
        symbol,
        timeframe_seconds,
        candles,
        agent_board,
        indicator_data,
        scan,
        memory_state,
        cfg,
    )
    gate = _ceo_quality_gate(agent_board, cfg)
    if not gate.get("present"):
        result["ceo_quality_gate"] = gate
        breakdown = dict(result.get("score_breakdown") or {})
        breakdown["ceo_quality_gate"] = gate
        result["score_breakdown"] = breakdown
        return result
    return _apply_gate_to_result(result, gate, cfg)


# --------------------------------------------------
# PATCH APPLICATION
# --------------------------------------------------
def apply_brain_ceo_quality_patch() -> None:
    br.build_brain_decision = _build_brain_decision_with_ceo_quality
