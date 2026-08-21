import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone


# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")


# ============================================================
# MARKET SYMBOLS
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
# SETTINGS
# ============================================================

MAX_RETRIES = 3

# Twelve Data Basic has an 8-credit/minute limit.
# Waiting between requests helps prevent 429 errors.
REQUEST_DELAY = 8


# ============================================================
# TWELVE DATA API REQUEST
# ============================================================

def api_request(endpoint, params):

    query = urllib.parse.urlencode(params)

    url = (
        "https://api.twelvedata.com/"
        + endpoint
        + "?"
        + query
    )

    for attempt in range(MAX_RETRIES):

        try:

            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "DollarProFX-MarketBot/1.0"
                }
            )

            with urllib.request.urlopen(
                request,
                timeout=30
            ) as response:

                raw_data = response.read().decode(
                    "utf-8"
                )

                data = json.loads(raw_data)

            # Twelve Data can return API errors
            # inside the JSON response.

            if isinstance(data, dict):

                if data.get("status") == "error":

                    code = data.get("code")
                    message = data.get(
                        "message",
                        "Unknown API error"
                    )

                    # Rate limit
                    if code == 429:

                        if attempt < MAX_RETRIES - 1:

                            print(
                                "Twelve Data rate limit reached."
                            )

                            print(
                                "Waiting 60 seconds..."
                            )

                            time.sleep(60)

                            continue

                    raise Exception(
                        "Twelve Data error "
                        + str(code)
                        + ": "
                        + str(message)
                    )

                if "code" in data:

                    code = data.get("code")

                    message = data.get(
                        "message",
                        "Unknown API error"
                    )

                    if code == 429:

                        if attempt < MAX_RETRIES - 1:

                            print(
                                "Rate limit reached. "
                                "Waiting 60 seconds..."
                            )

                            time.sleep(60)

                            continue

                    raise Exception(
                        "Twelve Data error "
                        + str(code)
                        + ": "
                        + str(message)
                    )

            return data

        except urllib.error.HTTPError as error:

            if error.code == 429:

                if attempt < MAX_RETRIES - 1:

                    print(
                        "HTTP 429 rate limit."
                    )

                    print(
                        "Waiting 60 seconds..."
                    )

                    time.sleep(60)

                    continue

            try:

                error_body = error.read().decode(
                    "utf-8"
                )

            except Exception:

                error_body = str(error)

            raise Exception(
                "HTTP "
                + str(error.code)
                + ": "
                + error_body
            )

        except urllib.error.URLError as error:

            if attempt < MAX_RETRIES - 1:

                print(
                    "Network error. Retrying..."
                )

                time.sleep(5)

                continue

            raise Exception(
                "Network error: "
                + str(error)
            )

    raise Exception(
        "API request failed after retries."
    )


# ============================================================
# GET CURRENT QUOTE
# ============================================================

def get_quote(symbol):

    print(
        "Getting quote for "
        + symbol
        + "..."
    )

    data = api_request(
        "quote",
        {
            "symbol": symbol,
            "apikey": TWELVEDATA_API_KEY
        }
    )

    return data


# ============================================================
# GET DAILY HISTORY
# ============================================================

