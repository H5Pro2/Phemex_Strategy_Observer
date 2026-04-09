# ============================================================
# ph_ohlcv.py
# ============================================================
import api
import time
import csv
import os
import importlib.util
from config import Config
from datetime import datetime
# --------------------------------------------------
# CSV LEARN MODE (Sliding Window)
LEARNING = bool(getattr(Config, "LEARN_MODE", False))
CSV_OHLCV_PATH = str(getattr(Config, "CSV_OHLCV_PATH", "data/workspace.csv"))

_CSV_BUFFER = []
_CSV_POS = 0
_CSV_LOADED = False
# ---------------------------------------------------  

# --------------------------------------------------
try:
    import debug_reader as dbr
except Exception:
    dbr = None

def create_exchange(api_key=api.API_KEY, secret=api.API_SECRET):
    if importlib.util.find_spec("ccxt") is None:
        raise ModuleNotFoundError(
            "ccxt ist nicht installiert. Für LIVE-Exchange bitte zuerst 'ccxt' installieren."
        )
    import ccxt
    return ccxt.phemex({
        "apiKey": api_key,
        "secret": secret,
        "enableRateLimit": True,
        'options': {'defaultType': Config.MECHANIK}  # Phemex Future
    })
# --------------------------------------------------

# ---------------------------------------------------  

def _load_csv_ohlcv():
    global _CSV_BUFFER, _CSV_LOADED

    if _CSV_LOADED:
        return

    if not os.path.exists(CSV_OHLCV_PATH):
        raise FileNotFoundError(CSV_OHLCV_PATH)

    with open(CSV_OHLCV_PATH, "r", encoding="utf-8") as f:
        r = csv.reader(f)
        next(r, None)  # erste Header-Zeile überspringen

        for row in r:
            if not row:
                continue
            if row[0].strip().lower() == "timestamp_ms":
                continue
            if len(row) < 8:
                continue

            try:
                ts = int(float(row[0]))
                o = float(row[3])
                h = float(row[4])
                l = float(row[5])
                c = float(row[6])
                v = float(row[7])
            except (ValueError, IndexError):
                continue

            _CSV_BUFFER.append([ts, o, h, l, c, v])

    _CSV_LOADED = True
# --------------------------------------------------  

