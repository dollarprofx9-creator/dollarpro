import os
import requests
import pandas as pd
from datetime import datetime
import pytz

# ================= CONFIG =================
API_KEY = os.environ.get("TWELVEDATA_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOL = "XAU/USD"
INTERVAL = "1min"
SMA_PERIOD = 20
ATR_PERIOD = 14
TIMEZONE = "Africa/Lagos"

DATA_URL = "https://api.twelvedata.com/time_series"

# ================= TELEGRAM =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    r = requests.post(url, data=payload, timeout=20)
    if not r.ok:
        raise RuntimeError(r.text)

# ================= DATA =================
def get_data():
    url = f"{DATA_URL}?symbol={SYMBOL}&interval={INTERVAL}&outputsize=200&apikey={API_KEY}"
    r = requests.get(url, timeout=20)
    data = r.json()
    if "values" not in data:
        raise RuntimeError(data)
    df = pd.DataFrame(data["values"])
    df = df.astype(float, errors="ignore")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    return df

# ================= INDICATORS =================
def sma(series, period):
    return series.rolling(period).mean()

def atr(df, period):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# ================= TIME LOGIC =================
def is_5pm():
    now = datetime.now(pytz.timezone(TIMEZONE))
    return now.hour == 17  # 5PM

# ================= MAIN LOGIC =================
def main():
    df = get_data()

    df["SMA"] = sma(df["close"], SMA_PERIOD)
    df["ATR"] = atr(df, ATR_PERIOD)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = last["close"]
    prev_close = prev["close"]
    sma_val = last["SMA"]
    atr_val = last["ATR"]

    trade_type = None
    entry = None
    sl = None
    tp = None

    # ===== SIGNAL LOGIC =====
    if prev_close < sma_val and close > sma_val:
        trade_type = "BUY"
        entry = close
        sl = entry - (atr_val * 1.5)
        tp = entry + (atr_val * 3)

    elif prev_close > sma_val and close < sma_val:
        trade_type = "SELL"
        entry = close
        sl = entry + (atr_val * 1.5)
        tp = entry - (atr_val * 3)

    # ===== EXIT LOGIC =====
    if trade_type:
        # Liquidity exit at 5PM
        if is_5pm():
            send_telegram(
                f"🚪 XAUUSD EXIT ALERT\n\n"
                f"⚠️ Reason: EXIT – LIQUIDITY IS LOW (5PM)\n"
                f"📍 Trade: {trade_type}\n"
                f"💰 Price: {close:.2f}\n\n"
                f"❌ Trade closed automatically"
            )
            return

        # TP/SL Exit
        if trade_type == "BUY":
            if close >= tp:
                reason = "🎯 TP REACHED"
            elif close <= sl:
                reason = "🛑 SL HIT"
            else:
                return

        if trade_type == "SELL":
            if close <= tp:
                reason = "🎯 TP REACHED"
            elif close >= sl:
                reason = "🛑 SL HIT"
            else:
                return

        send_telegram(
            f"🚪 XAUUSD EXIT ALERT\n\n"
            f"📌 Reason: {reason}\n"
            f"📍 Trade: {trade_type}\n"
            f"💰 Exit Price: {close:.2f}\n\n"
            f"⚠️ Trade closed – wait for next setup"
        )

if __name__ == "__main__":
    main()
