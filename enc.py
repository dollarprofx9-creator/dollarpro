import os
import requests

# ==========================
# Environment Variables
# ==========================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


# ==========================
# Telegram Message
# ==========================
message = """💡 Consistency beats chasing wins. Not every signal will be a winner, but following a disciplined strategy over time is what gives traders an edge.

✅ Stick to your risk management.
✅ Avoid emotional entries and exits.
✅ Trust the process and let probabilities play out.

The goal isn't to win every trade—it's to stay consistent, protect your capital, and grow steadily over the long run.

Trade smart. Stay disciplined. Success is built one well-managed trade at a time."""


# ==========================
# Send Telegram Message
# ==========================
def send_message():

    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    if not CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID is not set")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()

    print("Weekly Monday message sent successfully!")


# ==========================
# Run Script
# ==========================
if __name__ == "__main__":
    send_message()
