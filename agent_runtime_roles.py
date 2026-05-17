from __future__ import annotations

from typing import Any

import agent_runtime as ar


# ==================================================
# agent_runtime_roles.py
# ==================================================
# AGENT ROLE CONTRACT EXTENSION
# ==================================================


# --------------------------------------------------
# AGENT ROLE CONTRACT
# --------------------------------------------------
def _agent_role(agent_name: str) -> str:
    text = agent_name.lower()
    if "ceo" in text or "brain" in text or "audit" in text or "llm" in text:
        return "decision"
    if "risk" in text or "volatility" in text or "vola" in text:
        return "risk"
    if "volume" in text:
        return "context"
    if (
        "bos" in text
        or "choch" in text
        or "box" in text
        or "support" in text
        or "resistance" in text
        or "swing" in text
        or "hh" in text
        or "breakout" in text
        or "fakeout" in text
    ):
        return "structure"
    if (
        "hma" in text
        or "sma" in text
        or "triple" in text
        or "macd" in text
        or "mfi" in text
        or "rsi" in text
        or "vwap" in text
    ):
        return "momentum"
    return "other"


# --------------------------------------------------
# AGENT QUALITY CONTRACT
# --------------------------------------------------
def _agent_quality_profile(report: ar.AgentReport) -> dict[str, Any]:
    role = _agent_role(report.agent_name)
    reads = str(report.reads or "").lower()
    message = str(report.message or "").lower()
    offline = (
        "_enabled=false" in reads
        or "indicator_show_" in reads
        or "deaktiviert" in message
        or "ausgeschaltet" in message
    )
    score = max(0, min(100, int(report.score)))
    reliability = score
    if report.conflict:
        reliability -= 18
    if report.blocking:
        reliability -= 35
    if offline:
        reliability -= 28
    if report.signal == "NEUTRAL" and score < 55:
        reliability -= 8
    if role == "context" and report.signal in ("LONG", "SHORT"):
        reliability = min(reliability, 68)
    if role in ("risk", "decision") and not report.blocking:
        reliability = min(reliability, 70)
    reliability = max(0, min(100, int(reliability)))

    if report.blocking:
        quality = "BLOCK"
        usable = False
    elif offline:
        quality = "OFFLINE"
        usable = False
    elif reliability >= 72 and report.signal in ("LONG", "SHORT") and role in ("structure", "momentum"):
        quality = "STRONG"
        usable = True
    elif reliability >= 55:
        quality = "OK"
        usable = role not in ("risk", "decision")
    else:
        quality = "WEAK"
        usable = report.signal in ("LONG", "SHORT") and reliability >= 40 and role not in ("risk", "decision")

    return {
        "quality": quality,
        "data_quality": "offline" if offline else "ok",
        "signal_strength": "strong" if score >= 72 else "medium" if score >= 50 else "weak",
        "reliability_score": reliability,
        "usable_for_bias": usable,
        "primary_bias_role": role in ("structure", "momentum"),
        "context_bias_role": role == "context",
        "role": role,
        "conflict": bool(report.conflict),
        "blocking": bool(report.blocking),
    }


# --------------------------------------------------
# QUALITY WEIGHT
# --------------------------------------------------
def _quality_weight(report: ar.AgentReport) -> float:
    profile = _agent_quality_profile(report)
    quality = str(profile.get("quality", "WEAK")).upper()
    if quality == "STRONG":
        return 1.15
    if quality == "OK":
        return 1.0
    if quality == "WEAK":
        return 0.55
    if quality == "OFFLINE":
        return 0.0
    if quality == "BLOCK":
        return 0.0
    return 0.75


