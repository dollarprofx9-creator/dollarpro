import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set.")

if not CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID is not set.")

message = (
    "💡 Consistency beats chasing wins. Not every signal will be a winner, "
    "but following a disciplined strategy over time is what gives traders an edge.\n\n"
    "✅ Stick to your risk management.\n"
    "✅ Avoid emotional entries and exits.\n"
    "✅ Trust the process and let probabilities play out.\n\n"
    "The goal isn't to win every trade—it's to stay consistent, protect your capital, "
    "and grow steadily over the long run.\n\n"
    "Trade smart. Stay disciplined. Success is built one well-managed trade at a time. 📈⚠️"
)

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

response = requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message,
    },
    timeout=30,
)

print("Status Code:", response.status_code)
print("Response:", response.text)

response.raise_for_status()
