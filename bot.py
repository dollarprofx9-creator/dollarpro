import os
import requests

# ==========================
# CONFIG
# ==========================
API_KEY = os.getenv("TWELVE_DATA_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Try XAU/USD first. If your account doesn't support it,
# change to "XAUUSD".
SYMBOL = "XAU/USD"
INTERVAL = "1h"

# ==========================
# GET DATA
# ==========================
url = "https://api.twelvedata.com/time_series"

params = {
    "symbol": SYMBOL,
    "interval": INTERVAL,
    "outputsize": 100,
    "apikey": API_KEY,
}

response = requests.get(url, params=params)
result = response.json()

print(result)  # Shows API response in GitHub Actions logs

if "values" not in result:
    raise Exception(f"Twelve Data API Error:\n{result}")

candles = list(reversed(result["values"]))

# ==========================
# CONVERT TO FLOATS
# ==========================
for candle in candles:
    candle["open"] = float(candle["open"])
    candle["high"] = float(candle["high"])
    candle["low"] = float(candle["low"])
    candle["close"] = float(candle["close"])

# ==========================
# SMA 50
# ==========================
closes = [c["close"] for c in candles]

sma50 = sum(closes[-50:]) / 50

# ==========================
# ATR 14
# ==========================
trs = []

for i in range(1, len(candles)):
    high = candles[i]["high"]
    low = candles[i]["low"]
    prev_close = candles[i - 1]["close"]

    tr = max(
        high - low,
        abs(high - prev_close),
        abs(low - prev_close),
    )

    trs.append(tr)

atr = sum(trs[-14:]) / 14

# ==========================
# SIGNAL
# ==========================
entry = closes[-1]

if entry > sma50:
    direction = "BUY"
else:
    direction = "SELL"

sl_distance = atr * 1.5
tp_distance = sl_distance * 2

if direction == "BUY":
    stop_loss = entry - sl_distance
    take_profit = entry + tp_distance
else:
    stop_loss = entry + sl_distance
    take_profit = entry - tp_distance

# ==========================
# MESSAGE
# ==========================
message = f"""
📊 DAILY XAUUSD SIGNAL

Direction: {direction}

Entry: {entry:.2f}

Stop Loss: {stop_loss:.2f}

Take Profit: {take_profit:.2f}

ATR(14): {atr:.2f}

SMA(50): {sma50:.2f}

Risk Reward: 1:2

Timeframe: H1

Generated Automatically
"""

print(message)

# ==========================
# SEND TO TELEGRAM
# ==========================
telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

telegram_response = requests.post(
    telegram_url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(telegram_response.text)
