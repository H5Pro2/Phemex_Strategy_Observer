import api
import threading
import time
from config import Config
import ph_ohlcv
import debug_reader as dbr
# --------------------------------------------------
_ACTIVE_ORDER_ID = None
_ACTIVE_SIDE = None
_ACTIVE_TP = None
_POSITION_OPEN = False
_LAST_SYNC_TS = None
_CONNECTION_OK = False
_BOOTSTRAPPED = False
_BOOTSTRAP_LOCK = threading.Lock()
_EXCHANGE = None
_SYMBOL = None
_ENTRY_REFERENCE = None
_ENTRY_DISTANCE = None
_RISK_REFERENCE = None
_ENTRY_VALIDITY_CENTER = None
_ENTRY_VALIDITY_LOWER = None
_ENTRY_VALIDITY_UPPER = None
# --------------------------------------------------
# CANCEL TRACKING
# --------------------------------------------------
_CANCEL_COUNT = 0
_CANCELLED_ORDER_IDS = set()
# --------------------------------------------------
# DEBUGGING
# --------------------------------------------------
def gate_debug(msg):
    dbr.dbr_debug(msg, "order_debug.csv")
# --------------------------------------------------
# ACTIVE CHECK - wird in rl_structure_bot.py genutz
# --------------------------------------------------
def is_order_active():
    global _ACTIVE_ORDER_ID, _POSITION_OPEN
    return (_ACTIVE_ORDER_ID is not None) or (_POSITION_OPEN is True)
# --------------------------------------------------
# EXCHANGE INIT / SAFE FETCH
# --------------------------------------------------
def _ensure_exchange():
    global _EXCHANGE, _SYMBOL

    if _SYMBOL is None:
        _SYMBOL = f"{Config.SYMBOL}:USDT"

    if _EXCHANGE is None:
        _EXCHANGE = ph_ohlcv.create_exchange(api.API_KEY, api.API_SECRET)

    return _EXCHANGE
# --------------------------------------------------
def _safe_fetch_open_orders(exchange):
    try:
        return exchange.fetch_open_orders(_SYMBOL)
    except Exception as e:
        gate_debug(f"❌ fetch_open_orders Fehler: {e}")
        return None
# --------------------------------------------------
def _safe_fetch_positions(exchange):
    # ccxt: nicht jede Börse unterstützt positions() gleich
    try:
        if hasattr(exchange, "fetch_positions"):
            return exchange.fetch_positions([_SYMBOL])
    except Exception as e:
        gate_debug(f"❌ fetch_positions Fehler: {e}")
        return None
    return None
# --------------------------------------------------
def _detect_open_position(positions):
    """
    Phemex Futures:
    Nur wenn contracts > 0 gilt Position als offen.
    Alles andere ignorieren.
    """
    if not positions:
        return False

    try:
        for p in positions:
            if not isinstance(p, dict):
                continue

            contracts = p.get("contracts")

            if contracts is None:
                continue

            try:
                if abs(float(contracts)) > 0.0:
                    return True
            except Exception:
                continue

    except Exception:
        return False

    return False
# --------------------------------------------------
def _sync_with_exchange(reason="startup"):
    global _ACTIVE_ORDER_ID, _ACTIVE_TP, _ACTIVE_SIDE, _POSITION_OPEN, _LAST_SYNC_TS, _CONNECTION_OK

    exchange = _ensure_exchange()

    #gate_debug("---------------------------------------")
    #gate_debug(f"🔄 SYNC START | reason={reason}")

    # 1) Positions prüfen (fail-safe)
    positions = _safe_fetch_positions(exchange)
    pos_open = _detect_open_position(positions)

    # POSITION_OPEN immer hart neu setzen (kein Sticky-Block mehr)
    if pos_open:
        _POSITION_OPEN = True
        gate_debug("⚠️ Sync: POSITION OFFEN erkannt → neue Orders gesperrt (failsafe)")
    else:
        if _POSITION_OPEN:
            gate_debug("🟢 Sync: vorher offene Position jetzt geschlossen → Freigabe")
        _POSITION_OPEN = False

    # 2) Open Orders prüfen
    open_orders = _safe_fetch_open_orders(exchange)
    if open_orders is None:
        _CONNECTION_OK = False
        gate_debug("❌ SYNC: open_orders nicht abrufbar → Verbindung OK? = False")
        gate_debug("---------------------------------------")
        return False

    _CONNECTION_OK = True

    # Wenn aktive Order-ID schon gesetzt ist, nur validieren
    if _ACTIVE_ORDER_ID is not None:
        exists = ph_ohlcv.check_order_id_exist(exchange, _SYMBOL, _ACTIVE_ORDER_ID)
        if exists:
            gate_debug(f"🟡 SYNC: aktive Order bestätigt | id={_ACTIVE_ORDER_ID}")
            _LAST_SYNC_TS = time.time()
            gate_debug("---------------------------------------")
            return True
        else:
            gate_debug(f"🟢 SYNC: aktive Order existiert nicht mehr → Freigabe | id={_ACTIVE_ORDER_ID}")
            _ACTIVE_ORDER_ID = None
            _ACTIVE_TP = None
            _ACTIVE_SIDE = None

    # Keine aktive Order: ggf. offene Orders übernehmen (defensiv: nur wenn eindeutig)
    if open_orders:
        if len(open_orders) == 1:
            o = open_orders[0]
            oid = o.get("id")
            side = str(o.get("side") or "").lower() or None
            _ACTIVE_ORDER_ID = oid
            _ACTIVE_SIDE = side
            _ACTIVE_TP = None  # TP unbekannt nach Restart
            gate_debug(f"🟡 SYNC: 1 offene Order übernommen | id={_ACTIVE_ORDER_ID} | side={_ACTIVE_SIDE}")
        else:
            gate_debug(f"⚠️ SYNC: {len(open_orders)} offene Orders gefunden → keine automatische Übernahme")
            # failsafe: wenn mehrere offene Orders existieren, blockieren wir neue Orders über _ACTIVE_ORDER_ID-Sentinel
            _ACTIVE_ORDER_ID = "MULTI_OPEN_ORDERS"
            _ACTIVE_SIDE = None
            _ACTIVE_TP = None
    #else:
        #gate_debug("🟢 SYNC: keine offenen Orders")

    _LAST_SYNC_TS = time.time()
    #gate_debug("---------------------------------------")
    return True
