from __future__ import annotations

import hashlib
import json
from typing import Any

import brain_runtime as br


# ==================================================
# brain_replay_enhancements.py
# ==================================================
# BRAIN / REPLAY STABILITY EXTENSION
# ==================================================


# --------------------------------------------------
# NORMALIZATION
# --------------------------------------------------
def _clean_symbol(symbol: Any) -> str:
    return str(symbol or "").replace(".P", "").split(":", 1)[0].strip().upper()


def _role_from_report(report: dict[str, Any]) -> str:
    role = str(report.get("role") or "").lower()
    if role in {"structure", "momentum", "context", "risk", "decision", "other"}:
        return role
    name = str(report.get("agent_name", "")).lower()
    if "risk" in name or "volatility" in name or "vola" in name:
        return "risk"
    if "volume" in name:
        return "context"
    if any(token in name for token in ("bos", "choch", "box", "support", "resistance", "swing", "hh", "breakout", "fakeout")):
        return "structure"
    if any(token in name for token in ("hma", "sma", "triple", "macd", "mfi", "rsi", "vwap")):
        return "momentum"
    if any(token in name for token in ("ceo", "brain", "audit", "llm")):
        return "decision"
    return "other"


def _quality_from_report(report: dict[str, Any]) -> str:
    details = report.get("details") if isinstance(report.get("details"), dict) else {}
    profile = details.get("quality_profile") if isinstance(details.get("quality_profile"), dict) else {}
    quality = str(profile.get("quality") or "OK").upper()
    if quality in {"STRONG", "OK", "WEAK", "OFFLINE", "BLOCK"}:
        return quality
    if bool(report.get("blocking", False)):
        return "BLOCK"
    return "OK"


def _signal_from_report(report: dict[str, Any]) -> str:
    signal = str(report.get("signal") or "NEUTRAL").upper()
    return signal if signal in {"LONG", "SHORT", "NEUTRAL"} else "NEUTRAL"


