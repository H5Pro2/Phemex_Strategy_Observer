# ============================================================
# debug_reader.py
# ============================================================
#   msg
#   Typ: beliebig → str(msg)
#   Bedeutung: zu schreibender Inhalt (eine Zeile)
#   path = "debug/debug.txt"
#   Typ: str
#   Bedeutung: Zieldatei
#   mode = "a"
#   Typ: str
#   "a" = anhängen
#   "w" = überschreiben
#   reset_on_start = True
#   Typ: bool
#   True = Datei einmalig beim Start löschen
#   False = Datei nie automatisch löschen
#   write_once = False
#   Typ: bool
#   True = immer mode="w" → nur eine Zeile, wird überschrieben
#   False = mode bleibt wie übergeben ("a" oder "w")
# ============================================================
import os
from config import Config
_RESET_DONE = set()
_DEBUG_COUNTERS = {}
# ─────────────────────────────────────────────
def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
# ─────────────────────────────────────────────
# ZENTRALES BACKEND
# ─────────────────────────────────────────────
def dbr_write(
    msg,
    path: str,
    mode: str = "a",
    reset_on_start: bool = False,
    write_once: bool = False,
):
    try:
        if msg is None:
            return

        s = str(msg)
        if not s:
            return

        _ensure_dir(path)

        if reset_on_start and path not in _RESET_DONE:
            if os.path.exists(path):
                os.remove(path)
            _RESET_DONE.add(path)

        if write_once:
            mode = "w"

        if mode == "a" and not write_once:
            every_n = max(1, int(getattr(Config, "DEBUG_WRITE_EVERY_N", 1) or 1))
            if every_n > 1:
                count = int(_DEBUG_COUNTERS.get(path, 0) or 0) + 1
                _DEBUG_COUNTERS[path] = count
                if (count % every_n) != 0:
                    return

        with open(path, mode, encoding="utf-8") as f:
            f.write(s + "\n")

    except Exception:
        pass

# ─────────────────────────────────────────────
# WRAPPER (API-KOMPATIBEL)
# ─────────────────────────────────────────────
def dbr_debug(msg,txt="debug.csv"):
    dbr_write(msg, os.path.join("debug", txt), "a", True, False)
# ─────────────────────────────────────────────
