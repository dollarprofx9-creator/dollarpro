import os
import requests
from datetime import datetime

# =====================
# ENV VARIABLES
# =====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("TWELVEDATA_API_KEY")

if not BOT_TOKEN or not CHAT_ID or not API_KEY:
    raise RuntimeError("❌ Missing environment variables")

# =====================
# FETCH LIVE XAUUSD PRICE
# =====================
def get_xauusd_price():
    url = "https://api.twelvedata.com/price"
    params = {
        "symbol": "XAU/USD",
        "apikey": API_KEY
    }
    r = requests.get(url, params=params, timeout=10).json()
    if "price" not in r:
        raise RuntimeError(f"TwelveData error: {r}")
    return float(r["price"])

# =====================
# SEND TELEGRAM MESSAGE
# =====================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(url, data=payload, timeout=10)
    if not response.ok:
        raise RuntimeError(f"Telegram error: {response.text}")

# =====================
# MAIN
# =====================
price = get_xauusd_price()
time_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

message = f"""
⚠️ XAUUSD LIQUIDITY WARNING

Liquidity is dropping.
Exit all open XAUUSD positions.

📉 Current Price: {price:.2f}
⏰ Time: {time_utc} UTC
"""

send_telegram(message.strip())
print("✅ Liquidity exit alert sent successfully")
