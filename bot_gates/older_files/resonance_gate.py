# ============================================================
# RESONANCE GATE
# ------------------------------------------------------------
# Nutzt TensionEncoder Werte:
#   energy
#   coherence
#   asymmetry
#
# Ziel:
#   echte Marktresonanz erkennen
#   Rauschen blockieren
#
# Prüfungen:
#   1) Resonance Strength
#   2) Phase Lock
#   3) Energy Gradient
#   4) Stability Window
# ============================================================

from collections import deque
from bot_engine.mcm_core_engine import compute_tension_from_ohlc
from debug_reader import dbr_debug

DEBUG = False

class ResonanceGate:

    # --------------------------------------------------
    def __init__(
        self,
        resonance_threshold=0.35,
        phase_tolerance=0.25,
        stability_bars=3,
    ):

        self.res_threshold = float(resonance_threshold)
        self.phase_tol = float(phase_tolerance)
        self.stability_bars = int(stability_bars)

        self.energy_hist = deque(maxlen=stability_bars)
        self.coh_hist = deque(maxlen=stability_bars)
        self.res_hist = deque(maxlen=stability_bars)

    # --------------------------------------------------
    # SINGLE BAR ENCODE
    # --------------------------------------------------
    def _encode(self, candle):

        o = float(candle["open"])
        h = float(candle["high"])
        l = float(candle["low"])
        c = float(candle["close"])

        energy, coherence, asym, coh_zone = compute_tension_from_ohlc(
            o,
            h,
            l,
            c,
        )
        return energy, coherence, asym, coh_zone

    # --------------------------------------------------
    # RESONANCE SCORE
    # --------------------------------------------------
    def _resonance(self, energy, coherence):
        return abs(energy) * abs(coherence)

    # --------------------------------------------------
    # PHASE LOCK
    # --------------------------------------------------
    def _phase_lock(self):

        if len(self.coh_hist) < 2:
            return False

        last = self.coh_hist[-1]
        prev = self.coh_hist[-2]

        return abs(last - prev) <= self.phase_tol

    # --------------------------------------------------
    # ENERGY GRADIENT
    # --------------------------------------------------
    def _energy_gradient(self, coherence):

        if len(self.energy_hist) < 2:
            return False

        if coherence > 0:
            return self.energy_hist[-1] >= self.energy_hist[-2]

        if coherence < 0:
            return self.energy_hist[-1] <= self.energy_hist[-2]

        return False

    # --------------------------------------------------
    # STABILITY CHECK
    # --------------------------------------------------
    def _stability(self):

        if len(self.res_hist) < self.stability_bars:
            return False

        count = 0

        for r in self.res_hist:
            if r >= self.res_threshold:
                count += 1

        return count >= max(2, self.stability_bars - 1)

    # --------------------------------------------------
    # MAIN PROCESS
    # --------------------------------------------------
    def process(self, window):

        if not window:
            return None

        candle = window[-1]

        energy, coherence, asym, coh_zone = self._encode(candle)

        resonance = self._resonance(energy, coherence)

        self.energy_hist.append(energy)
        self.coh_hist.append(coherence)
        self.res_hist.append(resonance)

        phase_ok = self._phase_lock()
        grad_ok = self._energy_gradient(coherence)
        stable_ok = self._stability()

        # --------------------------------------------------
        # RESONANCE ALLOW DECISION
        # --------------------------------------------------
        # allow = phase_ok and grad_ok and stable_ok
        strong_resonance = resonance >= 1.0

        allow = (
            (phase_ok and grad_ok and stable_ok)
            or strong_resonance
        )

        side = None
        
        if DEBUG:
            dbr_debug(f"energy: {energy} | coherence: {coherence} | asym: {asym} | coh_zone: {coh_zone}","tension_debug.txt")
            dbr_debug(f"resonance: {resonance} | phase_ok: {phase_ok} | grad_ok: {grad_ok} | stable_ok: {stable_ok}","resonance_debug.txt")

        return {            
            "allow": bool(allow),
            "side": side,
            "energy": float(energy),
            "coherence": float(coherence),
            "asymmetry": int(asym),
            "coh_zone": coh_zone,
            "resonance": float(resonance),
            "phase_lock": bool(phase_ok),
            "energy_gradient": bool(grad_ok),
            "stability": bool(stable_ok),
        }
