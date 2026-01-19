import os
import requests
from datetime import datetime

# ================== ENV VARIABLES ==================
TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# ================== SAFETY CHECK ==================
if not all([TWELVEDATA_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    raise RuntimeError("❌ Missing environment variables")

# ================== WEEKDAY CHECK ==================
# GitHub Actions runs in UTC
weekday = datetime.utcnow().weekday()  # Mon=0 ... Sun=6
if weekday >= 5:
    print("🛑 Weekend detected — no post sent")
    exit(0)

# ================== FETCH XAUUSD DATA ==================
def get_xauusd():
    url = (
        "https://api.twelvedata.com/time_series"
        "?symbol=XAU/USD"
        "&interval=1day"
        "&outputsize=2"
        f"&apikey={TWELVEDATA_API_KEY}"
    )

    r = requests.get(url, timeout=20)
    data = r.json()

    if "values" not in data:
        raise RuntimeError(f"❌ TwelveData error: {data}")

    today = data["values"][0]
    prev = data["values"][1]

    return {
        "price": float(today["close"]),
        "high": float(today["high"]),
        "low": float(today["low"]),
        "prev_close": float(prev["close"]),
    }

# ================== FORMAT TELEGRAM POST ==================
def build_message(d):
    direction = "🔼" if d["price"] > d["prev_close"] else "🔽"

    return (
        "🟡 *XAUUSD Market Update*\n\n"
        f"💰 *Price:* ${d['price']:,.2f} {direction}\n"
        f"📈 *High:* ${d['high']:,.2f}\n"
        f"📉 *Low:* ${d['low']:,.2f}\n"
        f"📅 *Prev Close:* ${d['prev_close']:,.2f}"
    )

# ================== SEND TO TELEGRAM ==================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,  # MUST be -100xxxxxxxxxx
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    r = requests.post(url, data=payload, timeout=20)
    print("📨 Telegram response:", r.text)

    if not r.ok:
        raise RuntimeError("❌ Telegram message failed")

# ================== MAIN ==================
try:
    data = get_xauusd()
    message = build_message(data)
    send_telegram(message)
    print("✅ XAUUSD update sent successfully")

except Exception as e:
    print("🔥 ERROR:", str(e))
    raise
