import os
import requests
import pandas as pd
import numpy as np

# Load Environment Variables
API_KEY = os.getenv("TWELVEDATA_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not API_KEY:
    print("❌ Error: 'TWELVEDATA_API_KEY' is missing or not set in environment secrets.")
    exit(1)

url = "https://twelvedata.com"

params = {
    "symbol": "XAU/USD",
    "interval": "15min",   
    "outputsize": 300,  
    "apikey": API_KEY
}

try:
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"❌ API HTTP Error Status {response.status_code}.")
        exit(1)
        
    try:
        res_data = response.json()
    except Exception:
        print("❌ Server did not respond with valid JSON text.")
        exit(1)
    
    if "values" not in res_data:
        print("❌ API Error payload returned from Twelve Data:", res_data)
        exit(1)
        
    data = res_data["values"]
    df = pd.DataFrame(data)
    df = df.iloc[::-1].reset_index(drop=True)  

    for c in ["open", "high", "low", "close"]:
        df[c] = df[c].astype(float)

    # --- Technical Indicators ---
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df["rsi"] = 100 - (100 / (1 + rs))
    
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()

    df["prev_high"] = df["high"].shift(1)
    df["prev_low"] = df["low"].shift(1)

    last = df.iloc[-1]

    if pd.isna(last["ema_200"]) or pd.isna(last["rsi"]) or pd.isna(last["atr"]):
        print("❌ Error: Insufficient historical candles to compute indicator metrics.")
        exit(1)

    entry = last["close"]
    ema50 = last["ema_50"]
    ema200 = last["ema_200"]
    rsi_val = last["rsi"]
    atr_val = last["atr"]
    prev_high = last["prev_high"]
    prev_low = last["prev_low"]

    # Strategy Conditions
    cond_ema_buy = ema50 > ema200
    cond_price_buy = (entry > ema50) and (entry > ema200)
    cond_rsi_buy = rsi_val > 55
    cond_break_buy = entry > prev_high

    cond_ema_sell = ema50 < ema200
    cond_price_sell = (entry < ema50) and (entry < ema200)
    cond_rsi_sell = rsi_val < 45
    cond_break_sell = entry < prev_low

    is_buy = cond_ema_buy and cond_price_buy and cond_rsi_buy and cond_break_buy
    is_sell = cond_ema_sell and cond_price_sell and cond_rsi_sell and cond_break_sell

    if is_buy or is_sell:
        direction = "BUY" if is_buy else "SELL"
        emoji = "🟢" if is_buy else "🔴"
        trend_status = "✔ EMA50 > EMA200" if is_buy else "✔ EMA50 < EMA200"
        breakout_status = "✔ Previous High Broken" if is_buy else "✔ Previous Low Broken"
        
        # --- DYNAMIC CONFIDENCE CALCULATION ENGINE ---
        # Base confidence starts at 70% if all baseline rules are met
        base_confidence = 70.0
        
        # 1. Momentum Component (Max +10%)
        # Awards more confidence the further RSI pushes into strong momentum territories
        if is_buy:
            rsi_excess = max(0, rsi_val - 55) # Scale from 55 to 75+
            momentum_score = (rsi_excess / 20.0) * 10.0
        else:
            rsi_excess = max(0, 45 - rsi_val) # Scale from 45 to 25-
            momentum_score = (rsi_excess / 20.0) * 10.0
        momentum_score = min(10.0, momentum_score)
        
        # 2. Trend Strength Component (Max +10%)
        # Uses the distance between EMA50 and EMA200 scaled by ATR to gauge trend power
        ema_gap = abs(ema50 - ema200)
        trend_score = (ema_gap / (atr_val * 2.0)) * 10.0 
        trend_score = min(10.0, trend_score)
        
        # 3. Breakout Strength Component (Max +10%)
        # Scores how aggressively the entry price smashed through the previous candle's barrier
        breakout_distance = (entry - prev_high) if is_buy else (prev_low - entry)
        breakout_score = (breakout_distance / (atr_val * 0.5)) * 10.0
        breakout_score = min(10.0, breakout_score)
        
        # Sum components and cap between 70% and 99%
        calculated_confidence = int(base_confidence + momentum_score + trend_score + breakout_score)
        confidence = max(70, min(99, calculated_confidence))
        
        # --- Risk Management Metrics ---
        sl_distance = atr_val * 1.5
        tp_distance = sl_distance * 2
        
        sl = entry - sl_distance if is_buy else entry + sl_distance
        tp = entry + tp_distance if is_buy else entry - tp_distance

        message = f"""📊 XAU/USD M15 SIGNAL

{emoji} {direction}

Confidence: {confidence}%

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

        telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"
        requests.post(telegram_url, data={"chat_id": CHAT_ID, "text": message})
        print("🚀 Signal matched! Sent message to Telegram successfully.")
        print(message)
    else:
        print("\n=== ⚠️ NO SIGNAL GENERATED ===")
        print(f"Current Market Data -> Entry: {entry:.2f} | RSI: {rsi_val:.1f} | EMA50: {ema50:.2f} | EMA200: {ema200:.2f}")

except Exception as e:
    print(f"❌ Script failed unexpectedly: {e}")