def get_daily_history(symbol):

    print(
        "Getting daily history for "
        + symbol
        + "..."
    )

    data = api_request(
        "time_series",
        {
            "symbol": symbol,
            "interval": "1day",
            "outputsize": 10,
            "apikey": TWELVEDATA_API_KEY
        }
    )

    if not isinstance(data, dict):

        raise Exception(
            "Invalid historical data response."
        )

    if data.get("status") == "error":

        raise Exception(
            data.get(
                "message",
                "Historical data unavailable"
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

    return (
        (
            current_price
            - previous_close
        )
        / previous_close
    ) * 100


# ============================================================
# WEEKLY CHANGE
#
# Current price compared with the PREVIOUS
# WEEK'S FINAL CLOSE.
# ============================================================

def calculate_weekly_change(
    symbol,
    current_price
):

    try:

        history = get_daily_history(
            symbol
        )

        if not history:
            return None

        # Twelve Data normally returns newest
        # candle first.

        candles = []

        for candle in history:

            if "datetime" not in candle:
                continue

            candle_date = datetime.strptime(
                candle["datetime"],
                "%Y-%m-%d"
            ).date()

            candle_close = candle.get(
                "close"
            )

            if candle_close is None:
                continue

            candles.append(
                {
                    "date": candle_date,
                    "close": float(candle_close)
                }
            )

        if len(candles) < 2:
            return None

        today = datetime.now(
            timezone.utc
        ).date()

        current_week = (
            today.isocalendar().week
        )

        current_year = (
            today.isocalendar().year
        )

        # Find candles from the previous
        # calendar week.

        previous_week_candles = []

        for candle in candles:

            candle_year = (
                candle["date"]
                .isocalendar()
                .year
            )

            candle_week = (
                candle["date"]
                .isocalendar()
                .week
            )

            if (
                candle_year == current_year
                and candle_week
                == current_week - 1
            ):

                previous_week_candles.append(
                    candle
                )

        # Year boundary handling
        if not previous_week_candles:

            for candle in candles:

                candle_year = (
                    candle["date"]
                    .isocalendar()
                    .year
                )

                candle_week = (
                    candle["date"]
                    .isocalendar()
                    .week
                )

                if (
                    candle_year
                    < current_year
                ):

                    previous_week_candles.append(
                        candle
                    )

        if not previous_week_candles:
            return None

        # The oldest available candle in
        # the previous week is not what we
        # need. We need the LAST trading
        # day's close.

        previous_week_candles.sort(
            key=lambda x: x["date"]
        )

        previous_week_close = (
            previous_week_candles[-1]["close"]
        )

        if previous_week_close == 0:
            return None

        return (
            (
                current_price
                - previous_week_close
            )
            / previous_week_close
        ) * 100

    except Exception as error:

        print(
            "Weekly change error for "
            + symbol
            + ": "
            + str(error)
        )

        return None


# ============================================================
# FORMAT PRICE
# ============================================================

def format_price(
    value,
    display_symbol
):

    if value is None:
        return "N/A"

    value = float(value)

    if display_symbol == "BTCUSD":

        return "${:,.2f}".format(
            value
        )

    if display_symbol == "XAUUSD":

        return "${:,.2f}".format(
            value
        )

    if display_symbol == "USDJPY":

        return "{:.3f}".format(
            value
        )

    return "{:.4f}".format(
        value
    )


# ============================================================
# FORMAT PERCENTAGE
# ============================================================

def format_percentage(value):

    if value is None:
        return "N/A"

    value = float(value)

    if value > 0:

        return "+{:.2f}%".format(
            value
        )

    if value < 0:

        return "{:.2f}%".format(
            value
        )

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

    # -----------------------------
    # Get quote
    # -----------------------------

    quote = get_quote(
        api_symbol
    )

    # -----------------------------
    # Current price
    # -----------------------------

    if "close" not in quote:

        raise Exception(
            "Current price unavailable."
        )

    current_price = float(
        quote["close"]
    )

    # -----------------------------
    # High
    # -----------------------------

    high_value = quote.get(
        "high"
    )

    high = (
        float(high_value)
        if high_value is not None
        else None
    )

    # -----------------------------
    # Low
    # -----------------------------

    low_value = quote.get(
        "low"
    )

    low = (
        float(low_value)
        if low_value is not None
        else None
    )

    # -----------------------------
    # Previous close
    # -----------------------------

    previous_close_value = (
        quote.get("previous_close")
    )

    if previous_close_value:

        previous_close = float(
            previous_close_value
        )

    else:

        previous_close = None

    # -----------------------------
    # Daily change
    # -----------------------------

    daily_change = (
        calculate_daily_change(
            current_price,
            previous_close
        )
    )

    # -----------------------------
    # Wait before historical request
    # -----------------------------

    time.sleep(
        REQUEST_DELAY
    )

    # -----------------------------
    # Weekly change
    # -----------------------------

    weekly_change = (
        calculate_weekly_change(
            api_symbol,
            current_price
        )
    )

    # -----------------------------
    # Direction
    # -----------------------------

    emoji = direction_emoji(
        daily_change
    )

    # -----------------------------
    # Build section
    # -----------------------------

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

    # Nigeria is UTC+1.
    # GitHub Actions runs in UTC.

    now = datetime.now(
        timezone.utc
    )

    date_text = now.strftime(
        "%d %B %Y"
    )

    message = (
        "📊 DAILY MARKET UPDATE\n"
        "📅 "
        + date_text
        + "\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    for display_symbol, api_symbol in SYMBOLS.items():

        try:

            print(
                "\nProcessing "
                + display_symbol
            )

            section = (
                create_market_section(
                    display_symbol,
                    api_symbol
                )
            )

            message += section
            message += "\n"

        except Exception as error:

            print(
                "ERROR: "
                + display_symbol
                + " -> "
                + str(error)
            )

            message += (
                "⚠️ "
                + display_symbol
                + "\n"
                + "Unable to retrieve market data.\n"
                + "Reason: "
                + str(error)
                + "\n\n"
            )

        # Wait before moving to the
        # next instrument.

        time.sleep(
            REQUEST_DELAY
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
            response.read().decode(
                "utf-8"
            )
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
        "===================================="
    )

    print(
        "DollarProFX Daily Market Bot"
    )

    print(
        "===================================="
    )

    validate_environment()

    print(
        "Environment variables OK."
    )

    print(
        "Generating market update..."
    )

    message = build_market_update()

    print(
        "\n========== MESSAGE ==========\n"
    )

    print(message)

    print(
        "\n==============================\n"
    )

    send_message(message)

    print(
        "Telegram market update sent successfully."
                        )
