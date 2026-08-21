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
# API REQUEST
# ============================================================

def api_request(endpoint, params):

    query = urllib.parse.urlencode(params)

    url = (
        "https://api.twelvedata.com/"
        + endpoint
        + "?"
        + query
    )

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
# GET DAILY HISTORY
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
# DAILY CHANGE
# ============================================================

def calculate_daily_change(
    current_price,
    previous_close
):

    if previous_close is None:
        return None

    if previous_close == 0:
        return None

    change = (
        (current_price - previous_close)
        / previous_close
    ) * 100

    return change


# ============================================================
# WEEKLY CHANGE
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

        current_year = today.isocalendar().year
        current_week = today.isocalendar().week

        week_candles = []

        for candle in history:

            candle_date = datetime.strptime(
                candle["datetime"],
                "%Y-%m-%d"
            ).date()

            candle_year = (
                candle_date.isocalendar().year
            )

            candle_week = (
                candle_date.isocalendar().week
            )

            if (
                candle_year == current_year
                and candle_week == current_week
            ):

                week_candles.append(candle)

        if not week_candles:
            return None

        oldest_candle = week_candles[-1]

        week_open = float(
            oldest_candle["open"]
        )

        if week_open == 0:
            return None

        weekly_change = (
            (current_price - week_open)
            / week_open
        ) * 100

        return weekly_change

    except Exception as error:

        print(
            "Weekly calculation error for "
            + symbol
            + ": "
            + str(error)
        )

        return None


# ============================================================
# FORMAT PRICE
# ============================================================

def format_price(value, symbol):

    if value is None:
        return "N/A"

    value = float(value)

    if symbol == "BTCUSD":
        return "${:,.2f}".format(value)

    if symbol == "XAUUSD":
        return "${:,.2f}".format(value)

    if symbol == "USDJPY":
        return "{:.3f}".format(value)

    return "{:.4f}".format(value)


# ============================================================
# FORMAT PERCENTAGE
# ============================================================

def format_percentage(value):

    if value is None:
        return "N/A"

    value = float(value)

    if value > 0:
        return "+{:.2f}%".format(value)

    if value < 0:
        return "{:.2f}%".format(value)

    return "0.00%"


# ============================================================
# DIRECTION EMOJI
# ============================================================

def direction_emoji(value):

    if value is None:
        return "⚪"

    if value > 0:
        return "🟢"

    if value < 0:
        return "🔴"

    return "⚪"


# ============================================================
# CREATE MARKET SECTION
# ============================================================

def create_market_section(
    display_symbol,
    api_symbol
):

    quote = get_quote(api_symbol)

    current_price = float(
        quote["close"]
    )

    high = float(
        quote["high"]
    )

    low = float(
        quote["low"]
    )

    previous_close_value = quote.get(
        "previous_close"
    )

    if previous_close_value:

        previous_close = float(
            previous_close_value
        )

    else:

        previous_close = None

    daily_change = calculate_daily_change(
        current_price,
        previous_close
    )

    weekly_change = calculate_weekly_change(
        api_symbol,
        current_price
    )

    emoji = direction_emoji(
        daily_change
    )

    section = (
        emoji
        + " "
        + display_symbol
        + "\n"
        + "💰 Price: "
        + format_price(
            current_price,
            display_symbol
        )
        + "\n"
        + "📈 Day High: "
        + format_price(
            high,
            display_symbol
        )
        + "\n"
        + "📉 Day Low: "
        + format_price(
            low,
            display_symbol
        )
        + "\n"
        + "🔒 Previous Close: "
        + format_price(
            previous_close,
            display_symbol
        )
        + "\n"
        + "📊 Daily Change: "
        + format_percentage(
            daily_change
        )
        + "\n"
        + "📅 Weekly Change: "
        + format_percentage(
            weekly_change
        )
        + "\n"
    )

    return section


# ============================================================
# BUILD MARKET UPDATE
# ============================================================

def build_market_update():

    today = datetime.now(
        timezone.utc
    ).strftime("%d %B %Y")

    message = (
        "📊 DAILY MARKET UPDATE\n"
        "📅 "
        + today
        + "\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    for display_symbol, api_symbol in SYMBOLS.items():

        try:

            section = create_market_section(
                display_symbol,
                api_symbol
            )

            message += section
            message += "\n"

        except Exception as error:

            print(
                "Error retrieving "
                + display_symbol
                + ": "
                + str(error)
            )

            message += (
                "⚠️ "
                + display_symbol
                + "\n"
                + "Unable to retrieve market data.\n\n"
            )

    message += (
        "━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Market data is for "
        "informational purposes only."
    )

    return message


# ============================================================
# SEND TELEGRAM MESSAGE
# ============================================================

def send_message(message):

    if not BOT_TOKEN:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN is not set"
        )

    if not CHAT_ID:
        raise ValueError(
            "TELEGRAM_CHAT_ID is not set"
        )

    url = (
        "https://api.telegram.org/"
        "bot"
        + BOT_TOKEN
        + "/sendMessage"
    )

    payload = urllib.parse.urlencode(
        {
            "chat_id": CHAT_ID,
            "text": message
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=30
    ) as response:

        result = json.loads(
            response.read().decode("utf-8")
        )

        if not result.get("ok"):

            raise Exception(
                result.get(
                    "description",
                    "Telegram API error"
                )
            )


# ============================================================
# VALIDATE ENVIRONMENT
# ============================================================

def validate_environment():

    missing = []

    if not BOT_TOKEN:
        missing.append(
            "TELEGRAM_BOT_TOKEN"
        )

    if not CHAT_ID:
        missing.append(
            "TELEGRAM_CHAT_ID"
        )

    if not TWELVEDATA_API_KEY:
        missing.append(
            "TWELVEDATA_API_KEY"
        )

    if missing:

        raise ValueError(
            "Missing environment variables: "
            + ", ".join(missing)
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "Starting Daily Market Update..."
    )

    validate_environment()

    message = build_market_update()

    print(message)

    send_message(message)

    print(
        "Daily market update sent successfully!"
        )
