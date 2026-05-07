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
    if "mfi" in text:
        return "agent_mfi"
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
            function="Preisposition in Strukturboxen pruefen",
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


def _volume_agent(candles: list[Any], period: int = 20) -> AgentReport:
    if len(candles) < 2:
        return AgentReport(
            agent_name="Volume Agent",
            function="Volumen-Kontext pruefen",
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
            function="Volumen-Kontext pruefen",
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


def _risk_agent(scan: dict[str, Any]) -> AgentReport:
    pipeline = str(scan.get("pipeline", "agents_brain_ceo_gate"))
    return AgentReport(
        agent_name="Risk Agent",
        function="Brain-Pipeline und harte Gate-Stufe beobachten",
        signal="NEUTRAL",
        score=50,
        reads=f"pipeline: {pipeline} | setup_found: {scan.get('setup_found', False)}",
        message="Trade-Freigabe entsteht erst nach Brain, CEO und Economic Gate.",
    )


# --------------------------------------------------
# CEO AGENT
# --------------------------------------------------
def _ceo_agent(reports: list[AgentReport]) -> AgentReport:
    directional = [report for report in reports if report.signal in ("LONG", "SHORT")]
    long_score = sum(report.score for report in directional if report.signal == "LONG")
    short_score = sum(report.score for report in directional if report.signal == "SHORT")
    long_count = sum(1 for report in directional if report.signal == "LONG")
    short_count = sum(1 for report in directional if report.signal == "SHORT")
    conflict = long_count > 0 and short_count > 0
    blocking = any(report.blocking for report in reports)

    if blocking:
        decision: AgentDecision = "BLOCKED"
        score = 0
        reason = "Mindestens ein blockierender Agent meldet Blockade."
    elif conflict:
        decision = "WAIT"
        score = max(long_score, short_score) // max(1, len(directional))
        reason = f"Konflikt: LONG {long_count} Agent(en), SHORT {short_count} Agent(en)."
    elif long_score > short_score and long_score >= 120:
        decision = "LONG_BIAS"
        score = min(100, long_score // max(1, long_count))
        reason = f"Agentenmehrheit LONG mit Score {score}."
    elif short_score > long_score and short_score >= 120:
        decision = "SHORT_BIAS"
        score = min(100, short_score // max(1, short_count))
        reason = f"Agentenmehrheit SHORT mit Score {score}."
    else:
        decision = "WAIT"
        score = 50
        reason = "Keine ausreichende gemeinsame Richtung."

    return AgentReport(
        agent_name="CEO Agent",
        function="Agentenberichte zusammenfassen und Konflikte pruefen",
        signal="LONG" if decision == "LONG_BIAS" else "SHORT" if decision == "SHORT_BIAS" else "NEUTRAL",
        score=score,
        reads=f"LONG {long_count}/{long_score} | SHORT {short_count}/{short_score}",
        message=f"{decision}: {reason}",
        conflict=conflict,
        blocking=blocking,
    )


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
) -> dict[str, Any]:
    indicator = indicator_data or {}
    scan_data = scan or {}
    cfg = config or {}
    volume_period = max(2, int(cfg.get("agent_volume_period", 20)))
    sma_period = max(2, int(cfg.get("agent_sma_period", 50)))
    mfi_period = max(2, int(cfg.get("agent_mfi_period", 14)))
    raw_reports = [
        _bos_choch_agent(indicator),
        _box_agent(candles, indicator),
        _support_resistance_agent(candles, indicator),
        _swing_agent(indicator),
        _hma_agent(candles, indicator),
        _sma_agent(candles, sma_period),
        _triple_ema_agent(indicator),
        _mfi_agent(candles, mfi_period),
        _volume_agent(candles, volume_period),
        _risk_agent(scan_data),
    ]
    reports = [_apply_agent_settings(report, cfg) for report in raw_reports]
    long_present = any(report.signal == "LONG" for report in reports)
    short_present = any(report.signal == "SHORT" for report in reports)
    reports = [
        AgentReport(
            agent_name=report.agent_name,
            function=report.function,
            signal=report.signal,
            score=report.score,
            reads=report.reads,
            message=report.message,
            conflict=(report.signal == "LONG" and short_present) or (report.signal == "SHORT" and long_present),
            blocking=report.blocking,
        )
        for report in reports
    ]
    board = AgentBoard(
        symbol=symbol,
        timeframe_seconds=int(timeframe_seconds),
        reports=reports,
        ceo=_ceo_agent(reports),
    )
    return board.to_dict()
