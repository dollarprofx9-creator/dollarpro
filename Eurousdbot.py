import requests
import os
import datetime
import pytz

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

last_signal = None
LONDON_TZ = pytz.timezone("Europe/London")

def is_london_session():
    """Check if current time is within London session (08:00–16:00 London time)."""
    now = datetime.datetime.now(LONDON_TZ)
    return 8 <= now.hour < 16

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram message sent successfully: {message}")
        else:
            print(f"❌ Telegram failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Exception sending Telegram message: {e}")

def get_eurusd_price():
    url = f"https://api.twelvedata.com/price?symbol=EUR/USD&apikey={TWELVEDATA_API_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
        if "price" in r:
            return float(r["price"])
        else:
            print(f"❌ TwelveData API error: {r}")
            return None
    except Exception as e:
        print(f"❌ Exception fetching price: {e}")
        return None

def generate_signal(price):
    if price > 1.0850:
        return "BUY"
    elif price < 1.0800:
        return "SELL"
    return None

def run_bot(manual=False):
    global last_signal

    # If not manual, only run during London session
    if not manual and not is_london_session():
        print("⏱ Outside London session")
        return

    price = get_eurusd_price()
    if price is None:
        print("Waiting for valid price data...")
        return

    signal = generate_signal(price)
    if signal and signal != last_signal:
        now = datetime.datetime.now(LONDON_TZ).strftime("%Y-%m-%d %H:%M")
        message = (
            f"🔥 {signal} Signal {'(London Session)' if not manual else '(London session)'}\n"
            f"💰 Pair: EUR/USD\n"
            f"💵 Price: {price}\n"
            f"🕒 Time: {now}"
        )
        send_telegram(message)
        last_signal = signal
    else:
        print("No new signal or already sent for this session.")

if __name__ == "__main__":
    # Set manual=True if you want to run manually
    run_bot(manual=True)
