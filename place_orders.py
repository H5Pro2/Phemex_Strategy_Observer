# ==================================================
# place_orders.py
# MINIMAL VERSION – MIT ORDER-ID MONITOR THREAD
# --------------------------------------------------
# Funktion der _order_monitor_loop:
#   - Existenzprüfung aktiver Orders
#   - Marktpreisprüfung
#   - Missed-TP-Erkennung
#   - Periodischer Restart-/Idle-Sync
#   - Reconnect-Erkennung und automatischer Re-Sync
#   - Positionsprüfung (Failsafe bei offener Position)
#   - Sentinel-Handling bei mehreren offenen Orders
#   - Alles im selben 10-Sekunden-Zyklus als eigener Thread
#   - Erweiterte Infrastruktur ohne Änderung der Ordersetz-Mechanik
# --------------------------------------------------
# Aktueller Stand:
#   Monitor-Thread startet beim Modul-Import.
#   Beim ersten Lauf erfolgt Bootstrap + Restart-Sync.
#
#   Monitor prüft:
#       - Order-Existenz
#       - Missed-TP
#       - Periodischen Exchange-Sync (auch ohne aktive Order)
#       - Verbindungsstatus (Reconnect-Handling)
#       - Offene Positionen (Failsafe-Block)
#
#   Bei PC-/Bot-Neustart:
#       - Exchange wird initialisiert
#       - Offene Orders werden geprüft und ggf. übernommen
#       - Offene Positionen werden erkannt und blockieren neue Orders
#       - Keine blinde Löschung oder Übernahme
#
#   Wenn Verbindung verloren geht:
#       - Fehler wird erkannt
#       - Trading pausiert implizit (Failsafe)
#       - Nach Reconnect erfolgt automatischer Full-Sync
# ==================================================
import api
import threading
import time
from config import Config
import ph_ohlcv
import debug_reader as dbr
from datetime import datetime
import place_orders_funktions as of
# --------------------------------------------------
# MODULE STATE (Backwards-Compat Imports)
# --------------------------------------------------
_SYMBOL = None
_MONITOR_THREAD = None
_MONITOR_LOCK = threading.Lock()

# --------------------------------------------------
# DEBUGGING
# --------------------------------------------------
def gate_debug(msg):
    dbr.dbr_debug(msg, "order_debug.csv")

# --------------------------------------------------
# CONTEXT (zustandsbasierte Monitor-Referenz)
# --------------------------------------------------
def set_context(
    exchange=None,
    symbol=None,
    timeframe=None,
    get_sufficient_balance=None,
    get_account_value=None,
    entry_reference=None,
    entry_distance=None,
    risk_reference=None,
    entry_validity_band=None,
):
    try:
        if exchange is not None:
            of._EXCHANGE = exchange
    except Exception:
        pass

    try:
        if symbol is not None:
            symbol_value = str(symbol)
            if ':USDT' not in symbol_value:
                symbol_value = f"{symbol_value}:USDT"
            of._SYMBOL = symbol_value
    except Exception:
        pass

    try:
        of._ENTRY_REFERENCE = float(entry_reference) if entry_reference is not None else None
    except Exception:
        of._ENTRY_REFERENCE = None

    try:
        of._ENTRY_DISTANCE = float(entry_distance) if entry_distance is not None else None
    except Exception:
        of._ENTRY_DISTANCE = None

    try:
        of._RISK_REFERENCE = float(risk_reference) if risk_reference is not None else None
    except Exception:
        of._RISK_REFERENCE = None

    band = dict(entry_validity_band or {})

    try:
        of._ENTRY_VALIDITY_CENTER = float(band.get("center")) if band.get("center") is not None else None
    except Exception:
        of._ENTRY_VALIDITY_CENTER = None

    try:
        of._ENTRY_VALIDITY_LOWER = float(band.get("lower")) if band.get("lower") is not None else None
    except Exception:
        of._ENTRY_VALIDITY_LOWER = None

    try:
        of._ENTRY_VALIDITY_UPPER = float(band.get("upper")) if band.get("upper") is not None else None
    except Exception:
        of._ENTRY_VALIDITY_UPPER = None

# --------------------------------------------------
# ACTIVE CHECK / SNAPSHOT (API)
# --------------------------------------------------
def is_order_active():
    return of.is_order_active()

