import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")


# ============================================================
# SYMBOLS
# ============================================================

SYMBOLS = {
    "EURUSD": "EUR/USD",
    "BTCUSD": "BTC/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USDCAD": "USD/CAD",
    "NZDUSD": "NZD/USD",
    "XAUUSD": "XAU/USD",
}


# ============================================================
# TWELVE DATA REQUEST
# ============================================================

def api_request(endpoint, params):

    query = urllib.parse.urlencode(params)

    url = f"https://api.twelvedata.com/{endpoint}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        data = response.read().decode("utf-8")

        return json.loads(data)


# ============================================================
# GET CURRENT QUOTE
# ============================================================

def get_quote(symbol):

    data = api_request(
        "quote",
        {
            "symbol": symbol,
            "apikey": TWELVEDATA_API_KEY
        }
    )

    if "code" in data:

        raise Exception(
            data.get(
                "message",
                "Unknown Twelve Data error"
            )
        )

    return data


# ============================================================
# GET DAILY DATA
# ============================================================

def get_daily_history(symbol):

    data = api_request(
        "time_series",
        {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": 10,
            "apikey": TWELVEDATA_API_KEY
        }
    )

    if "code" in data:

        raise Exception(
            data.get(
                "message",
                "Unknown Twelve Data error"
            )
        )

    return data.get("values", [])


# ============================================================
# CALCULATE DAILY CHANGE
# ============================================================

def calculate_daily_change(
    current_price,
    previous_close
):

    if previous_close is None:
        return None

    previous_close = float(previous_close)

    if previous_close == 0:
        return None

    return (
        (current_price - previous_close)
        / previous_close
    ) * 100


# ============================================================
# CALCULATE WEEKLY CHANGE
# ============================================================

def calculate_weekly_change(
    symbol,
    current_price
):

    try:

        history = get_daily_history(symbol)

        if not history:
            return None

        today = datetime.now(
            timezone.utc
        ).date()

        current_year, current_week, _ = (
            today.isocalendar()
        )

        week_candles = []

        for candle in history:

            candle_date = datetime.strptime(
                candle["datetime"],
                "%Y-%m-%d"
            ).date()

            candle_year, candle_week, _ = (
                candle_date.isocalendar()
            )

            if (
                candle_year == current_year
                and candle_week == current_week
            ):

                week_candles.append(candle)

        if not week_candles:
            return None

        # Twelve Data normally returns newest
        # candle first, so the last candle is
        # the oldest available candle of the week.

        oldest_candle = week_candles[-1]

        week_open = float(
            oldest_candle["open"]
        )

        if week_open == 0:
            return None

        return (
            (current_price - week_open)
            / week_open
        ) * 
