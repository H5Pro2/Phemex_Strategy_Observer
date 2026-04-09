# ============================================================
# STRUCTURE ENTRY GATE
# ------------------------------------------------------------
# Ziel
#   Erkennung echter Marktstruktur
#   HH / HL / LL / LH
#   zusätzlich nur Kontext:
#       structure_break   (BOS / CHOCH)
#       structure_id      (Pattern-ID für Memory)
#       structure_strength
#       structure_age
#       swing_impulse
#       structure_stability
#
# Return:
#   structure_type
#   structure_break
#   structure_id
#   structure_strength
#   structure_age
#   swing_impulse
#   structure_stability
#
# Kein Entry-Preis
# Kein structure_range im Rückgabepfad
# ============================================================


class StructureEntryGate:

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------
    def __init__(
        self,
        lookback=20,
        swing_size=2,
    ):

        self.lookback = int(lookback)
        self.swing_size = int(swing_size)


    # --------------------------------------------------
    # SWING HIGH
    # --------------------------------------------------
    def _is_swing_high(self, window, i):

        center = window[i]["high"]

        for j in range(i - self.swing_size, i + self.swing_size + 1):

            if j == i:
                continue

            if j < 0 or j >= len(window):
                continue

            if window[j]["high"] >= center:
                return False

        return True


    # --------------------------------------------------
    # SWING LOW
    # --------------------------------------------------
    def _is_swing_low(self, window, i):

        center = window[i]["low"]

        for j in range(i - self.swing_size, i + self.swing_size + 1):

            if j == i:
                continue

            if j < 0 or j >= len(window):
                continue

            if window[j]["low"] <= center:
                return False

        return True


    # --------------------------------------------------
    # COLLECT SWINGS
    # --------------------------------------------------
    def _collect_swings(self, window):

        swings_high = []
        swings_low = []

        start = max(0, len(window) - self.lookback)

        for i in range(start, len(window)):

            if self._is_swing_high(window, i):
                swings_high.append((i, window[i]["high"]))

            if self._is_swing_low(window, i):
                swings_low.append((i, window[i]["low"]))

        return swings_high, swings_low


    # --------------------------------------------------
    # DETECT STRUCTURE TYPE
    # --------------------------------------------------
    def _detect_structure_type(self, swings_high, swings_low):

        structure_type = None

        if len(swings_high) >= 2:

            prev_high = swings_high[-2][1]
            last_high = swings_high[-1][1]

            if last_high > prev_high:
                structure_type = "HH"

            elif last_high < prev_high:
                structure_type = "LH"

        if len(swings_low) >= 2:

            prev_low = swings_low[-2][1]
            last_low = swings_low[-1][1]

            if last_low > prev_low:
                structure_type = "HL"

            elif last_low < prev_low:
                structure_type = "LL"

        return structure_type


    # --------------------------------------------------
    # STRUCTURE BREAK
    # --------------------------------------------------
    def _detect_structure_break(self, structure_type, prev_structure_type):

        if structure_type is None:
            return None

        if prev_structure_type is None:
            return None

        if structure_type == prev_structure_type:
            return "BOS"

        if (
            (prev_structure_type in ["HH", "HL"] and structure_type in ["LH", "LL"])
            or
            (prev_structure_type in ["LH", "LL"] and structure_type in ["HH", "HL"])
        ):
            return "CHOCH"

        return None


    # --------------------------------------------------
    # STRUCTURE ID
    # --------------------------------------------------
    def _build_structure_id(self, prev_structure_type, structure_type):

        if structure_type is None:
            return None

        if prev_structure_type is None:
            return structure_type

        return f"{prev_structure_type}->{structure_type}"


    # --------------------------------------------------
    # STRUCTURE AGE
    # --------------------------------------------------
    def _compute_structure_age(self, window, swing_index):

        if swing_index is None:
            return None

        return len(window) - swing_index


    # --------------------------------------------------
    # SWING IMPULSE
    # --------------------------------------------------
    def _compute_swing_impulse(self, window, swing_price):

        if swing_price is None:
            return None

        last_close = window[-1]["close"]

        return float(abs(last_close - swing_price))


    # --------------------------------------------------
    # STRUCTURE STRENGTH
    # --------------------------------------------------
    def _compute_structure_strength(self, swing_impulse, structure_range):

        if swing_impulse is None:
            return None

        if structure_range == 0:
            return None

        return float(swing_impulse / structure_range)


    # --------------------------------------------------
    # MAIN PROCESS
    # --------------------------------------------------
    def process(self, window, prev_structure_type=None):

        if not window:
            return None

        swings_high, swings_low = self._collect_swings(window)

        if len(swings_high) < 2 and len(swings_low) < 2:

            return {
                "structure_type": None,
                "structure_break": None,
                "structure_id": None,
                "structure_strength": None,
                "structure_age": None,
                "swing_impulse": None,
                "structure_stability": None,
                "swing_high": None,
                "swing_low": None,
            }

        structure_type = self._detect_structure_type(swings_high, swings_low)

        structure_break = self._detect_structure_break(
            structure_type,
            prev_structure_type,
        )

        structure_id = self._build_structure_id(
            prev_structure_type,
            structure_type,
        )

        last = window[-1]

        last_high_index = swings_high[-1][0] if swings_high else None
        last_low_index = swings_low[-1][0] if swings_low else None

        last_high = swings_high[-1][1] if swings_high else float(last["close"])
        last_low = swings_low[-1][1] if swings_low else float(last["close"])

        # --------------------------------------------------
        # STRUKTUR-RANGE NUR INTERN FÜR KONTEXTMETRIKEN
        # --------------------------------------------------
        structure_range = float(abs(last_high - last_low))

        swing_index = last_high_index if last_high_index is not None else last_low_index
        swing_price = last_high if swings_high else last_low

        structure_age = self._compute_structure_age(window, swing_index)

        swing_impulse = self._compute_swing_impulse(window, swing_price)

        structure_strength = self._compute_structure_strength(
            swing_impulse,
            structure_range,
        )

        # --------------------------------------------------
        # STRUCTURE STABILITY
        # --------------------------------------------------
        structure_stability = None

        if swing_impulse is not None and structure_range > 0:
            structure_stability = float(swing_impulse / structure_range)

        return {
            "structure_type": structure_type,
            "structure_break": structure_break,
            "structure_id": structure_id,
            "structure_strength": structure_strength,
            "structure_age": structure_age,
            "swing_impulse": swing_impulse,
            "structure_stability": structure_stability,
            "swing_high": float(last_high),
            "swing_low": float(last_low),
        }
