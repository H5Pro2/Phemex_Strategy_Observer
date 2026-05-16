from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from math import sqrt
from typing import Any, Literal


# ==================================================
# indikator.py
# ==================================================
# MARKET STRUCTURE INDICATOR INTERFACE
# ==================================================


SwingText = Literal["HH", "LH", "HL", "LL"]
BreakText = Literal["BOS", "CHoCH"]
Direction = Literal["rising", "falling"]


@dataclass(frozen=True)
class StructureLabel:
    timestamp: int
    price: float
    text: SwingText
    direction: Direction


@dataclass(frozen=True)
class BreakLine:
    start_timestamp: int
    end_timestamp: int
    price: float
    text: BreakText
    direction: Direction


@dataclass(frozen=True)
class StructureBox:
    start_timestamp: int
    end_timestamp: int
    top: float
    bottom: float
    text: str
    direction: Direction
    opacity: float


@dataclass(frozen=True)
class SupportResistanceLevel:
    price: float
    upper: float
    lower: float
    strength: int
    kind: str
    label: str
    crossed: str
    color: str


@dataclass(frozen=True)
class SeriesPoint:
    timestamp: int
    value: float


@dataclass(frozen=True)
class IndicatorLine:
    name: str
    label: str
    color: str
    series: list[SeriesPoint]
    pane: str = "price"


@dataclass(frozen=True)
class IndicatorResult:
    name: str
    label: str
    swing_size: int
    hhll_range: int
    box_extend_candles: int
    hma_period: int
    sma_period: int
    mfi_period: int
    macd_fast_period: int
    macd_slow_period: int
    macd_signal_period: int
    triple_ema_period: int
    sr_pivot_period: int
    sr_max_levels: int
    labels: list[StructureLabel]
    break_lines: list[BreakLine]
    boxes: list[StructureBox]
    support_resistance: list[SupportResistanceLevel]
    lines: list[IndicatorLine]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label": self.label,
            "swing_size": self.swing_size,
            "hhll_range": self.hhll_range,
            "box_extend_candles": self.box_extend_candles,
            "hma_period": self.hma_period,
            "sma_period": self.sma_period,
            "mfi_period": self.mfi_period,
            "macd_fast_period": self.macd_fast_period,
            "macd_slow_period": self.macd_slow_period,
            "macd_signal_period": self.macd_signal_period,
            "triple_ema_period": self.triple_ema_period,
            "sr_pivot_period": self.sr_pivot_period,
            "sr_max_levels": self.sr_max_levels,
            "labels": [asdict(item) for item in self.labels],
            "break_lines": [asdict(item) for item in self.break_lines],
            "boxes": [asdict(item) for item in self.boxes],
            "support_resistance": [asdict(item) for item in self.support_resistance],
            "lines": [
                {
                    "name": item.name,
                    "label": item.label,
                    "color": item.color,
                    "pane": item.pane,
                    "series": [asdict(point) for point in item.series],
                }
                for item in self.lines
            ],
        }


# --------------------------------------------------
# VALUE ACCESS
# --------------------------------------------------
def _candle_value(candle: Any, key: str) -> float:
    if isinstance(candle, dict):
        return float(candle[key])
    return float(getattr(candle, key))


def _timestamp(candle: Any) -> int:
    return int(_candle_value(candle, "timestamp"))


def _hl2(candle: Any) -> float:
    return (_candle_value(candle, "high") + _candle_value(candle, "low")) / 2.0


# --------------------------------------------------
# PIVOTS
# --------------------------------------------------
def _pivot_high(candles: list[Any], index: int, size: int) -> float | None:
    start = index - size
    end = index + size + 1
    if start < 0 or end > len(candles):
        return None
    high = _candle_value(candles[index], "high")
    window = [_candle_value(candle, "high") for candle in candles[start:end]]
    return high if high >= max(window) else None


def _pivot_low(candles: list[Any], index: int, size: int) -> float | None:
    start = index - size
    end = index + size + 1
    if start < 0 or end > len(candles):
        return None
    low = _candle_value(candles[index], "low")
    window = [_candle_value(candle, "low") for candle in candles[start:end]]
    return low if low <= min(window) else None


def _pivot_high_value(values: list[float], index: int, size: int) -> float | None:
    start = index - size
    end = index + size + 1
    if start < 0 or end > len(values):
        return None
    value = float(values[index])
    window = [float(item) for item in values[start:end]]
    return value if value >= max(window) else None


