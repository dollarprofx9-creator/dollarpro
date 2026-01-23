import os
import requests
from datetime import datetime

# ======================
# ENV VARIABLES
# ======================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("TWELVEDATA_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not API_KEY:
    raise RuntimeError("❌ Missing Telegram or TwelveData credentials")

# ======================
# OPTIONAL TRADE DATA
# ======================
ENTRY_PRICE = os.getenv("ENTRY_PRICE")
STOP_LOSS = os.getenv("STOP_LOSS")
TRADE_TYPE = os.getenv("TRADE_TYPE")  # BUY or SELL

# If no active trade → exit safely
if not ENTRY_PRICE or not STOP_LOSS or not TRADE_TYPE:
    print("ℹ️ No active trade found. Exit bot stopped safely.")
    exit(0)

ENTRY_PRICE = float(ENTRY_PRICE)
STOP_LOSS = float(STOP_LOSS)
TRADE_TYPE = TRADE_TYPE.upper()

# ======================
# CALCULATE TP (1:2 RR)
# ======================
risk = abs(ENTRY_PRICE - STOP_LOSS)
TP = ENTRY_PRICE + (2 * risk) if TRADE_TYPE == "BUY" else ENTRY_PRICE - (2 * risk)

# ======================
# FETCH LIVE PRICE
# ======================
def get_price():
    url = "https://api.twelvedata.com/price"
    params = {"symbol": "XAU/USD", "apikey": API_KEY}
    r = requests.get(url, params=params, timeout=10).json()
    return float(r["price"])

# ======================
# SEND TELEGRAM
# ======================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(url, data=payload, timeout=10)

# ======================
# MAIN EXIT LOGIC
# ======================
price = get_price()
exit_reason = None

if TRADE_TYPE == "BUY":
    if price <= STOP_LOSS:
        exit_reason = "Stop Loss Hit ❌"
    elif price >= TP:
        exit_reason = "Take Profit Reached 🎯"

elif TRADE_TYPE == "SELL":
    if price >= STOP_LOSS:
        exit_reason = "Stop Loss Hit ❌"
    elif price <= TP:
        exit_reason = "Take Profit Reached 🎯"

if not exit_reason:
    print("ℹ️ Trade still active. No exit.")
    exit(0)

message = f"""
🚪 XAUUSD EXIT SIGNAL

Type: {TRADE_TYPE}
Reason: {exit_reason}

Entry: {ENTRY_PRICE:.2f}
SL: {STOP_LOSS:.2f}
TP: {TP:.2f}
Exit Price: {price:.2f}

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
"""

send_telegram(message.strip())
print("✅ Exit message sent")
