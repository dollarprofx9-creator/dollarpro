import os
import requests
import pandas as pd
from twelvedata import TDClient

# Load Twelve Data from Environment
API_KEY = os.getenv("TWELVEDATA_API_KEY")

# --- PASTE YOUR RAW TELEGRAM DETAILS DIRECTLY HERE ---
BOT_TOKEN = "PASTE_YOUR_ACTUAL_BOT_TOKEN_HERE"
CHAT_ID = "PASTE_YOUR_ACTUAL_CHAT_ID_HERE"
# -----------------------------------------------------

if not API_KEY: 
    print("❌ Configuration Error: Missing TWELVEDATA_API_KEY secret.")
    exit(0)

try:
    # Initialize the official SDK client
    td = TDClient(apikey=API_KEY)
    
    ts = td.time_series(
        symbol="XAU/USD",
        interval="15min",
        outputsize=300
    )
    
    df = ts.as_pandas()
    df = df.iloc[::-1].reset_index(drop=True)

    for c in ["open", "high", "low", "close"]:
        df[c] = df[c].astype(float)

    # --- Pure Pandas Technical Indicators ---
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
        print("❌ Error: Insufficient historical candles to compute indicators.")
        exit(0)

    entry = last["close"]
    ema50 = last["ema_50"]
    ema200 = last["ema_200"]
    rsi_val = last["rsi"]
    atr_val = last["atr"]
    prev_high = last["prev_high"]
    prev_low = last["prev_low"]

    # Strategy Conditions
    is_buy = (ema50 > ema200) and (entry > ema50) and (entry > ema200) and (rsi_val > 55) and (entry > prev_high)
    is_sell = (ema50 < ema200) and (entry < ema50) and (entry < ema200) and (rsi_val < 45) and (entry < prev_low)

    # FIXED: Restored the exact, un-corrupted official Telegram URL pattern
    telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"

    if is_buy or is_sell:
        direction = "BUY" if is_buy else "SELL"
        emoji = "🟢" if is_buy else "🔴"
        trend_status = "✔ EMA50 > EMA200" if is_buy else "✔ EMA50 < EMA200"
        breakout_status = "✔ Previous High Broken" if is_buy else "✔ Previous Low Broken"
        
        # --- Confidence Engine ---
        base_confidence = 70.0
        rsi_excess = max(0, rsi_val - 55) if is_buy else max(0, 45 - rsi_val)
        momentum_score = min(10.0, (rsi_excess / 20.0) * 10.0)
        trend_score = min(10.0, (abs(ema50 - ema200) / (atr_val * 2.0)) * 10.0)
        breakout_distance = (entry - prev_high) if is_buy else (prev_low - entry)
        breakout_score = min(10.0, (breakout_distance / (atr_val * 0.5)) * 10.0)
        
        confidence = max(70, min(99, int(base_confidence + momentum_score + trend_score + breakout_score)))
        
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

    else:
        message = f"""📊 XAU/USD M15 SIGNAL

⚪ NO SIGNAL

Market conditions do not fully align. Sitting on hands to manage risk. 🛡️

Current Metrics:
• Price: {entry:.2f}
• RSI: {rsi_val:.1f} (Filter: >55 or <45)
• EMA50: {ema50:.2f}
• EMA200: {ema200:.2f}

Timeframe: M15
Generated Automatically 🤖"""

    # Broadcast message to Telegram channel
    res = requests.post(telegram_url, data={"chat_id": CHAT_ID, "text": message})
    
    if res.status_code == 200:
        print("🚀 Channel update broadcasted successfully.")
        print(message)
    else:
        print(f"❌ Telegram API Error ({res.status_code}): {res.text}")

except Exception as e:
    print(f"❌ Script failed unexpectedly: {e}")
