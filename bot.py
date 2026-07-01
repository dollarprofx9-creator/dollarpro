import os
import requests
import pandas as pd

API_KEY = os.getenv("TWELVEDATA_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

url = "https://api.twelvedata.com/time_series"

params = {
    "symbol": "XAU/USD",
    "interval": "1h",
    "outputsize": 100,
    "apikey": API_KEY
}

response = requests.get(url, params=params)
data = response.json()["values"]

df = pd.DataFrame(data)
df = df.iloc[::-1]

for c in ["open","high","low","close"]:
    df[c] = df[c].astype(float)

high = df["high"]
low = df["low"]
close = df["close"]

prev_close = close.shift()

tr = pd.concat([
    high-low,
    (high-prev_close).abs(),
    (low-prev_close).abs()
], axis=1).max(axis=1)

atr = tr.rolling(14).mean().iloc[-1]

last = df.iloc[-1]

entry = last["close"]

direction = "BUY" if last["close"] > last["open"] else "SELL"

sl_distance = atr * 1.5
tp_distance = sl_distance * 2

if direction == "BUY":
    sl = entry - sl_distance
    tp = entry + tp_distance
else:
    sl = entry + sl_distance
    tp = entry - tp_distance

message = f"""
📊 DAILY XAUUSD SIGNAL
Direction: {direction}
Entry: {entry:.2f}
Stop Loss: {sl:.2f}
Take Profit: {tp:.2f}
ATR(14): {atr:.2f}
Risk Reward: 1:2
Timeframe: H1
Generated Automatically
"""

requests.post(
    f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": message
    }
)

print(message)
