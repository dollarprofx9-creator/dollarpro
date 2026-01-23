import os
import requests
from datetime import datetime

# =======================
# ENV VARIABLES
# =======================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID or not TWELVEDATA_API_KEY:
    raise RuntimeError("❌ Missing environment variables")

# =======================
# ACTIVE TRADE SETTINGS
# =======================
try:
    ENTRY_PRICE = float(os.getenv("ENTRY_PRICE"))
    STOP_LOSS = float(os.getenv("STOP_LOSS"))
    TRADE_TYPE = os.getenv("TRADE_TYPE").upper()  # BUY or SELL
except Exception:
    raise RuntimeError("❌ Invalid trade environment variables")

# =======================
# CALCULATE TP BASED ON 1:2 RISK-REWARD
# =======================
def calculate_tp(entry, sl, trade_type):
    risk = abs(entry - sl)
    reward = risk * 2
    if trade_type == "BUY":
        return entry + reward
    elif trade_type == "SELL":
        return entry - reward
    else:
        return None

TAKE_PROFIT = calculate_tp(ENTRY_PRICE, STOP_LOSS, TRADE_TYPE)

# =======================
# FETCH CURRENT XAUUSD PRICE
# =======================
def fetch_price():
    url = "https://api.twelvedata.com/price"
    params = {
        "symbol": "XAU/USD",
        "apikey": TWELVE_API_KEY
    }
    r = requests.get(url, params=params, timeout=15)
    data = r.json()
    if "price" not in data:
        raise RuntimeError(f"❌ TwelveData error: {data}")
    return float(data["price"])

# =======================
# SEND TELEGRAM MESSAGE
# =======================
def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    r = requests.post(url, data=payload, timeout=10)
    print("📨 Telegram response:", r.text)
    if not r.ok:
        raise RuntimeError("❌ Telegram message failed")

# =======================
# MAIN EXIT LOGIC
# =======================
def main():
    print("🚀 Running XAUUSD EXIT Bot")
    price = fetch_price()
    reason = None

    # Check exit conditions
    if TRADE_TYPE == "BUY":
        if price <= STOP_LOSS:
            reason = "Stop Loss Hit ❌"
        elif price >= TAKE_PROFIT:
            reason = "Take Profit Reached 🎯"
    elif TRADE_TYPE == "SELL":
        if price >= STOP_LOSS:
            reason = "Stop Loss Hit ❌"
        elif price <= TAKE_PROFIT:
            reason = "Take Profit Reached 🎯"

    # Optional: Liquidity low exit at 5 PM UTC
    # if datetime.utcnow().hour == 17:
    #     reason = "Liquidity Low — Exit Trade 🕔"

    if not reason:
        print("ℹ️ No exit condition met")
        return

    message = f"""
🚪 XAUUSD EXIT ALERT

Reason: {reason}
Entry Price: {ENTRY_PRICE:.2f}
SL: {STOP_LOSS:.2f}
TP: {TAKE_PROFIT:.2f}
Exit Price: {price:.2f}

⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
"""
    send_telegram(message.strip())
    print("✅ Exit message sent")

if __name__ == "__main__":
    main()
