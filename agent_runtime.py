from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


AgentSignal = Literal["LONG", "SHORT", "NEUTRAL"]
AgentDecision = Literal["LONG_BIAS", "SHORT_BIAS", "WAIT", "BLOCKED"]


# ==================================================
# agent_runtime.py
# ==================================================
# AGENT BOARD RUNTIME
# ==================================================


@dataclass(frozen=True)
class AgentReport:
    agent_name: str
    function: str
    signal: AgentSignal
    score: int
    reads: str
    message: str
    conflict: bool = False
    blocking: bool = False
    role: str = "signal"
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AgentBoard:
    symbol: str
    timeframe_seconds: int
    reports: list[AgentReport]
    ceo: AgentReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe_seconds": self.timeframe_seconds,
            "reports": [report.to_dict() for report in self.reports],
            "ceo": self.ceo.to_dict(),
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


def _last(candles: list[Any]) -> Any | None:
    return candles[-1] if candles else None


def _close(candles: list[Any]) -> float | None:
    candle = _last(candles)
    return _value(candle, "close") if candle is not None else None


def _last_series_value(line: dict[str, Any]) -> float | None:
    series = line.get("series") or []
    if not series:
        return None
    value = series[-1].get("value")
    return float(value) if value is not None else None


def _previous_series_value(line: dict[str, Any]) -> float | None:
    series = line.get("series") or []
    if len(series) < 2:
        return None
    value = series[-2].get("value")
    return float(value) if value is not None else None


def _score_from_distance(current: float, low: float, high: float) -> int:
    if low <= current <= high:
        return 75
    width = max(abs(high - low), current * 0.0001, 1e-12)
    distance = min(abs(current - low), abs(current - high))
    return max(35, min(68, int(68 - (distance / width) * 16)))


def _line_map(indicator: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(line.get("name")): line for line in indicator.get("lines", []) if isinstance(line, dict)}


# --------------------------------------------------
# AGENT ROLES
# --------------------------------------------------
def _agent_role(agent_name: str) -> str:
    text = agent_name.lower()
    if "risk" in text or "volatility" in text or "vola" in text:
        return "risk"
    if "bos" in text or "choch" in text or "box" in text or "support" in text or "resistance" in text or "swing" in text or "hh" in text or "breakout" in text or "fakeout" in text:
        return "structure"
    if "hma" in text or "sma" in text or "triple" in text or "macd" in text or "mfi" in text or "volume" in text or "rsi" in text or "vwap" in text:
        return "momentum"
    if "ceo" in text:
        return "decision"
    return "signal"


def _agent_quality_profile(report: AgentReport) -> dict[str, Any]:
    reads = str(report.reads or "").lower()
    message = str(report.message or "").lower()
    offline = "_enabled=false" in reads or "indicator_show_" in reads or "deaktiviert" in message or "ausgeschaltet" in message
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
    reliability = max(0, min(100, int(reliability)))
    if report.blocking:
        quality = "BLOCK"
        usable = False
    elif offline:
        quality = "OFFLINE"
        usable = False
    elif reliability >= 72 and report.signal in ("LONG", "SHORT"):
        quality = "STRONG"
        usable = True
    elif reliability >= 55:
        quality = "OK"
        usable = True
    else:
        quality = "WEAK"
        usable = report.signal in ("LONG", "SHORT") and reliability >= 40
    return {
        "quality": quality,
        "data_quality": "offline" if offline else "ok",
        "signal_strength": "strong" if score >= 72 else "medium" if score >= 50 else "weak",
        "reliability_score": reliability,
        "usable_for_bias": usable,
        "role": _agent_role(report.agent_name),
        "conflict": bool(report.conflict),
        "blocking": bool(report.blocking),
    }


def _with_quality_profile(report: AgentReport) -> AgentReport:
    details = dict(report.details or {})
    details["quality_profile"] = _agent_quality_profile(report)
    return AgentReport(
        agent_name=report.agent_name,
        function=report.function,
        signal=report.signal,
        score=report.score,
        reads=report.reads,
        message=report.message,
        conflict=report.conflict,
        blocking=report.blocking,
        role=_agent_role(report.agent_name),
        details=details,
    )


def _quality_weight(report: AgentReport) -> float:
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


