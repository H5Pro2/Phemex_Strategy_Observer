from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import threading
from typing import Any, Literal
from urllib import error as urlerror, request as urlrequest


BrainDecisionValue = Literal["LONG", "SHORT", "WAIT", "BLOCKED"]
BrainSignal = Literal["LONG", "SHORT", "NEUTRAL"]


# ==================================================
# brain_runtime.py
# ==================================================
# AGENT BRAIN / LEARNING DECISION RUNTIME
# ==================================================


@dataclass(frozen=True)
class BrainReport:
    agent_name: str
    function: str
    signal: BrainSignal
    score: int
    reads: str
    message: str
    conflict: bool = False
    blocking: bool = False
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrainMemoryMatch:
    pattern_key: str
    count: int
    win_rate: float | None
    avg_r: float | None
    entry_offset_in_box: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrainTradeCandidate:
    symbol: str
    decision: Literal["LONG", "SHORT"]
    side: Literal["long", "short"]
    entry_price: float
    sl_price: float
    tp_price: float
    entry_zone_low: float
    entry_zone_high: float
    entry_method: str
    target_method: str
    signal_candle_time: int
    confirmation_candle_time: int
    pattern_key: str
    confidence: float
    score: int
    reason: str
    features: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --------------------------------------------------
# LLM ASYNC WORKER STATE
# --------------------------------------------------
_LLM_AUDIT_LOCK = threading.Lock()
_LLM_AUDIT_STATE: dict[str, Any] = {
    "running": False,
    "active_key": None,
    "active_hash": None,
    "last_hash_by_key": {},
    "last_result_by_key": {},
}


# --------------------------------------------------
# VALUE ACCESS
# --------------------------------------------------
def _value(candle: Any, key: str, default: float = 0.0) -> float:
    try:
        if isinstance(candle, dict):
            return float(candle.get(key, default))
        return float(getattr(candle, key, default))
    except (TypeError, ValueError):
        return float(default)


def _timestamp(candle: Any, default: int = 0) -> int:
    try:
        if isinstance(candle, dict):
            return int(candle.get("timestamp", default))
        return int(getattr(candle, "timestamp", default))
    except (TypeError, ValueError):
        return int(default)


def _last(candles: list[Any]) -> Any | None:
    return candles[-1] if candles else None


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(fallback)


def _round_price(value: float) -> float:
    return round(float(value), 8)


# --------------------------------------------------
# AGENT SCOREBOARD
# --------------------------------------------------
def _agent_weight(name: str) -> float:
    text = name.lower()
    if "bos" in text or "choch" in text:
        return 1.25
    if "box" in text:
        return 1.25
    if "hh" in text or "swing" in text:
        return 1.0
    if "triple" in text:
        return 0.9
    if "macd" in text:
        return 0.85
    if "hma" in text:
        return 0.8
    if "sma" in text:
        return 0.8
    if "mfi" in text:
        return 0.75
    if "rsi" in text:
        return 0.8
    if "vwap" in text:
        return 0.85
    if "breakout" in text or "fakeout" in text:
        return 1.05
    if "volume" in text:
        return 0.75
    if "volatility" in text:
        return 0.55
    if "risk" in text:
        return 0.5
    return 1.0


def _report_quality_weight(report: dict[str, Any]) -> float:
    details = report.get("details") if isinstance(report.get("details"), dict) else {}
    profile = details.get("quality_profile") if isinstance(details.get("quality_profile"), dict) else {}
    quality = str(profile.get("quality", "OK")).upper()
    reliability = max(0.0, min(100.0, _safe_float(profile.get("reliability_score"), report.get("score", 50.0))))
    if bool(report.get("blocking", False)) or quality == "BLOCK":
        return 0.0
    if quality == "OFFLINE":
        return 0.0
    if quality == "WEAK":
        return max(0.35, reliability / 140.0)
    if quality == "STRONG":
        return 1.12
    return max(0.65, min(1.05, reliability / 75.0))


def _direction_scores(agent_board: dict[str, Any]) -> dict[str, Any]:
    reports = agent_board.get("reports") or []
    long_score = 0.0
    short_score = 0.0
    long_count = 0
    short_count = 0
    neutral_count = 0
    long_weight_sum = 0.0
    short_weight_sum = 0.0
    weak_count = 0
    offline_count = 0
    blocking_count = 0
    parts: list[str] = []
    for report in reports:
        signal = str(report.get("signal", "NEUTRAL")).upper()
        score = max(0.0, min(100.0, _safe_float(report.get("score"), 0.0)))
        details = report.get("details") if isinstance(report.get("details"), dict) else {}
        profile = details.get("quality_profile") if isinstance(details.get("quality_profile"), dict) else {}
        quality = str(profile.get("quality", "OK")).upper()
        if quality == "WEAK":
            weak_count += 1
        if quality == "OFFLINE":
            offline_count += 1
        if bool(report.get("blocking", False)):
            blocking_count += 1
        weight = _agent_weight(str(report.get("agent_name", ""))) * _report_quality_weight(report)
        adjusted = score * weight
        if signal == "LONG" and adjusted > 0:
            long_score += adjusted
            long_weight_sum += weight
            long_count += 1
        elif signal == "SHORT" and adjusted > 0:
            short_score += adjusted
            short_weight_sum += weight
            short_count += 1
        else:
            neutral_count += 1
        parts.append(f"{report.get('agent_name', '-')}: {signal} {int(score)} q={quality} w={round(weight, 2)}")
    return {
        "long_score": round(long_score, 3),
        "short_score": round(short_score, 3),
        "long_weight_sum": round(long_weight_sum, 6),
        "short_weight_sum": round(short_weight_sum, 6),
        "long_count": long_count,
        "short_count": short_count,
        "neutral_count": neutral_count,
        "long_weight_sum": round(long_weight_sum, 6),
        "short_weight_sum": round(short_weight_sum, 6),
        "weak_count": weak_count,
        "offline_count": offline_count,
        "blocking_count": blocking_count,
        "data_quality_penalty": min(12, weak_count * 2),
        "reads": " | ".join(parts),
        "conflict": long_count > 0 and short_count > 0,
    }


