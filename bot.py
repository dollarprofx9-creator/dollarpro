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
# Validate Environment Variables
# ==========================
if not API_KEY:
    raise Exception("TWELVEDATA_API_KEY is not set")

if not BOT_TOKEN:
    raise Exception("TELEGRAM_BOT_TOKEN is not set")

if not CHAT_ID:
    raise Exception("TELEGRAM_CHAT_ID is not set")

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

response = requests.get(url, params=params, timeout=30)
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
    axis=1
).max(axis=1)

atr = tr.rolling(14).mean().iloc[-1]

if pd.isna(atr):
    raise Exception("Unable to calculate ATR")

# ==========================
# Last Closed Candle
# ==========================
last = df.iloc[-1]

entry = last["close"]

# ==========================
# SL / TP Calculation
# ==========================
sl_distance = atr * 1.5
tp_distance = sl_distance * 2

# ==========================
# Nigeria Time (WAT)
# ==========================
wat_time = datetime.utcnow() + timedelta(hours=1)

signal_date = wat_time.strftime("%d %b %Y")
signal_time = wat_time.strftime("%I:%M %p")

# ==========================
# Signal Exit Time
# 2 Hours After Signal
# ==========================
exit_time = wat_time + timedelta(hours=2)

exit_time_formatted = exit_time.strftime("%I:%M %p")

# ==========================
# Determine Trade Direction
# ==========================
# Bullish candle = BUY
# Bearish candle = SELL
# Doji = SELL

if last["close"] > last["open"]:

    signal = "🟢 BUY"

    stop_loss = entry - sl_distance
    take_profit = entry + tp_distance

else:

    # Bearish candle OR Doji = SELL
    signal = "🔴 SELL"

    stop_loss = entry + sl_distance
    take_profit = entry - tp_distance

# ==========================
# Telegram Message
# ==========================
message = f"""📊 XAUUSD SIGNAL

{signal}

Entry: {entry:.2f}
Stop Loss: {stop_loss:.2f}
Take Profit: {take_profit:.2f}

Timeframe: M15
Date: {signal_date}
Signal Time: {signal_time} WAT
Signal Exit Time: {exit_time_formatted} WAT

⚠️ Close the trade at the stated exit time if TP or SL has not been reached. Manage your risk accordingly."""

# ==========================
# Send Telegram Message
# ==========================
telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

telegram_response = requests.post(
    telegram_url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=30
)

telegram_response.raise_for_status()

# ==========================
# Output
# ==========================
print("Signal sent successfully!")
print()
print(message)
