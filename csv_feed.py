# ==================================================
# csv_feed.py
# ==================================================
# CSV Feed
# - liest OHLCV CSV mit Header
# - erwartet Spalten:
#   timestamp_ms, open, high, low, close, volume
# - robust gegen Header-Zeile
# - robust gegen BOM
# ==================================================

import csv
import time
from collections import deque
from typing import Iterator, List, Dict


class CSVFeed:

    # --------------------------------------------------
    def __init__(self, filepath: str):
        self.filepath = filepath

    # --------------------------------------------------
    # Einzelne Zeilen (Iterator)
    # --------------------------------------------------
    def rows(self, delay_seconds: float = 0.0) -> Iterator[Dict]:

        with open(self.filepath, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)

            required = {
                "timestamp_ms",
                "open",
                "high",
                "low",
                "close",
                "volume",
            }

            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError(
                    f"CSV Spalten stimmen nicht. Gefunden: {reader.fieldnames}"
                )

            for row in reader:
                try:
                    parsed = {
                        "timestamp": int(float(row["timestamp_ms"])),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                    }
                except (ValueError, TypeError):
                    # fehlerhafte Zeile überspringen
                    continue

                yield parsed

                if delay_seconds > 0:
                    time.sleep(delay_seconds)

    # --------------------------------------------------
    # Sliding Window
    # --------------------------------------------------
    def window(
        self,
        size: int,
        delay_seconds: float = 0.0
    ) -> Iterator[List[Dict]]:

        buffer = deque(maxlen=size)

        for row in self.rows(delay_seconds=delay_seconds):
            buffer.append(row)

            if len(buffer) == size:
                yield list(buffer)


# --------------------------------------------------
# Beispiel Nutzung
# --------------------------------------------------
if __name__ == "__main__":

    DATA_FILE = "data/5m_SOLUSDT.csv"

    feed = CSVFeed(DATA_FILE)

    print("Erste 3 Zeilen:")
    for i, row in enumerate(feed.rows()):
        print(row)
        if i >= 2:
            break

    print("\nWindow Beispiel (3 Bars):")
    for window in feed.window(3):
        print(window)
        break
