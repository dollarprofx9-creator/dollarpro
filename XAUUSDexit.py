import os
import requests
import pandas as pd
from datetime import datetime

# ======================
# ENV VARIABLES
# ======================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_API_KEY = os.getenv("TWELVE_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not TWELVE_API_KEY:
    raise RuntimeError("❌ Missing environment variables")

# ======================
# CONFIG
# ======================
SYMBOL = "XAUUSD"
INTERVAL = "15min"
SMA_PERIOD = 20

# ⚠️ THESE MUST MATCH YOUR ENTRY BOT VALUES
ENTRY_PRICE = float(os.getenv("ENTRY_PRICE", "0"))
STOP_LOSS = float(os.getenv("STOP_LOSS", "0"))
TAKE_PROFIT = float(os.getenv("TAKE_PROFIT", "0"))
TRADE_TYPE = os.getenv("TRADE_TYPE")  # BUY or SELL

# ======================
# FETCH MARKET DATA
# ======================
def fetch_price():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "apikey": TWELVE_API_KEY,
        "outputsize": 2
    }

    r = requests.get(url, params=params, timeout=15)
    data = r.json()

    if "values" not in data:
        raise RuntimeError(f"TwelveData error: {data}")

    price = float(data["values"][0]["close"])
    return price

# ======================
# TELEGRAM
# ======================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg
    }

    r = requests.post(url, data=payload, timeout=10)
    print("📨 Telegram:", r.text)

    if not r.ok:
        raise RuntimeError("Telegram send failed")

# ======================
# EXIT LOGIC
# ======================
def main():
    print("🚪 Running EXIT bot")

    if ENTRY_PRICE == 0 or STOP_LOSS == 0 or TAKE_PROFIT == 0:
        print("ℹ️ No active trade — exiting")
        return

    price = fetch_price()
    reason = None

    if TRADE_TYPE == "BUY":
        if price <= STOP_LOSS:
            reason = "Stop Loss Hit ❌"
        elif price >= TAKE_PROFIT:
            reason = "Take Profit Reached 🎯"

    if TRADE_TYPE == "SELL":
        if price >= STOP_LOSS:
            reason = "Stop Loss Hit ❌"
        elif price <= TAKE_PROFIT:
            reason = "Take Profit Reached 🎯"

    # 5PM Liquidity Exit
    if datetime.utcnow().hour == 16:
        reason = "Liquidity is Low — Exit Trade 🕔"

    if not reason:
        print("ℹ️ No exit condition met")
        return

    message = f"""
🚪 XAUUSD EXIT ALERT

Reason: {reason}
Exit Price: {price:.2f}

⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
"""

    send_telegram(message.strip())
    print("✅ Exit message sent")

if __name__ == "__main__":
    main()