def _pattern_key(agent_board: dict[str, Any]) -> str:
    items: list[str] = []
    for report in agent_board.get("reports") or []:
        name = str(report.get("agent_name", "agent")).lower()
        short_name = (
            name.replace(" agent", "")
            .replace(" / ", "_")
            .replace(" ", "_")
            .replace("_/_", "_")
        )
        signal = str(report.get("signal", "NEUTRAL")).upper()
        score_bucket = int(_safe_float(report.get("score"), 0.0) // 10 * 10)
        items.append(f"{short_name}={signal}:{score_bucket}")
    return "|".join(items)


# --------------------------------------------------
# MEMORY MATCHING
# --------------------------------------------------
def _memory_match(memory_state: dict[str, Any] | None, pattern_key: str) -> BrainMemoryMatch:
    if not memory_state:
        return BrainMemoryMatch(pattern_key, 0, None, None, None)
    records = memory_state.get("completed_trades", []) or []
    matches: list[dict[str, Any]] = []
    offsets: list[float] = []
    for record in records:
        setup = record.get("setup", {}) if isinstance(record, dict) else {}
        features = setup.get("features", {}) if isinstance(setup, dict) else {}
        if features.get("brain_pattern_key") != pattern_key:
            continue
        matches.append(record)
        offset = features.get("brain_entry_offset_in_box")
        if offset is not None and _safe_float(record.get("result_r"), 0.0) > 0:
            offsets.append(max(0.0, min(1.0, _safe_float(offset, 0.5))))
    count = len(matches)
    if count == 0:
        return BrainMemoryMatch(pattern_key, 0, None, None, None)
    wins = sum(1 for item in matches if _safe_float(item.get("result_r"), 0.0) > 0)
    sum_r = sum(_safe_float(item.get("result_r"), 0.0) for item in matches)
    return BrainMemoryMatch(
        pattern_key=pattern_key,
        count=count,
        win_rate=round(wins / count, 3),
        avg_r=round(sum_r / count, 3),
        entry_offset_in_box=round(sum(offsets) / len(offsets), 3) if offsets else None,
    )


def _memory_score_adjustment(match: BrainMemoryMatch, min_count: int) -> int:
    if match.count < max(1, min_count) or match.win_rate is None or match.avg_r is None:
        return 0
    win_component = int((match.win_rate - 0.5) * 30)
    r_component = int(max(-1.0, min(1.5, match.avg_r)) * 12)
    return max(-20, min(22, win_component + r_component))




# --------------------------------------------------
# REPLAY RULE WEIGHTING
# --------------------------------------------------
def _rule_pattern_matches(rule: dict[str, Any], pattern_key: str) -> bool:
    rule_pattern = str(rule.get("pattern_key") or "")
    rule_key = str(rule.get("key") or "")
    if rule_pattern and rule_pattern == pattern_key:
        return True
    if rule_key == pattern_key:
        return True
    return f"pattern={pattern_key}" in rule_key


def _replay_rule_weight(pattern_key: str, config: dict[str, Any], symbol: str | None = None) -> dict[str, Any]:
    if not bool(config.get("replay_rule_weight_enabled", False)):
        return {"enabled": False, "matched": False, "adjustment": 0, "quality": "OFF", "reason": "replay_rule_weight_enabled=false"}

    rules = config.get("replay_rule_weight_rules", []) or []
    if not isinstance(rules, list):
        return {"enabled": True, "matched": False, "adjustment": 0, "quality": "INVALID", "reason": "replay_rule_weight_rules ist keine Liste"}

    active_symbol = str(symbol or "").replace(".P", "").split(":", 1)[0].strip().upper()
    default_scope = str(config.get("replay_rule_scope", "asset")).lower()
    min_count = int(config.get("replay_rule_weight_min_count", 2))
    good_bonus = int(config.get("replay_rule_good_bonus", 8))
    bad_penalty = int(config.get("replay_rule_bad_penalty", -14))
    max_abs = max(0, int(config.get("replay_rule_max_abs_adjustment", 18)))

    skipped_asset = 0
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        scope = str(rule.get("scope") or default_scope or "asset").lower()
        rule_symbol = str(rule.get("symbol") or "").replace(".P", "").split(":", 1)[0].strip().upper()
        if scope == "asset" and active_symbol and rule_symbol and rule_symbol != active_symbol:
            skipped_asset += 1
            continue
        if not _rule_pattern_matches(rule, pattern_key):
            continue
        count = int(rule.get("count") or 0)
        if count < min_count:
            return {"enabled": True, "matched": True, "adjustment": 0, "quality": str(rule.get("quality", "WATCH")), "count": count, "symbol": rule_symbol, "scope": scope, "key": rule.get("key", pattern_key), "reason": "Replay-Regel unter Mindestanzahl"}
        quality = str(rule.get("quality", "WATCH")).upper()
        if quality == "GOOD":
            adjustment = good_bonus
        elif quality == "BAD":
            adjustment = bad_penalty
        else:
            adjustment = 0
        adjustment = max(-max_abs, min(max_abs, int(adjustment)))
        return {
            "enabled": True,
            "matched": True,
            "adjustment": adjustment,
            "quality": quality,
            "count": count,
            "symbol": rule_symbol,
            "scope": scope,
            "key": rule.get("key", pattern_key),
            "pattern_key": rule.get("pattern_key", pattern_key),
            "win_rate": rule.get("win_rate"),
            "avg_r": rule.get("avg_r"),
            "reason": "Asset-gebundene Replay-Regel angewendet" if scope == "asset" and adjustment else "Replay-Regelgewicht angewendet" if adjustment else "Replay-Regel nur Watch/Neutral",
        }

    reason = "Keine passende Replay-Regel"
    if skipped_asset:
        reason = f"Keine passende Replay-Regel für {active_symbol}; {skipped_asset} Regel(n) anderes Asset"
    return {"enabled": True, "matched": False, "adjustment": 0, "quality": "NO_MATCH", "symbol": active_symbol, "scope": default_scope, "reason": reason}


# --------------------------------------------------
# STRUCTURE SELECTION
# --------------------------------------------------
def _boxes_for_direction(indicator_data: dict[str, Any], decision: str) -> list[dict[str, Any]]:
    wanted = "rising" if decision == "LONG" else "falling"
    boxes = [box for box in indicator_data.get("boxes", []) if str(box.get("direction")) == wanted]
    boxes.sort(key=lambda box: int(box.get("start_timestamp", 0)))
    return boxes


def _box_bounds(box: dict[str, Any]) -> tuple[float, float]:
    top = _safe_float(box.get("top"), 0.0)
    bottom = _safe_float(box.get("bottom"), 0.0)
    return min(top, bottom), max(top, bottom)


def _entry_from_box(decision: str, box: dict[str, Any], match: BrainMemoryMatch, config: dict[str, Any]) -> tuple[float, float, float, float]:
    low, high = _box_bounds(box)
    width = max(high - low, 1e-12)
    default_offset = _safe_float(config.get("brain_entry_box_offset", 0.35), 0.35)
    memory_offset = match.entry_offset_in_box
    offset = memory_offset if memory_offset is not None else default_offset
    offset = max(0.1, min(0.9, offset))
    if decision == "LONG":
        entry = low + (width * offset)
    else:
        entry = high - (width * offset)
        offset = (entry - low) / width
    return _round_price(entry), _round_price(low), _round_price(high), round(offset, 4)


def _fallback_entry(candles: list[Any], decision: str) -> tuple[float, float, float, float]:
    last = _last(candles)
    if last is None:
        return 0.0, 0.0, 0.0, 0.5
    close = _value(last, "close")
    high = _value(last, "high")
    low = _value(last, "low")
    if high <= low:
        high = close * 1.0005
        low = close * 0.9995
    return _round_price(close), _round_price(low), _round_price(high), 0.5


def _target_from_labels(decision: str, entry: float, indicator_data: dict[str, Any]) -> tuple[float | None, str]:
    labels = indicator_data.get("labels") or []
    candidates: list[float] = []
    for label in labels:
        text = str(label.get("text", ""))
        price = _safe_float(label.get("price"), 0.0)
        if decision == "LONG" and text in ("HH", "LH") and price > entry:
            candidates.append(price)
        if decision == "SHORT" and text in ("HL", "LL") and 0 < price < entry:
            candidates.append(price)
    if decision == "LONG" and candidates:
        return _round_price(min(candidates)), "nearest_swing_label_high"
    if decision == "SHORT" and candidates:
        return _round_price(max(candidates)), "nearest_swing_label_low"
    return None, "missing_swing_label_target"


def _target_from_recent_range(decision: str, entry: float, candles: list[Any], config: dict[str, Any]) -> tuple[float | None, str]:
    lookback = max(10, int(config.get("brain_target_lookback_candles", 36)))
    window = candles[-min(len(candles), lookback):]
    if not window:
        return None, "missing_recent_range"
    if decision == "LONG":
        target = max(_value(candle, "high") for candle in window)
        return (_round_price(target), "local_visible_high") if target > entry else (None, "local_high_not_above_entry")
    target = min(_value(candle, "low") for candle in window)
    return (_round_price(target), "local_visible_low") if 0 < target < entry else (None, "local_low_not_below_entry")


def _target_from_reward_risk(decision: str, entry: float, sl: float, rr: float) -> float | None:
    risk = abs(entry - sl)
    if risk <= 0 or rr <= 0:
        return None
    if decision == "LONG":
        return _round_price(entry + risk * rr)
    return _round_price(entry - risk * rr)


def _apply_timeframe_target_cap(
    decision: str,
    entry: float,
    sl: float,
    tp: float,
    target_method: str,
    config: dict[str, Any],
) -> tuple[float, str]:
    if not bool(config.get("brain_cap_target_to_max_rr", True)):
        return _round_price(tp), target_method

    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk <= 0 or reward <= 0:
        return _round_price(tp), target_method

    configured_rr = _safe_float(config.get("reward_risk", 1.5), 1.5)
    max_rr = _safe_float(config.get("brain_max_target_rr", configured_rr), configured_rr)
    if max_rr <= 0:
        return _round_price(tp), target_method

    target_rr = reward / risk
    if target_rr <= max_rr:
        return _round_price(tp), target_method

    capped_tp = _target_from_reward_risk(decision, entry, sl, max_rr)
    if capped_tp is None:
        return _round_price(tp), target_method
    return capped_tp, f"{target_method}_capped_to_{round(max_rr, 3)}r"


def _true_range(candle: Any, previous_close: float | None) -> float:
    high = _value(candle, "high")
    low = _value(candle, "low")
    if previous_close is None:
        return max(high - low, 0.0)
    return max(high - low, abs(high - previous_close), abs(low - previous_close), 0.0)


def _atr_value(candles: list[Any], period: int) -> float | None:
    if not candles:
        return None
    safe_period = max(1, int(period))
    previous_close: float | None = None
    ranges: list[float] = []
    for candle in candles:
        ranges.append(_true_range(candle, previous_close))
        previous_close = _value(candle, "close")
    window = ranges[-min(len(ranges), safe_period):]
    if not window:
        return None
    atr = sum(window) / len(window)
    return atr if atr > 0 else None


def _structure_stop_price(decision: str, entry: float, zone_low: float, zone_high: float, candles: list[Any], config: dict[str, Any]) -> float:
    lookback = max(2, int(config.get("brain_stop_lookback_candles", 8)))
    window = candles[-min(len(candles), lookback):]
    buffer_fraction = _safe_float(config.get("stop_loss_buffer_percent", 0.0), 0.0) / 100.0
    buffer = entry * buffer_fraction
    if decision == "LONG":
        recent_low = min((_value(candle, "low") for candle in window), default=zone_low)
        return _round_price(min(zone_low, recent_low) - buffer)
    recent_high = max((_value(candle, "high") for candle in window), default=zone_high)
    return _round_price(max(zone_high, recent_high) + buffer)


def _atr_stop_price(decision: str, entry: float, candles: list[Any], config: dict[str, Any]) -> float | None:
    period = max(1, int(config.get("stop_loss_atr_period", 14)))
    multiplier = max(0.0, _safe_float(config.get("stop_loss_atr_multiplier", 1.5), 1.5))
    atr = _atr_value(candles, period)
    if atr is None or multiplier <= 0:
        return None
    distance = atr * multiplier
    if decision == "LONG":
        return _round_price(entry - distance)
    return _round_price(entry + distance)


def _stop_price(decision: str, entry: float, zone_low: float, zone_high: float, candles: list[Any], config: dict[str, Any]) -> tuple[float, str]:
    mode = str(config.get("stop_loss_mode", "structure")).lower()
    if mode == "atr":
        atr_stop = _atr_stop_price(decision, entry, candles, config)
        if atr_stop is not None:
            return atr_stop, "atr_stop"
        return _structure_stop_price(decision, entry, zone_low, zone_high, candles, config), "structure_stop_atr_fallback"
    if mode == "fixed_percent":
        stop_fraction = _safe_float(config.get("stop_loss_percent", 0.25), 0.25) / 100.0
        if stop_fraction > 0:
            if decision == "LONG":
                return _round_price(entry * (1.0 - stop_fraction)), "fixed_percent_stop"
            return _round_price(entry * (1.0 + stop_fraction)), "fixed_percent_stop"
    return _structure_stop_price(decision, entry, zone_low, zone_high, candles, config), "structure_stop"


# --------------------------------------------------
# LLM AUDIT LAYER
# --------------------------------------------------
def _llm_audit_response(
    enabled: bool,
    provider: str,
    model: str,
    verdict: str,
    message: str,
    confidence_note: str = "-",
    risk_note: str = "-",
    conflict_note: str = "-",
    advice: str = "-",
    block_hint: bool = False,
) -> dict[str, Any]:
    return {
        "enabled": enabled,
        "provider": provider,
        "model": model,
        "role": "local_trade_auditor",
        "verdict": verdict,
        "confidence_note": confidence_note,
        "risk_note": risk_note,
        "conflict_note": conflict_note,
        "advice": advice,
        "block_hint": block_hint,
        "message": message,
    }


def _llm_audit_context(
    agent_board: dict[str, Any],
    scan: dict[str, Any],
    match: BrainMemoryMatch,
    decision: str | None,
    candidate: dict[str, Any] | None,
    economic_gate: dict[str, Any] | None,
) -> dict[str, Any]:
    reports = []
    for report in agent_board.get("reports", [])[:12]:
        reports.append(
            {
                "agent_name": str(report.get("agent_name", "-")),
                "signal": str(report.get("signal", "NEUTRAL")),
                "score": int(_safe_float(report.get("score"), 0.0)),
                "conflict": bool(report.get("conflict", False)),
                "blocking": bool(report.get("blocking", False)),
            }
        )

    scores = _direction_scores(agent_board)
    gate = economic_gate or {}
    return {
        "symbol": str(agent_board.get("symbol", scan.get("symbol", "-"))),
        "timeframe_seconds": int(_safe_float(agent_board.get("timeframe_seconds", 0), 0.0)),
        "decision": str(decision or "WAIT"),
        "agent_scores": scores,
        "agent_reports": reports,
        "memory_match": {
            "count": match.count,
            "win_rate": match.win_rate,
            "avg_r": match.avg_r,
        },
        "candidate_present": candidate is not None,
        "economic_gate": {
            "present": bool(economic_gate),
            "trade_allowed": bool(gate.get("trade_allowed", False)) if economic_gate else None,
            "reason": str(gate.get("reason", "")) if economic_gate else "",
        },
        "scan": {
            "setup_found": bool(scan.get("setup_found", False)),
            "side": str(scan.get("side", "")),
            "reason": str(scan.get("reason", "")),
        },
    }


def _llm_system_prompt() -> str:
    return (
        "Du bist ein lokaler Trade-Auditor fuer ein Paper-Trading-System. "
        "Antworte immer auf Deutsch. "
        "Verwende keine chinesischen, japanischen oder koreanischen Schriftzeichen. "
        "Antworte nur mit einem einzelnen JSON-Objekt ohne Markdown, ohne Codeblock und ohne Zusatztext. "
        "Du darfst keine Entry-, Stop-Loss-, Take-Profit- oder Positionsgroessen setzen. "
        "Du darfst das Economic Gate nicht umgehen."
    )


def _llm_prompt(context: dict[str, Any], config: dict[str, Any]) -> str:
    max_chars = max(500, int(_safe_float(config.get("ollama_max_prompt_chars", 4000), 4000.0)))
    payload = json.dumps(context, ensure_ascii=False, separators=(",", ":"))[:max_chars]
    return (
        "Erzeuge ein deutsches Audit fuer den folgenden reduzierten Bot-Kontext. "
        "Pflichtformat: JSON mit exakt diesen Schluesseln: "
        "verdict, confidence_note, risk_note, conflict_note, advice, block_hint. "
        "Erlaubte verdict Werte: OK, WARN, BLOCK_HINT, NO_DATA, ERROR. "
        "Alle Textfelder muessen kurz, sachlich und deutsch sein. "
        "Wenn keine passende Aussage moeglich ist, nutze '-' als Textwert. "
        "Beispiel: {\"verdict\":\"WARN\",\"confidence_note\":\"-\",\"risk_note\":\"Risiko pruefen.\",\"conflict_note\":\"-\",\"advice\":\"Abwarten.\",\"block_hint\":false}. "
        f"Audit-Kontext: {payload}"
    )


def _ollama_generate(prompt: str, config: dict[str, Any]) -> str:
    base_url = str(config.get("ollama_base_url", "http://127.0.0.1:11434")).rstrip("/")
    model = str(config.get("ollama_model", "qwen2.5:3b"))
    timeout = max(1.0, min(300.0, _safe_float(config.get("ollama_timeout_seconds", 60), 60.0)))
    temperature = max(0.0, min(1.0, _safe_float(config.get("ollama_temperature", 0.0), 0.0)))
    payload = {
        "model": model,
        "system": _llm_system_prompt(),
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature},
    }
    request = urlrequest.Request(
        f"{base_url}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlrequest.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8")
    data = json.loads(raw)
    return str(data.get("response", ""))


