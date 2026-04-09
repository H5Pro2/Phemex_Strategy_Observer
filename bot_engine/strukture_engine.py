"""
strukture_engine.py
-------------------
Soft-Perception Engine für Marktstruktur.

Wichtig:
- Kein hartes Entry-Gate
- Keine LONG/SHORT-Entscheidung
- Keine festen Handelsregeln

Diese Engine liefert nur Wahrnehmungs-Signale (structure_perception_state),
die später von den lernenden Schichten (felt/thought/meta) genutzt werden.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _get_float(candle: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(candle.get(key, default))
    except Exception:
        return float(default)


@dataclass
class StructureEngine:
    lookback: int = 48
    swing_size: int = 3
    zone_width_factor: float = 0.20

    # ------------------------------------------------------------------
    # Swing-Detektion als Wahrnehmung (keine Regel-Freigabe)
    # ------------------------------------------------------------------
    def _is_swing_high(self, candles: List[dict], idx: int) -> bool:
        center = _get_float(candles[idx], "high")
        for j in range(idx - self.swing_size, idx + self.swing_size + 1):
            if j == idx or j < 0 or j >= len(candles):
                continue
            if _get_float(candles[j], "high") >= center:
                return False
        return True

    def _is_swing_low(self, candles: List[dict], idx: int) -> bool:
        center = _get_float(candles[idx], "low")
        for j in range(idx - self.swing_size, idx + self.swing_size + 1):
            if j == idx or j < 0 or j >= len(candles):
                continue
            if _get_float(candles[j], "low") <= center:
                return False
        return True

    def _collect_swings(self, candles: List[dict]) -> Tuple[List[float], List[float]]:
        if not candles:
            return [], []

        start = max(0, len(candles) - max(2, int(self.lookback)))
        highs: List[float] = []
        lows: List[float] = []

        for i in range(start, len(candles)):
            if self._is_swing_high(candles, i):
                highs.append(_get_float(candles[i], "high"))
            if self._is_swing_low(candles, i):
                lows.append(_get_float(candles[i], "low"))
        return highs, lows

    # ------------------------------------------------------------------
    # Öffentliche API: reine Struktur-Wahrnehmung
    # ------------------------------------------------------------------
    def build_structure_perception_state(self, window: List[dict]) -> Dict[str, float]:
        if not window:
            return {
                "structure_seen": 0.0,
                "swing_high_strength": 0.0,
                "swing_low_strength": 0.0,
                "zone_proximity": 0.0,
                "structure_stability": 0.0,
                "structure_quality": 0.0,
                "stress_relief_potential": 0.0,
                "context_confidence": 0.0,
            }

        highs, lows = self._collect_swings(window)
        last = window[-1]
        close_price = _get_float(last, "close")

        if close_price <= 0.0 or not highs or not lows:
            return {
                "structure_seen": 0.0,
                "swing_high_strength": 0.0,
                "swing_low_strength": 0.0,
                "zone_proximity": 0.0,
                "structure_stability": 0.0,
                "structure_quality": 0.0,
                "stress_relief_potential": 0.0,
                "context_confidence": 0.0,
            }

        structure_high = max(highs)
        structure_low = min(lows)
        structure_range = max(1e-9, structure_high - structure_low)
        zone_halfwidth = max(1e-9, structure_range * max(0.05, float(self.zone_width_factor)))

        dist_to_low = abs(close_price - structure_low)
        dist_to_high = abs(close_price - structure_high)
        nearest_dist = min(dist_to_low, dist_to_high)

        # Nähe zu Strukturzonen (0..1), ohne harte Freigabe
        zone_proximity = _clip01(1.0 - (nearest_dist / (zone_halfwidth * 2.0)))

        # Stärke/Frequenz der Strukturpunkte (mehr bestätigte Swings -> stärker)
        swing_high_strength = _clip01(len(highs) / max(2.0, self.lookback / 6.0))
        swing_low_strength = _clip01(len(lows) / max(2.0, self.lookback / 6.0))

        # Stabilität: ausgewogene Swing-Verteilung + sinnvolle Range
        balance = 1.0 - abs(len(highs) - len(lows)) / max(1.0, float(len(highs) + len(lows)))
        range_ratio = structure_range / max(1e-9, close_price)
        range_stability = _clip01(1.0 - abs(range_ratio - 0.02) / 0.04)
        structure_stability = _clip01((balance * 0.55) + (range_stability * 0.45))

        # Gesamtqualität als weiche, lernbare Wahrnehmung
        structure_quality = _clip01(
            (zone_proximity * 0.34)
            + (swing_high_strength * 0.18)
            + (swing_low_strength * 0.18)
            + (structure_stability * 0.30)
        )

        # Hypothese: gute Strukturzonen entlasten Stress (nur Signal, keine Regel)
        stress_relief_potential = _clip01(
            (zone_proximity * 0.42) + (structure_stability * 0.38) + (structure_quality * 0.20)
        )

        # Kontextvertrauen als aggregierte Wahrnehmung
        context_confidence = _clip01(
            (structure_quality * 0.50) + (structure_stability * 0.25) + (zone_proximity * 0.25)
        )

        return {
            "structure_seen": 1.0,
            "structure_high": float(structure_high),
            "structure_low": float(structure_low),
            "structure_range": float(structure_range),
            "swing_high_strength": float(swing_high_strength),
            "swing_low_strength": float(swing_low_strength),
            "zone_proximity": float(zone_proximity),
            "structure_stability": float(structure_stability),
            "structure_quality": float(structure_quality),
            "stress_relief_potential": float(stress_relief_potential),
            "context_confidence": float(context_confidence),
        }

