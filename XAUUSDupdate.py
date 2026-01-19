import os
import requests
from datetime import datetime

# ---------------- CONFIG ----------------
TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # Can be @username or -100XXXXXXXXXX
SYMBOL = "XAU/USD"

# ---------------- WEEKDAY CHECK ----------------
weekday = datetime.utcnow().weekday()  # GitHub Actions runs in UTC
if weekday >= 5:  # 5=Saturday, 6=Sunday
    print("🛑 Weekend detected — skipping post")
    exit(0)

# ---------------- FETCH LIVE DATA ----------------
def get_xauusd():
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol={SYMBOL}&interval=1day&outputsize=2&apikey={TWELVEDATA_API_KEY}"
    )
    r = requests.get(url, timeout=20)
    data = r.json()

    if "values" not in data:
        raise RuntimeError(f"❌ TwelveData API error: {data}")

    today = data["values"][0]
    prev = data["values"][1]

    return {
        "price": float(today["close"]),
        "high": float(today["high"]),
        "low": float(today["low"]),
        "prev_close": float(prev["close"]),
    }

# ---------------- FORMAT TELEGRAM MESSAGE ----------------
def build_message(d):
    direction = "🔼" if d["price"] > d["prev_close"] else "🔽"

    return (
        "🟡 *XAUUSD Market Update*\n\n"
        f"💰 *Price:* ${d['price']:,.2f} {direction}\n"
        f"📈 *High:* ${d['high']:,.2f}\n"
        f"📉 *Low:* ${d['low']:,.2f}\n"
        f"📅 *Prev Close:* ${d['prev_close']:,.2f}"
    )

# ---------------- SEND TO TELEGRAM ----------------
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    r = requests.post(url, data=payload, timeout=20)
    print("📨 Telegram response:", r.text)
    if not r.ok:
        raise RuntimeError("❌ Telegram message failed")

# ---------------- MAIN ----------------
try:
    data = get_xauusd()
    message = build_message(data)
    send_telegram(message)
    print("✅ XAUUSD update sent successfully")

except Exception as e:
    print("🔥 ERROR:", e)
    raise
