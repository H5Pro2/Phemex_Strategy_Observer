# ============================================================
# workspace.py
# ============================================================

import csv
import os
from config import Config
from ph_ohlcv import fetch_ohlcv

WORKSPACE_PATH = str(getattr(Config, "CSV_OHLCV_PATH", "data/workspace.csv") or "data/workspace.csv")


# ============================================================
# SNAPSHOT MODE (BACKTEST / ALT)
# ============================================================
def build_and_save_workspace(exchange, symbol: str, timeframe: str, window_size: int) -> bool:

    raw = fetch_ohlcv(exchange, symbol, timeframe)

    if raw is None or not isinstance(raw, list):
        print("FETCH ERROR: raw is invalid")
        return False

    if len(raw) > 0:
        raw = raw[:-1]

    if len(raw) < window_size:
        return False

    raw = raw[-window_size:]

    os.makedirs(os.path.dirname(WORKSPACE_PATH), exist_ok=True)

    with open(WORKSPACE_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        w.writerow([
            "timestamp_ms",
            "symbol",
            "timeframe",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ])

        for ts, o, h, l, c, v in raw:
            w.writerow([
                int(ts),
                symbol,
                timeframe,
                float(o),
                float(h),
                float(l),
                float(c),
                float(v),
            ])

    return True


# ============================================================
# LIVE MODE (SEQUENZIELL · BACKEND-IDENTISCH)
# ============================================================

# ------------------------------------------------------------
# Initialisierung (einmalig)
# ------------------------------------------------------------
def init_workspace_live(symbol: str, timeframe: str, candles: list):

    os.makedirs(os.path.dirname(WORKSPACE_PATH), exist_ok=True)

    with open(WORKSPACE_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)

        w.writerow([
            "timestamp_ms",
            "symbol",
            "timeframe",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ])

        for ts, o, h, l, c, v in candles:
            w.writerow([
                int(ts),
                symbol,
                timeframe,
                float(o),
                float(h),
                float(l),
                float(c),
                float(v),
            ])


# ------------------------------------------------------------
# Append (jede neue geschlossene Kerze)
# ------------------------------------------------------------
def append_workspace_live(symbol: str, timeframe: str, candle):

    ts, o, h, l, c, v = candle

    with open(WORKSPACE_PATH, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            int(ts),
            symbol,
            timeframe,
            float(o),
            float(h),
            float(l),
            float(c),
            float(v),
        ])