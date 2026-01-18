import requests
from datetime import datetime, timezone
import schedule
import time
import os  # <-- needed for GitHub Secrets

# ------------------- CONFIG -------------------
TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY")  # From GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")  # From GitHub Secrets
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # From GitHub Secrets
SYMBOL = "XAU/USD"
# ----------------------------------------------

def get_xauusd_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval=1day&outputsize=7&apikey={TWELVEDATA_API_KEY}"
    response = requests.get(url)
    data = response.json()

    if "values" not in data:
        raise Exception(f"Error fetching data: {data}")

    today = data["values"][0]
    prev_close = float(data["values"][1]["close"])
    current_price = float(today["close"])
    high = float(today["high"])
    low = float(today["low"])
    
    weekly_change = ((current_price - float(data["values"][-1]["close"])) / float(data["values"][-1]["close"])) * 100
    trend_emoji = "🔼" if weekly_change >= 0 else "🔽"

    return {
        "current_price": current_price,
        "high": high,
        "low": low,
        "prev_close": prev_close,
        "weekly_change": weekly_change,
        "trend_emoji": trend_emoji
    }

def format_telegram_post(data):
    post = f"🟡 *XAUUSD (Gold) Price Update*\n\n"
    post += f"💰 *Current Price:* ${data['current_price']:,.2f}\n"
    post += f"📈 *Day High:* ${data['high']:,.2f} | *Day Low:* ${data['low']:,.2f}\n"
    post += f"📅 *Prev Close:* ${data['prev_close']:,.2f} | *Weekly Move:* {data['weekly_change']:.2f}% {data['trend_emoji']}"
    return post

def send_to_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, data=payload)
    return response.json()

def job():
    today_weekday = datetime.now().weekday()
    if today_weekday >= 5:
        print(f"{datetime.now()} - Weekend detected. Skipping Telegram post.")
        return

    try:
        data = get_xauusd_data()
        message = format_telegram_post(data)
        result = send_to_telegram(message)
        print(f"{datetime.now()} - Telegram post sent:", result)
    except Exception as e:
        print(f"{datetime.now()} - Error:", e)

# Schedule daily post at 8:00 AM Nigerian time
schedule.every().day.at("08:00").do(job)

print("Scheduler started. Waiting for 8 AM Nigeria time (Mon-Fri)...")
while True:
    schedule.run_pending()
    time.sleep(30)
