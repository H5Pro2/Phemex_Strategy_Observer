from __future__ import annotations

import json
import os
import time
from typing import Any

import requests


ROLE_ORDER = [
    "market_structure",
    "momentum",
    "risk_officer",
    "skeptic",
    "execution",
]

OLLAMA_FAST_ROLE_ORDER = [
    "market_structure",
    "risk_officer",
    "skeptic",
]

ROLE_DEFINITIONS: dict[str, dict[str, str]] = {
    "market_structure": {
        "name": "Market Structure Analyst",
        "focus": "BOS, CHoCH, HH/LL, Range, Trendkontext und Strukturqualität.",
    },
    "momentum": {
        "name": "Momentum Analyst",
        "focus": "RSI, MACD, EMA/HMA/VWAP, Volumenimpuls und Momentum-Konflikte.",
    },
    "risk_officer": {
        "name": "Risk Officer",
        "focus": "Fee/R, SL-Distanz, RR, Volatilität, Overtrading und offene Trades.",
    },
    "skeptic": {
        "name": "Skeptic / Bear Case",
        "focus": "Aktiv Gründe gegen den Trade suchen und schwache Annahmen markieren.",
    },
    "execution": {
        "name": "Execution Coach",
        "focus": "Entry-Art, Limit/Market-Qualität, Timing und ob der Trade zu spät kommt.",
    },
}

JUDGE_NAME = "CEO / Judge"

ROLE_PROMPT_EXTRA_KEYS = {
    "market_structure": "llm_role_market_structure_prompt_extra",
    "momentum": "llm_role_momentum_prompt_extra",
    "risk_officer": "llm_role_risk_officer_prompt_extra",
    "skeptic": "llm_role_skeptic_prompt_extra",
    "execution": "llm_role_execution_prompt_extra",
    "judge": "llm_role_judge_prompt_extra",
}


def role_enabled(config: dict[str, Any], role_key: str) -> bool:
    return bool(config.get(f"llm_role_{role_key}_enabled", True))


def llm_roles_enabled(config: dict[str, Any]) -> bool:
    return bool(config.get("llm_role_team_enabled", config.get("brain_llm_layer_enabled", False)))


def llm_provider_enabled(config: dict[str, Any]) -> bool:
    provider = str(config.get("llm_provider", "openai")).lower()
    if provider == "openai":
        return bool(config.get("openai_enabled", False)) and bool(os.getenv("OPENAI_API_KEY"))
    if provider == "ollama":
        return bool(config.get("ollama_enabled", False))
    return False


def _elapsed_seconds(started: float) -> float:
    return max(0.001, round(time.perf_counter() - started, 3))


