# ==================================================
# trade_value_gate.py
# ==================================================
# MINIMAL TRADE VALUE GATE
#
# Prüft ausschließlich:
# 1) Preisgeometrie von Entry / SL / TP korrekt
# 2) Risk <= MAX_SL_DISTANCE
# 3) RR >= MIN_RR oder min_rr_override
# 4) TP-Distanz >= Entry * MIN_TP_DISTANCE
#
# Keine Richtungsentscheidung
# Keine Marktstrukturprüfung
# Keine TP/SL Berechnung
# ==================================================

from typing import Dict, Any
from config import Config


class TradeValueGate:

    # --------------------------------------------------
    # VALUE CHECK
    # --------------------------------------------------
    def evaluate(self, entry_result: Dict[str, Any]) -> Dict[str, Any]:

        decision = entry_result.get("decision")
        entry = entry_result.get("entry_price")
        tp = entry_result.get("tp_price")
        sl = entry_result.get("sl_price")

        # --------------------------------------------------
        # Basisprüfung
        # --------------------------------------------------
        if decision not in ("LONG", "SHORT"):
            return {"trade_allowed": False}

        if entry is None or tp is None or sl is None:
            return {"trade_allowed": False}

        entry = float(entry)
        tp = float(tp)
        sl = float(sl)
        min_rr_override = entry_result.get("min_rr_override")

        if entry <= 0:
            return {"trade_allowed": False}

        # --------------------------------------------------
        # Preisgeometrie & Risk / Reward
        # --------------------------------------------------
      
        if decision == "LONG":

            if not sl < entry:
                return {"trade_allowed": False}

            risk = entry - sl
            reward = tp - entry

        else:  # SHORT

            if not entry < sl:
                return {"trade_allowed": False}

            risk = sl - entry
            reward = entry - tp

        if risk <= 0 or reward <= 0:
            return {"trade_allowed": False}
   
        # --------------------------------------------------
        # ABSOLUTE MOVE FILTER (HARTE MARKTBEWEGUNG)
        # minimale tp zu entry distanz, harte regel und ein zu kleinen tp weg zu filtern
        # --------------------------------------------------
        min_move = entry * float(getattr(Config, "MIN_TP_DISTANCE", 0.008))

        if reward < min_move:
            return {"trade_allowed": False, "reason": "reward_too_small"}
        
        # --------------------------------------------------
        # MAX SL DISTANZ Schutz Absicherung das der SL nicht zu groß werden kann
        # --------------------------------------------------
        max_sl_pct = float(getattr(Config, "MAX_SL_DISTANCE", 0.0))

        if max_sl_pct > 0:
            max_sl_distance = entry * max_sl_pct

            if risk > max_sl_distance:
                return {
                    "trade_allowed": False,
                    "reason": "sl_distance_too_high",
                    "risk": risk,
                    "max_sl_distance": max_sl_distance,
                }
        
        # --------------------------------------------------
        # RR MINIMUM
        # --------------------------------------------------
        rr = reward / risk
        min_rr = float(min_rr_override) if min_rr_override is not None else float(getattr(Config, "MIN_RR", 2.0))

        if min_rr > 0:
            if rr < min_rr:
                return {
                    "trade_allowed": False,
                    "reason": "rr_too_low",
                    "rr": rr,
                    "min_rr": min_rr,
                }

        # --------------------------------------------------
        # OK
        # --------------------------------------------------
        return {
            "trade_allowed": True,
            "risk": risk,
            "reward": reward,
            "rr": rr,
        }