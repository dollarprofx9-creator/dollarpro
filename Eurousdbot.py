import requests
import os
import datetime
import pytz

# =========================
# ENV VARIABLES
# =========================
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TWELVEDATA_API_KEY:
    raise ValueError("❌ TWELVEDATA_API_KEY is missing")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is missing")

if not TELEGRAM_CHAT_ID:
    raise ValueError("❌ TELEGRAM_CHAT_ID is missing")

# =========================
# SETTINGS
# =========================
SYMBOL = "EUR/USD"
DISPLAY_PAIR = "EUR/USD"
INTERVAL = "15min"
SMA_PERIOD = 20
TIMEZONE = pytz.timezone("Africa/Lagos")

# =========================
# TELEGRAM
# =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload, timeout=10)
    print("📨 Telegram response:", response.text)

# =========================
# FETCH DATA
# =========================
def get_price_data():
    url = (
        "https://api.twelvedata.com/time_series"
        f"?symbol={SYMBOL}"
        f"&interval={INTERVAL}"
        f"&outputsize={SMA_PERIOD + 2}"
        f"&apikey={TWELVEDATA_API_KEY}"
    )

    data = requests.get(url, timeout=10).json()

    if "values" not in data:
        raise ValueError(f"❌ TwelveData API error: {data}")

    values = list(reversed(data["values"]))
    closes = [float(v["close"]) for v in values]

    last_close_price = closes[-1]
    candle_time = values[-1]["datetime"]

    return closes, last_close_price, candle_time

# =========================
# SMA LOGIC
# =========================
def calculate_sma(prices):
    return sum(prices) / len(prices)

def generate_signal(closes):
    last_close = closes[-1]
    sma = calculate_sma(closes[-SMA_PERIOD-1:-1])

    print(f"📊 Last Close: {last_close}")
    print(f"📈 SMA({SMA_PERIOD}): {sma}")

    if last_close > sma:
        return "BUY"
    elif last_close < sma:
        return "SELL"
    return None

# =========================
# MAIN
# =========================
def main():
    now = datetime.datetime.now(TIMEZONE)
    date_str = now.strftime("%Y-%m-%d %H:%M")

    print("🕒 Bot run time (Nigeria):", date_str)

    closes, price, candle_time = get_price_data()
    signal = generate_signal(closes)

    if not signal:
        print("ℹ️ No signal generated")
        return

    emoji = "💚" if signal == "BUY" else "💔"

    message = (
        f"🔥{emoji} {signal} Signal (London Session Start)\n"
        f"💰 Pair: {DISPLAY_PAIR}\n"
        f"💵 Price: {price}\n"
        f"🕒 Session: London\n"
        f"📅 Date: {date_str}"
    )

    send_telegram(message)
    print("✅ Signal sent")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    main()
