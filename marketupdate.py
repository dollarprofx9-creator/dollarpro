import os
import json
import urllib.request
import urllib.parse
from datetime import datetime


# ==========================
# Environment Variables
# ==========================
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TWELVE_DATA_API_KEY = os.getenv("TWELVE_DATA_API_KEY")


# ==========================
# Market Symbols
# ==========================
SYMBOLS = {
    "EURUSD": "EUR/USD",
    "BTCUSD": "BTC/USD",
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USDCAD": "USD/CAD",
    "NZDUSD": "NZD/USD",
    "XAUUSD": "XAU/USD",
}


# ==========================
# API Request
# ==========================
def api_request(url, params):

    query = urllib.parse.urlencode(params)

    full_url = f"{url}?{query}"

    request = urllib.request.Request(
        full_url,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    with urllib.request.urlopen(request, timeout=30) as response:

        data = response.read().decode("utf-8")

        return json.loads(data)


# ==========================
# Get Current Quote
# ==========================
def get_quote(symbol):

    url = "https://api.twelvedata.com/quote"

    params = {
        "symbol": symbol,
        "apikey": TWELVE_DATA_API_KEY
    }

    data = api_request(url, params)

    if "code" in data:
        raise Exception(
            data.get("message", "Unknown API error")
        )

    return data


# ==========================
# Get Daily History
# ==========================
def get_daily_history(symbol):

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 10,
        "apikey": TWELVE_DATA_API_KEY
    }

    data = api_request(url, params)

    if "code" in data:
        raise Exception(
            data.get("message", "Unknown API error")
        )

    return data.get("values", [])


# ==========================
# Calculate Weekly Change
# ==========================
def calculate_weekly_change(symbol, current_price):

    history = get_daily_history(symbol)

    if len(history) < 5:
        return None

    try:

        # Find the oldest daily close available
        # within the recent trading week.
        today = datetime.utcnow().date()

        current_week = today.isocalendar().week

        week_data = []

        for candle in history:

            candle_date = datetime.strptime(
                candle["datetime"],
                "%Y-%m-%d"
            ).date()

            if candle_date.isocalendar().week == current_week:

                week_data.append(candle)

        if len(week_data) < 2:
            return None

        # Oldest candle of current week
        week_open = float(week_data[-1]["open"])

        if week_open == 0:
            return None

        change = (
            (current_price - week_open)
            / week_open
        ) * 100

        return change

    except Exception:

        return None


# ==========================
# Format Price
# ==========================
def format_price(value, symbol):

    if value is None:
        return "N/A"

    value = float(value)

    if symbol == "BTCUSD":
        return f"${value:,.2f}"

    if symbol == "XAUUSD":
        return f"${value:,.2f}"

    if symbol == "USDJPY":
        return f"{value:.3f}"

    return f"{value:.4f}"


# ==========================
# Format Percentage
# ==========================
def format_percentage(value):

    if value is None:
        return "N/A"

    value = float(value)

    if value > 0:
        return f"+{value:.2f}%"

    return f"{value:.2f}%"


# ==========================
# Direction Emoji
# ==========================
def direction_emoji(value):

    if value is None:
        return "⚪"

    value = float(value)

    if value > 0:
        return "🟢"

    if value < 0:
        return "🔴"

    return "⚪"


# ==========================
# Build Market Update
# ==========================
def build_market_update():

    today = datetime.utcnow().strftime("%d %B %Y")

    message = f"""📊 DAILY MARKET UPDATE
📅 {today}

"""

    for display_name, api_symbol in SYMBOLS.items():

        try:

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

            previous_close = quote.get(
                "previous_close"
            )

            if previous_close:

                previous_close = float(
                    previous_close
                )

                daily_change = (
                    (current_price - previous_close)
                    / previous_close
                ) * 100

            else:

                daily_change = None

            weekly_change = calculate_weekly_change(
                api_symbol,
                current_price
            )

            emoji = direction_emoji(
                daily_change
            )

            message += (
                f"{emoji} {display_name}\n"
                f"💰 Price: "
                f"{format_price(current_price, display_name)}\n"
                f"📈 Day High: "
                f"{format_price(high, display_name)}\n"
                f"📉 Day Low: "
                f"{format_price(low, display_name)}\n"
                f"🔒 Previous Close: "
                f"{format_price(previous_close, display_name)}\n"
                f"📊 Daily Change: "
                f"{format_percentage(daily_change)}\n"
                f"📅 Weekly Change: "
                f"{format_percentage(weekly_change)}\n\n"
            )

        except Exception as error:

            print(
                f"Error retrieving {display_name}: "
                f"{error}"
            )

            message += (
                f"⚠️ {display_name}\n"
                f"Unable to retrieve market data.\n\n"
            )

    message += (
        "━━━━━━━━━━━━━━━━━━\n"
        "⚠️ Market data is for informational purposes only."
    )

    return message


# ==========================
# Send Telegram Message
# ==========================
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
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

    data = urllib.parse.urlencode({
        "chat_id": CHAT_ID,
        "text": message
    }).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST"
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


# ==========================
# Main
# ==========================
if __name__ == "__main__":

    if not TWELVE_DATA_API_KEY:
        raise ValueError(
            "TWELVE_DATA_API_KEY is not set"
        )

    print("Generating market update...")

    message = build_market_update()

    print(message)

    send_message(message)

    print(
        "Daily market update sent successfully!"
)
