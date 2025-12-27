import requests
import os
import datetime
import pytz

# ===== ENV VARIABLES =====
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ===== GLOBAL MEMORY =====
last_signal = None

# ===== TIME SETTINGS =====
LONDON_TZ = pytz.timezone("Europe/London")

def is_london_session():
    now = datetime.datetime.now(LONDON_TZ)
    return 7 <= now.hour <= 11

# ===== TELEGRAM =====
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    requests.post(url, json=payload)

# ===== PRICE FETCH =====
def get_eurusd_price():
    url = (
        "https://api.twelvedata.com/price"
        "?symbol=EUR/USD"
        "&apikey=" + TWELVEDATA_API_KEY
    )
    r = requests.get(url).json()
    return float(r["price"])

# ===== SIGNAL LOGIC =====
def generate_signal(price):
    if price > 1.0850:
        return "BUY"
    elif price < 1.0800:
        return "SELL"
    return None

# ===== MAIN =====
def run_bot():
    global last_signal  # ✅ MUST BE FIRST

    if not is_london_session():
        print("Outside London session")
        return

    price = get_eurusd_price()
    signal = generate_signal(price)

    if signal and signal != last_signal:
        now = datetime.datetime.now(LONDON_TZ).strftime("%Y-%m-%d %H:%M")

        message = (
            f"🔥 {signal} Signal (London Session)\n"
            f"💰 Pair: EUR/USD\n"
            f"💵 Price: {price}\n"
            f"🕒 Time: {now}"
        )

        send_telegram(message)
        last_signal = signal
        print("Signal sent")

    else:
        print("No new signal")

if __name__ == "__main__":
    run_bot()