def _role_signal_summary(reports: list[AgentReport]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for role in ("structure", "momentum", "risk", "signal", "other"):
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
        bucket = result.setdefault(role, {
            "role": role, "long_count": 0, "short_count": 0, "neutral_count": 0,
            "long_score": 0.0, "short_score": 0.0, "score_sum": 0.0, "quality_score_sum": 0.0,
            "active_count": 0, "usable_count": 0, "weak_count": 0, "offline_count": 0,
            "blocking_count": 0, "conflict": False, "consensus": "NEUTRAL", "strength": 0,
            "quality_strength": 0, "agents": [],
        })
        signal = report.signal
        score = max(0, min(100, int(report.score)))
        profile = _agent_quality_profile(report)
        quality = str(profile.get("quality", "WEAK")).upper()
        quality_weight = _quality_weight(report)
        adjusted_score = round(score * quality_weight, 3)
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


def _with_agent_role(report: AgentReport) -> AgentReport:
    if report.role != "signal" or report.details is not None:
        return report
    return AgentReport(
        agent_name=report.agent_name,
        function=report.function,
        signal=report.signal,
        score=report.score,
        reads=report.reads,
        message=report.message,
        conflict=report.conflict,
        blocking=report.blocking,
        role=_agent_role(report.agent_name),
        details=report.details,
    )


# --------------------------------------------------
# AGENT SETTINGS
# --------------------------------------------------
def _agent_setting_key(agent_name: str) -> str:
    text = agent_name.lower()
    if "bos" in text or "choch" in text:
        return "agent_bos_choch"
    if "box" in text:
        return "agent_box"
    if "support" in text or "resistance" in text or text.startswith("sr "):
        return "agent_support_resistance"
    if "hh" in text or "swing" in text:
        return "agent_swing_labels"
    if "hma" in text:
        return "agent_hma"
    if "sma" in text:
        return "agent_sma"
    if "triple" in text:
        return "agent_triple_ema"
    if "macd" in text:
        return "agent_macd"
    if "mfi" in text:
        return "agent_mfi"
    if "rsi" in text:
        return "agent_rsi"
    if "vwap" in text:
        return "agent_vwap"
    if "breakout" in text or "fakeout" in text:
        return "agent_breakout_fakeout"
    if "volatility" in text or "vola" in text:
        return "agent_volatility_regime"
    if "volume" in text:
        return "agent_volume"
    if "risk" in text:
        return "agent_risk"
    return "agent_unknown"


def _linked_indicator_off(key: str, cfg: dict[str, Any]) -> str | None:
    links = {
        "agent_bos_choch": "indicator_show_bos_choch",
        "agent_box": "indicator_show_boxes",
        "agent_support_resistance": "indicator_show_support_resistance",
        "agent_swing_labels": "indicator_show_swing_labels",
        "agent_hma": "indicator_show_hma",
        "agent_sma": "indicator_show_sma",
        "agent_triple_ema": "indicator_show_triple_ema",
        "agent_macd": "indicator_show_macd",
        "agent_mfi": "indicator_show_mfi",
    }
    indicator_key = links.get(key)
    if indicator_key and not bool(cfg.get(indicator_key, False)):
        return indicator_key
    return None


def _apply_agent_settings(report: AgentReport, cfg: dict[str, Any]) -> AgentReport:
    key = _agent_setting_key(report.agent_name)
    enabled = bool(cfg.get(f"{key}_enabled", True))
    if not enabled:
        return AgentReport(
            agent_name=report.agent_name,
            function=report.function,
            signal="NEUTRAL",
            score=0,
            reads=f"{key}_enabled=false",
            message="Agent ist im Agent Settings Fenster deaktiviert.",
            conflict=False,
            blocking=False,
            role=_agent_role(report.agent_name),
            details=report.details,
        )

    linked_off = _linked_indicator_off(key, cfg)
    if linked_off:
        return AgentReport(
            agent_name=report.agent_name,
            function=report.function,
            signal="NEUTRAL",
            score=0,
            reads=f"{linked_off}=false",
            message="Gekoppelter Indikator ist ausgeschaltet; Agent liest keine Daten.",
            conflict=False,
            blocking=bool(cfg.get(f"{key}_blocking", False)),
            role=_agent_role(report.agent_name),
            details=report.details,
        )

    weight = max(0.0, min(5.0, float(cfg.get(f"{key}_weight", 1.0))))
    min_score = max(0, min(100, int(cfg.get(f"{key}_min_score", 0))))
    score = max(0, min(100, int(round(report.score * weight))))
    signal = report.signal
    message = report.message
    blocking = bool(report.blocking)
    if signal != "NEUTRAL" and score < min_score:
        message = f"{message} Mindestscore {min_score} nicht erreicht."
        signal = "NEUTRAL"
        blocking = bool(cfg.get(f"{key}_blocking", False))
    return AgentReport(
        agent_name=report.agent_name,
        function=report.function,
        signal=signal,
        score=score,
        reads=f"{report.reads} | weight {weight} | min {min_score}",
        message=message,
        conflict=report.conflict,
        blocking=blocking,
        role=_agent_role(report.agent_name),
        details=report.details,
    )


# --------------------------------------------------
# AGENTS
# --------------------------------------------------
def _bos_choch_agent(indicator: dict[str, Any]) -> AgentReport:
    lines = indicator.get("break_lines") or []
    if not lines:
        return AgentReport(
            agent_name="BOS / CHoCH Agent",
            function="Strukturbruch lesen",
            signal="NEUTRAL",
            score=45,
            reads="break_lines: 0",
            message="Kein aktiver BOS / CHoCH im aktuellen Lookback.",
        )
    last_line = lines[-1]
    direction = str(last_line.get("direction", ""))
    text = str(last_line.get("text", "BOS"))
    price = last_line.get("price")
    signal: AgentSignal = "LONG" if direction == "rising" else "SHORT" if direction == "falling" else "NEUTRAL"
    return AgentReport(
        agent_name="BOS / CHoCH Agent",
        function="BOS / CHoCH Richtung bewerten",
        signal=signal,
        score=72 if text == "BOS" else 68,
        reads=f"letzter {text} @ {price}",
        message=f"{text} Richtung {direction}; Struktur gibt {signal}-Bias.",
    )


def _box_agent(candles: list[Any], indicator: dict[str, Any]) -> AgentReport:
    current = _close(candles)
    boxes = indicator.get("boxes") or []
    if current is None or not boxes:
        return AgentReport(
            agent_name="LL / HH Box Agent",
            function="Preisposition in Strukturboxen prüfen",
            signal="NEUTRAL",
            score=45,
            reads=f"boxes: {len(boxes)}",
            message="Keine aktive LL / HH Box vorhanden.",
        )
    candidates = []
    for box in boxes:
        top = float(box.get("top", 0.0))
        bottom = float(box.get("bottom", 0.0))
        high = max(top, bottom)
        low = min(top, bottom)
        candidates.append((_score_from_distance(current, low, high), box, low, high))
    score, box, low, high = max(candidates, key=lambda item: item[0])
    direction = str(box.get("direction", ""))
    signal: AgentSignal = "LONG" if direction == "rising" else "SHORT" if direction == "falling" else "NEUTRAL"
    in_box = low <= current <= high
    return AgentReport(
        agent_name="LL / HH Box Agent",
        function="LL / HH Box Reaktion kontrollieren",
        signal=signal if in_box or score >= 60 else "NEUTRAL",
        score=score,
        reads=f"close {round(current, 8)} | box {round(low, 8)} - {round(high, 8)}",
        message=("Preis liegt in der Box." if in_box else "Preis ist nahe an der letzten Box.") + f" Box-Richtung {direction}.",
    )



def _support_resistance_agent(candles: list[Any], indicator: dict[str, Any]) -> AgentReport:
    current = _close(candles)
    levels = indicator.get("support_resistance") or []
    if current is None or not levels:
        return AgentReport(
            agent_name="Support / Resistance Agent",
            function="Dynamische Support-/Resistance-Level lesen",
            signal="NEUTRAL",
            score=45,
            reads=f"levels: {len(levels)}",
            message="Keine dynamischen Support-/Resistance-Level vorhanden.",
        )

    parsed: list[dict[str, Any]] = []
    for level in levels:
        try:
            parsed.append(
                {
                    "price": float(level.get("price", 0.0)),
                    "upper": float(level.get("upper", level.get("price", 0.0))),
                    "lower": float(level.get("lower", level.get("price", 0.0))),
                    "strength": int(level.get("strength", 0)),
                    "kind": str(level.get("kind", "")),
                    "crossed": str(level.get("crossed", "none")),
                }
            )
        except (TypeError, ValueError):
            continue
    if not parsed:
        return AgentReport(
            agent_name="Support / Resistance Agent",
            function="Dynamische Support-/Resistance-Level lesen",
            signal="NEUTRAL",
            score=45,
            reads="levels: 0",
            message="Support-/Resistance-Level sind ungueltig.",
        )

    broken_up = [level for level in parsed if level["crossed"] == "over"]
    if broken_up:
        level = max(broken_up, key=lambda item: (item["strength"], -abs(item["price"] - current)))
        return AgentReport(
            agent_name="Support / Resistance Agent",
            function="Dynamische Support-/Resistance-Level lesen",
            signal="LONG",
            score=min(82, 68 + int(level["strength"] * 3)),
            reads=f"break over {round(level['price'], 8)} | strength {level['strength']}",
            message="Preis bricht ueber Resistance-Level.",
        )

    broken_down = [level for level in parsed if level["crossed"] == "under"]
    if broken_down:
        level = max(broken_down, key=lambda item: (item["strength"], -abs(item["price"] - current)))
        return AgentReport(
            agent_name="Support / Resistance Agent",
            function="Dynamische Support-/Resistance-Level lesen",
            signal="SHORT",
            score=min(82, 68 + int(level["strength"] * 3)),
            reads=f"break under {round(level['price'], 8)} | strength {level['strength']}",
            message="Preis bricht unter Support-Level.",
        )

    nearest = min(parsed, key=lambda item: abs(item["price"] - current))
    distance_fraction = abs(current - nearest["price"]) / max(abs(current), 1e-12)
    near_threshold = 0.004
    if distance_fraction > near_threshold:
        return AgentReport(
            agent_name="Support / Resistance Agent",
            function="Dynamische Support-/Resistance-Level lesen",
            signal="NEUTRAL",
            score=52,
            reads=f"nearest {nearest['kind']} {round(nearest['price'], 8)} | strength {nearest['strength']}",
            message="Naechstes Support-/Resistance-Level ist aktuell nicht nah genug.",
        )

    if nearest["kind"] == "support" and current >= nearest["price"]:
        signal: AgentSignal = "LONG"
        message = "Preis reagiert ueber nahem Support-Level."
    elif nearest["kind"] == "resistance" and current <= nearest["price"]:
        signal = "SHORT"
        message = "Preis reagiert unter nahem Resistance-Level."
    else:
        signal = "NEUTRAL"
        message = "Preis befindet sich uneindeutig relativ zum naechsten Level."
    score = 54 if signal == "NEUTRAL" else max(58, min(78, 72 - int(distance_fraction * 10000) + int(nearest["strength"] * 2)))
    return AgentReport(
        agent_name="Support / Resistance Agent",
        function="Dynamische Support-/Resistance-Level lesen",
        signal=signal,
        score=score,
        reads=f"nearest {nearest['kind']} {round(nearest['price'], 8)} | strength {nearest['strength']}",
        message=message,
    )

def _swing_agent(indicator: dict[str, Any]) -> AgentReport:
    labels = indicator.get("labels") or []
    if not labels:
        return AgentReport(
            agent_name="HH / LH / HL / LL Agent",
            function="Swing Labels lesen",
            signal="NEUTRAL",
            score=45,
            reads="labels: 0",
            message="Keine Swing Labels im aktuellen Lookback.",
        )
    last_label = labels[-1]
    text = str(last_label.get("text", ""))
    direction = str(last_label.get("direction", ""))
    signal: AgentSignal = "LONG" if text in ("HH", "HL") else "SHORT" if text in ("LH", "LL") else "NEUTRAL"
    return AgentReport(
        agent_name="HH / LH / HL / LL Agent",
        function="Marktstrukturfolge bewerten",
        signal=signal,
        score=66 if text in ("HH", "LL") else 58,
        reads=f"letztes Label {text} @ {last_label.get('price')}",
        message=f"Letztes Swing Label {text}; Struktur-Richtung {direction}.",
    )


def _hma_agent(candles: list[Any], indicator: dict[str, Any]) -> AgentReport:
    current = _close(candles)
    line = _line_map(indicator).get("HMA")
    if current is None or not line:
        return AgentReport(
            agent_name="HMA Agent",
            function="HMA Trendneigung kontrollieren",
            signal="NEUTRAL",
            score=45,
            reads="HMA Linie nicht aktiv",
            message="HMA ist aus oder hat nicht genug Werte.",
        )
    last_value = _last_series_value(line)
    previous_value = _previous_series_value(line)
    if last_value is None or previous_value is None:
        return AgentReport(
            agent_name="HMA Agent",
            function="HMA Trendneigung kontrollieren",
            signal="NEUTRAL",
            score=45,
            reads="HMA Warmup",
            message="HMA hat noch keinen stabilen letzten Wert.",
        )
    rising = last_value > previous_value
    above = current > last_value
    signal: AgentSignal = "LONG" if rising and above else "SHORT" if (not rising and not above) else "NEUTRAL"
    score = 70 if signal != "NEUTRAL" else 52
    return AgentReport(
        agent_name="HMA Agent",
        function="Momentum ueber HMA lesen",
        signal=signal,
        score=score,
        reads=f"close {round(current, 8)} | HMA {round(last_value, 8)} | prev {round(previous_value, 8)}",
        message=f"HMA {'steigt' if rising else 'faellt'}; Preis ist {'ueber' if above else 'unter'} HMA.",
    )


def _triple_ema_agent(indicator: dict[str, Any]) -> AgentReport:
    lines = _line_map(indicator)
    fast = lines.get("TRIPLE_EMA_FAST")
    slow = lines.get("TRIPLE_EMA_SLOW")
    if not fast or not slow:
        return AgentReport(
            agent_name="Triple EMA Agent",
            function="Fast / Slow Triple EMA vergleichen",
            signal="NEUTRAL",
            score=45,
            reads="Triple EMA Linien nicht aktiv",
            message="Triple EMA ist aus oder hat nicht genug Werte.",
        )
    fast_value = _last_series_value(fast)
    slow_value = _last_series_value(slow)
    if fast_value is None or slow_value is None:
        return AgentReport(
            agent_name="Triple EMA Agent",
            function="Fast / Slow Triple EMA vergleichen",
            signal="NEUTRAL",
            score=45,
            reads="Triple EMA Warmup",
            message="Fast / Slow Triple EMA liefern noch keine stabilen Werte.",
        )
    diff = fast_value - slow_value
    signal: AgentSignal = "LONG" if diff > 0 else "SHORT" if diff < 0 else "NEUTRAL"
    score = min(76, 55 + int(abs(diff) / max(abs(slow_value), 1e-12) * 10000))
    return AgentReport(
        agent_name="Triple EMA Agent",
        function="Trendfilter Fast gegen Slow",
        signal=signal,
        score=score,
        reads=f"fast {round(fast_value, 8)} | slow {round(slow_value, 8)}",
        message=f"Fast Triple EMA liegt {'ueber' if diff > 0 else 'unter' if diff < 0 else 'gleich'} Slow Triple EMA.",
    )


def _macd_agent(indicator: dict[str, Any]) -> AgentReport:
    lines = _line_map(indicator)
    macd = lines.get("MACD")
    signal_line = lines.get("MACD_SIGNAL")
    histogram = lines.get("MACD_HISTOGRAM")
    if not macd or not signal_line or not histogram:
        return AgentReport(
            agent_name="MACD Agent",
            function="MACD Linie, Signal und Histogramm vergleichen",
            signal="NEUTRAL",
            score=45,
            reads="MACD Linien nicht aktiv",
            message="MACD ist aus oder hat nicht genug Werte.",
        )

    macd_value = _last_series_value(macd)
    signal_value = _last_series_value(signal_line)
    histogram_value = _last_series_value(histogram)
    previous_macd = _previous_series_value(macd)
    previous_signal = _previous_series_value(signal_line)
    previous_histogram = _previous_series_value(histogram)
    if macd_value is None or signal_value is None or histogram_value is None or previous_macd is None or previous_signal is None:
        return AgentReport(
            agent_name="MACD Agent",
            function="MACD Linie, Signal und Histogramm vergleichen",
            signal="NEUTRAL",
            score=45,
            reads="MACD Warmup",
            message="MACD liefert noch keine stabilen Vergleichswerte.",
        )

    bullish_cross = previous_macd <= previous_signal and macd_value > signal_value
    bearish_cross = previous_macd >= previous_signal and macd_value < signal_value
    histogram_rising = previous_histogram is not None and histogram_value > previous_histogram
    histogram_falling = previous_histogram is not None and histogram_value < previous_histogram

    if bullish_cross:
        signal: AgentSignal = "LONG"
        score = 78
        message = "MACD kreuzt ueber die Signallinie."
    elif bearish_cross:
        signal = "SHORT"
        score = 78
        message = "MACD kreuzt unter die Signallinie."
    elif macd_value > signal_value and histogram_value > 0:
        signal = "LONG"
        score = 70 if histogram_rising else 64
        message = "MACD liegt ueber der Signallinie; Histogramm ist positiv."
    elif macd_value < signal_value and histogram_value < 0:
        signal = "SHORT"
        score = 70 if histogram_falling else 64
        message = "MACD liegt unter der Signallinie; Histogramm ist negativ."
    else:
        signal = "NEUTRAL"
        score = 52
        message = "MACD liefert keine klare Richtungsbestaetigung."

    return AgentReport(
        agent_name="MACD Agent",
        function="Momentumwechsel ueber MACD lesen",
        signal=signal,
        score=score,
        reads=f"MACD {round(macd_value, 8)} | Signal {round(signal_value, 8)} | Hist {round(histogram_value, 8)}",
        message=message,
    )


def _sma_agent(candles: list[Any], period: int = 50) -> AgentReport:
    safe_period = max(2, int(period))
    if len(candles) < safe_period + 1:
        return AgentReport(
            agent_name="SMA Agent",
            function="Preisposition und SMA-Neigung kontrollieren",
            signal="NEUTRAL",
            score=45,
            reads=f"candles {len(candles)} | period {safe_period}",
            message="SMA hat noch nicht genug Kerzen.",
        )
    closes = [_value(candle, "close") for candle in candles]
    current = closes[-1]
    sma = sum(closes[-safe_period:]) / safe_period
    previous_sma = sum(closes[-safe_period - 1:-1]) / safe_period
    rising = sma > previous_sma
    above = current > sma
    signal: AgentSignal = "LONG" if rising and above else "SHORT" if (not rising and not above) else "NEUTRAL"
    distance_fraction = abs(current - sma) / max(abs(sma), 1e-12)
    score = 52 if signal == "NEUTRAL" else max(58, min(78, 58 + int(distance_fraction * 10000)))
    return AgentReport(
        agent_name="SMA Agent",
        function="Trendfilter ueber SMA lesen",
        signal=signal,
        score=score,
        reads=f"close {round(current, 8)} | SMA{safe_period} {round(sma, 8)} | prev {round(previous_sma, 8)}",
        message=f"SMA {'steigt' if rising else 'faellt'}; Preis ist {'ueber' if above else 'unter'} SMA.",
    )


def _mfi_agent(candles: list[Any], period: int = 14) -> AgentReport:
    safe_period = max(2, int(period))
    if len(candles) < safe_period + 1:
        return AgentReport(
            agent_name="MFI Agent",
            function="Money Flow Index kontrollieren",
            signal="NEUTRAL",
            score=45,
            reads=f"candles {len(candles)} | period {safe_period}",
            message="MFI hat noch nicht genug Kerzen.",
        )
    window = candles[-safe_period - 1:]
    positive_flow = 0.0
    negative_flow = 0.0
    previous_typical = (_value(window[0], "high") + _value(window[0], "low") + _value(window[0], "close")) / 3.0
    for candle in window[1:]:
        typical = (_value(candle, "high") + _value(candle, "low") + _value(candle, "close")) / 3.0
        raw_flow = typical * max(0.0, _value(candle, "volume"))
        if typical > previous_typical:
            positive_flow += raw_flow
        elif typical < previous_typical:
            negative_flow += raw_flow
        previous_typical = typical
    if positive_flow <= 0 and negative_flow <= 0:
        mfi = 50.0
    elif negative_flow <= 0:
        mfi = 100.0
    else:
        money_ratio = positive_flow / negative_flow
        mfi = 100.0 - (100.0 / (1.0 + money_ratio))
    signal: AgentSignal = "LONG" if mfi >= 55.0 else "SHORT" if mfi <= 45.0 else "NEUTRAL"
    score = 50 if signal == "NEUTRAL" else max(56, min(78, 50 + int(abs(mfi - 50.0) * 1.1)))
    return AgentReport(
        agent_name="MFI Agent",
        function="Kapitalfluss ueber MFI lesen",
        signal=signal,
        score=score,
        reads=f"MFI{safe_period} {round(mfi, 2)} | positive {round(positive_flow, 4)} | negative {round(negative_flow, 4)}",
        message=("MFI zeigt positiven Kapitalfluss." if signal == "LONG" else "MFI zeigt negativen Kapitalfluss." if signal == "SHORT" else "MFI ist neutral."),
    )



def _true_range(current: Any, previous_close: float | None) -> float:
    high = _value(current, "high")
    low = _value(current, "low")
    if previous_close is None:
        return max(high - low, 0.0)
    return max(high - low, abs(high - previous_close), abs(low - previous_close), 0.0)


def _atr_values(candles: list[Any], period: int) -> list[float]:
    safe_period = max(2, int(period))
    if len(candles) < safe_period + 1:
        return []
    ranges: list[float] = []
    previous_close: float | None = None
    for candle in candles:
        ranges.append(_true_range(candle, previous_close))
        previous_close = _value(candle, "close")
    atrs: list[float] = []
    for index in range(safe_period, len(ranges) + 1):
        atrs.append(sum(ranges[index - safe_period:index]) / safe_period)
    return atrs


def _rsi_agent(candles: list[Any], period: int = 14) -> AgentReport:
    safe_period = max(2, int(period))
    if len(candles) < safe_period + 1:
        return AgentReport(
            agent_name="RSI Agent",
            function="RSI Momentum und Ueberdehnung kontrollieren",
            signal="NEUTRAL",
            score=45,
            reads=f"candles {len(candles)} | period {safe_period}",
            message="RSI hat noch nicht genug Kerzen.",
        )
    closes = [_value(candle, "close") for candle in candles[-safe_period - 1:]]
    gains = 0.0
    losses = 0.0
    for previous, current in zip(closes, closes[1:]):
        change = current - previous
        if change > 0:
            gains += change
        elif change < 0:
            losses += abs(change)
    avg_gain = gains / safe_period
    avg_loss = losses / safe_period
    if avg_loss <= 0 and avg_gain <= 0:
        rsi = 50.0
    elif avg_loss <= 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100.0 - (100.0 / (1.0 + rs))
    if rsi >= 55.0:
        signal: AgentSignal = "LONG"
    elif rsi <= 45.0:
        signal = "SHORT"
    else:
        signal = "NEUTRAL"
    overextended = rsi >= 75.0 or rsi <= 25.0
    base_score = 50 if signal == "NEUTRAL" else 54 + int(abs(rsi - 50.0) * 1.1)
    score = max(35, min(82, base_score))
    if overextended and signal != "NEUTRAL":
        score = min(score, 66)
    return AgentReport(
        agent_name="RSI Agent",
        function="RSI Momentum und Ueberdehnung kontrollieren",
        signal=signal,
        score=score,
        reads=f"RSI{safe_period} {round(rsi, 2)} | gain {round(avg_gain, 8)} | loss {round(avg_loss, 8)}",
        message=("RSI bestaetigt LONG-Momentum." if signal == "LONG" else "RSI bestaetigt SHORT-Momentum." if signal == "SHORT" else "RSI liegt in der neutralen Zone.") + (" Achtung: RSI ist ueberdehnt." if overextended else ""),
        details={"rsi": round(rsi, 3), "period": safe_period, "overextended": overextended},
    )


def _vwap_agent(candles: list[Any], lookback: int = 96) -> AgentReport:
    if len(candles) < 3:
        return AgentReport(
            agent_name="VWAP Agent",
            function="Preis relativ zum VWAP-Fair-Value lesen",
            signal="NEUTRAL",
            score=45,
            reads="zu wenig Kerzen",
            message="VWAP kann noch nicht bewertet werden.",
        )
    safe_lookback = max(5, min(int(lookback), len(candles)))
    window = candles[-safe_lookback:]
    previous_window = candles[-safe_lookback - 1:-1] if len(candles) > safe_lookback else window[:-1]

    def calc_vwap(items: list[Any]) -> float | None:
        volume_sum = sum(max(0.0, _value(candle, "volume")) for candle in items)
        if volume_sum <= 0:
            return None
        typical_sum = 0.0
        for candle in items:
            typical = (_value(candle, "high") + _value(candle, "low") + _value(candle, "close")) / 3.0
            typical_sum += typical * max(0.0, _value(candle, "volume"))
        return typical_sum / volume_sum

    vwap = calc_vwap(window)
    previous_vwap = calc_vwap(previous_window)
    if vwap is None or previous_vwap is None:
        return AgentReport(
            agent_name="VWAP Agent",
            function="Preis relativ zum VWAP-Fair-Value lesen",
            signal="NEUTRAL",
            score=45,
            reads="volume leer",
            message="VWAP hat keine verwertbaren Volumendaten.",
        )
    close = _value(candles[-1], "close")
    above = close > vwap
    rising = vwap >= previous_vwap
    if above and rising:
        signal: AgentSignal = "LONG"
    elif (not above) and (not rising):
        signal = "SHORT"
    else:
        signal = "NEUTRAL"
    distance_fraction = abs(close - vwap) / max(abs(vwap), 1e-12)
    score = 50 if signal == "NEUTRAL" else max(56, min(80, 56 + int(distance_fraction * 10000)))
    return AgentReport(
        agent_name="VWAP Agent",
        function="Preis relativ zum VWAP-Fair-Value lesen",
        signal=signal,
        score=score,
        reads=f"close {round(close, 8)} | VWAP{safe_lookback} {round(vwap, 8)} | prev {round(previous_vwap, 8)}",
        message=("Preis haelt ueber steigendem VWAP." if signal == "LONG" else "Preis liegt unter fallendem VWAP." if signal == "SHORT" else "VWAP liefert keine klare Richtungsfreigabe."),
        details={"vwap": round(vwap, 8), "previous_vwap": round(previous_vwap, 8), "lookback": safe_lookback, "distance_fraction": round(distance_fraction, 6)},
    )


def _breakout_fakeout_agent(candles: list[Any], lookback: int = 20) -> AgentReport:
    safe_lookback = max(3, int(lookback))
    if len(candles) < safe_lookback + 1:
        return AgentReport(
            agent_name="Breakout / Fakeout Agent",
            function="Breakout oder Fakeout an lokaler Range erkennen",
            signal="NEUTRAL",
            score=45,
            reads=f"candles {len(candles)} | lookback {safe_lookback}",
            message="Breakout/Fakeout Agent hat noch nicht genug Kerzen.",
        )
    current = candles[-1]
    history = candles[-safe_lookback - 1:-1]
    range_high = max(_value(candle, "high") for candle in history)
    range_low = min(_value(candle, "low") for candle in history)
    close = _value(current, "close")
    high = _value(current, "high")
    low = _value(current, "low")
    body = abs(close - _value(current, "open"))
    candle_range = max(_value(current, "high") - _value(current, "low"), 1e-12)
    body_fraction = body / candle_range
    if close > range_high:
        signal: AgentSignal = "LONG"
        mode = "breakout_up"
        score = 72 if body_fraction >= 0.45 else 64
        message = "Kerzenschluss bricht ueber die lokale Range."
    elif close < range_low:
        signal = "SHORT"
        mode = "breakout_down"
        score = 72 if body_fraction >= 0.45 else 64
        message = "Kerzenschluss bricht unter die lokale Range."
    elif high > range_high and close <= range_high:
        signal = "SHORT"
        mode = "fakeout_up"
        score = 74
        message = "Oberer Range-Ausbruch wurde zurueckgewiesen."
    elif low < range_low and close >= range_low:
        signal = "LONG"
        mode = "fakeout_down"
        score = 74
        message = "Unterer Range-Ausbruch wurde zurueckgewiesen."
    else:
        signal = "NEUTRAL"
        mode = "inside_range"
        score = 50
        message = "Preis bleibt innerhalb der lokalen Range."
    return AgentReport(
        agent_name="Breakout / Fakeout Agent",
        function="Breakout oder Fakeout an lokaler Range erkennen",
        signal=signal,
        score=score,
        reads=f"lookback {safe_lookback} | high {round(range_high, 8)} | low {round(range_low, 8)} | close {round(close, 8)}",
        message=message,
        details={"mode": mode, "range_high": round(range_high, 8), "range_low": round(range_low, 8), "body_fraction": round(body_fraction, 4)},
    )


def _volatility_regime_agent(candles: list[Any], period: int = 14, lookback: int = 50) -> AgentReport:
    safe_period = max(2, int(period))
    safe_lookback = max(safe_period + 2, int(lookback))
    if len(candles) < safe_period + safe_lookback:
        return AgentReport(
            agent_name="Volatility Regime Agent",
            function="ATR-Volatilität und Risiko-Regime kontrollieren",
            signal="NEUTRAL",
            score=45,
            reads=f"candles {len(candles)} | ATR {safe_period} | lookback {safe_lookback}",
            message="Volatility Regime Agent hat noch nicht genug Kerzen.",
        )
    atrs = _atr_values(candles, safe_period)
    if len(atrs) < 2:
        return AgentReport(
            agent_name="Volatility Regime Agent",
            function="ATR-Volatilität und Risiko-Regime kontrollieren",
            signal="NEUTRAL",
            score=45,
            reads="ATR leer",
            message="ATR-Regime kann nicht bewertet werden.",
        )
    current_atr = atrs[-1]
    history = atrs[-safe_lookback:-1] if len(atrs) > safe_lookback else atrs[:-1]
    average_atr = sum(history) / max(1, len(history))
    ratio = current_atr / average_atr if average_atr > 0 else 1.0
    if ratio >= 1.85:
        regime = "extrem"
        score = 38
        blocking = False
        message = "Volatilität ist extrem hoch; Risiko-Regime markiert starke Vorsicht."
    elif ratio >= 1.35:
        regime = "hoch"
        score = 48
        blocking = False
        message = "Volatilität ist erhöht; Entries brauchen bessere Bestätigung."
    elif ratio <= 0.65:
        regime = "ruhig"
        score = 55
        blocking = False
        message = "Volatilität ist niedrig; Breakouts können schwach sein."
    else:
        regime = "normal"
        score = 68
        blocking = False
        message = "Volatilität liegt im normalen Arbeitsbereich."
    return AgentReport(
        agent_name="Volatility Regime Agent",
        function="ATR-Volatilität und Risiko-Regime kontrollieren",
        signal="NEUTRAL",
        score=score,
        reads=f"ATR{safe_period} {round(current_atr, 8)} | avg {round(average_atr, 8)} | ratio {round(ratio, 2)}x | regime {regime}",
        message=message,
        blocking=blocking,
        role="risk",
        details={"atr": round(current_atr, 8), "average_atr": round(average_atr, 8), "ratio": round(ratio, 4), "regime": regime},
    )


def _volume_agent(candles: list[Any], period: int = 20) -> AgentReport:
    if len(candles) < 2:
        return AgentReport(
            agent_name="Volume Agent",
            function="Volumen-Kontext prüfen",
            signal="NEUTRAL",
            score=45,
            reads="zu wenig Kerzen",
            message="Volumen kann noch nicht bewertet werden.",
        )
    current = candles[-1]
    window = candles[-min(max(2, period), len(candles)) - 1:-1]
    volumes = [_value(candle, "volume") for candle in window if _value(candle, "volume") >= 0]
    if not volumes:
        return AgentReport(
            agent_name="Volume Agent",
            function="Volumen-Kontext prüfen",
            signal="NEUTRAL",
            score=45,
            reads="volume leer",
            message="Keine Volumendaten vorhanden.",
        )
    current_volume = _value(current, "volume")
    average_volume = sum(volumes) / len(volumes)
    ratio = current_volume / average_volume if average_volume > 0 else 0.0
    bullish = _value(current, "close") > _value(current, "open")
    bearish = _value(current, "close") < _value(current, "open")
    if ratio >= 1.2 and bullish:
        signal: AgentSignal = "LONG"
    elif ratio >= 1.2 and bearish:
        signal = "SHORT"
    else:
        signal = "NEUTRAL"
    score = max(35, min(78, int(42 + ratio * 18)))
    return AgentReport(
        agent_name="Volume Agent",
        function="Volumenbestaetigung lesen",
        signal=signal,
        score=score,
        reads=f"volume {round(current_volume, 4)} | avg {round(average_volume, 4)} | ratio {round(ratio, 2)}x",
        message=("Volumen bestaetigt die aktuelle Kerzenrichtung." if signal != "NEUTRAL" else "Volumen liefert keine klare Richtungsbestaetigung."),
    )


def _risk_agent(scan: dict[str, Any], risk_context: dict[str, Any] | None = None) -> AgentReport:
    context = risk_context or {}
    pipeline = str(scan.get("pipeline", "agents_brain_ceo_gate"))
    setup_found = bool(scan.get("setup_found", False) or context.get("candidate_present", False))
    gate = context.get("economic_gate") or {}
    broker = context.get("broker") or {}
    active = context.get("active_trades") or {}

    gate_known = isinstance(gate, dict) and "trade_allowed" in gate
    gate_allowed = bool(gate.get("trade_allowed", False)) if gate_known else None
    broker_known = isinstance(broker, dict) and "allowed" in broker
    broker_allowed = bool(broker.get("allowed", False)) if broker_known else None

    rr = gate.get("rr") if isinstance(gate, dict) else None
    min_rr = context.get("min_rr")
    risk_fraction = gate.get("risk_fraction") if isinstance(gate, dict) else context.get("sl_distance_fraction")
    max_sl_fraction = context.get("max_sl_distance_fraction")
    net_profit_fraction = gate.get("net_profit_fraction") if isinstance(gate, dict) else None
    min_net_profit_fraction = gate.get("min_net_profit_fraction") if isinstance(gate, dict) else context.get("min_net_profit_fraction")

    hard_blocks: list[str] = []
    warnings: list[str] = []
    if gate_known and not gate_allowed:
        hard_blocks.append(f"Economic Gate: {gate.get('reason', 'blocked')}")
    if broker_known and not broker_allowed:
        hard_blocks.append(f"Broker/Risk Lock: {broker.get('reason', 'blocked')}")
    if risk_fraction is not None and max_sl_fraction not in (None, 0, 0.0) and float(risk_fraction) > float(max_sl_fraction):
        hard_blocks.append("SL-Distanz ueber Limit")
    if rr is not None and min_rr not in (None, 0, 0.0) and float(rr) < float(min_rr):
        hard_blocks.append("RR unter Minimum")
    if net_profit_fraction is not None and min_net_profit_fraction not in (None, 0, 0.0) and float(net_profit_fraction) < float(min_net_profit_fraction):
        hard_blocks.append("Netto-Profit unter Minimum")
    if int(active.get("same_asset", 0) or 0) > 0:
        warnings.append("Asset hat aktive Trades")
    if int(active.get("correlated_same_direction", 0) or 0) > 0:
        warnings.append("Korrelierte gleiche Richtung aktiv")

    if not setup_found:
        score = 45
        message = "Kein Trade-Kandidat; Risk Agent wartet auf Brain-Candidate."
        blocking = False
    elif hard_blocks:
        score = 15
        message = "Hard Block: " + "; ".join(hard_blocks)
        blocking = True
    elif warnings:
        score = 58
        message = "Risk Warnung: " + "; ".join(warnings)
        blocking = False
    elif gate_known and broker_known:
        score = 82
        message = "Risk Check frei: Economic Gate und Broker Locks erlauben den Paper-Trade."
        blocking = False
    elif gate_known:
        score = 72 if gate_allowed else 20
        message = "Economic Gate geprüft; Broker-Locks noch nicht final bewertet."
        blocking = not bool(gate_allowed)
    else:
        score = 50
        message = "Trade-Freigabe entsteht erst nach Brain, CEO, Economic Gate und Broker-Locks."
        blocking = False

    reads = [
        f"pipeline: {pipeline}",
        f"setup_found: {setup_found}",
        f"gate: {gate_allowed if gate_known else 'pending'}",
        f"broker: {broker_allowed if broker_known else 'pending'}",
        f"active_total: {active.get('total', 0)}",
        f"same_asset: {active.get('same_asset', 0)}",
        f"corr_same_dir: {active.get('correlated_same_direction', 0)}",
        f"rr: {round(float(rr), 4) if rr is not None else '-'}",
        f"risk_pct: {round(float(risk_fraction) * 100, 4) if risk_fraction is not None else '-'}",
        f"net_pct: {round(float(net_profit_fraction) * 100, 4) if net_profit_fraction is not None else '-'}",
    ]
    return AgentReport(
        agent_name="Risk Agent",
        function="Offene Trades, Korrelation, SL-Distanz und Value-Gate-Risiko bewerten",
        signal="NEUTRAL",
        score=max(0, min(100, int(score))),
        reads=" | ".join(reads),
        message=message,
        conflict=False,
        blocking=blocking,
        role="risk",
        details={
            "pipeline": pipeline,
            "setup_found": setup_found,
            "economic_gate": gate,
            "broker": broker,
            "active_trades": active,
            "rr": rr,
            "min_rr": min_rr,
            "risk_fraction": risk_fraction,
            "max_sl_distance_fraction": max_sl_fraction,
            "net_profit_fraction": net_profit_fraction,
            "min_net_profit_fraction": min_net_profit_fraction,
            "hard_blocks": hard_blocks,
            "warnings": warnings,
        },
    )


# --------------------------------------------------
# CEO AGENT
# --------------------------------------------------
def _ceo_agent(reports: list[AgentReport]) -> AgentReport:
    role_groups = _role_signal_summary(reports)
    blocking = any(report.blocking for report in reports)
    structure = role_groups.get("structure", {})
    momentum = role_groups.get("momentum", {})
    risk = role_groups.get("risk", {})
    other = role_groups.get("signal", {})

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
    risk_signal = str(risk.get("consensus", "NEUTRAL"))
    hard_role_conflict = structure_signal in ("LONG", "SHORT") and momentum_signal in ("LONG", "SHORT") and structure_signal != momentum_signal

    weighted_long = (float(structure.get("long_score", 0)) * 1.35) + (float(momentum.get("long_score", 0)) * 1.05) + (float(other.get("long_score", 0)) * 0.6)
    weighted_short = (float(structure.get("short_score", 0)) * 1.35) + (float(momentum.get("short_score", 0)) * 1.05) + (float(other.get("short_score", 0)) * 0.6)
    if risk_signal == "LONG":
        weighted_long += float(risk.get("long_score", 0)) * 0.45
    elif risk_signal == "SHORT":
        weighted_short += float(risk.get("short_score", 0)) * 0.45
    weighted_gap = abs(weighted_long - weighted_short)
    data_quality_penalty = min(22, weak_count * 3 + offline_count * 6)
    base_strength = int(max(weighted_long, weighted_short) / max(1, long_count if weighted_long >= weighted_short else short_count)) if (long_count + short_count) else 50
    quality_score = max(0, min(100, base_strength - data_quality_penalty))

    if blocking:
        decision: AgentDecision = "BLOCKED"
        score = 0
        reason = "Mindestens ein blockierender Agent meldet Blockade."
    elif hard_role_conflict:
        decision = "WAIT"
        score = max(0, min(100, quality_score))
        reason = f"Struktur und Momentum widersprechen sich: Struktur {structure_signal}, Momentum {momentum_signal}."
    elif usable_count < 2:
        decision = "WAIT"
        score = max(35, min(55, quality_score))
        reason = "Zu wenige qualitativ nutzbare Agentensignale für CEO-Bias."
    elif weighted_long > weighted_short and weighted_long >= 110 and weighted_gap >= 22 and long_count >= 2:
        decision = "LONG_BIAS"
        score = max(0, min(100, quality_score))
        reason = f"Rollen-Konsens LONG: Struktur {structure_signal}, Momentum {momentum_signal}, Risk {risk_signal}."
    elif weighted_short > weighted_long and weighted_short >= 110 and weighted_gap >= 22 and short_count >= 2:
        decision = "SHORT_BIAS"
        score = max(0, min(100, quality_score))
        reason = f"Rollen-Konsens SHORT: Struktur {structure_signal}, Momentum {momentum_signal}, Risk {risk_signal}."
    else:
        decision = "WAIT"
        score = max(35, min(60, quality_score))
        reason = "Keine ausreichende Rollen-Bestätigung zwischen Struktur, Momentum und Risk."

    return AgentReport(
        agent_name="CEO Agent",
        function="Agentenberichte nach Rollen, Datenqualität, Konflikten und Risk-Gates bewerten",
        signal="LONG" if decision == "LONG_BIAS" else "SHORT" if decision == "SHORT_BIAS" else "NEUTRAL",
        score=score,
        reads=f"Structure {structure_signal} | Momentum {momentum_signal} | Risk {risk_signal} | Quality {quality_score} | LONG {long_count}/{round(long_score, 1)} | SHORT {short_count}/{round(short_score, 1)}",
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
            "weak_count": weak_count,
            "offline_count": offline_count,
            "decision": decision,
            "reason": reason,
            "role_groups": role_groups,
            "hard_role_conflict": hard_role_conflict,
        },
    )


