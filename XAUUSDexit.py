import os
import requests
from datetime import datetime

# === ENV (EXACT SECRET NAMES) ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN missing")

if not TELEGRAM_CHAT_ID:
    raise RuntimeError("❌ TELEGRAM_CHAT_ID missing")

if not TWELVEDATA_API_KEY:
    raise RuntimeError("❌ TWELVEDATA_API_KEY missing")

# === GET LIVE XAUUSD PRICE ===
def get_price():
    url = "https://api.twelvedata.com/price"
    params = {
        "symbol": "XAU/USD",
        "apikey": TWELVEDATA_API_KEY
    }
    r = requests.get(url, params=params, timeout=10).json()
    if "price" not in r:
        raise RuntimeError(f"TwelveData error: {r}")
    return float(r["price"])

# === SEND TELEGRAM MESSAGE ===
def send_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    response = requests.post(url, data=payload, timeout=10)
    if not response.ok:
        raise RuntimeError(f"Telegram error: {response.text}")

# === MAIN ===
price = get_price()
time_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

message = (
    "⚠️ XAUUSD LIQUIDITY WARNING\n\n"
    "Liquidity is dropping.\n"
    "Exit all open XAUUSD positions.\n\n"
    f"📉 Exit Price: {price:.2f}\n"
    f"⏰ Time: {time_utc}"
)

send_message(message)
print("✅ Message sent successfully")
