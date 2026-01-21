import os
import requests

# ================== CONFIG ==================
API_KEY = os.environ.get("TWELVEDATA_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOL = "XAU/USD"
INTERVAL = "15min"
SMA_PERIOD = 20
ATR_PERIOD = 14

# ================== FETCH MARKET DATA ==================
def get_candles():
    url = (
        f"https://api.twelvedata.com/time_series?"
        f"symbol={SYMBOL}&interval={INTERVAL}&outputsize=50&apikey={API_KEY}"
    )
    r = requests.get(url, timeout=20)
    data = r.json()
    if "values" not in data:
        raise RuntimeError(data)
    return list(reversed(data["values"]))

# ================== SMA CALCULATION ==================
def sma(values, period):
    closes = [float(v["close"]) for v in values]
    return sum(closes[-period:]) / period

# ================== ATR CALCULATION ==================
def atr(values, period):
    trs = []
    for i in range(1, len(values)):
        high = float(values[i]["high"])
        low = float(values[i]["low"])
        prev_close = float(values[i-1]["close"])
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs[-period:]) / period

# ================== SIGNAL LOGIC ==================
def check_signal(candles):
    curr = candles[-1]  # last closed candle
    sma_value = sma(candles, SMA_PERIOD)
    atr_value = atr(candles, ATR_PERIOD)

    curr_close = float(curr["close"])

    # BUY signal
    if curr_close > sma_value:
        entry = curr_close
        sl = entry - atr_value          # SL = entry - ATR
        tp = entry + 2 * (entry - sl)   # TP = 1:2 RR
        return "BUY", entry, sl, tp

    # SELL signal
    if curr_close < sma_value:
        entry = curr_close
        sl = entry + atr_value          # SL = entry + ATR
        tp = entry - 2 * (sl - entry)   # TP = 1:2 RR
        return "SELL", entry, sl, tp

    return None

# ================== TELEGRAM ==================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, data=payload, timeout=20)
    if not r.ok:
        raise RuntimeError(f"Telegram error: {r.text}")

# ================== MAIN ==================
try:
    candles = get_candles()
    signal = check_signal(candles)

    if signal:
        side, entry, sl, tp = signal
        message = (
            f"📡 *XAUUSD SIGNAL*\n\n"
            f"🔔 *Type:* {side}\n"
            f"💰 *Entry:* {entry:.2f}\n"
            f"🛑 *Stop Loss:* {sl:.2f}\n"
            f"🎯 *Take Profit:* {tp:.2f}\n\n"
            f"📊 *Risk–Reward:* 1:2\n"
            f"⏱ *Timeframe:* M15"
        )
        send_telegram(message)
        print("✅ Signal sent")
    else:
        print("ℹ️ No signal")

except Exception as e:
    print("❌ ERROR:", e)
    raise
