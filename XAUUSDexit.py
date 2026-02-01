import os
import requests
from datetime import datetime

# =====================
# REQUIRED SECRETS
# =====================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
API_KEY = os.getenv("TWELVEDATA_API_KEY")

if BOT_TOKEN is None:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN not found")

if CHAT_ID is None:
    raise RuntimeError("❌ TELEGRAM_CHAT_ID not found")

if API_KEY is None:
    raise RuntimeError("❌ TWELVEDATA_API_KEY not found")

# =====================
# FETCH LIVE XAUUSD PRICE
# =====================
def get_xauusd_price():
    url = "https://api.twelvedata.com/price"
    params = {
        "symbol": "XAU/USD",
        "apikey": API_KEY
    }
    response = requests.get(url, params=params, timeout=10)
    data = response.json()

    if "price" not in data:
        raise RuntimeError(f"❌ TwelveData error: {data}")

    return float(data["price"])

# =====================
# SEND TELEGRAM MESSAGE
# =====================
def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }
    r = requests.post(url, data=payload, timeout=10)
    if not r.ok:
        raise RuntimeError(f"❌ Telegram error: {r.text}")

# =====================
# MAIN EXECUTION
# =====================
price = get_xauusd_price()
utc_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

message = (
    "⚠️ XAUUSD LIQUIDITY WARNING\n\n"
    "Liquidity is dropping.\n"
    "Exit all open XAUUSD positions.\n\n"
    f"📉 Exit Price: {price:.2f}\n"
    f"⏰ Time: {utc_time}"
)

send_telegram(message)

print("✅ Liquidity exit message sent successfully")
