import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

message = """
⏰ TRADE UPDATE

✅ Close all open positions,
and wait/get ready for the 
next signal 👇.

🤖 Automated Trade Management
"""

requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(message)
