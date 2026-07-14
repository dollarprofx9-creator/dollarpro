import os
import requests
import pandas as pd
import pandas_ta as ta  # Efficient technical analysis library

# Load Environment Variables
API_KEY = os.getenv("TWELVEDATA_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

url = "https://api.twelvedata.com/time_series"

# Increased outputsize to 300 to ensure enough data for EMA 200 and RSI 14
params = {
    "symbol": "XAU/USD",
    "interval": "15min",   
    "outputsize": 300,
    "apikey": API_KEY
}

try:
    response = requests.get(url, params=params)
    res_data = response.json()
    
    if "values" not in res_data:
        print("Error fetching data from Twelve Data:", res_data)
        exit()
        
    data = res_data["values"]
    df = pd.DataFrame(data)
    df = df.iloc[::-1].reset_index(drop=True)  # Chronological order

    # Convert columns to float
    for c in ["open", "high", "low", "close"]:
        df[c] = df[c].astype(float)

    # Calculate Technical Indicators using pandas_ta
    df["ema_50"] = ta.ema(df["close"], length=50)
    df["ema_200"] = ta.ema(df["close"], length=200)
    df["rsi"] = ta.rsi(df["close"], length=14)
    df["atr"] = ta.atr(df["high"], df["low"], df["close"], length=14)

    # Shift columns to easily access historical data relative to current row
    df["prev_high"] = df["high"].shift(1)
    df["prev_low"] = df["low"].shift(1)

    # Extract the most recent closed candle data
    last = df.iloc[-1]

    # Check for NaN values (e.g., if there wasn't enough data for indicators)
    if pd.isna(last["ema_200"]) or pd.isna(last["rsi"]) or pd.isna(last["atr"]):
        print("Error: Not enough data points to compute indicators.")
        exit()

    # Extract required strategy values
    entry = last["close"]
    open_p = last["open"]
    high = last["high"]
    low = last["low"]
    ema50 = last["ema_50"]
    ema200 = last["ema_200"]
    rsi_val = last["rsi"]
    atr_val = last["atr"]
    prev_high = last["prev_high"]
    prev_low = last["prev_low"]

    # Evaluate Strategy Rules
    is_buy = (
        (ema50 > ema200) and 
        (entry > ema50) and (entry > ema200) and 
        (rsi_val > 55) and 
        (entry > prev_high)
    )

    is_sell = (
        (ema50 < ema200) and 
        (entry < ema50) and (entry < ema200) and 
        (rsi_val < 45) and 
        (entry < prev_low)
    )

    # Process and send signal if conditions are met
    if is_buy or is_sell:
        direction = "BUY" if is_buy else "SELL"
        emoji = "🟢" if is_buy else "🔴"
        trend_status = "✔ EMA50 > EMA200" if is_buy else "✔ EMA50 < EMA200"
        breakout_status = "✔ Previous High Broken" if is_buy else "✔ Previous Low Broken"
        
        # Calculate Risk Management Metrics
        sl_distance = atr_val * 1.5
        tp_distance = sl_distance * 2
        
        if is_buy:
            sl = entry - sl_distance
            tp = entry + tp_distance
        else:
            sl = entry + sl_distance
            tp = entry - tp_distance

        # Note: 'Confidence' is kept as a visual template placeholder based on your example
        message = f"""📊 XAU/USD M15 SIGNAL

{emoji} {direction}

Confidence: 94%

Entry: {entry:.2f}
Stop Loss: {sl:.2f}
Take Profit: {tp:.2f}

Trend:
{trend_status}

Momentum:
✔ RSI = {rsi_val:.1f}

Volatility:
✔ ATR = {atr_val:.2f}

Breakout:
{breakout_status}

Risk Reward:
1:2

Generated Automatically 🤖"""

        # Send message to Telegram
        telegram_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        telegram_res = requests.post(telegram_url, data={"chat_id": CHAT_ID, "text": message})
        
        print("Signal sent successfully!")
        print(message)
    else:
        print("No signal generated: Strategy market conditions were not fully satisfied.")

except Exception as e:
    print(f"An error occurred: {e}")
