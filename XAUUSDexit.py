import os
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    raise RuntimeError("❌ Missing Telegram credentials")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
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
