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
    """Check if current time is within London session (08:00–16:00 London time)."""
    now = datetime.datetime.now(LONDON_TZ)
    return 8 <= now.hour < 16

# ===== TELEGRAM =====
def send_telegram(message):
    """Send a message to Telegram and log the response."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        # Log Telegram response
        if response.status_code == 200:
            print(f"✅ Telegram message sent successfully: {message}")
        else:
            print(f"❌ Telegram failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Exception sending Telegram message: {e}")

# ===== PRICE FETCH =====
def get_eurusd_price():
    """Fetch current EUR/USD price from TwelveData."""
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

# ===== SIGNAL LOGIC =====
def generate_signal(price):
    """Simple example: Buy if price > 1.0850, Sell if price < 1.0800"""
    if price > 1.0850:
        return "BUY"
    elif price < 1.0800:
        return "SELL"
    return None

# ===== MAIN =====
def run_bot():
    global last_signal  # Must be first

    if not is_london_session():
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
            f"🔥 {signal} Signal (London Session)\n"
            f"💰 Pair: EUR/USD\n"
            f"💵 Price: {price}\n"
            f"🕒 Time: {now}"
        )
        send_telegram(message)
        last_signal = signal  # Save last signal
    else:
        print("No new signal or already sent for this session.")

# ===== RUN =====
if __name__ == "__main__":
    run_bot()