# --------------------------------------------------
def _bootstrap_once():
    global _BOOTSTRAPPED

    if _BOOTSTRAPPED:
        return

    with _BOOTSTRAP_LOCK:
        if _BOOTSTRAPPED:
            return
        try:
            _ensure_exchange()
            _sync_with_exchange(reason="bootstrap")
        except Exception as e:
            gate_debug(f"❌ BOOTSTRAP Fehler: {e}")
        _BOOTSTRAPPED = True
# --------------------------------------------------
# get_active_order_snapshot - wird in rl_structure_bot.py genutz
# - prüft, ob aktuell eine Order offen ist (über _ACTIVE_ORDER_ID oder _POSITION_OPEN) 
# # --------------------------------------------------       
def get_active_order_snapshot():
    global _ACTIVE_ORDER_ID, _ACTIVE_SIDE

    exchange = _ensure_exchange()
    open_orders = _safe_fetch_open_orders(exchange)

    if not open_orders:
        return None

    if len(open_orders) != 1:
        return None

    o = open_orders[0]
    info = o.get("info", {})

    try:
        # --------------------------------------------------
        # Exchange Timestamp (ms)
        # --------------------------------------------------
        order_ts = int(o.get("timestamp"))

        # --------------------------------------------------
        # Timeframe → ms berechnen
        # --------------------------------------------------
        tf = str(Config.TIMEFRAME).lower().strip()

        if tf.endswith("m"):
            tf_minutes = int(tf[:-1])
            timeframe_ms = tf_minutes * 60 * 1000
        elif tf.endswith("h"):
            tf_hours = int(tf[:-1])
            timeframe_ms = tf_hours * 60 * 60 * 1000
        else:
            timeframe_ms = 5 * 60 * 1000  # fallback 5m

        # --------------------------------------------------
        # Floor auf Candle-Open
        # --------------------------------------------------
        entry_ts = (order_ts // timeframe_ms) * timeframe_ms

        return {
            "id": o.get("id"),
            "side": str(o.get("side")).upper(),
            "entry": float(o.get("price")),
            "tp": float(info.get("takeProfitRp")) if info.get("takeProfitRp") else None,
            "sl": float(info.get("stopLossRp")) if info.get("stopLossRp") else None,
            "entry_ts": entry_ts,
        }

    except Exception:
        return None
# --------------------------------------------------
def mark_order_cancelled(order_id, cause: str = None):
    global _CANCEL_COUNT, _CANCELLED_ORDER_IDS

    if order_id is None:
        return

    _CANCEL_COUNT += 1
    _CANCELLED_ORDER_IDS.add(str(order_id))

    if cause:
        try:
            gate_debug(f"🟠 CANCEL_TRACK | id={order_id} | cause={cause}")
            gate_debug("---------------------------------------")
        except Exception:
            pass
# --------------------------------------------------
def consume_cancelled(order_id) -> bool:
    global _CANCELLED_ORDER_IDS

    if order_id is None:
        return False

    oid = str(order_id)
    if oid in _CANCELLED_ORDER_IDS:
        try:
            _CANCELLED_ORDER_IDS.remove(oid)
        except Exception:
            pass
        return True

    return False
# --------------------------------------------------
def get_cancel_count() -> int:
    return int(_CANCEL_COUNT or 0)
# --------------------------------------------------