from debug_reader import dbr_debug
from datetime import datetime
import csv

class ExitEngine:
    # ─────────────────────────────────────────────
    # Exit
    # ─────────────────────────────────────────────
    def process(self, window, position: dict, txt):

        if not position:
            return None

        side = str(position.get("side")).upper().strip()

        entry = float(position.get("entry", 0.0))
        tp = float(position.get("tp", 0.0))
        sl = float(position.get("sl", 0.0))

        entry_ts = position.get("entry_ts")

        meta = position.get("meta") or {}
        state_meta = meta.get("state") or {}

        energy = float(state_meta.get("energy", 0.0) or 0.0)

        if tp is None or sl is None or entry is None:
            return None

        if not isinstance(entry_ts, (int, float)):
            return None
        
        # --------------------------------------------------
        # TRADE EXIT DEBUG
        # --------------------------------------------------
        def trade_debug_exit(position, reason, pnl, time_str, txt):

            side = str(position.get("side")).upper().strip()

            entry = float(position.get("entry", 0.0))
            tp = float(position.get("tp", 0.0))
            sl = float(position.get("sl", 0.0))

            mfe = float(position.get("mfe", 0.0))
            mae = float(position.get("mae", 0.0))
            risk = float(position.get("risk", 0.0))

            meta = position.get("meta") or {}
            state_meta = meta.get("state") or {}
            focus_meta = meta.get("focus") or {}
            signature_meta = meta.get("state_signature") or {}
            signal_meta = meta.get("signal") or {}

            energy = float(state_meta.get("energy", 0.0) or 0.0)
            coherence = float(state_meta.get("coherence", 0.0) or 0.0)
            asymmetry = int(state_meta.get("asymmetry", 0) or 0)
            coh_zone = float(state_meta.get("coh_zone", 0.0) or 0.0)

            focus_point = float(focus_meta.get("focus_point", 0.0) or 0.0)
            focus_confidence = float(focus_meta.get("focus_confidence", 0.0) or 0.0)
            target_lock = float(focus_meta.get("target_lock", 0.0) or 0.0)
            target_drift = float(focus_meta.get("target_drift", 0.0) or 0.0)

            signature_key = str(signature_meta.get("signature_key", "-") or "-")

            signature_bias = float(signal_meta.get("signature_bias", 0.0) or 0.0)
            signature_block = bool(signal_meta.get("signature_block", False))
            signature_quality = float(signal_meta.get("signature_quality", 0.0) or 0.0)
            signature_distance = float(signal_meta.get("signature_distance", 0.0) or 0.0)
            context_cluster_id = str(signal_meta.get("context_cluster_id", "-") or "-")
            context_cluster_bias = float(signal_meta.get("context_cluster_bias", 0.0) or 0.0)
            context_cluster_quality = float(signal_meta.get("context_cluster_quality", 0.0) or 0.0)
            context_cluster_distance = float(signal_meta.get("context_cluster_distance", 0.0) or 0.0)
            context_cluster_block = bool(signal_meta.get("context_cluster_block", False))
            inhibition_level = float(signal_meta.get("inhibition_level", 0.0) or 0.0)
            habituation_level = float(signal_meta.get("habituation_level", 0.0) or 0.0)
            competition_bias = float(signal_meta.get("competition_bias", 0.0) or 0.0)
            observation_mode = bool(signal_meta.get("observation_mode", False))

            long_score = float(signal_meta.get("long_score", 0.0) or 0.0)
            short_score = float(signal_meta.get("short_score", 0.0) or 0.0)

            dbr_debug(
                f"EXIT {reason} | "
                f"time={time_str} "
                f"side={side} "
                f"entry={entry:.4f} "
                f"tp={tp:.4f} "
                f"sl={sl:.4f} "
                f"risk={risk:.4f} "
                f"mfe={mfe:.4f} "
                f"mae={mae:.4f} "
                f"energy={energy:.4f} "
                f"coherence={coherence:.4f} "
                f"asymmetry={asymmetry} "
                f"coh_zone={coh_zone:.4f} "
                f"focus_point={focus_point:.4f} "
                f"focus_confidence={focus_confidence:.4f} "
                f"target_lock={target_lock:.4f} "
                f"target_drift={target_drift:.4f} "
                f"signature_key={signature_key} "
                f"signature_bias={signature_bias:.4f} "
                f"signature_block={signature_block} "
                f"signature_quality={signature_quality:.4f} "
                f"signature_distance={signature_distance:.4f} "
                f"context_cluster_id={context_cluster_id} "
                f"context_cluster_bias={context_cluster_bias:.4f} "
                f"context_cluster_quality={context_cluster_quality:.4f} "
                f"context_cluster_distance={context_cluster_distance:.4f} "
                f"context_cluster_block={context_cluster_block} "
                f"inhibition_level={inhibition_level:.4f} "
                f"habituation_level={habituation_level:.4f} "
                f"competition_bias={competition_bias:.4f} "
                f"observation_mode={observation_mode} "
                f"long_score={long_score:.4f} "
                f"short_score={short_score:.4f} "
                f"pnl={pnl:.4f}",
                txt
            )
        # --------------------------------------------------
        # Sliding Hit Search ab entry_ts
        # --------------------------------------------------
        for c in window:

            ts = c.get("timestamp")
            if not isinstance(ts, (int, float)):
                continue

            if ts < entry_ts:
                continue

            high = c["high"]
            low = c["low"]
            close = c["close"]

            time_str = "N/A"
            if ts > 0:
                try:
                    time_str = datetime.fromtimestamp(ts / 1000).strftime("%d/%m/%Y %H:%M")
                except Exception:
                    time_str = "N/A"

            # ─────────────────────────────────────────────
            # LONG
            # ─────────────────────────────────────────────
            if side == "LONG":

                if low <= sl and high >= tp:
                    pnl = sl - entry
                    trade_debug_exit(
                        position,
                         "SL (BOTH HIT)",
                        pnl,
                        time_str,
                        txt                        
                    )
                    return {"reason": "sl_hit"}

                if low <= sl:
                    pnl = sl - entry
                    trade_debug_exit(
                        position,
                        "SL",
                        pnl,
                        time_str,
                        txt
                    )
                    return {"reason": "sl_hit"}

                if high >= tp:
                    pnl = tp - entry
                    trade_debug_exit(
                        position,
                        "TP",
                        pnl,
                        time_str,
                        txt
                    )
                    return {"reason": "tp_hit"}

            # ─────────────────────────────────────────────
            # SHORT
            # ─────────────────────────────────────────────
            if side == "SHORT":

                if high >= sl and low <= tp:
                    pnl = entry - sl
                    trade_debug_exit(
                        position,
                        "SL (BOTH HIT)",
                        pnl,
                        time_str,
                        txt
                    )
                    return {"reason": "sl_hit"}

                if high >= sl:
                    pnl = entry - sl
                    trade_debug_exit(
                        position,
                        "SL",
                        pnl,
                        time_str,
                        txt
                    )
                    return {"reason": "sl_hit"}

                if low <= tp:
                    pnl = entry - tp
                    trade_debug_exit(
                        position,
                        "TP",
                        pnl,
                        time_str,
                        txt
                    )
                    return {"reason": "tp_hit"}

        return None