def get_active_order_snapshot():
    return of.get_active_order_snapshot()

# --------------------------------------------------
# CANCEL TRACKING (API)
# --------------------------------------------------
def consume_cancelled(order_id) -> bool:
    return of.consume_cancelled(order_id)

def get_cancel_count() -> int:
    return of.get_cancel_count()
# --------------------------------------------------
def ensure_order_monitor_started():
    global _MONITOR_THREAD

    if str(getattr(Config, "MODE", "LIVE")).upper() != "LIVE":
        return None

    if _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive():
        return _MONITOR_THREAD

    with _MONITOR_LOCK:
        if _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive():
            return _MONITOR_THREAD

        _MONITOR_THREAD = threading.Thread(
            target=_order_monitor_loop,
            daemon=True,
        )
        _MONITOR_THREAD.start()

    return _MONITOR_THREAD
# --------------------------------------------------
# CANCEL ORDER BY ID
# --------------------------------------------------
def cancel_order_by_id(order_id, cause: str = None):
    global _SYMBOL

    if order_id is None:
        gate_debug("❌ cancel_order_by_id: keine Order-ID übergeben")
        return False

    try:
        exchange = of._ensure_exchange()
        _SYMBOL = of._SYMBOL

        if exchange is None or _SYMBOL is None:
            gate_debug("❌ cancel_order_by_id: Exchange oder Symbol nicht gesetzt")
            return False

        gate_debug(f"🗑️ Versuche Order zu canceln | id={order_id}")

        result = exchange.cancel_order(order_id, _SYMBOL)

        gate_debug(f"✅ Order gecancelt | id={order_id}")
        gate_debug("---------------------------------------")

        if str(of._ACTIVE_ORDER_ID) == str(order_id):
            of._ACTIVE_ORDER_ID = None
            of._ACTIVE_TP = None
            of._ACTIVE_SIDE = None
            set_context()

        # Cancel Tracking
        of.mark_order_cancelled(order_id, cause=cause)

        return result

    except Exception as e:
        gate_debug(f"❌ cancel_order_by_id ERROR: {e}")
        return False 

