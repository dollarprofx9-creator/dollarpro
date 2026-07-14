import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

message = """
💡 Consistency beats chasing wins. Not every signal will be a winner, but following a disciplined strategy over time is what gives traders an edge.

✅ Stick to your risk management.
✅ Avoid emotional entries and exits.
✅ Trust the process and let probabilities play out.

The goal isn't to win every trade—it's to stay consistent, protect your capital, and grow steadily over the long run.

Trade smart. Stay disciplined. Success is built one well-managed trade at a time. 📈⚠️
"""

requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(message)