def _contains_disallowed_llm_script(value: Any) -> bool:
    text = str(value or "")
    return any(
        ("\u3040" <= char <= "\u30ff")
        or ("\u3400" <= char <= "\u4dbf")
        or ("\u4e00" <= char <= "\u9fff")
        or ("\uf900" <= char <= "\ufaff")
        or ("\uac00" <= char <= "\ud7af")
        for char in text
    )


def _clean_llm_text_value(value: Any, fallback: str = "-", max_chars: int = 240) -> str:
    if value is None or isinstance(value, (dict, list, tuple, set)):
        return fallback
    text = str(value).replace("\r", " ").replace("\n", " ").strip()
    text = " ".join(text.split())
    text = text.strip(" `\"',;")
    if not text or text in {"-", "--", "---", "–", "—", "null", "None", "none"}:
        return fallback
    if not any(char.isalnum() for char in text):
        return fallback
    if _contains_disallowed_llm_script(text):
        return fallback
    return text[:max_chars]


def _llm_text_field(parsed: dict[str, Any], key: str, fallback: str = "-") -> str:
    return _clean_llm_text_value(parsed.get(key, fallback), fallback=fallback)


def _parse_llm_audit(raw_text: str, config: dict[str, Any]) -> dict[str, Any]:
    provider = "ollama"
    model = str(config.get("ollama_model", "qwen2.5:3b"))
    allowed_verdicts = {"OK", "WARN", "BLOCK_HINT", "NO_DATA", "ERROR"}
    try:
        parsed = json.loads(raw_text)
    except (TypeError, json.JSONDecodeError):
        return _llm_audit_response(
            True,
            provider,
            model,
            "WARN",
            "Ollama-Antwort war kein valides JSON; Pipeline laeuft deterministisch weiter.",
            advice=_clean_llm_text_value(raw_text),
        )

    if not isinstance(parsed, dict):
        return _llm_audit_response(
            True,
            provider,
            model,
            "WARN",
            "Ollama-Antwort war kein JSON-Objekt; Pipeline laeuft deterministisch weiter.",
            advice="Ollama muss ein einzelnes JSON-Objekt liefern.",
        )

    checked_fields = ["confidence_note", "risk_note", "conflict_note", "advice"]
    if any(_contains_disallowed_llm_script(parsed.get(field, "")) for field in checked_fields):
        return _llm_audit_response(
            True,
            provider,
            model,
            "ERROR",
            "Ollama-Antwort verworfen: Antwortsprache ist nicht Deutsch; Pipeline laeuft deterministisch weiter.",
            risk_note="Ollama-Antwort enthielt nicht erlaubte Schriftzeichen und wurde nicht angezeigt.",
            conflict_note="-",
            advice="Modell erneut laufen lassen oder Prompt/Modell pruefen.",
            block_hint=False,
        )

    verdict = str(parsed.get("verdict", "WARN")).upper()
    if verdict not in allowed_verdicts:
        verdict = "WARN"
    block_hint = bool(parsed.get("block_hint", False)) and bool(config.get("ollama_block_hint_enabled", False))
    return _llm_audit_response(
        True,
        provider,
        model,
        verdict,
        "Ollama-Audit abgeschlossen; Ergebnis ist nur Hinweis, keine Trade-Freigabe.",
        confidence_note=_llm_text_field(parsed, "confidence_note"),
        risk_note=_llm_text_field(parsed, "risk_note"),
        conflict_note=_llm_text_field(parsed, "conflict_note"),
        advice=_llm_text_field(parsed, "advice"),
        block_hint=block_hint,
    )