# --------------------------------------------------
# ROLE SUMMARY
# --------------------------------------------------
def _role_signal_summary(reports: list[ar.AgentReport]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for role in ("structure", "momentum", "context", "risk", "decision", "other"):
        result[role] = {
            "role": role,
            "long_count": 0,
            "short_count": 0,
            "neutral_count": 0,
            "long_score": 0.0,
            "short_score": 0.0,
            "score_sum": 0.0,
            "quality_score_sum": 0.0,
            "active_count": 0,
            "usable_count": 0,
            "weak_count": 0,
            "offline_count": 0,
            "blocking_count": 0,
            "conflict": False,
            "consensus": "NEUTRAL",
            "strength": 0,
            "quality_strength": 0,
            "agents": [],
        }

    for report in reports:
        role = _agent_role(report.agent_name)
        bucket = result.setdefault(
            role,
            {
                "role": role,
                "long_count": 0,
                "short_count": 0,
                "neutral_count": 0,
                "long_score": 0.0,
                "short_score": 0.0,
                "score_sum": 0.0,
                "quality_score_sum": 0.0,
                "active_count": 0,
                "usable_count": 0,
                "weak_count": 0,
                "offline_count": 0,
                "blocking_count": 0,
                "conflict": False,
                "consensus": "NEUTRAL",
                "strength": 0,
                "quality_strength": 0,
                "agents": [],
            },
        )
        signal = report.signal
        score = max(0, min(100, int(report.score)))
        profile = _agent_quality_profile(report)
        quality = str(profile.get("quality", "WEAK")).upper()
        adjusted_score = round(score * _quality_weight(report), 3)
        bucket["score_sum"] += score
        bucket["quality_score_sum"] += adjusted_score
        bucket["agents"].append(report.agent_name)
        if quality == "WEAK":
            bucket["weak_count"] += 1
        if quality == "OFFLINE":
            bucket["offline_count"] += 1
        if bool(profile.get("usable_for_bias")):
            bucket["usable_count"] += 1
        if report.blocking:
            bucket["blocking_count"] += 1
        if signal == "LONG":
            bucket["long_count"] += 1
            bucket["long_score"] += adjusted_score
            bucket["active_count"] += 1
        elif signal == "SHORT":
            bucket["short_count"] += 1
            bucket["short_score"] += adjusted_score
            bucket["active_count"] += 1
        else:
            bucket["neutral_count"] += 1

    for bucket in result.values():
        bucket["conflict"] = bucket["long_count"] > 0 and bucket["short_count"] > 0
        if bucket["long_score"] > bucket["short_score"] and bucket["long_count"] > 0:
            bucket["consensus"] = "LONG"
            bucket["strength"] = int(bucket["long_score"] / max(1, bucket["long_count"]))
        elif bucket["short_score"] > bucket["long_score"] and bucket["short_count"] > 0:
            bucket["consensus"] = "SHORT"
            bucket["strength"] = int(bucket["short_score"] / max(1, bucket["short_count"]))
        else:
            bucket["consensus"] = "NEUTRAL"
            bucket["strength"] = int(bucket["quality_score_sum"] / max(1, len(bucket["agents"]))) if bucket["agents"] else 0
        bucket["quality_strength"] = bucket["strength"]
        bucket["long_score"] = round(bucket["long_score"], 3)
        bucket["short_score"] = round(bucket["short_score"], 3)
        bucket["score_sum"] = round(bucket["score_sum"], 3)
        bucket["quality_score_sum"] = round(bucket["quality_score_sum"], 3)
    return result


# --------------------------------------------------
# CEO AGENT CONTRACT
# --------------------------------------------------
def _ceo_agent(reports: list[ar.AgentReport]) -> ar.AgentReport:
    role_groups = _role_signal_summary(reports)
    blocking = any(report.blocking for report in reports)
    structure = role_groups.get("structure", {})
    momentum = role_groups.get("momentum", {})
    context = role_groups.get("context", {})
    risk = role_groups.get("risk", {})

    long_count = sum(int(group.get("long_count", 0)) for group in role_groups.values())
    short_count = sum(int(group.get("short_count", 0)) for group in role_groups.values())
    long_score = sum(float(group.get("long_score", 0)) for group in role_groups.values())
    short_score = sum(float(group.get("short_score", 0)) for group in role_groups.values())
    weak_count = sum(int(group.get("weak_count", 0)) for group in role_groups.values())
    offline_count = sum(int(group.get("offline_count", 0)) for group in role_groups.values())
    usable_count = sum(int(group.get("usable_count", 0)) for group in role_groups.values())
    conflict = long_count > 0 and short_count > 0

    structure_signal = str(structure.get("consensus", "NEUTRAL"))
    momentum_signal = str(momentum.get("consensus", "NEUTRAL"))
    context_signal = str(context.get("consensus", "NEUTRAL"))
    risk_signal = str(risk.get("consensus", "NEUTRAL"))
    hard_role_conflict = (
        structure_signal in ("LONG", "SHORT")
        and momentum_signal in ("LONG", "SHORT")
        and structure_signal != momentum_signal
    )

    primary_long_count = int(structure.get("long_count", 0)) + int(momentum.get("long_count", 0))
    primary_short_count = int(structure.get("short_count", 0)) + int(momentum.get("short_count", 0))
    primary_usable_count = int(structure.get("usable_count", 0)) + int(momentum.get("usable_count", 0))
    context_usable_count = int(context.get("usable_count", 0))

    weighted_long = (
        float(structure.get("long_score", 0)) * 1.35
        + float(momentum.get("long_score", 0)) * 1.05
        + float(context.get("long_score", 0)) * 0.45
    )
    weighted_short = (
        float(structure.get("short_score", 0)) * 1.35
        + float(momentum.get("short_score", 0)) * 1.05
        + float(context.get("short_score", 0)) * 0.45
    )
    weighted_gap = abs(weighted_long - weighted_short)
    data_quality_penalty = min(22, weak_count * 3 + offline_count * 6)
    long_direction_count = max(1, primary_long_count + int(context.get("long_count", 0)))
    short_direction_count = max(1, primary_short_count + int(context.get("short_count", 0)))
    base_strength = int(max(weighted_long / long_direction_count, weighted_short / short_direction_count)) if (long_count + short_count) else 50
    quality_score = max(0, min(100, base_strength - data_quality_penalty))

    if blocking:
        decision: ar.AgentDecision = "BLOCKED"
        score = 0
        reason = "Mindestens ein blockierender Agent meldet Blockade."
    elif hard_role_conflict:
        decision = "WAIT"
        score = max(0, min(100, quality_score))
        reason = f"Struktur und Momentum widersprechen sich: Struktur {structure_signal}, Momentum {momentum_signal}."
    elif primary_usable_count < 2:
        decision = "WAIT"
        score = max(35, min(55, quality_score))
        reason = "Zu wenige nutzbare Struktur-/Momentum-Agenten fuer CEO-Bias."
    elif weighted_long > weighted_short and weighted_long >= 110 and weighted_gap >= 22 and primary_long_count >= 2:
        decision = "LONG_BIAS"
        score = max(0, min(100, quality_score))
        reason = f"Rollen-Konsens LONG: Struktur {structure_signal}, Momentum {momentum_signal}, Kontext {context_signal}, Risk {risk_signal}."
    elif weighted_short > weighted_long and weighted_short >= 110 and weighted_gap >= 22 and primary_short_count >= 2:
        decision = "SHORT_BIAS"
        score = max(0, min(100, quality_score))
        reason = f"Rollen-Konsens SHORT: Struktur {structure_signal}, Momentum {momentum_signal}, Kontext {context_signal}, Risk {risk_signal}."
    else:
        decision = "WAIT"
        score = max(35, min(60, quality_score))
        reason = "Keine ausreichende Rollen-Bestaetigung zwischen Struktur und Momentum."

    return ar.AgentReport(
        agent_name="CEO Agent",
        function="Agentenberichte nach Rollen, Datenqualitaet, Konflikten und Risk-Gates bewerten",
        signal="LONG" if decision == "LONG_BIAS" else "SHORT" if decision == "SHORT_BIAS" else "NEUTRAL",
        score=score,
        reads=f"Structure {structure_signal} | Momentum {momentum_signal} | Context {context_signal} | Risk {risk_signal} | Quality {quality_score} | LONG {long_count}/{round(long_score, 1)} | SHORT {short_count}/{round(short_score, 1)}",
        message=f"{decision}: {reason}",
        conflict=conflict or hard_role_conflict,
        blocking=blocking,
        role="decision",
        details={
            "long_count": long_count,
            "short_count": short_count,
            "long_score": round(long_score, 3),
            "short_score": round(short_score, 3),
            "weighted_long_score": round(weighted_long, 3),
            "weighted_short_score": round(weighted_short, 3),
            "weighted_gap": round(weighted_gap, 3),
            "quality_score": quality_score,
            "data_quality_penalty": data_quality_penalty,
            "usable_count": usable_count,
            "primary_usable_count": primary_usable_count,
            "context_usable_count": context_usable_count,
            "primary_long_count": primary_long_count,
            "primary_short_count": primary_short_count,
            "weak_count": weak_count,
            "offline_count": offline_count,
            "decision": decision,
            "reason": reason,
            "role_groups": role_groups,
            "hard_role_conflict": hard_role_conflict,
        },
    )


# --------------------------------------------------
# PATCH APPLICATION
# --------------------------------------------------
def apply_agent_runtime_role_patch() -> None:
    ar._agent_role = _agent_role
    ar._agent_quality_profile = _agent_quality_profile
    ar._quality_weight = _quality_weight
    ar._role_signal_summary = _role_signal_summary
    ar._ceo_agent = _ceo_agent