# --------------------------------------------------
# ORDER MONITOR LOOP (läuft im Hintergrund)
# --------------------------------------------------
def _order_monitor_loop():

    of._bootstrap_once()

    while True:
        try:
            time.sleep(10)

            exchange = of._ensure_exchange()
            if exchange is None:
                continue

            if not of.is_order_active():
                if (time.time() - float(of._LAST_SYNC_TS or 0.0)) >= 60.0:
                    of._sync_with_exchange(reason="periodic_idle_sync")
                continue

            if str(of._ACTIVE_ORDER_ID) == "MULTI_OPEN_ORDERS":
                gate_debug("⚠️ MULTI_OPEN_ORDERS aktiv → blockiert bis manuell geklärt")
                gate_debug("---------------------------------------")
                continue

            exists = ph_ohlcv.check_order_id_exist(
                exchange,
                of._SYMBOL,
                of._ACTIVE_ORDER_ID,
            )

            if not exists:
                gate_debug(f"🟢 Order {of._ACTIVE_ORDER_ID} ist NICHT mehr aktiv → Freigabe")
                gate_debug("---------------------------------------")
                of._ACTIVE_ORDER_ID = None
                of._ACTIVE_TP = None
                of._ACTIVE_SIDE = None
                set_context()
                of._sync_with_exchange(reason="order_disappeared_sync")
                continue

            price_data = ph_ohlcv.get_current_price(
                exchange,
                Config.SYMBOL,
            )

            if not price_data:
                continue

            current_price = float(price_data.get("price"))
            tp = of._ACTIVE_TP
            side = of._ACTIVE_SIDE

            if tp is None or side is None:
                gate_debug(f"🟡 Order {of._ACTIVE_ORDER_ID} aktiv | TP/Side unbekannt → nur Existenzprüfung")
                gate_debug("---------------------------------------")
                continue

            # --------------------------------------------------
            # MARKET SHIFT DETECTION
            # --------------------------------------------------
            try:

                entry_reference = float(getattr(of, "_ENTRY_REFERENCE", 0.0) or 0.0)
                entry_distance = float(getattr(of, "_ENTRY_DISTANCE", 0.0) or 0.0)
                risk_reference = float(getattr(of, "_RISK_REFERENCE", 0.0) or 0.0)
                entry_validity_lower = getattr(of, "_ENTRY_VALIDITY_LOWER", None)
                entry_validity_upper = getattr(of, "_ENTRY_VALIDITY_UPPER", None)

                if entry_validity_lower is not None and entry_validity_upper is not None:

                    validity_lower = float(entry_validity_lower)
                    validity_upper = float(entry_validity_upper)

                    if side == "buy" and current_price > validity_upper:

                        gate_debug("❌ MARKET SHIFT → LONG validity band broken")
                        cancel_order_by_id(of._ACTIVE_ORDER_ID, cause="market_shift")
                        continue

                    if side == "sell" and current_price < validity_lower:

                        gate_debug("❌ MARKET SHIFT → SHORT validity band broken")
                        cancel_order_by_id(of._ACTIVE_ORDER_ID, cause="market_shift")
                        continue

                cancel_band = 0.0

                if risk_reference > 0.0:
                    cancel_band = risk_reference

                if entry_distance > 0.0 and risk_reference > 0.0:
                    cancel_band = max(cancel_band, entry_distance * risk_reference)

                if entry_reference > 0.0 and cancel_band > 0.0:

                    if side == "buy" and current_price > (entry_reference + cancel_band):

                        gate_debug("❌ MARKET SHIFT → LONG invalid")
                        cancel_order_by_id(of._ACTIVE_ORDER_ID, cause="market_shift")
                        continue

                    if side == "sell" and current_price < (entry_reference - cancel_band):

                        gate_debug("❌ MARKET SHIFT → SHORT invalid")
                        cancel_order_by_id(of._ACTIVE_ORDER_ID, cause="market_shift")
                        continue

            except Exception:
                pass

            # --------------------------------------------------
            # 3. Missed-TP-Erkennung
            # --------------------------------------------------
            if side == "buy" and current_price >= float(tp):
                gate_debug("❌ TP bereits erreicht → Order wird gecancelt")
                cancel_order_by_id(of._ACTIVE_ORDER_ID, cause="missed_tp")
                of._ACTIVE_ORDER_ID = None
                of._ACTIVE_TP = None
                of._ACTIVE_SIDE = None
                set_context()
                of._sync_with_exchange(reason="missed_tp_cancel_sync")
                continue

            if side == "sell" and current_price <= float(tp):
                gate_debug("❌ TP bereits erreicht → Order wird gecancelt")
                cancel_order_by_id(of._ACTIVE_ORDER_ID, cause="missed_tp")
                of._ACTIVE_ORDER_ID = None
                of._ACTIVE_TP = None
                of._ACTIVE_SIDE = None
                set_context()
                of._sync_with_exchange(reason="missed_tp_cancel_sync")
                continue

            #gate_debug(f"🟡 Order {of._ACTIVE_ORDER_ID} ist noch aktiv")
            #gate_debug("---------------------------------------")

        except Exception as e:
            of._CONNECTION_OK = False
            gate_debug(f"❌ Monitor Fehler: {e}")

