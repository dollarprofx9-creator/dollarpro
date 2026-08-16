import os
import time
import requests
import yaml
from datetime import datetime
from zoneinfo import ZoneInfo

# ==========================
# Environment Variables
# ==========================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set.")

if not CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID is not set.")

# ==========================
# Load YAML Configuration
# ==========================
with open("config.yaml", "r", encoding="utf-8") as file:
    config = yaml.safe_load(file)

schedule = config.get("schedule", {})

DAY = schedule.get("day", "Monday")
SEND_TIME = schedule.get("time", "08:00")
TIMEZONE_NAME = schedule.get("timezone", "Africa/Lagos")

# ==========================
# Validate Day
# ==========================
VALID_DAYS = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6
}

if DAY not in VALID_DAYS:
    raise ValueError(
        "Invalid day. Use Monday, Tuesday, Wednesday, Thursday, "
        "Friday, Saturday, or Sunday."
    )

DAY_NUMBER = VALID_DAYS[DAY]

# ==========================
# Validate Time
# ==========================
try:
    datetime.strptime(SEND_TIME, "%H:%M")
except ValueError:
    raise ValueError("Time must use HH:MM format, e.g. 08:00.")

# ==========================
# Timezone
# ==========================
try:
    TIMEZONE = ZoneInfo(TIMEZONE_NAME)
except Exception:
    raise ValueError(f"Invalid timezone: {TIMEZONE_NAME}")

# ==========================
# Telegram Message
# ==========================
MESSAGE = """💡 Consistency beats chasing wins. Not every signal will be a winner, but following a disciplined strategy over time is what gives traders an edge.

✅ Stick to your risk management.
✅ Avoid emotional entries and exits.
✅ Trust the process and let probabilities play out.

The goal isn't to win every trade—the goal is to stay consistent, protect your capital, and grow steadily over the long run.

Trade smart. Stay disciplined. Success is built one well-managed trade at a time."""

# ==========================
# Send Telegram Message
# ==========================
def send_message():

    telegram_url = (
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": CHAT_ID,
        "text": MESSAGE
    }

    try:
        response = requests.post(
            telegram_url,
            data=payload,
            timeout=30
        )

        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            raise Exception(result)

        print(
            f"[{datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}] "
            "Weekly message sent successfully!"
        )

    except requests.RequestException as e:
        print(f"Telegram request failed: {e}")

    except Exception as e:
        print(f"Failed to send message: {e}")


# ==========================
# Scheduler
# ==========================
print("====================================")
print(" Telegram Weekly Message Bot")
print("====================================")
print(f"Day: {DAY}")
print(f"Time: {SEND_TIME}")
print(f"Timezone: {TIMEZONE_NAME}")
print("Bot is running...")
print("====================================")

last_sent = None

while True:

    now = datetime.now(TIMEZONE)

    current_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M")

    # ==========================
    # Monday + Scheduled Time
    # ==========================
    if (
        now.weekday() == DAY_NUMBER
        and current_time == SEND_TIME
        and last_sent != current_date
    ):
        send_message()

        # Prevent duplicate messages
        last_sent = current_date

    # Check every 30 seconds
    time.sleep(30)
