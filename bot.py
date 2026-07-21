import os
import requests
import pandas as pd
from datetime import datetime, timedelta

# Environment Variables
API_KEY = os.getenv("TWELVEDATA_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Twelve Data API Endpoint
url = "https://api.twelvedata.com/time_series"

params = {
    "symbol": "XAU/USD",
    "interval": "15min",
    "outputsize": 100,
    "apikey": API_KEY
}

# Get Market Data
response = requests.get(url, params=params)
data = response.json()["values"]

# Create DataFrame
df = pd.DataFrame(data)
df = df.iloc[::-1].reset_index(drop=True)

# Convert Columns to Float
for col in ["open", "high", "low", "close"]:
    df[col] = df[col].astype(float)

high = df["high"]
low = df["low"]
close = df["close"]

# ATR(14) Calculation
prev_close = close.shift()

tr = pd.concat([
    high - low,
    (high - prev_close).abs(),
    (low - prev_close).abs()
], axis=1).max(axis=1)

atr = tr.rolling(14).mean().iloc[-1]

# Latest Candle
last = df.iloc[-1]

entry = last["close"]

# Calculate Buy Levels
buy_sl_distance = atr * 1.5
buy_tp_distance = buy_sl_distance * 2

buy_sl = entry - buy_sl_distance
buy_tp = entry + buy_tp_distance

# Calculate Sell Levels
sell_sl = entry + buy_sl_distance
sell_tp = entry - buy_tp_distance

# Nigeria Time (WAT)
wat_time = datetime.utcnow() + timedelta(hours=1)

signal_date = wat_time.strftime("%d %b %Y")
signal_time = wat_time.strftime("%I:%M %p")
# Telegram Message Format
message = f"""📊 XAUUSD SIGNAL

🟢 BUY

Entry: {entry:.2f}
Stop Loss: {buy_sl:.2f}
Take Profit: {buy_tp:.2f}

Timeframe: M15
Date: {signal_date}
Signal Time: {signal_time} WAT

🔴 SELL

Entry: {entry:.2f}
Stop Loss: {sell_sl:.2f}
Take Profit: {sell_tp:.2f}

Timeframe: M15
Date: {signal_date}
Signal Time: {signal_time} WAT
"""

# Send to Telegram
telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

requests.post(
    telegram_url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(message)