# --------------------------------------------------
# PLACE ORDER
# --------------------------------------------------
def place_order(order_type, price, amount, open_orders=None, tp=None, sl=None, params=None):
    
    global _SYMBOL

    of._bootstrap_once()

    _SYMBOL = f"{Config.SYMBOL}:USDT"
    of._SYMBOL = _SYMBOL

    exchange = ph_ohlcv.create_exchange(api.API_KEY, api.API_SECRET)
    of._EXCHANGE = exchange

    # sobald wir hier sind, ist Verbindung wieder da (best effort)
    of._CONNECTION_OK = True

    # falls nach Restart Position offen erkannt wurde: fail-safe block
    if of._POSITION_OPEN is True:
        gate_debug("⚠️ place_order blockiert: POSITION OFFEN (failsafe) – erst Sync/Manuell klären")
        gate_debug("---------------------------------------")
        return None

    open_orders = exchange.fetch_open_orders(_SYMBOL)
    #print(open_orders)
    # ----------------------------------------------------------------------------------------------------
    # OPEN ORDERS MANAGEMENT
    # - identische Order (side+price) behalten
    # - sonst: offene Orders canceln
    # ----------------------------------------------------------------------------------------------------
    if open_orders:

        target_side = str(order_type).lower()
        target_price = float(price)

        identical_id = None
        for o in open_orders:
            try:
                o_side = str(o.get("side") or "").lower()
                o_price = o.get("price")
                if o_price is None:
                    continue
                if o_side == target_side and abs(float(o_price) - target_price) < 0.0001:
                    identical_id = o.get("id")
                    break
            except Exception:
                continue

        if identical_id:
            of._ACTIVE_ORDER_ID = identical_id
            gate_debug(f"➡️ Order existiert bereits | id={of._ACTIVE_ORDER_ID}")
            gate_debug("---------------------------------------")
            return of._ACTIVE_ORDER_ID

        gate_debug("🗑️ open_orders vorhanden → canceln (veraltet/abweichend)")

        for o in open_orders:
            try:
                oid = o.get("id")
                if oid:
                    cancel_order_by_id(oid, cause="cleanup")
            except Exception:
                continue

        try:
            open_orders = exchange.fetch_open_orders(_SYMBOL)
        except Exception:
            open_orders = []
    
    if not open_orders:
        # ----------------------------------------------------------------------------------------------------
        # Balance prüfen
        # ----------------------------------------------------------------------------------------------------
        has_balance, message = ph_ohlcv.get_sufficient_balance(
            exchange,
            str(order_type).lower(),
            float(price),
            float(amount),
            Config.USDT,
            Config.COIN,
            symbol=_SYMBOL,
        )

        gate_debug("---------------------------------------")
        gate_debug(message)

        if not has_balance:
            gate_debug(
                f"⏭️ Order wird gehalten: {str(order_type).upper()} | menge: {amount} | Größe: {price}$ – Unzureichendes Guthaben"
            )
            gate_debug("---------------------------------------")
            return None
        else:
            gate_debug(
                f"✅ genügend Guthaben vorhanden: {str(order_type).upper()} | menge: {amount} | Größe: {price}$"
            )

        # ----------------------------------------------------------------------------------------------------
        # Params (Future TP/SL)
        # ----------------------------------------------------------------------------------------------------
        params_ = dict(params or {})

        context_entry_reference = params_.pop("_entry_reference", price)
        context_entry_distance = params_.pop("_entry_distance", 0.0)
        context_risk_reference = params_.pop("_risk_reference", abs(float(price) - float(sl)) if sl is not None else 0.0)
        context_entry_validity_band = dict(params_.pop("_entry_validity_band", {}) or {})

        if sl is not None:
            params_["stopLossPrice"] = float(sl)
        if tp is not None:
            params_["takeProfitPrice"] = float(tp)

        # ----------------------------------------------------------------------------------------------------
        # Order setzen 
        # ----------------------------------------------------------------------------------------------------
        order = exchange.create_order(
            _SYMBOL,
            "limit",
            str(order_type).lower(),
            float(amount),
            float(price),
            params_ if params_ else None,
        )
        # ----------------------------------------------------------------------------------------------------
        # Order gesetzt – ID extrahieren und Monitor-Thread informiert (über globale State-Variablen)
        # ----------------------------------------------------------------------------------------------------
        order_id = None
        if isinstance(order, dict):
            order_id = order.get("id")

        of._ACTIVE_ORDER_ID = order_id
        of._ACTIVE_TP = float(tp) if tp is not None else None
        of._ACTIVE_SIDE = str(order_type).lower()

        # --------------------------------------------------
        # CONTEXT TRACKING (MARKET SHIFT)
        # --------------------------------------------------
        set_context(
            entry_reference=context_entry_reference,
            entry_distance=context_entry_distance,
            risk_reference=context_risk_reference,
            entry_validity_band=context_entry_validity_band,
        )

        if order_id is not None:
            gate_debug(
                f"✅ Order gesetzt: {str(order_type).upper()} | menge: {amount} | Größe: {price}$ | id={of._ACTIVE_ORDER_ID}"
            )
        else:
            gate_debug(
                f"⚠️ Order ohne ID gesetzt: {str(order_type).upper()} | menge: {amount} | Größe: {price}$"
            )

        gate_debug("---------------------------------------")
        return order_id