# ==================================================
# trade_value_gate.py
# ==================================================
# CONFIG TRADE VALUE GATE
# ==================================================

from typing import Any


class TradeValueGate:

    # --------------------------------------------------
    # INIT
    # --------------------------------------------------
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    # --------------------------------------------------
    # VALUE CHECK
    # --------------------------------------------------
    def evaluate(self, entry_result: dict[str, Any]) -> dict[str, Any]:
        decision = entry_result.get("decision")
        entry = entry_result.get("entry_price")
        tp = entry_result.get("tp_price")
        sl = entry_result.get("sl_price")

        # --------------------------------------------------
        # Basisprüfung
        # --------------------------------------------------
        if decision not in ("LONG", "SHORT"):
            return {"trade_allowed": False, "reason": "invalid_side"}

        if entry is None or tp is None or sl is None:
            return {"trade_allowed": False, "reason": "missing_price"}

        entry = float(entry)
        tp = float(tp)
        sl = float(sl)
        if entry <= 0:
            return {"trade_allowed": False, "reason": "invalid_entry"}

        # --------------------------------------------------
        # Preisgeometrie & Risk / Reward
        # --------------------------------------------------
        if decision == "LONG":
            if not sl < entry < tp:
                return {"trade_allowed": False, "reason": "invalid_long_geometry"}
            risk = entry - sl
            reward = tp - entry
        else:
            if not tp < entry < sl:
                return {"trade_allowed": False, "reason": "invalid_short_geometry"}
            risk = sl - entry
            reward = entry - tp

        if risk <= 0 or reward <= 0:
            return {"trade_allowed": False, "reason": "invalid_risk_reward"}

        # --------------------------------------------------
        # MIN TP DISTANZ
        # --------------------------------------------------
        min_tp_fraction = float(self.config.get("min_tp_distance_fraction", 0.0))
        min_tp_distance = entry * min_tp_fraction

        if min_tp_fraction > 0 and reward < min_tp_distance:
            return {
                "trade_allowed": False,
                "reason": "reward_too_small",
                "reward": reward,
                "min_tp_distance": min_tp_distance,
                "min_tp_distance_fraction": min_tp_fraction,
            }

        # --------------------------------------------------
        # MAX SL DISTANZ
        # --------------------------------------------------
        symbol = entry_result.get("symbol")
        max_sl_by_symbol = self.config.get("max_sl_distance_fraction_by_symbol", {}) or {}
        symbol_max_sl = max_sl_by_symbol.get(symbol) if symbol and isinstance(max_sl_by_symbol, dict) else None
        max_sl_fraction = float(
            symbol_max_sl
            if symbol_max_sl is not None
            else self.config.get("max_sl_distance_fraction", 0.0)
        )
        max_sl_distance = entry * max_sl_fraction

        if max_sl_fraction > 0 and risk > max_sl_distance:
            return {
                "trade_allowed": False,
                "reason": "sl_distance_too_high",
                "risk": risk,
                "max_sl_distance": max_sl_distance,
                "max_sl_distance_fraction": max_sl_fraction,
            }

        # --------------------------------------------------
        # RR INFO
        # --------------------------------------------------
        rr = reward / risk
        min_rr = float(self.config.get("min_rr", 0.0))
        if min_rr > 0 and rr < min_rr:
            return {
                "trade_allowed": False,
                "reason": "rr_too_small",
                "rr": round(rr, 6),
                "min_rr": min_rr,
                "risk": risk,
                "reward": reward,
            }

        quantity = entry_result.get("planned_quantity_asset", entry_result.get("quantity"))
        notional = entry_result.get("planned_notional_usd", entry_result.get("notional"))
        quantity = float(quantity) if quantity is not None else None
        if (quantity is None or quantity <= 0) and notional is not None:
            quantity = float(notional) / entry
        if quantity is not None and quantity > 0:
            fee_rate = float(self.config.get("estimated_taker_fee_rate", 0.0006))
            min_profit_by_symbol = self.config.get("min_net_profit_fraction_by_symbol", {}) or {}
            symbol_min_profit = min_profit_by_symbol.get(symbol) if symbol and isinstance(min_profit_by_symbol, dict) else None
            min_net_profit_fraction = float(
                symbol_min_profit
                if symbol_min_profit is not None
                else self.config.get("min_net_profit_fraction", 0.001)
            )
            entry_notional = entry * quantity
            gross_profit_usd = reward * quantity
            estimated_fees_usd = (entry * quantity + tp * quantity) * fee_rate
            net_profit_usd = gross_profit_usd - estimated_fees_usd
            net_profit_fraction = net_profit_usd / entry_notional if entry_notional > 0 else 0.0
            min_net_profit_usd = entry_notional * min_net_profit_fraction
            if min_net_profit_fraction > 0 and net_profit_fraction < min_net_profit_fraction:
                return {
                    "trade_allowed": False,
                    "reason": "net_profit_too_small",
                    "gross_profit_usd": round(gross_profit_usd, 8),
                    "estimated_fees_usd": round(estimated_fees_usd, 8),
                    "net_profit_usd": round(net_profit_usd, 8),
                    "net_profit_fraction": round(net_profit_fraction, 8),
                    "min_net_profit_fraction": min_net_profit_fraction,
                    "min_net_profit_usd": round(min_net_profit_usd, 8),
                    "estimated_taker_fee_rate": fee_rate,
                    "planned_quantity_asset": quantity,
                    "entry_notional_usd": round(entry_notional, 8),
                }
        else:
            gross_profit_usd = None
            estimated_fees_usd = None
            net_profit_usd = None
            net_profit_fraction = None
            entry_notional = None

        # --------------------------------------------------
        # OK
        # --------------------------------------------------
        result = {
            "trade_allowed": True,
            "risk": risk,
            "reward": reward,
            "rr": rr,
            "risk_fraction": risk / entry,
            "reward_fraction": reward / entry,
        }
        if quantity is not None and quantity > 0:
            result.update(
                {
                    "gross_profit_usd": round(float(gross_profit_usd), 8),
                    "estimated_fees_usd": round(float(estimated_fees_usd), 8),
                    "net_profit_usd": round(float(net_profit_usd), 8),
                    "net_profit_fraction": round(float(net_profit_fraction), 8),
                    "min_net_profit_fraction": min_net_profit_fraction,
                    "min_net_profit_usd": round(float(entry_notional) * min_net_profit_fraction, 8),
                    "estimated_taker_fee_rate": float(self.config.get("estimated_taker_fee_rate", 0.0006)),
                }
            )
        return result
