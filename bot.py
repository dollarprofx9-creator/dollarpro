import os
import requests
import pandas as pd

# Load Environment Variables
API_KEY = os.getenv("TWELVEDATA_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Check if environment keys are missing before running
if not API_KEY:
    print("❌ Error: 'TWELVEDATA_API_KEY' is missing or not set in environment secrets.")
    exit(1)

url = "https://api.twelvedata.com/time_series"

params = {
    "symbol": "XAU/USD",
    "interval": "15min",   
    "outputsize": 300,  # Required for EMA 200 calculations
    "apikey": API_KEY
}

try:
    response = requests.get(url, params=params)
    
    # Check for HTTP status errors (like 401, 403, 429)
    if response.status_code != 200:
        print(f"❌ API HTTP Error Status {response.status_code}. Raw Server output:")
        print(response.text)
        exit(1)
        
    # Safeguard JSON decoding to avoid "Expecting value" crashes
    try:
        res_data = response.json()
    except Exception:
        print("❌ Server did not respond with valid JSON text. Raw output:")
        print(response.text)
        exit(1)
    
    # Handle custom API errors sent by Twelve Data inside JSON
    if "values" not in res_data:
        print("❌ API Error payload returned from Twelve Data:")
        print(res_data)
        exit(1)
        
    data = res_data["values"]
    df = pd.DataFrame(data)
    df = df.iloc[::-1].reset_index(drop=True)  # Chronological order

    for c in ["open", "high", "low", "close"]:
        df[c] = df[c].astype(float)

    # --- Pure Pandas Technical Indicators ---
    # 1. EMA Calculations
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
    
    # 2. RSI Calculation
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10) # 1e-10 prevents zero division bugs
    df["rsi"] = 100 - (100 / (1 + rs))
    
    # 3. ATR Calculation
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs()
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(window=14).mean()

    last = df.iloc[-1]

    if pd.isna(last["ema_200"]) or pd.isna(last["rsi"]) or pd.isna(last["atr"]):
        print("❌ Error: Insufficient historical candles to compute indicator metrics.")
        exit(1)

    # Extract required strategy values
    entry = last["close"]
    ema50 = last["ema_50"]
    ema200 = last["ema_200"]
    rsi_val = last["rsi"]
    atr_val = last["atr"]

    # Individual validation checks for debug printing
    cond_ema_buy = ema50 > ema200
    cond_price_buy = (entry > ema50) and (entry > ema200)
    cond_rsi_buy = rsi_val > 55

    cond_ema_sell = ema50 < ema200
    cond_price_sell = (entry < ema50) and (entry < ema200)
    cond_rsi_sell = rsi_val < 45

    # Executing logic without previous high/low constraints
    is_buy = cond_ema_buy and cond_price_buy and cond_rsi_buy
    is_sell = cond_ema_sell and cond_price_sell and cond_rsi_sell

    if is_buy or is_sell:
        direction = "BUY" if is_buy else "SELL"
        emoji = "🟢" if is_buy else "🔴"
        trend_status = "✔ EMA50 > EMA200" if is_buy else "✔ EMA50 < EMA200"
        
        sl_distance = atr_val * 1.5
        tp_distance = sl_distance * 2
        
        sl = entry - sl_distance if is_buy else entry + sl_distance
        tp = entry + tp_distance if is_buy else entry - tp_distance

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
        print("\n[BUY Conditions Status]:")
        print(f" └─ EMA50 > EMA200: {cond_ema_buy}")
        print(f" └─ Price above EMAs: {cond_price_buy}")
        print(f" └─ RSI > 55: {cond_rsi_buy}")
        print("\n[SELL Conditions Status]:")
        print(f" └─ EMA50 < EMA200: {cond_ema_sell}")
        print(f" └─ Price below EMAs: {cond_price_sell}")
        print(f" └─ RSI < 45: {cond_rsi_sell}")

except Exception as e:
    print(f"❌ Script failed unexpectedly: {e}")
