import os
import requests
import pandas as pd
from datetime import datetime

# -------------------------
# ENV VARIABLES
# -------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not TWELVEDATA_API_KEY:
    raise RuntimeError("❌ Missing environment variables")

# -------------------------
# CONFIG
# -------------------------
SYMBOL = "XAU/USD"
INTERVAL = "15min"
SMA_PERIOD = 20

# -------------------------
# FETCH MARKET DATA
# -------------------------
def fetch_data():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "apikey": TWELVEDATA_API_KEY,
        "outputsize": SMA_PERIOD + 2  # Need extra for SMA calculation
    }
    r = requests.get(url, params=params, timeout=15)
    data = r.json()
    if "values" not in data:
        raise RuntimeError(f"❌ TwelveData error: {data}")
    df = pd.DataFrame(data["values"])
    df = df[::-1]  # Oldest to newest
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["SMA20"] = df["close"].rolling(SMA_PERIOD).mean()
    return df

# -------------------------
# DECIDE SIGNAL
# -------------------------
def check_signal(df):
    last_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]

    # BUY signal: previous close < SMA, current close > SMA
    if prev_candle["close"] < prev_candle["SMA20"] and last_candle["close"] > last_candle["SMA20"]:
        trade_type = "BUY"
        entry = last_candle["close"]
        stop_loss = last_candle["low"]
        risk = entry - stop_loss
        take_profit = entry + 2 * risk
        return trade_type, entry, stop_loss, take_profit

    # SELL signal: previous close > SMA, current close < SMA
    elif prev_candle["close"] > prev_candle["SMA20"] and last_candle["close"] < last_candle["SMA20"]:
        trade_type = "SELL"
        entry = last_candle["close"]
        stop_loss = last_candle["high"]
        risk = stop_loss - entry
        take_profit = entry - 2 * risk
        return trade_type, entry, stop_loss, take_profit

    return None, None, None, None

# -------------------------
# SEND TELEGRAM
# -------------------------
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    r = requests.post(url, data=payload, timeout=10)
    print("📨 Telegram response:", r.text)
    if not r.ok:
        raise RuntimeError("❌ Telegram message failed")

# -------------------------
# MAIN
# -------------------------
def main():
    print("🚀 Running XAUUSD SMA Signal Bot")

    df = fetch_data()
    trade_type, entry, sl, tp = check_signal(df)

    if not trade_type:
        print("ℹ️ No SMA signal detected")
        return

    message = f"""
📈 XAUUSD SIGNAL ALERT

Trade Type: {trade_type}
Entry Price: {entry:.2f}
SL: {sl:.2f}
TP: {tp:.2f}

⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
"""
    send_telegram(message.strip())
    print("✅ Signal sent")

if __name__ == "__main__":
    main()
