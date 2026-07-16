name: Daily XAUUSD Signal

on:
  schedule:
    - cron: "*/15 * * * 1-5"
  workflow_dispatch:

jobs:
  signal:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests pandas numpy twelvedata

      # This runs the python script inline, ensuring it uses the newest code
      - name: Run Bot Inline
        env:
          TWELVEDATA_API_KEY: ${{ secrets.TWELVEDATA_API_KEY }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: |
          python -c '
          import os
          import requests
          import pandas as pd
          from twelvedata import TDClient

          API_KEY = os.getenv("TWELVEDATA_API_KEY")
          BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
          CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

          missing = []
          if not API_KEY: missing.append("TWELVEDATA_API_KEY")
          if not BOT_TOKEN: missing.append("TELEGRAM_BOT_TOKEN")
          if not CHAT_ID: missing.append("TELEGRAM_CHAT_ID")

          if missing:
              print(f"❌ Configuration Error: Missing secrets: {\", \".join(missing)}")
              exit(0)

          try:
              td = TDClient(apikey=API_KEY)
              ts = td.time_series(symbol="XAU/USD", interval="15min", outputsize=300)
              df = ts.as_pandas()
              df = df.iloc[::-1].reset_index(drop=True)

              for c in ["open", "high", "low", "close"]:
                  df[c] = df[c].astype(float)

              df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
              df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
              
              delta = df["close"].diff()
              gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
              loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
              rs = gain / (loss + 1e-10)
              df["rsi"] = 100 - (100 / (1 + rs))
              
              prev_close = df["close"].shift(1)
              tr = pd.concat([df["high"] - df["low"], (df["high"] - prev_close).abs(), (df["low"] - prev_close).abs()], axis=1).max(axis=1)
              df["atr"] = tr.rolling(window=14).mean()

              df["prev_high"] = df["high"].shift(1)
              df["prev_low"] = df["low"].shift(1)

              last = df.iloc[-1]
              entry, ema50, ema200, rsi_val, atr_val, prev_high, prev_low = last["close"], last["ema_50"], last["ema_200"], last["rsi"], last["atr"], last["prev_high"], last["prev_low"]

              is_buy = (ema50 > ema200) and (entry > ema50) and (entry > ema200) and (rsi_val > 55) and (entry > prev_high)
              is_sell = (ema50 < ema200) and (entry < ema50) and (entry < ema200) and (rsi_val < 45) and (entry < prev_low)

              telegram_url = f"https://telegram.org{BOT_TOKEN}/sendMessage"

              if is_buy or is_sell:
                  direction = "BUY" if is_buy else "SELL"
                  emoji = "🟢" if is_buy else "🔴"
                  trend_status = "✔ EMA50 > EMA200" if is_buy else "✔ EMA50 < EMA200"
                  breakout_status = "✔ Previous High Broken" if is_buy else "✔ Previous Low Broken"
                  
                  base_confidence = 70.0
                  rsi_excess = max(0, rsi_val - 55) if is_buy else max(0, 45 - rsi_val)
                  momentum_score = min(10.0, (rsi_excess / 20.0) * 10.0)
                  trend_score = min(10.0, (abs(ema50 - ema200) / (atr_val * 2.0)) * 10.0)
                  breakout_distance = (entry - prev_high) if is_buy else (prev_low - entry)
                  breakout_score = min(10.0, (breakout_distance / (atr_val * 0.5)) * 10.0)
                  
                  confidence = max(70, min(99, int(base_confidence + momentum_score + trend_score + breakout_score)))
                  sl_distance = atr_val * 1.5
                  tp_distance = sl_distance * 2
                  sl = entry - sl_distance if is_buy else entry + sl_distance
                  tp = entry + tp_distance if is_buy else entry - tp_distance

                  message = f"📊 XAU/USD M15 SIGNAL\n\n{emoji} {direction}\n\nConfidence: {confidence}%\n\nEntry: {entry:.2f}\nStop Loss: {sl:.2f}\nTake Profit: {tp:.2f}\n\nTrend:\n{trend_status}\n\nMomentum:\n✔ RSI = {rsi_val:.1f}\n\nVolatility:\n✔ ATR = {atr_val:.2f}\n\nBreakout:\n{breakout_status}\n\nRisk Reward:\n1:2\n\nGenerated Automatically 🤖"
              else:
                  message = f"📊 XAU/USD M15 SIGNAL\n\n⚪ NO SIGNAL\n\nMarket conditions do not fully align. Sitting on hands to manage risk. 🛡️\n\nCurrent Metrics:\n• Price: {entry:.2f}\n• RSI: {rsi_val:.1f} (Filter: >55 or <45)\n• EMA50: {ema50:.2f}\n• EMA200: {ema200:.2f}\n\nTimeframe: M15\nGenerated Automatically 🤖"

              res = requests.post(telegram_url, data={"chat_id": CHAT_ID, "text": message})
              print("🚀 Channel update complete." if res.status_code == 200 else f"❌ Telegram Error: {res.text}")
          except Exception as e:
              print(f"❌ Failed: {e}")
          '
