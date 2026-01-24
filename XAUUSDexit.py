import os
import requests
from datetime import datetime

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise RuntimeError("❌ Missing Telegram credentials")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    r = requests.post(url, data=payload, timeout=10)
    if not r.ok:
        raise RuntimeError(f"Telegram error: {r.text}")

message = f"""
⚠️ XAUUSD LIQUIDITY WARNING

Liquidity is dropping.
Exit all open XAUUSD positions.

⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
"""

send_telegram(message.strip())
print("✅ Liquidity exit alert sent")
