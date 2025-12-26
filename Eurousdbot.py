import requests
import os
import time
from datetime import datetime

# ===== LOAD SECRETS =====
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ===== SETTINGS =====
SYMBOL = "EUR/USD"
INTERVAL = "1min"
SMA_PERIOD = 20
CHECK_DELAY = 60  # seconds
SESSION = "New York"

last_signal = None


# ===== FUNCTIONS =====
def get_price_data():
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "apikey": TWELVEDATA_API_KEY,
        "outputsize": 50
    }

    response = requests.get(url, timeout=10).json()

    if "values" not in response:
        return None, None

    closes = [float(candle["close"]) for candle in response["values"]]
    current_price = closes[0]
    return current_price, closes


def calculate_sma(data, period):
    return sum(data[:period]) / period


def format_signal(signal_type, price):
    date_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    if signal_type == "BUY":
        emoji = "🔥💚"
        direction = "Buy"
    else:
        emoji = "🔥❤️"
        direction = "Sell"

    message = (
        f"{emoji} {direction} Signal ({SESSION} Session Start)\n"
        f"💰 Pair: EUR/USD\n"
        f"💵 Price: {price}\n"
        f"🕒 Session: {SESSION}\n"
        f"📅 Date: {date_time}"
    )

    return message


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text
    }
    requests.post(url, json=payload, timeout=10)


# ===== MAIN LOOP =====
while True:
    price, closes = get_price_data()

    if price is None:
        time.sleep(CHECK_DELAY)
        continue

    sma = calculate_sma(closes, SMA_PERIOD)

    if price > sma and last_signal != "BUY":
        msg = format_signal("BUY", price)
        send_telegram_message(msg)
        last_signal = "BUY"

    elif price < sma and last_signal != "SELL":
        msg = format_signal("SELL", price)
        send_telegram_message(msg)
        last_signal = "SELL"

    time.sleep(CHECK_DELAY)