def refresh_risk_agent_report(
    board: dict[str, Any],
    scan: dict[str, Any] | None,
    config: dict[str, Any] | None = None,
    risk_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cfg = config or {}
    reports_raw = board.get("reports") or []
    reports = [
        AgentReport(
            agent_name=str(item.get("agent_name", "Agent")),
            function=str(item.get("function", "")),
            signal=str(item.get("signal", "NEUTRAL")).upper() if str(item.get("signal", "NEUTRAL")).upper() in ("LONG", "SHORT", "NEUTRAL") else "NEUTRAL",
            score=int(_safe_number(item.get("score", 0))),
            reads=str(item.get("reads", "")),
            message=str(item.get("message", "")),
            conflict=bool(item.get("conflict", False)),
            blocking=bool(item.get("blocking", False)),
            role=str(item.get("role", _agent_role(str(item.get("agent_name", ""))))),
            details=item.get("details") if isinstance(item.get("details"), dict) else None,
        )
        for item in reports_raw
        if str(item.get("agent_name", "")) != "Risk Agent"
    ]
    risk_report = _apply_agent_settings(_risk_agent(scan or {}, risk_context), cfg)
    reports.append(risk_report)
    long_present = any(report.signal == "LONG" for report in reports)
    short_present = any(report.signal == "SHORT" for report in reports)
    reports = [
        _with_quality_profile(AgentReport(
            agent_name=report.agent_name,
            function=report.function,
            signal=report.signal,
            score=report.score,
            reads=report.reads,
            message=report.message,
            conflict=(report.signal == "LONG" and short_present) or (report.signal == "SHORT" and long_present),
            blocking=report.blocking,
            role=_agent_role(report.agent_name),
            details=report.details,
        ))
        for report in reports
    ]
    refreshed = dict(board)
    refreshed["reports"] = [report.to_dict() for report in reports]
    refreshed["ceo"] = _ceo_agent(reports).to_dict()
    return refreshed


def _safe_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


# --------------------------------------------------
# BOARD BUILDER
# --------------------------------------------------
def build_agent_board(
    symbol: str,
    timeframe_seconds: int,
    candles: list[Any],
    indicator_data: dict[str, Any] | None,
    scan: dict[str, Any] | None,
    config: dict[str, Any] | None = None,
    risk_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    indicator = indicator_data or {}
    scan_data = scan or {}
    cfg = config or {}
    volume_period = max(2, int(cfg.get("agent_volume_period", 20)))
    sma_period = max(2, int(cfg.get("indicator_sma_period", cfg.get("agent_sma_period", 50))))
    mfi_period = max(2, int(cfg.get("indicator_mfi_period", cfg.get("agent_mfi_period", 14))))
    rsi_period = max(2, int(cfg.get("agent_rsi_period", 14)))
    vwap_lookback = max(5, int(cfg.get("agent_vwap_lookback_candles", 96)))
    breakout_lookback = max(3, int(cfg.get("agent_breakout_fakeout_lookback", 20)))
    volatility_atr_period = max(2, int(cfg.get("agent_volatility_atr_period", 14)))
    volatility_lookback = max(volatility_atr_period + 2, int(cfg.get("agent_volatility_lookback", 50)))
    raw_reports = [
        _bos_choch_agent(indicator),
        _box_agent(candles, indicator),
        _support_resistance_agent(candles, indicator),
        _swing_agent(indicator),
        _hma_agent(candles, indicator),
        _sma_agent(candles, sma_period),
        _triple_ema_agent(indicator),
        _macd_agent(indicator),
        _mfi_agent(candles, mfi_period),
        _rsi_agent(candles, rsi_period),
        _vwap_agent(candles, vwap_lookback),
        _breakout_fakeout_agent(candles, breakout_lookback),
        _volume_agent(candles, volume_period),
        _volatility_regime_agent(candles, volatility_atr_period, volatility_lookback),
        _risk_agent(scan_data, risk_context),
    ]
    reports = [_apply_agent_settings(report, cfg) for report in raw_reports]
    long_present = any(report.signal == "LONG" for report in reports)
    short_present = any(report.signal == "SHORT" for report in reports)
    reports = [
        _with_quality_profile(AgentReport(
            agent_name=report.agent_name,
            function=report.function,
            signal=report.signal,
            score=report.score,
            reads=report.reads,
            message=report.message,
            conflict=(report.signal == "LONG" and short_present) or (report.signal == "SHORT" and long_present),
            blocking=report.blocking,
            role=_agent_role(report.agent_name),
            details=report.details,
        ))
        for report in reports
    ]
    board = AgentBoard(
        symbol=symbol,
        timeframe_seconds=int(timeframe_seconds),
        reports=reports,
        ceo=_ceo_agent(reports),
    )
    return board.to_dict()
