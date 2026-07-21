import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# ==========================
# Environment Variables
# ==========================
API_KEY = os.getenv("TWELVEDATA_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==========================
# Twelve Data API
# ==========================
url = "https://api.twelvedata.com/time_series"

params = {
    "symbol": "XAU/USD",
    "interval": "15min",
    "outputsize": 100,
    "apikey": API_KEY
}

response = requests.get(url, params=params)
response.raise_for_status()

result = response.json()

if "values" not in result:
    raise Exception(result)

data = result["values"]

# ==========================
# DataFrame
# ==========================
df = pd.DataFrame(data)

# Oldest candle first
df = df.iloc[::-1].reset_index(drop=True)

# Convert prices to float
for col in ["open", "high", "low", "close"]:
    df[col] = df[col].astype(float)
    # ==========================
# ATR (14) Calculation
# ==========================
high = df["high"]
low = df["low"]
close = df["close"]

prev_close = close.shift()

tr = pd.concat(
    [
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ],
    axis=1,
).max(axis=1)

atr = tr.rolling(14).mean().iloc[-1]

# ==========================
# Last Closed Candle
# ==========================
last = df.iloc[-1]

entry = last["close"]

sl_distance = atr * 1.5
tp_distance = sl_distance * 2

# ==========================
# Nigeria Time (WAT)
# ==========================
wat_time = datetime.utcnow() + timedelta(hours=1)

signal_date = wat_time.strftime("%d %b %Y")
signal_time = wat_time.strftime("%I:%M %p")

# ==========================
# Determine Trade Direction
# ==========================
if last["close"] > last["open"]:

    signal = "🟢 BUY"
    stop_loss = entry - sl_distance
    take_profit = entry + tp_distance

else:
    # Bearish candle OR Doji
    signal = "🔴 SELL"
    stop_loss = entry + sl_distance
    take_profit = entry - tp_distance
    # ==========================
# Build Telegram Message
# ==========================
if signal == "⚪ NO SIGNAL":

    message = f"""📊 XAUUSD SIGNAL

{signal}

The latest M15 candle closed as a Doji.

Timeframe: M15
Date: {signal_date}
Signal Time: {signal_time} WAT
"""

else:

    message = f"""📊 XAUUSD SIGNAL

{signal}

Entry: {entry:.2f}
Stop Loss: {stop_loss:.2f}
Take Profit: {take_profit:.2f}

ATR(14): {atr:.2f}

Timeframe: M15
Date: {signal_date}
Signal Time: {signal_time} WAT
"""
    # ==========================
# Send Telegram Message
# ==========================
telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

response = requests.post(
    telegram_url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

response.raise_for_status()

print("Signal sent successfully!")
print(message)
