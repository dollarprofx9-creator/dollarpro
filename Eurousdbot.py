import requests
import os
import datetime
import pytz
import sys

# ===== ENV VARIABLES =====
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # @username or numeric ID

# ===== GLOBAL =====
last_signal = None
LONDON_TZ = pytz.timezone("Europe/London")

# ===== TIME CHECK =====
def is_london_session():
    now = datetime.datetime.now(LONDON_TZ)
    return 8 <= now.hour < 16

# ===== TELEGRAM =====
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Telegram message sent: {message}")
        else:
            print(f"❌ Telegram failed ({response.status_code}): {response.text}")
    except Exception as e:
        print(f"❌ Exception sending Telegram: {e}")

# ===== FETCH HISTORICAL DATA =====
def get_historical_prices(interval="15min", outputsize=50):
    url = f"https://api.twelvedata.com/time_series?symbol=EUR/USD&interval={interval}&outputsize={outputsize}&apikey={TWELVEDATA_API_KEY}"
    try:
        r = requests.get(url, timeout=10).json()
        if "values" in r:
            # Return closes in chronological order
            closes = [float(v["close"]) for v in reversed(r["values"])]
            return closes
        else:
            print(f"❌ TwelveData API error: {r}")
            return None
    except Exception as e:
        print(f"❌ Exception fetching historical prices: {e}")
        return None

# ===== CALCULATE SMA =====
def calculate_sma(prices):
    if len(prices) == 0:
        return None
    return sum(prices) / len(prices)

# ===== SIGNAL LOGIC =====
def generate_signal(prices):
    global last_signal
    if len(prices) < 2:
        return None  # Not enough data

    sma = calculate_sma(prices[:-1])  # exclude latest candle for SMA
    latest_close = prices[-1]

    if latest_close > sma:
        signal = "💚 BUY"
    elif latest_close < sma:
        signal = "♥️ SELL"
    else:
        signal = None

    # Avoid duplicate signals
    if signal == last_signal:
        return None

    last_signal = signal
    return signal

# ===== MAIN BOT =====
def run_bot(manual=False):
    if not manual and not is_london_session():
        print("⏱ Outside London session")
        return

    prices = get_historical_prices()
    if not prices:
        print("❌ No price data available")
        return

    signal = generate_signal(prices)
    if signal:
        now = datetime.datetime.now(LONDON_TZ).strftime("%Y-%m-%d %H:%M")
        message = (
            f"🔥 {signal} Signal {'(London Session)' if not manual else '(London session)'}\n"
            f"💰 Pair: EUR/USD\n"
            f"💵 Price: {prices[-1]}\n"
            f"🕒 Time: {now}"
        )
        send_telegram(message)
    else:
        print("No new signal to send")

# ===== HANDLE MANUAL FLAG =====
manual = False
for arg in sys.argv:
    if arg.lower() in ["--manual=true", "--manual=1"]:
        manual = True

if __name__ == "__main__":
    run_bot(manual=manual)