def _bucket_score(value: Any) -> int:
    score = max(0.0, min(100.0, br._safe_float(value, 0.0)))
    return int(score // 20 * 20)


# --------------------------------------------------
# STABLE PATTERN KEY
# --------------------------------------------------
def stable_pattern_parts(agent_board: dict[str, Any]) -> list[str]:
    reports = agent_board.get("reports") or []
    role_state: dict[str, dict[str, Any]] = {}
    for report in reports:
        if not isinstance(report, dict):
            continue
        role = _role_from_report(report)
        if role in {"risk", "decision", "other"}:
            continue
        quality = _quality_from_report(report)
        if quality in {"OFFLINE", "BLOCK"}:
            continue
        signal = _signal_from_report(report)
        score_bucket = _bucket_score(report.get("score"))
        bucket = role_state.setdefault(
            role,
            {
                "long": 0,
                "short": 0,
                "neutral": 0,
                "score_sum": 0,
                "count": 0,
                "strong": 0,
                "weak": 0,
            },
        )
        if signal == "LONG":
            bucket["long"] += 1
        elif signal == "SHORT":
            bucket["short"] += 1
        else:
            bucket["neutral"] += 1
        bucket["score_sum"] += score_bucket
        bucket["count"] += 1
        if quality == "STRONG":
            bucket["strong"] += 1
        if quality == "WEAK":
            bucket["weak"] += 1

    parts: list[str] = []
    for role in ("structure", "momentum", "context"):
        bucket = role_state.get(role, {})
        count = int(bucket.get("count", 0))
        if count <= 0:
            parts.append(f"{role}=OFF")
            continue
        long_count = int(bucket.get("long", 0))
        short_count = int(bucket.get("short", 0))
        if long_count > short_count:
            direction = "LONG"
        elif short_count > long_count:
            direction = "SHORT"
        else:
            direction = "NEUTRAL"
        avg_score = int(bucket.get("score_sum", 0) / max(1, count))
        quality_code = "S" if int(bucket.get("strong", 0)) > 0 else "W" if int(bucket.get("weak", 0)) >= max(1, count) else "O"
        parts.append(f"{role}={direction}:{avg_score}:{quality_code}:{count}")
    return parts


def _stable_pattern_key(agent_board: dict[str, Any]) -> str:
    symbol = _clean_symbol(agent_board.get("symbol"))
    timeframe = int(br._safe_float(agent_board.get("timeframe_seconds"), 0.0))
    parts = stable_pattern_parts(agent_board)
    base = f"symbol={symbol}|tf={timeframe}|" + "|".join(parts)
    digest = hashlib.sha1(base.encode("utf-8")).hexdigest()[:12]
    return f"v2:{digest}:{base}"


# --------------------------------------------------
# MEMORY MATCHING
# --------------------------------------------------
def _enhanced_memory_match(memory_state: dict[str, Any] | None, pattern_key: str) -> br.BrainMemoryMatch:
    if not memory_state:
        return br.BrainMemoryMatch(pattern_key, 0, None, None, None)
    records = memory_state.get("completed_trades", []) or []
    exact: list[dict[str, Any]] = []
    legacy: list[dict[str, Any]] = []
    offsets: list[float] = []
    stable_prefix = pattern_key.split(":", 2)[0] if pattern_key else ""
    stable_body = pattern_key.split(":", 2)[-1] if pattern_key else ""
    for record in records:
        if not isinstance(record, dict):
            continue
        setup = record.get("setup", {}) if isinstance(record.get("setup"), dict) else {}
        features = setup.get("features", {}) if isinstance(setup.get("features"), dict) else {}
        stored_key = str(features.get("brain_pattern_key") or features.get("pattern_key") or "")
        if stored_key == pattern_key:
            exact.append(record)
        elif stable_prefix == "v2" and stable_body and stable_body in stored_key:
            legacy.append(record)
        else:
            continue
        offset = features.get("brain_entry_offset_in_box")
        if offset is not None and br._safe_float(record.get("result_r"), 0.0) > 0:
            offsets.append(max(0.0, min(1.0, br._safe_float(offset, 0.5))))
    matches = exact + legacy[: max(0, 5 - len(exact))]
    count = len(matches)
    if count == 0:
        return br.BrainMemoryMatch(pattern_key, 0, None, None, None)
    wins = sum(1 for item in matches if br._safe_float(item.get("result_r"), 0.0) > 0)
    sum_r = sum(br._safe_float(item.get("result_r"), 0.0) for item in matches)
    return br.BrainMemoryMatch(
        pattern_key=pattern_key,
        count=count,
        win_rate=round(wins / count, 3),
        avg_r=round(sum_r / count, 3),
        entry_offset_in_box=round(sum(offsets) / len(offsets), 3) if offsets else None,
    )


# --------------------------------------------------
# REPLAY RULE WEIGHTING
# --------------------------------------------------
def _safe_rule_score(rule: dict[str, Any]) -> float:
    count = max(0, int(rule.get("count") or 0))
    win_rate = br._safe_float(rule.get("win_rate"), 0.5)
    avg_r = br._safe_float(rule.get("avg_r"), 0.0)
    profit_factor = br._safe_float(rule.get("profit_factor"), 1.0)
    count_factor = min(1.0, count / 25.0)
    win_edge = max(-1.0, min(1.0, (win_rate - 0.5) * 2.0))
    avg_edge = max(-1.0, min(1.0, avg_r / 1.5))
    pf_edge = max(-1.0, min(1.0, (profit_factor - 1.0) / 2.0))
    return round((win_edge * 0.45 + avg_edge * 0.40 + pf_edge * 0.15) * count_factor, 4)


def _rule_pattern_matches(rule: dict[str, Any], pattern_key: str) -> bool:
    rule_pattern = str(rule.get("pattern_key") or "")
    rule_key = str(rule.get("key") or "")
    if rule_pattern == pattern_key or rule_key == pattern_key:
        return True
    if pattern_key and f"pattern={pattern_key}" in rule_key:
        return True
    if pattern_key.startswith("v2:") and rule_pattern.startswith("v2:"):
        return rule_pattern.split(":", 2)[-1] == pattern_key.split(":", 2)[-1]
    return False


def _enhanced_replay_rule_weight(pattern_key: str, config: dict[str, Any], symbol: str | None = None) -> dict[str, Any]:
    if not bool(config.get("replay_rule_weight_enabled", False)):
        return {"enabled": False, "matched": False, "adjustment": 0, "quality": "OFF", "reason": "replay_rule_weight_enabled=false"}

    rules = config.get("replay_rule_weight_rules", []) or []
    if not isinstance(rules, list):
        return {"enabled": True, "matched": False, "adjustment": 0, "quality": "INVALID", "reason": "replay_rule_weight_rules ist keine Liste"}

    active_symbol = _clean_symbol(symbol)
    default_scope = str(config.get("replay_rule_scope", "asset")).lower()
    min_count = max(3, int(config.get("replay_rule_weight_min_count", 5)))
    good_bonus = max(0, int(config.get("replay_rule_good_bonus", 6)))
    bad_penalty = min(0, int(config.get("replay_rule_bad_penalty", -10)))
    max_abs = max(0, int(config.get("replay_rule_max_abs_adjustment", 12)))
    min_edge = br._safe_float(config.get("replay_rule_min_edge_score", 0.12), 0.12)

    candidates: list[dict[str, Any]] = []
    skipped_asset = 0
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        scope = str(rule.get("scope") or default_scope or "asset").lower()
        rule_symbol = _clean_symbol(rule.get("symbol"))
        if scope == "asset" and active_symbol and rule_symbol and rule_symbol != active_symbol:
            skipped_asset += 1
            continue
        if not _rule_pattern_matches(rule, pattern_key):
            continue
        clean = dict(rule)
        clean["scope"] = scope
        clean["symbol"] = rule_symbol
        clean["safe_edge_score"] = _safe_rule_score(rule)
        candidates.append(clean)

    if not candidates:
        reason = "Keine passende Replay-Regel"
        if skipped_asset:
            reason = f"Keine passende Replay-Regel fuer {active_symbol}; {skipped_asset} Regel(n) anderes Asset"
        return {"enabled": True, "matched": False, "adjustment": 0, "quality": "NO_MATCH", "symbol": active_symbol, "scope": default_scope, "reason": reason}

    candidates.sort(
        key=lambda item: (
            1 if str(item.get("scope")) == "asset" else 0,
            int(item.get("count") or 0),
            abs(float(item.get("safe_edge_score") or 0.0)),
        ),
        reverse=True,
    )
    selected = candidates[0]
    count = int(selected.get("count") or 0)
    quality = str(selected.get("quality", "WATCH")).upper()
    edge = float(selected.get("safe_edge_score") or 0.0)

    if count < min_count:
        return {
            "enabled": True,
            "matched": True,
            "adjustment": 0,
            "quality": quality,
            "count": count,
            "symbol": selected.get("symbol", active_symbol),
            "scope": selected.get("scope", default_scope),
            "key": selected.get("key", pattern_key),
            "pattern_key": selected.get("pattern_key", pattern_key),
            "safe_edge_score": edge,
            "reason": "Replay-Regel unter Mindestanzahl",
        }

    adjustment = 0
    if quality == "GOOD" and edge >= min_edge:
        adjustment = good_bonus
    elif quality == "BAD" and edge <= -min_edge:
        adjustment = bad_penalty
    elif edge >= min_edge * 1.5:
        adjustment = max(1, int(good_bonus * 0.5))
        quality = "WATCH_GOOD_EDGE"
    elif edge <= -min_edge * 1.5:
        adjustment = min(-1, int(bad_penalty * 0.5))
        quality = "WATCH_BAD_EDGE"

    adjustment = max(-max_abs, min(max_abs, int(adjustment)))
    return {
        "enabled": True,
        "matched": True,
        "adjustment": adjustment,
        "quality": quality,
        "count": count,
        "symbol": selected.get("symbol", active_symbol),
        "scope": selected.get("scope", default_scope),
        "key": selected.get("key", pattern_key),
        "pattern_key": selected.get("pattern_key", pattern_key),
        "win_rate": selected.get("win_rate"),
        "avg_r": selected.get("avg_r"),
        "profit_factor": selected.get("profit_factor"),
        "safe_edge_score": edge,
        "min_edge_score": min_edge,
        "candidate_rules": len(candidates),
        "reason": "Robuste Replay-Regel angewendet" if adjustment else "Replay-Regel ohne ausreichenden sicheren Edge",
    }


# --------------------------------------------------
# PATCH APPLICATION
# --------------------------------------------------
def apply_brain_replay_enhancement_patch() -> None:
    br._pattern_key = _stable_pattern_key
    br._memory_match = _enhanced_memory_match
    br._rule_pattern_matches = _rule_pattern_matches
    br._replay_rule_weight = _enhanced_replay_rule_weight