def _pivot_low_value(values: list[float], index: int, size: int) -> float | None:
    start = index - size
    end = index + size + 1
    if start < 0 or end > len(values):
        return None
    value = float(values[index])
    window = [float(item) for item in values[start:end]]
    return value if value <= min(window) else None


# --------------------------------------------------
# MOVING AVERAGES
# --------------------------------------------------
def _wma(values: list[float], period: int) -> list[float | None]:
    safe_period = max(1, int(period))
    denominator = safe_period * (safe_period + 1) / 2.0
    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < safe_period:
            result.append(None)
            continue
        window = values[index - safe_period + 1:index + 1]
        weighted = sum(value * weight for weight, value in enumerate(window, start=1))
        result.append(weighted / denominator)
    return result


def _hma(values: list[float], period: int) -> list[float | None]:
    safe_period = max(1, int(period))
    half_period = max(1, safe_period // 2)
    sqrt_period = max(1, int(sqrt(safe_period)))
    wma_half = _wma(values, half_period)
    wma_full = _wma(values, safe_period)
    raw: list[float] = []
    raw_valid: list[bool] = []
    for half, full in zip(wma_half, wma_full):
        if half is None or full is None:
            raw.append(0.0)
            raw_valid.append(False)
        else:
            raw.append((2.0 * half) - full)
            raw_valid.append(True)
    hma_raw = _wma(raw, sqrt_period)
    return [value if valid and value is not None else None for value, valid in zip(hma_raw, raw_valid)]


def _ema_series(values: list[float], period: int) -> list[float | None]:
    safe_period = max(1, int(period))
    alpha = 2.0 / (safe_period + 1.0)
    result: list[float | None] = []
    ema: float | None = None
    for index, value in enumerate(values):
        if ema is None:
            ema = float(value)
        else:
            ema = (float(value) * alpha) + (ema * (1.0 - alpha))
        result.append(ema if index + 1 >= safe_period else None)
    return result


def _triple_ema(values: list[float], period: int) -> list[float | None]:
    ema1 = _ema_series(values, period)
    ema1_source = [value if value is not None else values[index] for index, value in enumerate(ema1)]
    ema2 = _ema_series(ema1_source, period)
    ema2_source = [value if value is not None else ema1_source[index] for index, value in enumerate(ema2)]
    ema3 = _ema_series(ema2_source, period)
    result: list[float | None] = []
    warmup = max(1, int(period)) * 3
    for index, (one, two, three) in enumerate(zip(ema1, ema2, ema3)):
        if index + 1 < warmup or one is None or two is None or three is None:
            result.append(None)
        else:
            result.append((3.0 * one) - (3.0 * two) + three)
    return result


def _ema_optional_series(values: list[float | None], period: int) -> list[float | None]:
    safe_period = max(1, int(period))
    alpha = 2.0 / (safe_period + 1.0)
    result: list[float | None] = []
    ema: float | None = None
    valid_count = 0
    for value in values:
        if value is None:
            result.append(None)
            continue
        valid_count += 1
        if ema is None:
            ema = float(value)
        else:
            ema = (float(value) * alpha) + (ema * (1.0 - alpha))
        result.append(ema if valid_count >= safe_period else None)
    return result


def _macd(values: list[float], fast_period: int, slow_period: int, signal_period: int) -> tuple[list[float | None], list[float | None], list[float | None]]:
    safe_fast = max(1, int(fast_period))
    safe_slow = max(safe_fast + 1, int(slow_period))
    safe_signal = max(1, int(signal_period))
    fast_ema = _ema_series(values, safe_fast)
    slow_ema = _ema_series(values, safe_slow)
    macd_values: list[float | None] = []
    for fast, slow in zip(fast_ema, slow_ema):
        if fast is None or slow is None:
            macd_values.append(None)
        else:
            macd_values.append(float(fast) - float(slow))
    signal_values = _ema_optional_series(macd_values, safe_signal)
    histogram_values: list[float | None] = []
    for macd_value, signal_value in zip(macd_values, signal_values):
        if macd_value is None or signal_value is None:
            histogram_values.append(None)
        else:
            histogram_values.append(float(macd_value) - float(signal_value))
    return macd_values, signal_values, histogram_values


def _oscillator_line_from_values(
    candles: list[Any],
    values: list[float | None],
    name: str,
    label: str,
    color: str,
    lookback_start: int = 0,
) -> IndicatorLine:
    series: list[SeriesPoint] = []
    for candle, value in zip(candles, values):
        timestamp = _timestamp(candle)
        if value is None or not _in_lookback(timestamp, lookback_start):
            continue
        series.append(SeriesPoint(timestamp=timestamp, value=round(float(value), 8)))
    return IndicatorLine(name=name, label=label, color=color, series=series, pane="oscillator")


def _line_from_values(
    candles: list[Any],
    values: list[float | None],
    name: str,
    label: str,
    color: str,
    lookback_start: int = 0,
) -> IndicatorLine:
    series: list[SeriesPoint] = []
    for candle, value in zip(candles, values):
        timestamp = _timestamp(candle)
        if value is None or not _in_lookback(timestamp, lookback_start):
            continue
        series.append(SeriesPoint(timestamp=timestamp, value=round(float(value), 8)))
    return IndicatorLine(name=name, label=label, color=color, series=series)


def _sma(values: list[float], period: int) -> list[float | None]:
    safe_period = max(1, int(period))
    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < safe_period:
            result.append(None)
            continue
        window = values[index - safe_period + 1:index + 1]
        result.append(sum(window) / safe_period)
    return result


def _mfi(candles: list[Any], period: int) -> list[float | None]:
    safe_period = max(1, int(period))
    typical_prices = [
        (_candle_value(candle, "high") + _candle_value(candle, "low") + _candle_value(candle, "close")) / 3.0
        for candle in candles
    ]
    raw_flows = [typical * _candle_value(candle, "volume") for typical, candle in zip(typical_prices, candles)]
    positive: list[float] = [0.0]
    negative: list[float] = [0.0]
    for index in range(1, len(candles)):
        if typical_prices[index] > typical_prices[index - 1]:
            positive.append(raw_flows[index])
            negative.append(0.0)
        elif typical_prices[index] < typical_prices[index - 1]:
            positive.append(0.0)
            negative.append(raw_flows[index])
        else:
            positive.append(0.0)
            negative.append(0.0)

    result: list[float | None] = []
    for index in range(len(candles)):
        if index + 1 < safe_period:
            result.append(None)
            continue
        start = index - safe_period + 1
        positive_flow = sum(positive[start:index + 1])
        negative_flow = sum(negative[start:index + 1])
        if positive_flow <= 0 and negative_flow <= 0:
            result.append(50.0)
        elif negative_flow <= 0:
            result.append(100.0)
        else:
            money_ratio = positive_flow / negative_flow
            result.append(100.0 - (100.0 / (1.0 + money_ratio)))
    return result


def _dynamic_support_resistance(
    candles: list[Any],
    pivot_period: int,
    source: str,
    max_pivots: int,
    channel_width_percent: int,
    max_levels: int,
    min_strength: int,
    support_color: str,
    resistance_color: str,
) -> list[SupportResistanceLevel]:
    if not candles:
        return []
    safe_pivot_period = max(4, min(30, int(pivot_period)))
    safe_max_pivots = max(5, min(100, int(max_pivots)))
    safe_channel_width_percent = max(1, int(channel_width_percent))
    safe_max_levels = max(1, min(10, int(max_levels)))
    safe_min_strength = max(1, min(10, int(min_strength)))
    closes = [_candle_value(candle, "close") for candle in candles]
    opens = [_candle_value(candle, "open") for candle in candles]
    highs = [_candle_value(candle, "high") for candle in candles]
    lows = [_candle_value(candle, "low") for candle in candles]
    if str(source) == "Close/Open":
        src_high = [max(close, open_) for close, open_ in zip(closes, opens)]
        src_low = [min(close, open_) for close, open_ in zip(closes, opens)]
    else:
        src_high = highs
        src_low = lows
    window = max(1, min(300, len(candles)))
    prd_highest = max(highs[-window:])
    prd_lowest = min(lows[-window:])
    channel_width = (prd_highest - prd_lowest) * (safe_channel_width_percent / 100.0)
    if channel_width <= 0:
        channel_width = max(abs(closes[-1]) * 0.001, 1e-12)

    pivotvals: list[float] = []
    for index in range(len(candles)):
        pivot_index = index - safe_pivot_period
        if pivot_index < 0:
            continue
        ph = _pivot_high_value(src_high, pivot_index, safe_pivot_period)
        pl = _pivot_low_value(src_low, pivot_index, safe_pivot_period)
        if ph is not None:
            pivotvals.insert(0, float(ph))
            if len(pivotvals) > safe_max_pivots:
                pivotvals.pop()
        if pl is not None:
            pivotvals.insert(0, float(pl))
            if len(pivotvals) > safe_max_pivots:
                pivotvals.pop()
    if not pivotvals:
        return []

    def get_sr_vals(ind: int) -> tuple[float, float, int]:
        lo = float(pivotvals[ind])
        hi = lo
        numpp = 0
        for cpp in pivotvals:
            width = (hi - cpp) if cpp <= lo else (cpp - lo)
            if width <= channel_width:
                if cpp <= hi:
                    lo = min(lo, cpp)
                else:
                    hi = max(hi, cpp)
                numpp += 1
        return hi, lo, numpp

    sr_up_level: list[float] = []
    sr_dn_level: list[float] = []
    sr_strength: list[int] = []

    def find_loc(strength: int) -> int:
        ret = len(sr_strength)
        for i in range(len(sr_strength) - 1, -1, -1):
            if strength <= sr_strength[i]:
                break
            ret = i
        return ret

    def check_sr(hi: float, lo: float, strength: int) -> bool:
        i = 0
        while i < len(sr_up_level):
            included = ((sr_up_level[i] >= lo and sr_up_level[i] <= hi) or (sr_dn_level[i] >= lo and sr_dn_level[i] <= hi))
            if included:
                if strength >= sr_strength[i]:
                    del sr_strength[i]
                    del sr_up_level[i]
                    del sr_dn_level[i]
                    return True
                return False
            i += 1
        return True

    for index in range(len(pivotvals)):
        hi, lo, strength = get_sr_vals(index)
        if check_sr(hi, lo, strength):
            loc = find_loc(strength)
            if loc < safe_max_levels and strength >= safe_min_strength:
                sr_strength.insert(loc, int(strength))
                sr_up_level.insert(loc, float(hi))
                sr_dn_level.insert(loc, float(lo))
                if len(sr_strength) > safe_max_levels:
                    sr_strength.pop()
                    sr_up_level.pop()
                    sr_dn_level.pop()

    current_close = float(closes[-1])
    previous_close = float(closes[-2]) if len(closes) > 1 else current_close
    levels: list[SupportResistanceLevel] = []
    for hi, lo, strength in zip(sr_up_level, sr_dn_level, sr_strength):
        mid = round((float(hi) + float(lo)) / 2.0, 8)
        kind = "resistance" if mid >= current_close else "support"
        crossed = "over" if previous_close <= mid < current_close else "under" if previous_close >= mid > current_close else "none"
        levels.append(
            SupportResistanceLevel(
                price=mid,
                upper=round(float(hi), 8),
                lower=round(float(lo), 8),
                strength=int(strength),
                kind=kind,
                label=f"{'R' if kind == 'resistance' else 'S'} {mid} ({int(strength)})",
                crossed=crossed,
                color=resistance_color if kind == "resistance" else support_color,
            )
        )
    return sorted(levels, key=lambda item: abs(item.price - current_close))


# --------------------------------------------------
# LOOKBACK
# --------------------------------------------------
def _lookback_start(candles: list[Any], days: int) -> int:
    if not candles or days <= 0:
        return 0
    latest = datetime.fromtimestamp(_timestamp(candles[-1]), tz=timezone.utc)
    day_start = datetime(latest.year, latest.month, latest.day, tzinfo=timezone.utc)
    return int(day_start.timestamp()) - (days * 24 * 3600)


def _in_lookback(timestamp: int, start_timestamp: int) -> bool:
    return start_timestamp <= 0 or timestamp >= start_timestamp


# --------------------------------------------------
# MARKET STRUCTURE INDICATOR
# --------------------------------------------------
def calculate_market_structure_indicator(
    candles: list[Any],
    swing_size: int = 5,
    hhll_range: int = 50,
    bos_confirmation: str = "Wicks",
    bos_choch_lookback_days: int = 3,
    boxes_lookback_days: int = 3,
    swing_labels_lookback_days: int = 3,
    hma_lookback_days: int = 0,
    sma_lookback_days: int = 0,
    triple_ema_lookback_days: int = 0,
    mfi_lookback_days: int = 0,
    macd_lookback_days: int = 0,
    show_swing_labels: bool = True,
    show_bos_choch: bool = True,
    show_boxes: bool = True,
    show_hma: bool = False,
    show_sma: bool = False,
    show_triple_ema: bool = False,
    show_mfi: bool = False,
    show_macd: bool = False,
    show_support_resistance: bool = False,
    hma_period: int = 20,
    sma_period: int = 50,
    triple_ema_period: int = 20,
    triple_ema_slow_period: int = 50,
    mfi_period: int = 14,
    macd_fast_period: int = 12,
    macd_slow_period: int = 26,
    macd_signal_period: int = 9,
    sr_pivot_period: int = 10,
    sr_source: str = "High/Low",
    sr_max_pivots: int = 20,
    sr_channel_width_percent: int = 10,
    sr_max_levels: int = 5,
    sr_min_strength: int = 2,
    box_extend_candles: int = 4,
    hma_color: str = "#7c3aed",
    sma_color: str = "#06b6d4",
    triple_ema_color: str = "#d97706",
    triple_ema_slow_color: str = "#2563eb",
    mfi_color: str = "#db2777",
    macd_color: str = "#0ea5e9",
    macd_signal_color: str = "#f97316",
    macd_histogram_color: str = "#64748b",
    sr_support_color: str = "#22c55e",
    sr_resistance_color: str = "#ef4444",
) -> IndicatorResult:
    safe_swing_size = max(1, int(swing_size))
    safe_hhll_range = max(1, int(hhll_range))
    safe_hma_period = max(1, int(hma_period))
    safe_sma_period = max(1, int(sma_period))
    safe_triple_ema_period = max(1, int(triple_ema_period))
    safe_triple_ema_slow_period = max(1, int(triple_ema_slow_period))
    safe_mfi_period = max(1, int(mfi_period))
    safe_macd_fast_period = max(1, int(macd_fast_period))
    safe_macd_slow_period = max(safe_macd_fast_period + 1, int(macd_slow_period))
    safe_macd_signal_period = max(1, int(macd_signal_period))
    safe_sr_pivot_period = max(4, min(30, int(sr_pivot_period)))
    safe_sr_max_pivots = max(5, min(100, int(sr_max_pivots)))
    safe_sr_channel_width_percent = max(1, int(sr_channel_width_percent))
    safe_sr_max_levels = max(1, min(10, int(sr_max_levels)))
    safe_sr_min_strength = max(1, min(10, int(sr_min_strength)))
    safe_box_extend_candles = max(2, int(box_extend_candles))
    labels: list[StructureLabel] = []
    break_lines: list[BreakLine] = []
    boxes: list[StructureBox] = []
    support_resistance: list[SupportResistanceLevel] = []
    lines: list[IndicatorLine] = []

    prev_high: float | None = None
    prev_low: float | None = None
    prev_high_index: int | None = None
    prev_low_index: int | None = None
    high_active = False
    low_active = False
    prev_breakout_dir = 0
    bos_choch_lookback_start = _lookback_start(candles, bos_choch_lookback_days)
    boxes_lookback_start = _lookback_start(candles, boxes_lookback_days)
    swing_labels_lookback_start = _lookback_start(candles, swing_labels_lookback_days)
    hma_lookback_start = _lookback_start(candles, hma_lookback_days)
    sma_lookback_start = _lookback_start(candles, sma_lookback_days)
    triple_ema_lookback_start = _lookback_start(candles, triple_ema_lookback_days)
    mfi_lookback_start = _lookback_start(candles, mfi_lookback_days)
    macd_lookback_start = _lookback_start(candles, macd_lookback_days)

    for index, candle in enumerate(candles):
        pivot_index = index - safe_swing_size
        if pivot_index >= 0:
            piv_hi = _pivot_high(candles, pivot_index, safe_swing_size)
            if piv_hi is not None:
                text: SwingText = "HH" if prev_high is not None and piv_hi >= prev_high else "LH"
                prev_high = piv_hi
                prev_high_index = pivot_index
                high_active = True
                if show_swing_labels and _in_lookback(_timestamp(candles[pivot_index]), swing_labels_lookback_start):
                    labels.append(
                        StructureLabel(
                            timestamp=_timestamp(candles[pivot_index]),
                            price=round(float(piv_hi), 8),
                            text=text,
                            direction="rising" if text == "HH" else "falling",
                        )
                    )

            piv_lo = _pivot_low(candles, pivot_index, safe_swing_size)
            if piv_lo is not None:
                text = "HL" if prev_low is not None and piv_lo >= prev_low else "LL"
                prev_low = piv_lo
                prev_low_index = pivot_index
                low_active = True
                if show_swing_labels and _in_lookback(_timestamp(candles[pivot_index]), swing_labels_lookback_start):
                    labels.append(
                        StructureLabel(
                            timestamp=_timestamp(candles[pivot_index]),
                            price=round(float(piv_lo), 8),
                            text=text,
                            direction="rising" if text == "HL" else "falling",
                        )
                    )

        high_src = _candle_value(candle, "close") if bos_confirmation == "Candle Close" else _candle_value(candle, "high")
        low_src = _candle_value(candle, "close") if bos_confirmation == "Candle Close" else _candle_value(candle, "low")
        current_timestamp = _timestamp(candle)

        if prev_high is not None and prev_high_index is not None and high_active and high_src > prev_high:
            high_active = False
            text: BreakText = "CHoCH" if prev_breakout_dir == -1 else "BOS"
            if show_bos_choch and _in_lookback(current_timestamp, bos_choch_lookback_start):
                break_lines.append(
                    BreakLine(
                        start_timestamp=_timestamp(candles[prev_high_index]),
                        end_timestamp=current_timestamp,
                        price=round(float(prev_high), 8),
                        text=text,
                        direction="rising",
                    )
                )
            prev_breakout_dir = 1

        if prev_low is not None and prev_low_index is not None and low_active and low_src < prev_low:
            low_active = False
            text = "CHoCH" if prev_breakout_dir == 1 else "BOS"
            if show_bos_choch and _in_lookback(current_timestamp, bos_choch_lookback_start):
                break_lines.append(
                    BreakLine(
                        start_timestamp=_timestamp(candles[prev_low_index]),
                        end_timestamp=current_timestamp,
                        price=round(float(prev_low), 8),
                        text=text,
                        direction="falling",
                    )
                )
            prev_breakout_dir = -1

    if candles and show_boxes:
        interval = int(_candle_value(candles[-1], "interval"))
        end_timestamp = _timestamp(candles[-1]) + interval * safe_box_extend_candles
        last_high_box: tuple[int, float, float, float] | None = None
        last_low_box: tuple[int, float, float, float] | None = None
        for index, candle in enumerate(candles):
            if index < 1:
                continue
            high = _candle_value(candle, "high")
            low = _candle_value(candle, "low")
            prev_start = max(0, index - safe_hhll_range)
            previous_highs = [_candle_value(item, "high") for item in candles[prev_start:index]]
            previous_lows = [_candle_value(item, "low") for item in candles[prev_start:index]]
            if previous_highs and high > max(previous_highs):
                midpoint = (high + _hl2(candle)) / 2.0
                last_high_box = (_timestamp(candle), high, midpoint, low)
            if previous_lows and low < min(previous_lows):
                midpoint = _hl2(candle) - ((high - _hl2(candle)) / 2.0)
                last_low_box = (_timestamp(candle), high, midpoint, low)

        if last_high_box and _in_lookback(last_high_box[0], boxes_lookback_start):
            start, high, midpoint, low = last_high_box
            boxes.append(StructureBox(start, end_timestamp, round(high, 8), round(midpoint, 8), "HH", "falling", 0.15))
            boxes.append(StructureBox(start, end_timestamp, round(midpoint, 8), round(low, 8), "", "falling", 0.04))
        if last_low_box and _in_lookback(last_low_box[0], boxes_lookback_start):
            start, high, midpoint, low = last_low_box
            boxes.append(StructureBox(start, end_timestamp, round(midpoint, 8), round(low, 8), "LL", "rising", 0.15))
            boxes.append(StructureBox(start, end_timestamp, round(high, 8), round(midpoint, 8), "", "rising", 0.04))

    close_values = [_candle_value(candle, "close") for candle in candles]
    if show_hma and close_values:
        lines.append(
            _line_from_values(
                candles,
                _hma(close_values, safe_hma_period),
                "HMA",
                f"HMA {safe_hma_period}",
                hma_color,
                hma_lookback_start,
            )
        )
    if show_sma and close_values:
        lines.append(
            _line_from_values(
                candles,
                _sma(close_values, safe_sma_period),
                "SMA",
                f"SMA {safe_sma_period}",
                sma_color,
                sma_lookback_start,
            )
        )
    if show_triple_ema and close_values:
        lines.append(
            _line_from_values(
                candles,
                _triple_ema(close_values, safe_triple_ema_period),
                "TRIPLE_EMA_FAST",
                f"Triple EMA Fast {safe_triple_ema_period}",
                triple_ema_color,
                triple_ema_lookback_start,
            )
        )
        lines.append(
            _line_from_values(
                candles,
                _triple_ema(close_values, safe_triple_ema_slow_period),
                "TRIPLE_EMA_SLOW",
                f"Triple EMA Slow {safe_triple_ema_slow_period}",
                triple_ema_slow_color,
                triple_ema_lookback_start,
            )
        )
    if show_macd and close_values:
        macd_values, macd_signal_values, macd_histogram_values = _macd(
            close_values,
            safe_macd_fast_period,
            safe_macd_slow_period,
            safe_macd_signal_period,
        )
        lines.append(
            _oscillator_line_from_values(
                candles,
                macd_values,
                "MACD",
                f"MACD {safe_macd_fast_period}/{safe_macd_slow_period}",
                macd_color,
                macd_lookback_start,
            )
        )
        lines.append(
            _oscillator_line_from_values(
                candles,
                macd_signal_values,
                "MACD_SIGNAL",
                f"MACD Signal {safe_macd_signal_period}",
                macd_signal_color,
                macd_lookback_start,
            )
        )
        lines.append(
            _oscillator_line_from_values(
                candles,
                macd_histogram_values,
                "MACD_HISTOGRAM",
                "MACD Histogram",
                macd_histogram_color,
                macd_lookback_start,
            )
        )
    if show_mfi and candles:
        lines.append(
            IndicatorLine(
                name="MFI",
                label=f"MFI {safe_mfi_period}",
                color=mfi_color,
                series=[
                    SeriesPoint(timestamp=_timestamp(candle), value=round(float(value), 4))
                    for candle, value in zip(candles, _mfi(candles, safe_mfi_period))
                    if value is not None and _in_lookback(_timestamp(candle), mfi_lookback_start)
                ],
                pane="oscillator",
            )
        )
    if show_support_resistance and candles:
        support_resistance = _dynamic_support_resistance(
            candles=candles,
            pivot_period=safe_sr_pivot_period,
            source=sr_source,
            max_pivots=safe_sr_max_pivots,
            channel_width_percent=safe_sr_channel_width_percent,
            max_levels=safe_sr_max_levels,
            min_strength=safe_sr_min_strength,
            support_color=sr_support_color,
            resistance_color=sr_resistance_color,
        )

    return IndicatorResult(
        name="MARKET_STRUCTURE_PA79_SPLIT",
        label="Market Structure PA79 Split",
        swing_size=safe_swing_size,
        hhll_range=safe_hhll_range,
        box_extend_candles=safe_box_extend_candles,
        hma_period=safe_hma_period,
        sma_period=safe_sma_period,
        mfi_period=safe_mfi_period,
        macd_fast_period=safe_macd_fast_period,
        macd_slow_period=safe_macd_slow_period,
        macd_signal_period=safe_macd_signal_period,
        triple_ema_period=safe_triple_ema_period,
        sr_pivot_period=safe_sr_pivot_period,
        sr_max_levels=safe_sr_max_levels,
        labels=labels,
        break_lines=break_lines,
        boxes=boxes,
        support_resistance=support_resistance,
        lines=lines,
    )


# --------------------------------------------------
# API RESPONSE
# --------------------------------------------------
def build_indicator_response(
    symbol: str,
    resolution: int,
    candles: list[Any],
    swing_size: int = 5,
    hhll_range: int = 50,
    bos_confirmation: str = "Wicks",
    bos_choch_lookback_days: int = 3,
    boxes_lookback_days: int = 3,
    swing_labels_lookback_days: int = 3,
    hma_lookback_days: int = 0,
    sma_lookback_days: int = 0,
    triple_ema_lookback_days: int = 0,
    mfi_lookback_days: int = 0,
    macd_lookback_days: int = 0,
    show_swing_labels: bool = True,
    show_bos_choch: bool = True,
    show_boxes: bool = True,
    show_hma: bool = False,
    show_sma: bool = False,
    show_triple_ema: bool = False,
    show_mfi: bool = False,
    show_macd: bool = False,
    show_support_resistance: bool = False,
    hma_period: int = 20,
    sma_period: int = 50,
    triple_ema_period: int = 20,
    triple_ema_slow_period: int = 50,
    mfi_period: int = 14,
    macd_fast_period: int = 12,
    macd_slow_period: int = 26,
    macd_signal_period: int = 9,
    sr_pivot_period: int = 10,
    sr_source: str = "High/Low",
    sr_max_pivots: int = 20,
    sr_channel_width_percent: int = 10,
    sr_max_levels: int = 5,
    sr_min_strength: int = 2,
    box_extend_candles: int = 4,
    hma_color: str = "#7c3aed",
    sma_color: str = "#06b6d4",
    triple_ema_color: str = "#d97706",
    triple_ema_slow_color: str = "#2563eb",
    mfi_color: str = "#db2777",
    macd_color: str = "#0ea5e9",
    macd_signal_color: str = "#f97316",
    macd_histogram_color: str = "#64748b",
    sr_support_color: str = "#22c55e",
    sr_resistance_color: str = "#ef4444",
) -> dict[str, Any]:
    indicator = calculate_market_structure_indicator(
        candles=candles,
        swing_size=swing_size,
        hhll_range=hhll_range,
        bos_confirmation=bos_confirmation,
        bos_choch_lookback_days=bos_choch_lookback_days,
        boxes_lookback_days=boxes_lookback_days,
        swing_labels_lookback_days=swing_labels_lookback_days,
        hma_lookback_days=hma_lookback_days,
        sma_lookback_days=sma_lookback_days,
        triple_ema_lookback_days=triple_ema_lookback_days,
        mfi_lookback_days=mfi_lookback_days,
        macd_lookback_days=macd_lookback_days,
        show_swing_labels=show_swing_labels,
        show_bos_choch=show_bos_choch,
        show_boxes=show_boxes,
        show_hma=show_hma,
        show_sma=show_sma,
        show_triple_ema=show_triple_ema,
        show_mfi=show_mfi,
        show_macd=show_macd,
        show_support_resistance=show_support_resistance,
        hma_period=hma_period,
        sma_period=sma_period,
        triple_ema_period=triple_ema_period,
        triple_ema_slow_period=triple_ema_slow_period,
        mfi_period=mfi_period,
        macd_fast_period=macd_fast_period,
        macd_slow_period=macd_slow_period,
        macd_signal_period=macd_signal_period,
        sr_pivot_period=sr_pivot_period,
        sr_source=sr_source,
        sr_max_pivots=sr_max_pivots,
        sr_channel_width_percent=sr_channel_width_percent,
        sr_max_levels=sr_max_levels,
        sr_min_strength=sr_min_strength,
        box_extend_candles=box_extend_candles,
        hma_color=hma_color,
        sma_color=sma_color,
        triple_ema_color=triple_ema_color,
        triple_ema_slow_color=triple_ema_slow_color,
        mfi_color=mfi_color,
        macd_color=macd_color,
        macd_signal_color=macd_signal_color,
        macd_histogram_color=macd_histogram_color,
        sr_support_color=sr_support_color,
        sr_resistance_color=sr_resistance_color,
    )
    return {
        "symbol": symbol,
        "resolution": int(resolution),
        "settings": {
            "show_swing_labels": bool(show_swing_labels),
            "show_bos_choch": bool(show_bos_choch),
            "show_boxes": bool(show_boxes),
            "show_hma": bool(show_hma),
            "show_sma": bool(show_sma),
            "show_triple_ema": bool(show_triple_ema),
            "show_mfi": bool(show_mfi),
            "show_macd": bool(show_macd),
            "show_support_resistance": bool(show_support_resistance),
            "bos_confirmation": bos_confirmation,
            "bos_choch_lookback_days": max(0, int(bos_choch_lookback_days)),
            "boxes_lookback_days": max(0, int(boxes_lookback_days)),
            "swing_labels_lookback_days": max(0, int(swing_labels_lookback_days)),
            "hma_lookback_days": max(0, int(hma_lookback_days)),
            "sma_lookback_days": max(0, int(sma_lookback_days)),
            "triple_ema_lookback_days": max(0, int(triple_ema_lookback_days)),
            "mfi_lookback_days": max(0, int(mfi_lookback_days)),
            "macd_lookback_days": max(0, int(macd_lookback_days)),
            "box_extend_candles": max(2, int(box_extend_candles)),
            "sma_period": max(1, int(sma_period)),
            "triple_ema_slow_period": max(1, int(triple_ema_slow_period)),
            "mfi_period": max(1, int(mfi_period)),
            "macd_fast_period": max(1, int(macd_fast_period)),
            "macd_slow_period": max(max(1, int(macd_fast_period)) + 1, int(macd_slow_period)),
            "macd_signal_period": max(1, int(macd_signal_period)),
            "sr_pivot_period": max(4, min(30, int(sr_pivot_period))),
            "sr_source": sr_source if sr_source in ("High/Low", "Close/Open") else "High/Low",
            "sr_max_pivots": max(5, min(100, int(sr_max_pivots))),
            "sr_channel_width_percent": max(1, int(sr_channel_width_percent)),
            "sr_max_levels": max(1, min(10, int(sr_max_levels))),
            "sr_min_strength": max(1, min(10, int(sr_min_strength))),
            "hma_color": hma_color,
            "sma_color": sma_color,
            "triple_ema_color": triple_ema_color,
            "mfi_color": mfi_color,
            "macd_color": macd_color,
            "macd_signal_color": macd_signal_color,
            "macd_histogram_color": macd_histogram_color,
            "sr_support_color": sr_support_color,
            "sr_resistance_color": sr_resistance_color,
        },
        **indicator.to_dict(),
    }
