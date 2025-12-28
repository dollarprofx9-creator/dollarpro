import requests
import os
import datetime
import pytz

# =========================
# ENVIRONMENT VARIABLES
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
INTERVAL = "15min"
SMA_PERIOD = 20
TIMEZONE = pytz.timezone("Africa/Lagos")

# =========================
# TELEGRAM FUNCTION
# =========================
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    response = requests.post(url, json=payload, timeout=10)
    print("📨 Telegram response:", response.text)

# =========================
# FETCH DATA FROM TWELVEDATA
# =========================
def get_price_data():
    url = (
        f"https://api.twelvedata.com/time_series"
        f"?symbol={SYMBOL}"
        f"&interval={INTERVAL}"
        f"&outputsize={SMA_PERIOD + 2}"
        f"&apikey={TWELVEDATA_API_KEY}"
    )

    response = requests.get(url, timeout=10).json()

    if "values" not in response:
        raise ValueError(f"❌ TwelveData error: {response}")

    values = list(reversed(response["values"]))
    closes = [float(candle["close"]) for candle in values]

    return closes, values[-1]["datetime"]

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
# MAIN BOT
# =========================
def main():
    now = datetime.datetime.now(TIMEZONE)
    print("🕒 Bot run time (Nigeria):", now.strftime("%Y-%m-%d %H:%M:%S"))

    closes, candle_time = get_price_data()
    signal = generate_signal(closes)

    if not signal:
        print("ℹ️ No clear signal")
        return

    message = (
        f"🔥 *{signal} Signal (London Session)*\n"
        f"💰 Pair: EUR/USD\n"
        f"⏱ Timeframe: 15M\n"
        f"📊 Strategy: SMA {SMA_PERIOD}\n"
        f"🕒 Candle Close: {candle_time}\n"
        f"📅 Date: {now.strftime('%Y-%m-%d %H:%M')}"
    )

    send_telegram(message)
    print("✅ Signal sent successfully")

# =========================
# RUN
# =========================
if __name__ == "__main__":
    main()
