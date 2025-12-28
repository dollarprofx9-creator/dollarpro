import requests
import os
import datetime
import pytz
import sys

# ===== ENV VARIABLES =====
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # numeric ID preferred

# ===== TIME SETTINGS =====
LONDON_TZ = pytz.timezone("Europe/London")
last_signal_sent = False

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
            closes = [float(v["close"]) for v in reversed(r["values"])]
            return closes
        else:
            print(f"❌ TwelveData API error: {r}")
            return None
    except Exception as e:
        print(f"❌ Exception fetching historical prices: {e}")
        return None

# ===== SMA LOGIC =====
def calculate_sma(prices):
    return sum(prices) / len(prices) if prices else None

def generate_signal(prices):
    sma = calculate_sma(prices[:-1])
    latest_close = prices[-1]
    if latest_close > sma:
        return "💚 BUY"
    elif latest_close < sma:
        return "♥️ SELL"
    return None

# ===== RUN BOT =====
def run_bot(manual=False):
    global last_signal_sent
    if last_signal_sent and not manual:
        print("✅ Signal already sent for today")
        return

    prices = get_historical_prices()
    if not prices:
        return

    signal = generate_signal(prices)
    if signal:
        now = datetime.datetime.now(LONDON_TZ).strftime("%Y-%m-%d %H:%M")
        message = (
            f"🔥 {signal} Signal {'(London session)' if not manual else '(London session)'}\n"
            f"💰 Pair: EUR/USD\n"
            f"💵 Price: {prices[-1]}\n"
            f"🕒 Time: {now}"
        )
        send_telegram(message)
        last_signal_sent = True
    else:
        print("No new signal")

# ===== MANUAL FLAG =====
manual = False
for arg in sys.argv:
    if arg.lower() in ["--manual=true", "--manual=1"]:
        manual = True

if __name__ == "__main__":
    run_bot(manual=manual)
