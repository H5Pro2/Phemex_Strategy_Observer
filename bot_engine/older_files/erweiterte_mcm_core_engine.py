"""
MCM Core Engine - Tension & Perception Core
=======================================

Verarbeitet Roh-Kerzen-Daten (OHLCV) in weiche, qualitative Zustandsgrößen
für das MCM-System (Wahrnehmung → felt_state / world_state).

Ziel: Keine harten Indikatoren, sondern eine "weiche" Marktwahrnehmung.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from dataclasses import dataclass


@dataclass
class TensionState:
    """Strukturierte Ausgabe der Tension-Berechnung"""
    energy: float                    # Intensität der Kerze(n)
    coherence: float                 # Richtung & Stärke [-1 bis +1]
    asymmetry: int                   # Vereinfachte Richtung (-1, 0, +1)
    coh_zone: float                  # Kategorisierte Zone (-2 bis +2)
    
    # Erweiterte Kontext-Werte
    volume_factor: float             # Normalisiertes Volumen
    relative_range: float            # Range im Verhältnis zum Durchschnitt
    momentum: float                  # Kurze Veränderung
    perceived_pressure: float        # Kombinierter "Marktdruck"
    stability: float                 # Stabilität der letzten Kerzen
    
    raw_candle: Optional[Dict] = None


class MCMCoreEngine:
    """Hauptklasse für die Kern-Verarbeitung von Kerzen-Daten"""

    def __init__(self, window: int = 20, vol_window: int = 50):
        self.window = window                    # Fenster für Durchschnittsberechnungen
        self.vol_window = vol_window            # Fenster für Volume-Normalisierung

    def compute_tension_from_ohlc(self, 
                                  candles: List[Dict[str, float]],
                                  ) -> TensionState:
        """
        Erweiterte Tension-Berechnung aus einer Liste von Kerzen.
        
        Parameters:
            candles: Liste von Dictionaries mit keys: 'open', 'high', 'low', 'close', 'volume'
                     Letzte Kerze = aktuellste
        
        Returns:
            TensionState mit weichen Wahrnehmungswerten
        """
        if len(candles) == 0:
            raise ValueError("Keine Kerzen übergeben")

        latest = candles[-1]
        o = latest['open']
        h = latest['high']
        l = latest['low']
        c = latest['close']
        v = latest.get('volume', 0.0)

        # 1. Basis-Werte (wie in Original, aber robuster)
        range_ = h - l if h > l else 0.000001
        body = c - o
        energy = (h - l) / range_ if range_ > 0 else 0.0                    # 0..1 (normalisiert)
        coherence = body / range_ if range_ > 0 else 0.0                    # -1 bis +1
        asymmetry = 1 if coherence > 0.2 else -1 if coherence < -0.2 else 0

        # Coh Zone (-2 bis +2)
        if coherence <= -0.7:
            coh_zone = -2.0
        elif coherence <= -0.3:
            coh_zone = -1.0
        elif coherence >= 0.7:
            coh_zone = 2.0
        elif coherence >= 0.3:
            coh_zone = 1.0
        else:
            coh_zone = 0.0

        # 2. Kontext-Werte (neu)
        # Relative Range (Vergleich mit den letzten N Kerzen)
        ranges = [candle['high'] - candle['low'] for candle in candles[-self.window:]]
        avg_range = np.mean(ranges) if ranges else range_
        relative_range = (h - l) / avg_range if avg_range > 0 else 1.0

        # Volume Factor
        volumes = [candle.get('volume', 0) for candle in candles[-self.vol_window:]]
        avg_volume = np.mean(volumes) if volumes else v
        volume_factor = v / avg_volume if avg_volume > 0 else 1.0
        volume_factor = min(volume_factor, 5.0)   # Begrenzen auf extreme Spikes

        # Momentum (kurzfristig)
        momentum = 0.0
        if len(candles) >= 2:
            prev_c = candles[-2]['close']
            momentum = (c - prev_c) / range_ if range_ > 0 else 0.0

        # Perceived Pressure (Kombination aus Energie, Richtung & Momentum)
        perceived_pressure = coherence * energy * (1 + momentum * 0.5)
        perceived_pressure = max(min(perceived_pressure, 2.0), -2.0)

        # Stability (wie "ruhig" waren die letzten 5 Kerzen)
        if len(candles) >= 5:
            recent_ranges = [c['high'] - c['low'] for c in candles[-5:]]
            stability = 1.0 - (np.std(recent_ranges) / (avg_range + 1e-8))
            stability = max(0.0, min(1.0, stability))
        else:
            stability = 0.8

        return TensionState(
            energy=round(energy, 4),
            coherence=round(coherence, 4),
            asymmetry=asymmetry,
            coh_zone=coh_zone,
            volume_factor=round(volume_factor, 3),
            relative_range=round(relative_range, 3),
            momentum=round(momentum, 4),
            perceived_pressure=round(perceived_pressure, 4),
            stability=round(stability, 3),
            raw_candle=latest
        )

    def compute_tension_batch(self, candles: List[Dict]) -> List[TensionState]:
        """Berechnet Tension für jede Kerze in der Liste (für Backtesting geeignet)"""
        results = []
        for i in range(1, len(candles) + 1):        # Mindestens 1 Kerze
            window = candles[:i]
            state = self.compute_tension_from_ohlc(window)
            results.append(state)
        return results


# ====================== Beispiel Nutzung ======================
if __name__ == "__main__":
    # Beispiel-Daten
    example_candles = [
        {"open": 100.0, "high": 102.5, "low": 99.8, "close": 101.2, "volume": 1200},
        {"open": 101.2, "high": 103.0, "low": 100.5, "close": 102.8, "volume": 1850},
        {"open": 102.8, "high": 104.1, "low": 101.9, "close": 103.5, "volume": 2450},
    ]

    engine = MCMCoreEngine(window=20, vol_window=50)
    tension = engine.compute_tension_from_ohlc(example_candles)

    print("=== MCM Tension State ===")
    print(f"Energy:              {tension.energy}")
    print(f"Coherence:           {tension.coherence}")
    print(f"Asymmetry:           {tension.asymmetry}")
    print(f"Coh Zone:            {tension.coh_zone}")
    print(f"Volume Factor:       {tension.volume_factor}")
    print(f"Relative Range:      {tension.relative_range}")
    print(f"Momentum:            {tension.momentum}")
    print(f"Perceived Pressure:  {tension.perceived_pressure}")
    print(f"Stability:           {tension.stability}")