# ---------------------------------------------------  
def fetch_ohlcv(exchange, symbol, timeframe):
    global _CSV_POS

    # --------------------------------------------------
    # LEARN MODE (CSV · Sliding Window)
    # --------------------------------------------------
    if LEARNING:
        
        _load_csv_ohlcv()

        ws_size = int(getattr(Config, "WINDOW_SIZE", 500) or 500)

        start = _CSV_POS
        end = start + ws_size

        if end > len(_CSV_BUFFER):
            # CSV vollständig abgearbeitet
            print('finish')
            return {
                "csv_done": True,
                "last_ts": _CSV_BUFFER[-1][0] if _CSV_BUFFER else None,
            }

        candles = _CSV_BUFFER[start:end]

        _CSV_POS += 1
        return candles

    # --------------------------------------------------
    # LIVE MODE (PHEMEX)
    # --------------------------------------------------
    needed = Config.WINDOW_SIZE + 10
    try:
        if needed <= 100:
            limit = 100
        elif needed <= 500:
            limit = 500
        else:
            limit = 1000

        ex = exchange.fetch_ohlcv(
            symbol,
            timeframe=timeframe,
            limit=limit
        )
        #print(ex)
        return ex
    except Exception:
        print(f"Time: [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        print("TIMEOUT fetch_ohlcv")
        return None
# --------------------------------------------------
# LIVE MINUTE OHLC STATE
# --------------------------------------------------
_CURRENT_MINUTE = None
_O = _H = _L = _C = None
def get_current_price(exchange, symbol):
    """
    Liefert:
        {
            "price": float,          # letzter Tradepreis
            "ohlc": (O, H, L, C),    # laufende Minutenkerze (live aggregiert)
        }
    """
    global _CURRENT_MINUTE, _O, _H, _L, _C

    try:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker.get("last")

        if price is None:
            raise ValueError("Ticker liefert keinen last-Preis")

        price = float(price)
        minute_ts = int(time.time() // 60) * 60

        # --------------------------------------------------
        # NEW MINUTE → RESET OHLC
        # --------------------------------------------------
        if _CURRENT_MINUTE != minute_ts:
            _CURRENT_MINUTE = minute_ts
            _O = _H = _L = _C = price

        # --------------------------------------------------
        # SAME MINUTE → UPDATE OHLC
        # --------------------------------------------------
        else:
            _H = max(_H, price)
            _L = min(_L, price)
            _C = price

        return {
            "price": price,
            "ohlc": (_O, _H, _L, _C),
        }

    except Exception as e:
        if dbr is not None:
            print("---------------------------------------")
            print("get_current_price")
            print(f"❌ Fehler beim Abrufen des aktuellen Preises: {e}")
        return None
# ---------------------------------------------------

# ---------------------------------------------------
def get_open_orders(exchange,PH_SYMBOL):
    """
    Holt die aktuell offenen Orders für das Symbol.

    Returns:
        list: Liste offener Orders oder leere Liste bei Fehler.
    """
    try:
        return exchange.fetch_open_orders(PH_SYMBOL)
    except Exception as e:
        print("---------------------------------------")
        print(f"❌ Fehler beim Abrufen der open-Orders: {e}")
        return []
# ---------------------------------------------------

# ---------------------------------------------------
def get_account_value(exchange, quote):
    """
    Berechne gesamten Account-Wert in quote (z.B. USDT)
    """
    balance = exchange.fetch_balance()
    total_value = 0.0

    for asset, info in balance['total'].items():
        if info > 0:
            if asset == quote:
                total_value += info
            else:
                try:
                    ticker = exchange.fetch_ticker(f"{asset}/{quote}")
                    price = ticker['last']
                    total_value += info * price
                except:
                    pass  # coin evtl. nicht handelbar gegen USDT

    return total_value
# ---------------------------------------------------

# ---------------------------------------------------
def check_order_id_exist(exchange,PH_SYMBOL,order_id):
    try:
        open_orders = exchange.fetch_open_orders(PH_SYMBOL)

        for order in (open_orders or []):
            # nur wirklich offene Orders zählen
            status = str(order.get("status") or "").lower()
            if status and status != "open":
                continue

            info = order.get("info") or {}

            # unterschiedliche ID-Felder je nach ccxt/exchange
            candidates = [
                order.get("id"),
                order.get("clientOrderId"),
                order.get("clientOrderID"),
                info.get("orderID"),
                info.get("orderId"),
                info.get("clientOrderId"),
                info.get("clientOrderID"),
            ]

            for cid in candidates:
                if cid is None:
                    continue
                if str(cid) == str(order_id):
                    return True

        return False

    except Exception:
        return False
# ---------------------------------------------------  

# ---------------------------------------------------
# Positionsdaten abfragen
# ---------------------------------------------------  
def get_account_leverage(exchange,PH_SYMBOL):
    positions = exchange.fetch_positions([PH_SYMBOL])
    for pos in positions:
        if pos['symbol'] == PH_SYMBOL:
            position = pos['leverage']
    return position   
# ---------------------------------------------------

# ---------------------------------------------------
def get_sufficient_balance(
    exchange,
    order_type,
    price,
    amount,
    usdt,
    coin,
    symbol=None,
):
    """
    Prüft ausreichendes Kapital.
    Spot: wie bisher
    Future: Margin-Prüfung (inkl. Leverage)
    """

    try:
        balance = exchange.fetch_balance()
        free_usdt = balance["free"].get(usdt, 0)

        # --------------------------------------------------
        # FUTURE (Swap)
        # --------------------------------------------------
        if symbol and ":USDT" in symbol:

            # Leverage holen
            leverage = 1
            try:
                positions = exchange.fetch_positions([symbol])
                for pos in positions:
                    if pos.get("symbol") == symbol:
                        leverage = float(pos.get("leverage", 1))
                        break
            except Exception:
                leverage = 1

            required_margin = (price * amount) / max(leverage, 1)

            if free_usdt >= required_margin:
                return True, (
                    f"✅ Margin OK | Free {usdt}: "
                    f"{free_usdt:.2f} ≥ {required_margin:.2f}"
                )
            else:
                return False, (
                    f"❌ Margin zu gering | Free {usdt}: "
                    f"{free_usdt:.2f} < {required_margin:.2f}"
                )

        # --------------------------------------------------
        # SPOT (unverändert)
        # --------------------------------------------------
        if order_type == "buy":
            usdt_needed = price * amount

            if free_usdt >= usdt_needed:
                return True, (
                    f"✅ Ausreichend {usdt} "
                    f"({free_usdt:.2f} ≥ {usdt_needed:.2f})"
                )
            else:
                return False, (
                    f"❌ Nicht genug {usdt} "
                    f"({free_usdt:.2f} < {usdt_needed:.2f})"
                )

        elif order_type == "sell":
            coin_balance = balance["free"].get(coin, 0)

            if coin_balance >= amount:
                return True, (
                    f"✅ Ausreichend {coin} "
                    f"({coin_balance:.4f} ≥ {amount:.4f})"
                )
            else:
                return False, (
                    f"❌ Nicht genug {coin} "
                    f"({coin_balance:.4f} < {amount:.4f})"
                )

        return False, "❌ Unbekannter Order-Typ"

    except Exception as e:
        return False, f"❌ Balance-Fehler: {e}"
# ---------------------------------------------------


# --------------------------------------------------
# CANDLE STATE
# --------------------------------------------------
def _build_candle_state(candle, prev_close=None):

    o = float(candle.get("open", 0.0) or 0.0)
    h = float(candle.get("high", o) or o)
    l = float(candle.get("low", o) or o)
    c = float(candle.get("close", o) or o)

    span = max(h - l, 1e-9)
    body = c - o
    upper_wick = max(0.0, h - max(o, c))
    lower_wick = max(0.0, min(o, c) - l)

    body_strength = max(0.0, min(abs(body) / span, 1.0))
    upper_wick_ratio = max(0.0, min(upper_wick / span, 1.0))
    lower_wick_ratio = max(0.0, min(lower_wick / span, 1.0))
    wick_bias = max(-1.0, min(lower_wick_ratio - upper_wick_ratio, 1.0))
    close_position = max(-1.0, min((((c - l) / span) * 2.0) - 1.0, 1.0))

    return_intensity = 0.0
    if prev_close is not None:
        prev_close = float(prev_close or 0.0)
        if prev_close > 0.0:
            return_intensity = max(-1.0, min(((c - prev_close) / prev_close) * 20.0, 1.0))

    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "body_strength": float(body_strength),
        "upper_wick_ratio": float(upper_wick_ratio),
        "lower_wick_ratio": float(lower_wick_ratio),
        "wick_bias": float(wick_bias),
        "close_position": float(close_position),
        "return_intensity": float(return_intensity),
    }