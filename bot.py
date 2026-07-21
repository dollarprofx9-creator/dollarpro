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
