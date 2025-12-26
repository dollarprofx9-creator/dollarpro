import os
import requests
from datetime import datetime, time as dt_time
import pytz
import time

# ===== Load secrets =====
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TWELVEDATA_API_KEY or not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ One or more secrets are missing. Exiting.")
    exit(1)

# ===== Settings =====
SYMBOL = "EUR/USD"
INTERVAL = "1min"
SMA_PERIOD = 20
CHECK_DELAY = 60  # seconds between checks
SESSION = "London"

last_signal = None
TIMEZONE = pytz.timezone("Europe/London")

# London session times
LONDON_OPEN = dt_time(8, 0)   # 08:00 London time
LONDON_CLOSE = dt_time(16, 0) # 16:00 London time


# ===== Functions =====
def is_london_session():
    now = datetime.now(TIMEZONE).time()
    return LONDON_OPEN <= now <= LONDON_CLOSE


def get_price_data():
    """Fetch EUR/USD price data from Twelve Data"""
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "apikey": TWELVEDATA_API_KEY,
        "outputsize": 50
    }

    try:
        response = requests.get(url, timeout=10).json()
        if "values" not in response:
            print("❌ Error fetching data:", response)
            return None, None

        closes = [float(candle["close"]) for candle in response["values"]]
        current_price = closes[0]
        return current_price, closes
    except Exception as e:
        print("❌ Exception fetching data:", e)
        return None, None


def calculate_sma(data, period):
    if len(data) < period:
        return None
    return sum(data[:period]) / period


def format_signal(signal_type, price):
    date_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M")
    emoji = "🔥💚" if signal_type == "BUY" else "🔥❤️"
    direction = "Buy" if signal_type == "BUY" else "Sell"

    return (
        f"{emoji} {direction} Signal ({SESSION} Session)\n"
        f"💰 Pair: EUR/USD\n"
        f"💵 Price: {price}\n"
        f"🕒 Session: {SESSION}\n"
        f"📅 Date: {date_time}"
    )


def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("✅ Message sent successfully")
        else:
            print("❌ Failed to send message:", response.text)
    except Exception as e:
        print("❌ Exception sending message:", e)


# ===== Main loop =====
while True:
    if not is_london_session():
        print("⏱ Outside London session, waiting...")
        time.sleep(CHECK_DELAY)
        continue

    price, closes = get_price_data()
    if price is None:
        print("Waiting before retrying...")
        time.sleep(CHECK_DELAY)
        continue

    sma = calculate_sma(closes, SMA_PERIOD)
    if sma is None:
        print(f"Not enough data to calculate SMA({SMA_PERIOD}). Retrying...")
        time.sleep(CHECK_DELAY)
        continue

    global last_signal
    if price > sma and last_signal != "BUY":
        msg = format_signal("BUY", price)
        send_telegram_message(msg)
        last_signal = "BUY"
    elif price < sma and last_signal != "SELL":
        msg = format_signal("SELL", price)
        send_telegram_message(msg)
        last_signal = "SELL"
    else:
        print("No new signal, waiting...")

    time.sleep(CHECK_DELAY)
