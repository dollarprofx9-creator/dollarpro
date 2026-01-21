import os
import requests
from datetime import datetime
import pytz

# ================== CONFIG ==================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

TIMEZONE = "Africa/Lagos"  # Nigeria Time

# ================== TELEGRAM ==================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "Markdown"
    }
    r = requests.post(url, data=payload, timeout=20)
    if not r.ok:
        raise RuntimeError(f"Telegram error: {r.text}")

# ================== MAIN ==================
def main():
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    weekday = now.weekday()  # 0=Monday, 6=Sunday

    if weekday < 5:
        # Monday-Friday
        msg = "📈 *Market Open* – XAUUSD trading active!"
    else:
        # Saturday-Sunday
        msg = "📴 *Market Closed* – XAUUSD trading paused."

    send_telegram(msg)
    print(f"✅ Message sent: {msg}")

if __name__ == "__main__":
    main()
