import os
import requests

# ================== CONFIG ==================
API_KEY = os.environ.get("TWELVEDATA_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOL = "XAU/USD"
INTERVAL = "15min"
SMA_PERIOD = 20

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

# ================== SMA ==================
def sma(values, period):
    closes = [float(v["close"]) for v in values]
    return sum(closes[-period:]) / period

# ================== SIGNAL LOGIC ==================
def check_signal(candles):
    curr = candles[-1]
    sma_value = sma(candles, SMA_PERIOD)

    curr_close = float(curr["close"])
    high = float(curr["high"])
    low = float(curr["low"])

    # BUY
    if curr_close > sma_value:
        sl = low
        tp = curr_close + (curr_close - sl) * 2
        return "BUY", curr_close, sl, tp

    # SELL
    if curr_close < sma_value:
        sl = high
        tp = curr_close - (sl - curr_close) * 2
        return "SELL", curr_close, sl, tp

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
        raise RuntimeError(r.text)

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

except Exception as e:
    print("❌ ERROR:", e)
    raise
