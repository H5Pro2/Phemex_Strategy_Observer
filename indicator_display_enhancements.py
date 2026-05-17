from __future__ import annotations

from typing import Any

import indikator as ind


# ==================================================
# indicator_display_enhancements.py
# ==================================================
# ADDITIONAL CHART INDICATOR DISPLAY LINES
# ==================================================

_ORIGINAL_BUILD_INDICATOR_RESPONSE = ind.build_indicator_response


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def _safe_bool(value: Any, default: bool = True) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "aktiv", "active"}:
        return True
    if text in {"0", "false", "no", "off", "aus", "inactive"}:
        return False
    return default


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _candle_value(candle: Any, key: str) -> float:
    if isinstance(candle, dict):
        return float(candle[key])
    return float(getattr(candle, key))


def _timestamp(candle: Any) -> int:
    return int(_candle_value(candle, "timestamp"))


def _lookback_start(candles: list[Any], lookback_days: int) -> int:
    if not candles or int(lookback_days) <= 0:
        return 0
    last_time = _timestamp(candles[-1])
    return int(last_time - (int(lookback_days) * 86400))


def _in_lookback(timestamp: int, start: int) -> bool:
    return start <= 0 or int(timestamp) >= int(start)


def _append_line(result: dict[str, Any], name: str, label: str, color: str, pane: str, candles: list[Any], values: list[float | None], lookback_days: int = 0) -> None:
    start = _lookback_start(candles, lookback_days)
    series = []
    for candle, value in zip(candles, values):
        if value is None:
            continue
        timestamp = _timestamp(candle)
        if not _in_lookback(timestamp, start):
            continue
        series.append({"timestamp": timestamp, "value": round(float(value), 8)})
    if not series:
        return
    lines = result.setdefault("lines", [])
    if any(str(line.get("name", "")).upper() == name.upper() for line in lines if isinstance(line, dict)):
        return
    lines.append({"name": name, "label": label, "color": color, "pane": pane, "series": series})


# --------------------------------------------------
# INDICATORS
# --------------------------------------------------
def _rsi(values: list[float], period: int) -> list[float | None]:
    safe_period = max(1, int(period))
    if not values:
        return []
    result: list[float | None] = [None]
    gains: list[float] = []
    losses: list[float] = []
    avg_gain: float | None = None
    avg_loss: float | None = None
    for index in range(1, len(values)):
        change = float(values[index]) - float(values[index - 1])
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
        if index < safe_period:
            result.append(None)
            continue
        if index == safe_period:
            avg_gain = sum(gains[-safe_period:]) / safe_period
            avg_loss = sum(losses[-safe_period:]) / safe_period
        else:
            avg_gain = ((avg_gain or 0.0) * (safe_period - 1) + gains[-1]) / safe_period
            avg_loss = ((avg_loss or 0.0) * (safe_period - 1) + losses[-1]) / safe_period
        if avg_loss is None or avg_loss <= 0:
            result.append(100.0)
        else:
            rs = (avg_gain or 0.0) / avg_loss
            result.append(100.0 - (100.0 / (1.0 + rs)))
    return result


def _vwap(candles: list[Any], lookback_candles: int) -> list[float | None]:
    safe_lookback = max(1, int(lookback_candles))
    result: list[float | None] = []
    typical_values = [(_candle_value(candle, "high") + _candle_value(candle, "low") + _candle_value(candle, "close")) / 3.0 for candle in candles]
    volumes = [_candle_value(candle, "volume") for candle in candles]
    for index in range(len(candles)):
        start = max(0, index - safe_lookback + 1)
        volume_sum = sum(volumes[start:index + 1])
        if volume_sum <= 0:
            result.append(None)
            continue
        weighted_sum = sum(typical_values[pos] * volumes[pos] for pos in range(start, index + 1))
        result.append(weighted_sum / volume_sum)
    return result


def _volume_values(candles: list[Any]) -> list[float | None]:
    return [_candle_value(candle, "volume") for candle in candles]


# --------------------------------------------------
# PATCHED API
# --------------------------------------------------
def build_indicator_response(*args, **kwargs) -> dict[str, Any]:
    candles = list(kwargs.get("candles") or (args[2] if len(args) >= 3 else []))
    result = _ORIGINAL_BUILD_INDICATOR_RESPONSE(*args, **kwargs)
    if not candles:
        return result

    close_values = [_candle_value(candle, "close") for candle in candles]

    show_rsi = _safe_bool(kwargs.get("show_rsi"), True)
    show_vwap = _safe_bool(kwargs.get("show_vwap"), True)
    show_volume = _safe_bool(kwargs.get("show_volume"), True)

    rsi_period = _safe_int(kwargs.get("rsi_period"), 14)
    vwap_lookback = _safe_int(kwargs.get("vwap_lookback_candles"), 96)
    volume_period = _safe_int(kwargs.get("volume_period"), 20)

    rsi_color = str(kwargs.get("rsi_color", "#818cf8"))
    vwap_color = str(kwargs.get("vwap_color", "#14b8a6"))
    volume_color = str(kwargs.get("volume_color", "#94a3b8"))

    rsi_lookback_days = _safe_int(kwargs.get("rsi_lookback_days"), 0)
    vwap_lookback_days = _safe_int(kwargs.get("vwap_lookback_days"), 0)
    volume_lookback_days = _safe_int(kwargs.get("volume_lookback_days"), 0)

    if show_rsi:
        _append_line(result, "RSI", f"RSI {rsi_period}", rsi_color, "oscillator", candles, _rsi(close_values, rsi_period), rsi_lookback_days)
    if show_vwap:
        _append_line(result, "VWAP", f"VWAP {vwap_lookback}", vwap_color, "price", candles, _vwap(candles, vwap_lookback), vwap_lookback_days)
    if show_volume:
        _append_line(result, "VOLUME", f"Volume {volume_period}", volume_color, "volume", candles, _volume_values(candles), volume_lookback_days)

    settings = result.setdefault("settings", {})
    settings.update(
        {
            "show_rsi": bool(show_rsi),
            "show_vwap": bool(show_vwap),
            "show_volume": bool(show_volume),
            "rsi_period": int(rsi_period),
            "vwap_lookback_candles": int(vwap_lookback),
            "volume_period": int(volume_period),
            "rsi_color": rsi_color,
            "vwap_color": vwap_color,
            "volume_color": volume_color,
        }
    )
    return result


# --------------------------------------------------
# INSTALLATION
# --------------------------------------------------
def install() -> None:
    ind.build_indicator_response = build_indicator_response


def apply_indicator_display_enhancement_patch() -> None:
    install()
