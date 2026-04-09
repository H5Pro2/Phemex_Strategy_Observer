import math


# --------------------------------------------------
# HELPERS
# --------------------------------------------------
def _clip(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


# --------------------------------------------------
def _coh_zone_from_value(coherence: float) -> float:
    if coherence < -0.6:
        return -2.0
    if coherence < -0.2:
        return -1.0
    if coherence > 0.6:
        return 2.0
    if coherence > 0.2:
        return 1.0
    return 0.0


# --------------------------------------------------
def _candle_span(candle: dict) -> float:
    high = float((candle or {}).get("high", 0.0) or 0.0)
    low = float((candle or {}).get("low", high) or high)
    return max(high - low, 1e-9)


# --------------------------------------------------
def _candle_coherence(candle: dict) -> float:
    open_price = float((candle or {}).get("open", 0.0) or 0.0)
    close_price = float((candle or {}).get("close", open_price) or open_price)
    span = _candle_span(candle)
    return _clip((close_price - open_price) / span, -1.0, 1.0)


# --------------------------------------------------
def compute_tension_from_ohlc(
    o_: float,
    h_: float,
    l_: float,
    c_: float,
    v_: float | None = None,
):
    """
    returns:
        energy (float)
        coherence (float) ∈ [-1, +1]
        asymmetry (int) ∈ {-1,0,+1}
        coh_zone: G1, G2, G3, G4, CENTER
    """

    span = max(h_ - l_, 1e-9)
    body = c_ - o_
    body_ratio = _clip(abs(body) / span, 0.0, 1.0)
    close_position = _clip((((c_ - l_) / span) * 2.0) - 1.0, -1.0, 1.0)
    upper_wick = max(0.0, h_ - max(o_, c_))
    lower_wick = max(0.0, min(o_, c_) - l_)
    wick_imbalance = _clip((lower_wick - upper_wick) / span, -1.0, 1.0)

    coherence = _clip(((body / span) * 0.72) + (close_position * 0.28), -1.0, 1.0)

    midpoint = (h_ + l_) / 2.0
    center_deviation = (
        abs(o_ - midpoint)
        + abs(c_ - midpoint)
        + abs(h_ - midpoint)
        + abs(l_ - midpoint)
    ) / (span * 2.0)
    range_pressure = _clip((span / max(abs(c_), 1e-9)) * 120.0, 0.0, 1.0)

    volume_factor = 1.0
    if v_ is not None:
        try:
            volume_factor += min(0.22, math.log1p(max(float(v_), 0.0)) / 18.0)
        except Exception:
            volume_factor = 1.0

    energy = (
        (center_deviation * 0.46)
        + (body_ratio * 0.34)
        + (abs(close_position) * 0.14)
        + (abs(wick_imbalance) * 0.06)
        + (range_pressure * 0.18)
    ) * volume_factor

    if coherence > 0:
        asymmetry = 1
    elif coherence < 0:
        asymmetry = -1
    else:
        asymmetry = 0

    coh_zone = _coh_zone_from_value(coherence)
    return float(energy), float(coherence), int(asymmetry), float(coh_zone)
# ------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------
def build_tension_state_from_window(window: list[dict]) -> dict:

    if not window:
        return {
            "energy": 0.0,
            "coherence": 0.0,
            "asymmetry": 0,
            "coh_zone": 0.0,
            "relative_range": 0.0,
            "momentum": 0.0,
            "stability": 0.0,
            "perceived_pressure": 0.0,
            "volume_pressure": 0.0,
        }

    candles = [dict(c or {}) for c in list(window or []) if isinstance(c, dict)]
    if not candles:
        return {
            "energy": 0.0,
            "coherence": 0.0,
            "asymmetry": 0,
            "coh_zone": 0.0,
            "relative_range": 0.0,
            "momentum": 0.0,
            "stability": 0.0,
            "perceived_pressure": 0.0,
            "volume_pressure": 0.0,
        }

    tail = candles[-8:]
    last = tail[-1]
    prev = tail[-2] if len(tail) > 1 else tail[-1]

    last_open = float(last.get("open", 0.0) or 0.0)
    last_high = float(last.get("high", last_open) or last_open)
    last_low = float(last.get("low", last_open) or last_open)
    last_close = float(last.get("close", last_open) or last_open)
    last_volume = float(last.get("volume", 0.0) or 0.0)
    prev_close = float(prev.get("close", last_close) or last_close)

    energy, coherence, asymmetry, coh_zone = compute_tension_from_ohlc(
        last_open,
        last_high,
        last_low,
        last_close,
        last_volume,
    )

    spans = [_candle_span(candle) for candle in tail]
    span_mean = sum(spans) / max(1, len(spans))
    last_span = spans[-1]

    relative_range_raw = last_span / max(span_mean, 1e-9)
    relative_range = _clip(relative_range_raw / 2.0, 0.0, 1.5)

    momentum_denominator = max(span_mean, last_close * 0.0012, 1e-9)
    momentum = _clip((last_close - prev_close) / momentum_denominator, -1.0, 1.0)

    coherences = [_candle_coherence(candle) for candle in tail]
    coherence_mean = sum(coherences) / max(1, len(coherences))
    coherence_dispersion = sum(abs(value - coherence_mean) for value in coherences) / max(1, len(coherences))
    range_dispersion = sum(abs((span / max(span_mean, 1e-9)) - 1.0) for span in spans) / max(1, len(spans))
    stability = _clip(1.0 - (coherence_dispersion * 0.62) - (range_dispersion * 0.28), 0.0, 1.0)

    volumes = [max(0.0, float((candle or {}).get("volume", 0.0) or 0.0)) for candle in tail]
    volume_mean = sum(volumes) / max(1, len(volumes))
    volume_pressure = _clip((last_volume / max(volume_mean, 1e-9)) - 1.0, -1.0, 1.0)

    perceived_pressure = _clip(
        (abs(momentum) * 0.34)
        + (max(0.0, relative_range_raw - 1.0) * 0.24)
        + (max(0.0, energy - 1.0) * 0.18)
        + (abs(volume_pressure) * 0.14)
        + ((1.0 - stability) * 0.18),
        0.0,
        1.0,
    )

    return {
        "energy": float(energy),
        "coherence": float(coherence),
        "asymmetry": int(asymmetry),
        "coh_zone": float(coh_zone),
        "relative_range": float(relative_range),
        "momentum": float(momentum),
        "stability": float(stability),
        "perceived_pressure": float(perceived_pressure),
        "volume_pressure": float(volume_pressure),
    }

def build_visual_market_state(window: list[dict]) -> dict:

    if not window:
        return {
            "spatial_bias": 0.0,
            "directional_bias": 0.0,
            "range_position": 0.0,
            "range_width": 0.0,
            "short_impulse": 0.0,
            "mid_impulse": 0.0,
            "compression": 0.0,
            "expansion": 0.0,
            "body_pressure": 0.0,
            "wick_pressure": 0.0,
            "volume_bias": 0.0,
            "market_balance": 0.0,
            "breakout_tension": 0.0,
            "visual_coherence": 0.0,
        }

    candles = [dict(c or {}) for c in list(window or []) if isinstance(c, dict)]
    if not candles:
        return {
            "spatial_bias": 0.0,
            "directional_bias": 0.0,
            "range_position": 0.0,
            "range_width": 0.0,
            "short_impulse": 0.0,
            "mid_impulse": 0.0,
            "compression": 0.0,
            "expansion": 0.0,
            "body_pressure": 0.0,
            "wick_pressure": 0.0,
            "volume_bias": 0.0,
            "market_balance": 0.0,
            "breakout_tension": 0.0,
            "visual_coherence": 0.0,
        }

    tail_short = candles[-8:]
    tail_mid = candles[-21:]
    last = tail_short[-1]
    prev = tail_short[-2] if len(tail_short) > 1 else tail_short[-1]

    last_open = float(last.get("open", 0.0) or 0.0)
    last_high = float(last.get("high", last_open) or last_open)
    last_low = float(last.get("low", last_open) or last_open)
    last_close = float(last.get("close", last_open) or last_open)
    last_volume = max(0.0, float(last.get("volume", 0.0) or 0.0))
    prev_close = float(prev.get("close", last_close) or last_close)

    short_spans = [_candle_span(candle) for candle in tail_short]
    mid_spans = [_candle_span(candle) for candle in tail_mid]
    short_span_mean = sum(short_spans) / max(1, len(short_spans))
    mid_span_mean = sum(mid_spans) / max(1, len(mid_spans))
    last_span = short_spans[-1]

    short_first_close = float((tail_short[0] or {}).get("close", last_close) or last_close)
    mid_first_close = float((tail_mid[0] or {}).get("close", last_close) or last_close)

    short_impulse = _clip(
        (last_close - short_first_close) / max(short_span_mean * 3.0, last_close * 0.0012, 1e-9),
        -1.0,
        1.0,
    )
    mid_impulse = _clip(
        (last_close - mid_first_close) / max(mid_span_mean * 8.0, last_close * 0.0020, 1e-9),
        -1.0,
        1.0,
    )

    mid_high = max(float((candle or {}).get("high", last_close) or last_close) for candle in tail_mid)
    mid_low = min(float((candle or {}).get("low", last_close) or last_close) for candle in tail_mid)
    mid_range = max(mid_high - mid_low, 1e-9)

    range_position = _clip((((last_close - mid_low) / mid_range) * 2.0) - 1.0, -1.0, 1.0)
    range_width = _clip(mid_range / max(last_close * 0.06, 1e-9), 0.0, 1.0)

    compression = _clip(1.0 - (last_span / max(short_span_mean, 1e-9)), 0.0, 1.0)
    expansion = _clip((last_span / max(short_span_mean, 1e-9)) - 1.0, 0.0, 1.0)

    body_pressure = _clip(abs(last_close - last_open) / max(last_span, 1e-9), 0.0, 1.0)
    upper_wick = max(0.0, last_high - max(last_open, last_close))
    lower_wick = max(0.0, min(last_open, last_close) - last_low)
    wick_pressure = _clip((upper_wick + lower_wick) / max(last_span, 1e-9), 0.0, 1.0)

    short_volumes = [max(0.0, float((candle or {}).get("volume", 0.0) or 0.0)) for candle in tail_short]
    short_volume_mean = sum(short_volumes) / max(1, len(short_volumes))
    volume_bias = _clip((last_volume / max(short_volume_mean, 1e-9)) - 1.0, -1.0, 1.0)

    directional_bias = _clip((short_impulse * 0.58) + (mid_impulse * 0.42), -1.0, 1.0)
    spatial_bias = _clip((range_position * 0.62) + (directional_bias * 0.38), -1.0, 1.0)
    breakout_tension = _clip(
        (expansion * 0.34)
        + (body_pressure * 0.22)
        + (abs(volume_bias) * 0.16)
        + (max(0.0, abs(range_position) - 0.55) * 0.22)
        + (abs(last_close - prev_close) / max(short_span_mean * 1.35, 1e-9) * 0.16),
        0.0,
        1.0,
    )
    market_balance = _clip(
        1.0
        - (abs(short_impulse - mid_impulse) * 0.46)
        - (expansion * 0.18)
        - (max(0.0, abs(range_position) - 0.35) * 0.24),
        0.0,
        1.0,
    )
    visual_coherence = _clip(
        (market_balance * 0.42)
        + ((1.0 - wick_pressure) * 0.18)
        + ((1.0 - min(1.0, abs(volume_bias))) * 0.12)
        + (max(0.0, 1.0 - abs(short_impulse - mid_impulse)) * 0.28),
        0.0,
        1.0,
    )

    return {
        "spatial_bias": float(spatial_bias),
        "directional_bias": float(directional_bias),
        "range_position": float(range_position),
        "range_width": float(range_width),
        "short_impulse": float(short_impulse),
        "mid_impulse": float(mid_impulse),
        "compression": float(compression),
        "expansion": float(expansion),
        "body_pressure": float(body_pressure),
        "wick_pressure": float(wick_pressure),
        "volume_bias": float(volume_bias),
        "market_balance": float(market_balance),
        "breakout_tension": float(breakout_tension),
        "visual_coherence": float(visual_coherence),
    }


