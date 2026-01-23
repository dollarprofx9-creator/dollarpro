import os
import requests
import pandas as pd

# ================= CONFIG =================
API_KEY = os.environ.get("TWELVEDATA_API_KEY")
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

SYMBOL = "XAU/USD"
INTERVAL = "15min"
SMA_PERIOD = 20
ATR_PERIOD = 14

DATA_URL = "https://api.twelvedata.com/time_series"

# ================= TELEGRAM =================
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    r = requests.post(url, data=payload, timeout=20)
    if not r.ok:
        raise RuntimeError(r.text)

# ================= DATA =================
def get_data():
    url = f"{DATA_URL}?symbol={SYMBOL}&interval={INTERVAL}&outputsize=200&apikey={API_KEY}"
    r = requests.get(url, timeout=20)
    data = r.json()
    if "values" not in data:
        raise RuntimeError(data)

    df = pd.DataFrame(data["values"])
    df = df.astype(float, errors="ignore")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    return df

# ================= INDICATORS =================
def calculate_sma(series, period):
    return series.rolling(period).mean()

def calculate_atr(df, period):
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    return tr.rolling(period).mean()

# ================= MAIN =================
def main():
    df = get_data()

    df["SMA"] = calculate_sma(df["close"], SMA_PERIOD)
    df["ATR"] = calculate_atr(df, ATR_PERIOD)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    close = last["close"]
    prev_close = prev["close"]
    sma = last["SMA"]
    atr = last["ATR"]

    trade_type = None

    # ===== SMA ENTRY LOGIC =====
    if prev_close < sma and close > sma:
        trade_type = "BUY"
    elif prev_close > sma and close < sma:
        trade_type = "SELL"

    if not trade_type:
        print("ℹ️ No active SMA trade")
        return

    # ===== EXIT MESSAGE =====
    message = (
        f"🚪 XAUUSD EXIT ALERT\n\n"
        f"⚠️ Reason: EXIT – MARKET LOSING LIQUIDITY\n"
        f"📍 Trade Type: {trade_type}\n"
        f"💰 Price: {close:.2f}\n\n"
        f"❌ Trade closed automatically"
    )

    send_telegram(message)
    print("✅ Exit message sent")

if __name__ == "__main__":
    main()