def _llm_audit_key(context: dict[str, Any]) -> str:
    return str(context.get("symbol") or "global")


def _llm_audit_hash(context: dict[str, Any]) -> str:
    payload = json.dumps(context, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _llm_async_status_response(config: dict[str, Any], message: str, risk_note: str, advice: str) -> dict[str, Any]:
    return _llm_audit_response(
        True,
        "ollama",
        str(config.get("ollama_model", "qwen2.5:3b")),
        "NO_DATA",
        message,
        risk_note=risk_note,
        advice=advice,
    )


def _run_ollama_audit_worker(context_key: str, context_hash: str, context: dict[str, Any], config: dict[str, Any]) -> None:
    try:
        raw_text = _ollama_generate(_llm_prompt(context, config), config)
        result = _parse_llm_audit(raw_text, config)
    except (OSError, TimeoutError, ValueError, json.JSONDecodeError, urlerror.URLError) as exc:
        result = _llm_audit_response(
            True,
            "ollama",
            str(config.get("ollama_model", "qwen2.5:3b")),
            "ERROR",
            f"Ollama-Audit fehlgeschlagen: {type(exc).__name__}; Pipeline laeuft deterministisch weiter.",
            risk_note=f"Ollama-Audit fehlgeschlagen: {type(exc).__name__}; Pipeline laeuft deterministisch weiter.",
            advice="Ollama-Server, Modellname und lokalen Modellstart pruefen.",
        )

    with _LLM_AUDIT_LOCK:
        _LLM_AUDIT_STATE["running"] = False
        _LLM_AUDIT_STATE["active_key"] = None
        _LLM_AUDIT_STATE["active_hash"] = None
        _LLM_AUDIT_STATE.setdefault("last_result_by_key", {})[context_key] = result
        if result.get("verdict") != "ERROR":
            _LLM_AUDIT_STATE.setdefault("last_hash_by_key", {})[context_key] = context_hash


def _submit_llm_audit_async(context: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    context_key = _llm_audit_key(context)
    context_hash = _llm_audit_hash(context)
    with _LLM_AUDIT_LOCK:
        last_hash = (_LLM_AUDIT_STATE.get("last_hash_by_key") or {}).get(context_key)
        last_result = (_LLM_AUDIT_STATE.get("last_result_by_key") or {}).get(context_key)
        if _LLM_AUDIT_STATE.get("running"):
            if last_result:
                result = dict(last_result)
                result["message"] = "Ollama verarbeitet noch den vorherigen Audit-Kontext; neuer Kontext wird erst nach Abschluss im naechsten Tick uebergeben."
                result["risk_note"] = "LLM-Worker ist beschaeftigt; Trading-Pipeline laeuft deterministisch weiter."
                result["advice"] = "Warten bis der lokale Ollama-Worker frei ist."
                return result
            return _llm_async_status_response(
                config,
                "Ollama verarbeitet den ersten Audit-Kontext im Hintergrund.",
                "LLM-Worker ist beschaeftigt; Trading-Pipeline laeuft deterministisch weiter.",
                "Neuer Kontext wird erst nach Abschluss im naechsten Tick uebergeben.",
            )
        if last_hash == context_hash and last_result:
            return dict(last_result)
        _LLM_AUDIT_STATE["running"] = True
        _LLM_AUDIT_STATE["active_key"] = context_key
        _LLM_AUDIT_STATE["active_hash"] = context_hash
        thread = threading.Thread(
            target=_run_ollama_audit_worker,
            args=(context_key, context_hash, json.loads(json.dumps(context)), dict(config)),
            daemon=True,
        )
        thread.start()
    return _llm_async_status_response(
        config,
        "Ollama-Audit wurde asynchron gestartet; Ergebnis erscheint nach Abschluss in einem folgenden Tick.",
        "LLM laeuft getrennt von der Trading-Pipeline; keine Blockade durch Modelllaufzeit.",
        "Warten auf lokalen Ollama-Worker.",
    )

def _llm_learning_layer(
    agent_board: dict[str, Any],
    scan: dict[str, Any],
    match: BrainMemoryMatch,
    config: dict[str, Any],
    decision: str | None = None,
    candidate: dict[str, Any] | None = None,
    economic_gate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    enabled = bool(config.get("brain_llm_layer_enabled", False))
    model = str(config.get("ollama_model", "qwen2.5:3b"))
    if not enabled:
        return _llm_audit_response(
            False,
            "ollama",
            model,
            "NO_DATA",
            "LLM-Schicht ist deaktiviert; Entscheidung nutzt Agenten, Struktur und Memory-Matching.",
            risk_note="Keine Datenuebertragung an Ollama, weil brain_llm_layer_enabled=false.",
            advice="LLM-Schicht und Ollama-Provider in Agent Settings aktivieren, wenn lokales Audit gewuenscht ist.",
        )

    if not bool(config.get("ollama_enabled", False)):
        return _llm_audit_response(
            False,
            "ollama",
            model,
            "NO_DATA",
            "LLM-Schicht ist aktiv, aber lokaler Ollama-Provider ist nicht aktiviert.",
            risk_note="Keine Datenuebertragung an Ollama, weil ollama_enabled=false.",
            advice="Ollama-Provider in Agent Settings aktivieren und lokalen Server bereitstellen.",
        )

    context = _llm_audit_context(agent_board, scan, match, decision, candidate, economic_gate)
    return _submit_llm_audit_async(context, config)


# --------------------------------------------------
# CANDIDATE BUILDING
# --------------------------------------------------
def _build_candidate(
    symbol: str,
    timeframe_seconds: int,
    decision: Literal["LONG", "SHORT"],
    score: int,
    pattern_key: str,
    match: BrainMemoryMatch,
    candles: list[Any],
    indicator_data: dict[str, Any],
    config: dict[str, Any],
) -> tuple[BrainTradeCandidate | None, str]:
    if not candles:
        return None, "keine Kerzen vorhanden"
    boxes = _boxes_for_direction(indicator_data, decision)
    require_box = bool(config.get("brain_require_box_for_trade", False))
    if boxes:
        active_box = boxes[-1]
        entry, zone_low, zone_high, entry_offset = _entry_from_box(decision, active_box, match, config)
        entry_method = "brain_box_optimized_limit"
        zone_type = "ll_box" if decision == "LONG" else "hh_box"
    elif require_box:
        return None, "keine passende LL/HH Box fuer Brain-Entry"
    else:
        entry, zone_low, zone_high, entry_offset = _fallback_entry(candles, decision)
        entry_method = "brain_agent_fallback_market_context"
        zone_type = "candle_fallback_range"

    sl, stop_method = _stop_price(decision, entry, zone_low, zone_high, candles, config)
    if decision == "LONG" and not sl < entry:
        return None, "ungueltiger LONG Stop unter Entry fehlt"
    if decision == "SHORT" and not sl > entry:
        return None, "ungueltiger SHORT Stop ueber Entry fehlt"

    rr_target = _safe_float(config.get("reward_risk", 1.5), 1.5)
    tp = _target_from_reward_risk(decision, entry, sl, rr_target)
    target_method = "reward_risk_target"
    if tp is None:
        return None, "kein gueltiges RR-TP-Ziel fuer Brain-Setup"

    if decision == "LONG" and not entry < tp:
        return None, "ungueltiger LONG TP ueber Entry fehlt"
    if decision == "SHORT" and not tp < entry:
        return None, "ungueltiger SHORT TP unter Entry fehlt"

    last_time = _timestamp(candles[-1], int(0))
    side = "long" if decision == "LONG" else "short"
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    rr = reward / risk if risk > 0 else 0.0
    confidence = round(max(0.05, min(0.95, score / 100.0)), 3)
    features = {
        "symbol": symbol,
        "side": side,
        "strategy": "agent_brain_ceo",
        "signal_tf": int(timeframe_seconds),
        "confirm_tf": int(timeframe_seconds),
        "entry_method": entry_method,
        "target_method": target_method,
        "stop_method": stop_method,
        "zone_type": zone_type,
        "zone_low": zone_low,
        "zone_high": zone_high,
        "zone_size_pct": round((zone_high - zone_low) / max(entry, 1e-12), 6),
        "brain_pattern_key": pattern_key,
        "brain_score": score,
        "brain_memory_count": match.count,
        "brain_memory_win_rate": match.win_rate,
        "brain_memory_avg_r": match.avg_r,
        "brain_entry_offset_in_box": entry_offset,
        "brain_rr_before_gate": round(rr, 6),
        "trend_alignment": "agent_board",
        "session": "all",
    }
    return BrainTradeCandidate(
        symbol=symbol,
        decision=decision,
        side=side,
        entry_price=entry,
        sl_price=sl,
        tp_price=_round_price(tp),
        entry_zone_low=zone_low,
        entry_zone_high=zone_high,
        entry_method=entry_method,
        target_method=target_method,
        signal_candle_time=last_time,
        confirmation_candle_time=last_time,
        pattern_key=pattern_key,
        confidence=confidence,
        score=score,
        reason=f"Brain {decision}: Agentenrichtung + Entry-Logik + Memory-Matching.",
        features=features,
    ), "candidate_ok"


# --------------------------------------------------
# PUBLIC DECISION
# --------------------------------------------------
def build_brain_decision(
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
    indicator = indicator_data or {}
    scan_data = scan or {}
    if not bool(cfg.get("brain_enabled", True)):
        brain_report = BrainReport(
            agent_name="Brain / Lernschicht",
            function="Handelsentscheidung aus Agenten und Erfahrung",
            signal="NEUTRAL",
            score=0,
            reads="brain_enabled=false",
            message="Brain ist deaktiviert; keine Brain-Handelsentscheidung.",
            blocking=True,
        )
        ceo_report = BrainReport(
            agent_name="CEO Trader",
            function="Brain + Economic Gate kontrollieren",
            signal="NEUTRAL",
            score=0,
            reads="Brain deaktiviert",
            message="BLOCKED: Brain deaktiviert.",
            blocking=True,
        )
        return {
            "decision": "BLOCKED",
            "brain": brain_report.to_dict(),
            "ceo": ceo_report.to_dict(),
            "candidate": None,
            "memory_match": BrainMemoryMatch("", 0, None, None, None).to_dict(),
            "llm_layer": _llm_learning_layer(agent_board, scan_data, BrainMemoryMatch("", 0, None, None, None), cfg, decision="BLOCKED"),
        }

    blocking_reports = [report for report in agent_board.get("reports", []) if bool(report.get("blocking", False))]
    if blocking_reports:
        names = ", ".join(str(report.get("agent_name", "Agent")) for report in blocking_reports)
        brain_report = BrainReport(
            agent_name="Brain / Lernschicht",
            function="Handelsentscheidung aus Agenten und Erfahrung",
            signal="NEUTRAL",
            score=0,
            reads=f"blocking: {names}",
            message="Brain blockiert, weil mindestens ein blockierender Agent keine Freigabe liefert.",
            blocking=True,
        )
        ceo_report = BrainReport(
            agent_name="CEO Trader",
            function="Brain + Economic Gate kontrollieren",
            signal="NEUTRAL",
            score=0,
            reads=f"blocking: {names}",
            message="BLOCKED: Agenten-Blockade vor Economic Gate.",
            blocking=True,
        )
        empty_match = BrainMemoryMatch("", 0, None, None, None)
        return {
            "decision": "BLOCKED",
            "brain": brain_report.to_dict(),
            "ceo": ceo_report.to_dict(),
            "candidate": None,
            "memory_match": empty_match.to_dict(),
            "llm_layer": _llm_learning_layer(agent_board, scan_data, empty_match, cfg, decision="BLOCKED"),
        }

    scores = _direction_scores(agent_board)
    pattern = _pattern_key(agent_board)
    min_memory_count = int(cfg.get("brain_memory_min_count", 3))
    match = _memory_match(memory_state, pattern)
    memory_adjustment = _memory_score_adjustment(match, min_memory_count)
    replay_rule_weight = _replay_rule_weight(pattern, cfg, symbol)
    replay_adjustment = int(replay_rule_weight.get("adjustment", 0))
    adjustment = memory_adjustment + replay_adjustment
    quality_penalty = int(scores.get("data_quality_penalty", 0))
    min_score = int(cfg.get("brain_min_score", 58))
    min_gap = float(cfg.get("brain_min_score_gap", 18.0))
    min_alignment = int(cfg.get("brain_min_agent_alignment", 2))
    long_score = float(scores["long_score"])
    short_score = float(scores["short_score"])
    long_count = int(scores["long_count"])
    short_count = int(scores["short_count"])
    long_weight_sum = float(scores.get("long_weight_sum", long_count) or long_count or 1.0)
    short_weight_sum = float(scores.get("short_weight_sum", short_count) or short_count or 1.0)
    decision: BrainDecisionValue = "WAIT"
    signal: BrainSignal = "NEUTRAL"
    base_score = 50
    reason = "Keine ausreichende Agenten-Mehrheit."

    if long_count >= min_alignment and long_score > short_score and (long_score - short_score) >= min_gap:
        signal = "LONG"
        raw_score = (long_score / max(0.1, long_weight_sum)) + adjustment - quality_penalty
        base_score = int(max(0, min(100, raw_score)))
        if base_score >= min_score:
            decision = "LONG"
            reason = "Agenten-Matching LONG dominiert."
        else:
            decision = "WAIT"
            reason = "LONG-Bias erkannt, aber Score nach Memory/Replay/Datenqualitaet unter Minimum."
    elif short_count >= min_alignment and short_score > long_score and (short_score - long_score) >= min_gap:
        signal = "SHORT"
        raw_score = (short_score / max(0.1, short_weight_sum)) + adjustment - quality_penalty
        base_score = int(max(0, min(100, raw_score)))
        if base_score >= min_score:
            decision = "SHORT"
            reason = "Agenten-Matching SHORT dominiert."
        else:
            decision = "WAIT"
            reason = "SHORT-Bias erkannt, aber Score nach Memory/Replay/Datenqualitaet unter Minimum."

    candidate: BrainTradeCandidate | None = None
    candidate_reason = "no_candidate"
    if decision in ("LONG", "SHORT") and base_score >= min_score:
        candidate, candidate_reason = _build_candidate(
            symbol=symbol,
            timeframe_seconds=timeframe_seconds,
            decision=decision,
            score=base_score,
            pattern_key=pattern,
            match=match,
            candles=candles,
            indicator_data=indicator,
            config=cfg,
        )
        if candidate is None:
            decision = "WAIT"
            reason = candidate_reason

    raw_direction_average = 50.0
    if signal == "LONG" and long_count:
        raw_direction_average = long_score / max(0.1, long_weight_sum)
    elif signal == "SHORT" and short_count:
        raw_direction_average = short_score / max(0.1, short_weight_sum)
    score_breakdown = {
        "decision": decision,
        "direction": signal,
        "candidate_reason": candidate_reason,
        "long_count": long_count,
        "short_count": short_count,
        "long_score": round(long_score, 3),
        "short_score": round(short_score, 3),
        "long_weight_sum": round(long_weight_sum, 6),
        "short_weight_sum": round(short_weight_sum, 6),
        "score_gap": round(abs(long_score - short_score), 3),
        "raw_direction_average": round(raw_direction_average, 3),
        "memory_adjustment": memory_adjustment,
        "replay_adjustment": replay_adjustment,
        "total_adjustment": adjustment,
        "quality_penalty": quality_penalty,
        "weak_count": scores.get("weak_count", 0),
        "offline_count": scores.get("offline_count", 0),
        "blocking_count": scores.get("blocking_count", 0),
        "final_score": base_score if signal != "NEUTRAL" else 50,
        "min_score": min_score,
        "min_gap": min_gap,
        "min_alignment": min_alignment,
        "memory_count": match.count,
        "memory_win_rate": match.win_rate,
        "memory_avg_r": match.avg_r,
        "replay_rule_quality": replay_rule_weight.get("quality"),
        "replay_rule_matched": replay_rule_weight.get("matched"),
        "replay_rule_scope": replay_rule_weight.get("scope"),
        "replay_rule_symbol": replay_rule_weight.get("symbol", symbol),
    }

    if candidate is not None:
        candidate.features["replay_rule_weight"] = replay_rule_weight
        candidate.features["replay_rule_weight_enabled"] = bool(replay_rule_weight.get("enabled", False))
        candidate.features["replay_rule_weight_matched"] = bool(replay_rule_weight.get("matched", False))
        candidate.features["replay_rule_weight_adjustment"] = replay_adjustment
        candidate.features["replay_rule_weight_quality"] = replay_rule_weight.get("quality", "OFF")
        candidate.features["replay_rule_weight_key"] = replay_rule_weight.get("key", pattern)
        candidate.features["replay_rule_weight_symbol"] = replay_rule_weight.get("symbol", symbol)
        candidate.features["replay_rule_weight_scope"] = replay_rule_weight.get("scope", cfg.get("replay_rule_scope", "asset"))
        candidate.features["brain_score_breakdown"] = score_breakdown

    if candidate is not None:
        llm_layer = _llm_audit_response(
            bool(cfg.get("brain_llm_layer_enabled", False)) and bool(cfg.get("ollama_enabled", False)),
            "ollama",
            str(cfg.get("ollama_model", "qwen2.5:3b")),
            "NO_DATA",
            "Ollama-Audit wartet auf Economic-Gate-Ergebnis.",
            risk_note="Economic Gate wurde fuer diesen Kandidaten noch nicht berechnet.",
            advice="Audit wird nach der Value-Gate-Pruefung aktualisiert.",
        )
    else:
        llm_layer = _llm_learning_layer(
            agent_board,
            scan_data,
            match,
            cfg,
            decision=decision,
            candidate=None,
        )

    brain_score = base_score if signal != "NEUTRAL" else 50
    brain_report = BrainReport(
        agent_name="Brain / Lernschicht",
        function="Agenten-Bias bewerten und Entry-Logik mit Erfahrung abgleichen",
        signal=signal,
        score=brain_score,
        reads=f"LONG {long_count}/{round(long_score,1)} | SHORT {short_count}/{round(short_score,1)} | Memory {match.count} | ReplayRule {replay_rule_weight.get('quality')} {replay_adjustment:+d} | DataPenalty {quality_penalty}",
        message=f"{decision}: {reason} Memory Winrate {match.win_rate if match.win_rate is not None else '-'} AvgR {match.avg_r if match.avg_r is not None else '-'}. Replay-Regel {replay_rule_weight.get('quality')} {replay_adjustment:+d}. Datenqualitaet {quality_penalty} Abzug.",
        conflict=bool(scores["conflict"]),
        blocking=decision == "BLOCKED",
        details={"score_breakdown": score_breakdown},
    )
    ceo_signal: BrainSignal = signal
    ceo_score = brain_score
    if candidate is not None:
        ceo_message = f"{candidate.decision}: Agenten-Bias bestaetigt; Brain-Kandidat bereit; Economic Gate prueft RR/TP/SL."
    elif signal in ("LONG", "SHORT"):
        ceo_message = f"WAIT: {signal}-Bias bewertet, aber kein freigegebener Trade-Plan ({candidate_reason})."
    else:
        ceo_message = "WAIT: Keine ausreichende Agentenmehrheit fuer einen Trade-Plan."
    ceo_report = BrainReport(
        agent_name="CEO Trader",
        function="Alle Agentendaten bewerten und nur freigegebene Trade-Plaene an Economic Gate uebergeben",
        signal=ceo_signal,
        score=ceo_score,
        reads=f"Agenten-Bias {signal} | Trade {decision} | Candidate {candidate_reason}",
        message=ceo_message,
        conflict=bool(scores["conflict"]),
        blocking=False,
        details={"score_breakdown": score_breakdown},
    )
    return {
        "decision": decision,
        "scores": scores,
        "agent_bias": signal,
        "agent_bias_score": brain_score,
        "candidate_reason": candidate_reason,
        "brain": brain_report.to_dict(),
        "ceo": ceo_report.to_dict(),
        "candidate": candidate.to_dict() if candidate else None,
        "memory_match": match.to_dict(),
        "replay_rule_weight": replay_rule_weight,
        "score_breakdown": score_breakdown,
        "llm_layer": llm_layer,
    }


def refresh_llm_layer_after_economic_gate(
    agent_board: dict[str, Any],
    scan: dict[str, Any],
    brain_decision: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or {}
    match_data = brain_decision.get("memory_match") or {}
    match = BrainMemoryMatch(
        pattern_key=str(match_data.get("pattern_key", "")),
        count=int(_safe_float(match_data.get("count"), 0.0)),
        win_rate=match_data.get("win_rate"),
        avg_r=match_data.get("avg_r"),
        entry_offset_in_box=match_data.get("entry_offset_in_box"),
    )
    return _llm_learning_layer(
        agent_board,
        scan or {},
        match,
        cfg,
        decision=str(brain_decision.get("decision", "WAIT")),
        candidate=brain_decision.get("candidate"),
        economic_gate=brain_decision.get("economic_gate"),
    )


def apply_economic_gate_to_brain_decision(brain_decision: dict[str, Any], value_result: dict[str, Any] | None) -> dict[str, Any]:
    result = dict(brain_decision)
    gate = value_result or {}
    result["economic_gate"] = gate
    ceo = dict(result.get("ceo") or {})
    if not gate:
        return result
    if gate.get("trade_allowed"):
        ceo["message"] = f"APPROVED: Brain-Kandidat besteht Economic Gate. RR {round(_safe_float(gate.get('rr'), 0.0), 3)}."
        ceo["blocking"] = False
    else:
        result["decision"] = "BLOCKED"
        ceo["signal"] = "NEUTRAL"
        ceo["score"] = 0
        ceo["message"] = f"BLOCKED: Economic Gate sperrt Setup ({gate.get('reason')})."
        ceo["blocking"] = True
    result["ceo"] = ceo
    return result