def default_role_team_response(
    config: dict[str, Any],
    verdict: str,
    message: str,
    enabled: bool | None = None,
    role_reports: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    provider = str(config.get("llm_provider", "openai")).lower()
    model = str(config.get("openai_model" if provider == "openai" else "ollama_model", "gpt-4.1-mini"))
    reports = role_reports or []
    judge = _judge_from_reports(reports, verdict=verdict, message=message)
    return {
        "enabled": llm_roles_enabled(config) if enabled is None else bool(enabled),
        "provider": provider,
        "model": model,
        "role": "llm_role_team",
        "verdict": verdict,
        "decision": judge.get("decision", "WAIT"),
        "confidence": judge.get("confidence", 0.0),
        "message": message,
        "risk_note": judge.get("summary", message),
        "conflict_note": judge.get("conflict_note", "-"),
        "advice": judge.get("advice", "-"),
        "block_hint": bool(judge.get("decision") == "BLOCK"),
        "roles": reports,
        "judge": judge,
    }


def build_role_context(
    agent_board: dict[str, Any],
    scan: dict[str, Any],
    memory_match: dict[str, Any] | None,
    decision: str | None,
    candidate: dict[str, Any] | None,
    economic_gate: dict[str, Any] | None,
    indicator_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    reports = []
    for report in (agent_board.get("reports") or [])[:16]:
        reports.append(
            {
                "agent_name": str(report.get("agent_name", "-")),
                "role": str(report.get("role", "-")),
                "signal": str(report.get("signal", "NEUTRAL")),
                "score": _safe_float(report.get("score"), 0.0),
                "conflict": bool(report.get("conflict", False)),
                "blocking": bool(report.get("blocking", False)),
                "reads": _short_text(report.get("reads", "-"), 220),
                "message": _short_text(report.get("message", "-"), 220),
                "details": _compact_report_details(report.get("details")),
            }
        )
    active_reports = [report for report in reports if _report_is_active_source(report)]
    active_sources = _active_source_keys(active_reports)
    gate = economic_gate or {}
    candidate_features = candidate.get("features", {}) if isinstance(candidate, dict) else {}
    indicator_snapshot = _indicator_snapshot(indicator_data or {}, active_sources)
    return {
        "symbol": str(agent_board.get("symbol", scan.get("symbol", "-"))),
        "timeframe_seconds": int(_safe_float(agent_board.get("timeframe_seconds", 0), 0.0)),
        "pipeline_decision": str(decision or "WAIT"),
        "candidate": _candidate_context(candidate),
        "economic_gate": {
            "present": bool(economic_gate),
            "trade_allowed": bool(gate.get("trade_allowed", False)) if economic_gate else None,
            "reason": str(gate.get("reason", "")) if economic_gate else "",
            "fee_to_risk_fraction": gate.get("fee_to_risk_fraction", candidate_features.get("fee_to_risk_fraction")),
            "risk_usd": gate.get("risk_usd", candidate_features.get("risk_usd")),
        },
        "scan": {
            "setup_found": bool(scan.get("setup_found", False)),
            "side": str(scan.get("side", "")),
            "reason": _short_text(scan.get("reason", ""), 280),
        },
        "memory_match": memory_match or {},
        "technical_reports": active_reports,
        "inactive_source_count": max(0, len(reports) - len(active_reports)),
        "active_sources": active_sources,
        "technical_summary": _technical_summary(active_reports),
        "indicator_snapshot": indicator_snapshot,
        "ceo": agent_board.get("ceo") or {},
    }


def evaluate_role_team(context: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    if not llm_roles_enabled(config):
        return default_role_team_response(
            config,
            "NO_DATA",
            "LLM-Rollenteam ist deaktiviert; Entscheidung nutzt deterministische Signalquellen.",
            enabled=False,
        )
    if not llm_provider_enabled(config):
        provider = str(config.get("llm_provider", "openai")).lower()
        reason = "OPENAI_API_KEY fehlt oder OpenAI ist deaktiviert." if provider == "openai" else "Ollama ist deaktiviert oder nicht erreichbar konfiguriert."
        return default_role_team_response(config, "NO_DATA", reason, enabled=False)

    role_reports: list[dict[str, Any]] = []
    for role_key in _active_role_order(config):
        if not role_enabled(config, role_key):
            continue
        role_reports.append(_run_role(role_key, context, config))

    judge_started = time.perf_counter()
    judge = _run_judge(context, role_reports, config)
    judge_duration = _elapsed_seconds(judge_started)
    judge["duration_seconds"] = judge_duration
    verdict = "BLOCK_HINT" if judge.get("decision") == "BLOCK" else "OK" if judge.get("decision") == "APPROVE" else "WARN"
    result = default_role_team_response(
        config,
        verdict,
        "OpenAI/LLM-Rollenteam abgeschlossen; Economic Gate bleibt harte Sperre.",
        enabled=True,
        role_reports=role_reports,
    )
    result["judge"] = judge
    result["decision"] = judge.get("decision", "WAIT")
    result["confidence"] = judge.get("confidence", 0.0)
    result["risk_note"] = judge.get("summary", "-")
    result["conflict_note"] = judge.get("conflict_note", "-")
    result["advice"] = judge.get("advice", "-")
    result["block_hint"] = judge.get("decision") == "BLOCK"
    result["context_trace"] = _context_trace(context, config)
    result["usage_estimate"] = estimate_llm_usage(result["context_trace"], role_reports, judge, config)
    total_duration = _elapsed_seconds(started)
    result["duration_seconds"] = total_duration
    result["role_duration_seconds"] = round(sum(_safe_float(report.get("duration_seconds"), 0.0) for report in role_reports), 3)
    result["judge_duration_seconds"] = judge_duration
    result["timing"] = {
        "total_seconds": total_duration,
        "roles_seconds": result["role_duration_seconds"],
        "judge_seconds": judge_duration,
        "role_count": len(role_reports),
    }
    return result


def _active_role_order(config: dict[str, Any]) -> list[str]:
    provider = str(config.get("llm_provider", "openai")).lower()
    mode = str(config.get("ollama_role_mode", "fast") or "fast").lower()
    if provider == "ollama" and mode != "full":
        return OLLAMA_FAST_ROLE_ORDER
    return ROLE_ORDER


def estimate_llm_usage(
    context_trace: dict[str, Any] | None,
    role_reports: list[dict[str, Any]] | None,
    judge: dict[str, Any] | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    provider = str(config.get("llm_provider", "openai")).lower()
    model = str(config.get("openai_model" if provider == "openai" else "ollama_model", "gpt-4.1-mini"))
    input_text = json.dumps(context_trace or {}, ensure_ascii=False, separators=(",", ":"))
    output_text = json.dumps({"roles": role_reports or [], "judge": judge or {}}, ensure_ascii=False, separators=(",", ":"))
    input_tokens = max(0, int(round(len(input_text) / 4)))
    output_tokens = max(0, int(round(len(output_text) / 4)))
    total_tokens = input_tokens + output_tokens
    cost_usd = None
    if provider == "openai":
        # Current rough gpt-4.1-mini estimate: $0.40/M input, $1.60/M output.
        input_per_million = 0.40
        output_per_million = 1.60
        cost_usd = round((input_tokens / 1_000_000 * input_per_million) + (output_tokens / 1_000_000 * output_per_million), 6)
    return {
        "estimated": True,
        "provider": provider,
        "model": model,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cost_usd": cost_usd,
        "note": "Grobe Schätzung aus Textlänge; echte API-Usage kann abweichen." if provider == "openai" else "Lokaler Provider; keine OpenAI API-Kosten.",
    }


def _run_role(role_key: str, context: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    role = ROLE_DEFINITIONS[role_key]
    prompt_extra = _role_prompt_extra(config, role_key)
    role_context = _role_context(context, role_key)
    system = (
        f"Du bist {role['name']} in einem Paper-Trading-Rollenteam. "
        f"Dein Fokus: {role['focus']} "
        f"{prompt_extra}"
        "Antworte nur mit einem JSON-Objekt. Keine Markdown-Codeblöcke. "
        "Erlaubte decision Werte: APPROVE, WAIT, BLOCK. "
        "Setze keine Entry-, SL-, TP- oder Positionsgrößen. "
        "Du darfst das Economic Gate nicht umgehen."
    )
    user = {
        "task": "Bewerte den Kandidaten aus deiner Spezialrolle.",
        "required_schema": {
            "role": role["name"],
            "decision": "APPROVE|WAIT|BLOCK",
            "confidence": "0.0-1.0",
            "reasons": ["kurze deutsche Gründe"],
            "hard_block": "boolean",
        },
        "context": role_context,
    }
    started = time.perf_counter()
    parsed = _call_llm_json(system, user, config)
    report = _normalize_role_report(role_key, role["name"], parsed)
    report["duration_seconds"] = _elapsed_seconds(started)
    return report


def _run_judge(context: dict[str, Any], role_reports: list[dict[str, Any]], config: dict[str, Any]) -> dict[str, Any]:
    if not role_reports:
        return _judge_from_reports(role_reports, verdict="NO_DATA", message="Keine aktiven LLM-Rollen.")
    prompt_extra = _role_prompt_extra(config, "judge")
    system = (
        "Du bist CEO / Judge eines Paper-Trading-Rollenteams. "
        "Fasse Rollenberichte zusammen und entscheide APPROVE, WAIT oder BLOCK. "
        "Hard-Blocks von Risk Officer oder Skeptic haben Vorrang. "
        "Economic Gate bleibt harte Sperre und darf nicht umgangen werden. "
        f"{prompt_extra}"
        "Antworte nur als JSON-Objekt."
    )
    user = {
        "task": "Erzeuge die finale Rollen-Team-Entscheidung.",
        "required_schema": {
            "role": JUDGE_NAME,
            "decision": "APPROVE|WAIT|BLOCK",
            "confidence": "0.0-1.0",
            "summary": "kurze deutsche Zusammenfassung",
            "conflict_note": "kurzer Konflikthinweis oder -",
            "advice": "kurze Handlungsempfehlung",
        },
        "context": context,
        "role_reports": role_reports,
    }
    parsed = _call_llm_json(system, user, config)
    return _normalize_judge(parsed, role_reports)


def _context_trace(context: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot = context.get("indicator_snapshot") if isinstance(context.get("indicator_snapshot"), dict) else {}
    reports = context.get("technical_reports") if isinstance(context.get("technical_reports"), list) else []
    cfg = config or {}
    return {
        "version": 1,
        "symbol": context.get("symbol"),
        "timeframe_seconds": context.get("timeframe_seconds"),
        "pipeline_decision": context.get("pipeline_decision"),
        "candidate": context.get("candidate"),
        "economic_gate": context.get("economic_gate"),
        "memory_match": context.get("memory_match"),
        "technical_summary": context.get("technical_summary"),
        "active_sources": context.get("active_sources") or [],
        "inactive_source_count": context.get("inactive_source_count", 0),
        "technical_reports": [
            {
                "agent_name": report.get("agent_name"),
                "role": report.get("role"),
                "signal": report.get("signal"),
                "score": report.get("score"),
                "reads": report.get("reads"),
                "message": report.get("message"),
            }
            for report in reports[:12]
            if isinstance(report, dict)
        ],
        "indicator_snapshot": snapshot,
        "role_inputs": {
            role_key: {
                "role": ROLE_DEFINITIONS.get(role_key, {}).get("name", role_key),
                "focus": ROLE_DEFINITIONS.get(role_key, {}).get("focus", "-"),
                "prompt_extra": _role_prompt_extra(cfg, role_key),
                "technical_reports": [
                    report.get("agent_name")
                    for report in _role_context(context, role_key).get("technical_reports", [])
                    if isinstance(report, dict)
                ],
                "snapshot_keys": sorted((_role_context(context, role_key).get("indicator_snapshot") or {}).keys()),
            }
            for role_key in _active_role_order(cfg)
        },
        "judge_input": {
            "role": JUDGE_NAME,
            "prompt_extra": _role_prompt_extra(cfg, "judge"),
        },
    }


def _role_prompt_extra(config: dict[str, Any], role_key: str) -> str:
    key = ROLE_PROMPT_EXTRA_KEYS.get(role_key)
    if not key:
        return ""
    value = str(config.get(key, "") or "").strip()
    if not value:
        return ""
    provider = str(config.get("llm_provider", "openai")).lower()
    value = _short_text(value, 700 if provider == "ollama" else 1600)
    return f"Zusätzliche Verhaltensanweisung aus der lokalen Konfiguration: {value} "


def _call_llm_json(system: str, user: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    provider = str(config.get("llm_provider", "openai")).lower()
    if provider == "ollama":
        return _call_ollama_json(system, user, config)
    return _call_openai_json(system, user, config)


def _call_openai_json(system: str, user: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY fehlt")
    model = str(config.get("openai_model", "gpt-4.1-mini"))
    timeout = max(1.0, min(120.0, _safe_float(config.get("llm_role_timeout_seconds", config.get("openai_timeout_seconds", 30)), 30.0)))
    temperature = max(0.0, min(1.0, _safe_float(config.get("llm_role_temperature", 0.0), 0.0)))
    payload = {
        "model": model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, separators=(",", ":"))},
        ],
    }
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=timeout,
    )
    if response.status_code >= 400:
        raise RuntimeError(_openai_error_message(response))
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("OpenAI-Antwort ist kein JSON-Objekt")
    return parsed


def _openai_error_message(response: requests.Response) -> str:
    status_code = int(response.status_code)
    message = response.text.strip()[:500] if response.text else f"HTTP {status_code}"
    error_type = ""
    error_code = ""
    try:
        data = response.json()
        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            message = str(error.get("message") or message)
            error_type = str(error.get("type") or "")
            error_code = str(error.get("code") or "")
    except ValueError:
        pass
    if status_code == 429 and (error_code == "insufficient_quota" or "quota" in message.lower()):
        return "Kein OpenAI API-Guthaben oder Projekt-Budget verfügbar. Bitte Billing/Guthaben in der OpenAI Platform prüfen."
    parts = [f"OpenAI HTTP {status_code}", message]
    meta = " / ".join(part for part in (error_type, error_code) if part)
    if meta:
        parts.append(meta)
    return ": ".join(parts)


def _call_ollama_json(system: str, user: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    base_url = str(config.get("ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
    model = str(config.get("ollama_model", "qwen2.5:3b"))
    timeout = max(1.0, min(300.0, _safe_float(config.get("ollama_timeout_seconds", config.get("llm_role_timeout_seconds", 60)), 60.0)))
    temperature = max(0.0, min(1.0, _safe_float(config.get("llm_role_temperature", config.get("ollama_temperature", 0.0)), 0.0)))
    payload = {
        "model": model,
        "system": system,
        "prompt": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature},
    }
    response = requests.post(f"{base_url}/api/generate", json=payload, timeout=timeout)
    response.raise_for_status()
    parsed = json.loads(str(response.json().get("response", "{}")))
    if not isinstance(parsed, dict):
        raise ValueError("Ollama-Antwort ist kein JSON-Objekt")
    return parsed


def _normalize_role_report(role_key: str, role_name: str, parsed: dict[str, Any]) -> dict[str, Any]:
    decision = str(parsed.get("decision", "WAIT")).upper()
    if decision not in {"APPROVE", "WAIT", "BLOCK"}:
        decision = "WAIT"
    reasons = parsed.get("reasons", [])
    if not isinstance(reasons, list):
        reasons = [str(reasons)]
    return {
        "role_key": role_key,
        "role": role_name,
        "decision": decision,
        "confidence": max(0.0, min(1.0, _safe_float(parsed.get("confidence"), 0.0))),
        "reasons": [_short_text(reason, 180) for reason in reasons[:4] if _short_text(reason, 180)],
        "hard_block": bool(parsed.get("hard_block", False)) or decision == "BLOCK",
    }


def _normalize_judge(parsed: dict[str, Any], reports: list[dict[str, Any]]) -> dict[str, Any]:
    fallback = _judge_from_reports(reports, verdict="WARN", message="Judge-Fallback aus Rollenentscheidungen.")
    decision = str(parsed.get("decision", fallback["decision"])).upper()
    if decision not in {"APPROVE", "WAIT", "BLOCK"}:
        decision = fallback["decision"]
    if any(report.get("hard_block") and report.get("role_key") in {"risk_officer", "skeptic"} for report in reports):
        decision = "BLOCK"
    return {
        "role": JUDGE_NAME,
        "decision": decision,
        "confidence": max(0.0, min(1.0, _safe_float(parsed.get("confidence"), fallback["confidence"]))),
        "summary": _short_text(parsed.get("summary", fallback["summary"]), 260),
        "conflict_note": _short_text(parsed.get("conflict_note", fallback["conflict_note"]), 220),
        "advice": _short_text(parsed.get("advice", fallback["advice"]), 220),
    }


def _judge_from_reports(reports: list[dict[str, Any]], verdict: str, message: str) -> dict[str, Any]:
    blocks = [report for report in reports if report.get("decision") == "BLOCK" or report.get("hard_block")]
    approves = [report for report in reports if report.get("decision") == "APPROVE"]
    waits = [report for report in reports if report.get("decision") == "WAIT"]
    if blocks:
        decision = "BLOCK"
        summary = f"{len(blocks)} Rolle(n) blockieren den Kandidaten."
    elif reports and len(approves) >= max(2, len(reports) - 1):
        decision = "APPROVE"
        summary = "Rollen-Team bestätigt den Kandidaten mehrheitlich."
    elif reports:
        decision = "WAIT"
        summary = "Rollen-Team sieht noch keinen sauberen Konsens."
    else:
        decision = "WAIT"
        summary = message
    avg_confidence = sum(_safe_float(report.get("confidence"), 0.0) for report in reports) / max(1, len(reports))
    return {
        "role": JUDGE_NAME,
        "decision": decision,
        "confidence": round(avg_confidence, 3),
        "summary": summary if reports else message,
        "conflict_note": f"{len(waits)} WAIT / {len(blocks)} BLOCK / {len(approves)} APPROVE" if reports else "-",
        "advice": "Kandidat nur weiterreichen, wenn Economic Gate ebenfalls freigibt." if decision == "APPROVE" else "Abwarten oder Kandidat verwerfen.",
        "verdict": verdict,
    }


def _candidate_context(candidate: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(candidate, dict):
        return None
    features = candidate.get("features", {}) if isinstance(candidate.get("features"), dict) else {}
    return {
        "symbol": candidate.get("symbol"),
        "decision": candidate.get("decision"),
        "side": candidate.get("side"),
        "entry_price": candidate.get("entry_price"),
        "sl_price": candidate.get("sl_price"),
        "tp_price": candidate.get("tp_price"),
        "entry_method": candidate.get("entry_method"),
        "target_method": candidate.get("target_method"),
        "confidence": candidate.get("confidence"),
        "score": candidate.get("score"),
        "reason": candidate.get("reason"),
        "fee_to_risk_fraction": features.get("fee_to_risk_fraction"),
        "risk_usd": features.get("risk_usd"),
        "value_preview": features.get("brain_value_preview"),
    }


def _role_context(context: dict[str, Any], role_key: str) -> dict[str, Any]:
    role_map = {
        "market_structure": {"structure", "signal"},
        "momentum": {"momentum", "signal"},
        "risk_officer": {"risk"},
        "execution": {"structure", "momentum", "risk", "signal"},
        "skeptic": {"structure", "momentum", "risk", "signal"},
    }
    allowed = role_map.get(role_key, {"structure", "momentum", "risk", "signal"})
    reports = [
        report for report in context.get("technical_reports", [])
        if str(report.get("role", "signal")) in allowed
    ]
    snapshot = context.get("indicator_snapshot") or {}
    return {
        "symbol": context.get("symbol"),
        "timeframe_seconds": context.get("timeframe_seconds"),
        "pipeline_decision": context.get("pipeline_decision"),
        "candidate": context.get("candidate"),
        "economic_gate": context.get("economic_gate"),
        "scan": context.get("scan"),
        "memory_match": context.get("memory_match"),
        "technical_summary": context.get("technical_summary"),
        "technical_reports": reports[:10],
        "indicator_snapshot": _snapshot_for_role(snapshot, role_key),
        "ceo": context.get("ceo"),
    }


def _technical_summary(reports: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for role in ("structure", "momentum", "risk", "signal"):
        items = [report for report in reports if str(report.get("role", "signal")) == role]
        summary[role] = {
            "count": len(items),
            "long": sum(1 for item in items if item.get("signal") == "LONG"),
            "short": sum(1 for item in items if item.get("signal") == "SHORT"),
            "neutral": sum(1 for item in items if item.get("signal") == "NEUTRAL"),
            "blocking": sum(1 for item in items if item.get("blocking")),
            "avg_score": round(sum(_safe_float(item.get("score"), 0.0) for item in items) / max(1, len(items)), 3),
        }
    return summary


def _snapshot_for_role(snapshot: dict[str, Any], role_key: str) -> dict[str, Any]:
    if role_key == "market_structure":
        return {key: snapshot.get(key) for key in ("structure", "support_resistance", "latest_price")}
    if role_key == "momentum":
        return {key: snapshot.get(key) for key in ("momentum", "volume", "latest_price")}
    if role_key == "risk_officer":
        return {key: snapshot.get(key) for key in ("risk", "volume", "latest_price")}
    if role_key == "execution":
        return {key: snapshot.get(key) for key in ("structure", "momentum", "risk", "latest_price")}
    return snapshot


def _report_is_active_source(report: dict[str, Any]) -> bool:
    reads = str(report.get("reads", "") or "").lower()
    message = str(report.get("message", "") or "").lower()
    inactive_markers = ("_enabled=false", "indicator_show_", "deaktiviert", "ausgeschaltet")
    if any(marker in reads or marker in message for marker in inactive_markers):
        return False
    name = str(report.get("agent_name", "") or "").lower()
    return "agent" in name or "risk" in name or "volume" in name


def _active_source_keys(reports: list[dict[str, Any]]) -> list[str]:
    keys: list[str] = []
    for report in reports:
        name = str(report.get("agent_name", "") or "").lower()
        if "bos" in name or "choch" in name:
            keys.append("bos_choch")
        elif "box" in name:
            keys.append("boxes")
        elif "support" in name or "resistance" in name:
            keys.append("support_resistance")
        elif "swing" in name:
            keys.append("swing_labels")
        elif "hma" in name:
            keys.append("hma")
        elif "sma" in name:
            keys.append("sma")
        elif "triple" in name:
            keys.append("triple_ema")
        elif "macd" in name:
            keys.append("macd")
        elif "mfi" in name:
            keys.append("mfi")
        elif "rsi" in name:
            keys.append("rsi")
        elif "vwap" in name:
            keys.append("vwap")
        elif "breakout" in name or "fakeout" in name:
            keys.append("breakout_fakeout")
        elif "volume" in name:
            keys.append("volume")
        elif "volatility" in name or "vola" in name:
            keys.append("volatility")
        elif "risk" in name:
            keys.append("risk")
    return sorted(set(keys))


def _line_if_active(lines: dict[str, dict[str, Any]], name: str, active_sources: set[str], source_key: str) -> dict[str, Any] | None:
    if source_key not in active_sources:
        return None
    return _line_tail(lines.get(name))


def _indicator_snapshot(indicator: dict[str, Any], active_source_keys: list[str] | None = None) -> dict[str, Any]:
    active_sources = set(active_source_keys or [])
    lines = {str(line.get("name")): line for line in indicator.get("lines", []) if isinstance(line, dict)}
    boxes = [item for item in indicator.get("boxes", []) if isinstance(item, dict)]
    labels = [item for item in indicator.get("labels", []) if isinstance(item, dict)]
    sr_levels = [item for item in indicator.get("support_resistance", []) if isinstance(item, dict)]
    latest_price = indicator.get("latest_price") or indicator.get("close")
    return {
        "latest_price": latest_price,
        "structure": {
            "bos_choch": _last_items(indicator.get("bos_choch") or indicator.get("events") or [], 6) if "bos_choch" in active_sources else [],
            "boxes": [_compact_map(item, ("type", "direction", "low", "high", "price", "start_time", "end_time")) for item in boxes[-6:]] if "boxes" in active_sources else [],
            "swing_labels": [_compact_map(item, ("text", "direction", "price", "time")) for item in labels[-8:]] if "swing_labels" in active_sources else [],
        },
        "support_resistance": [_compact_map(item, ("kind", "price", "strength", "crossed")) for item in sr_levels[-8:]] if "support_resistance" in active_sources else [],
        "momentum": {
            "hma": _line_if_active(lines, "HMA", active_sources, "hma"),
            "sma": _line_if_active(lines, "SMA", active_sources, "sma"),
            "triple_ema_fast": _line_if_active(lines, "TRIPLE_EMA_FAST", active_sources, "triple_ema"),
            "triple_ema_slow": _line_if_active(lines, "TRIPLE_EMA_SLOW", active_sources, "triple_ema"),
            "macd": _line_if_active(lines, "MACD", active_sources, "macd"),
            "macd_signal": _line_if_active(lines, "MACD_SIGNAL", active_sources, "macd"),
            "macd_histogram": _line_if_active(lines, "MACD_HISTOGRAM", active_sources, "macd"),
            "mfi": _line_if_active(lines, "MFI", active_sources, "mfi"),
        },
        "volume": {
            "volume_agent": _line_if_active(lines, "Volume", active_sources, "volume"),
            "raw": indicator.get("volume") if "volume" in active_sources else None,
        },
        "risk": {
            "atr": indicator.get("atr") if "volatility" in active_sources or "risk" in active_sources else None,
            "volatility": indicator.get("volatility") if "volatility" in active_sources or "risk" in active_sources else None,
        },
    }


def _line_tail(line: dict[str, Any] | None, count: int = 3) -> dict[str, Any] | None:
    if not isinstance(line, dict):
        return None
    series = [item for item in line.get("series", []) if isinstance(item, dict)]
    tail = series[-count:]
    return {
        "name": line.get("name"),
        "last": tail[-1].get("value") if tail else None,
        "previous": tail[-2].get("value") if len(tail) >= 2 else None,
        "tail": [_compact_map(item, ("time", "value")) for item in tail],
    }


def _last_items(value: Any, count: int) -> list[Any]:
    if not isinstance(value, list):
        return []
    return [_compact_any(item) for item in value[-count:]]


def _compact_report_details(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    profile = value.get("quality_profile") if isinstance(value.get("quality_profile"), dict) else {}
    return {
        "quality_profile": _compact_map(
            profile,
            ("quality", "data_quality", "signal_strength", "reliability_score", "usable_for_bias", "role", "conflict", "blocking"),
        )
    }


def _compact_map(value: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: _compact_any(value.get(key)) for key in keys if key in value}


def _compact_any(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 8)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _compact_any(val) for key, val in list(value.items())[:12]}
    if isinstance(value, list):
        return [_compact_any(item) for item in value[:8]]
    return str(value)


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _short_text(value: Any, max_chars: int) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = " ".join(text.split())
    return text[:max_chars]
