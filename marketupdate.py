import os
import requests
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
    "GBPUSD": "GBP/USD",
    "USDJPY": "USD/JPY",
    "USDCAD": "USD/CAD",
    "NZDUSD": "NZD/USD",
    "BTCUSD": "BTC/USD",
    "XAUUSD": "XAU/USD",
}

# ==========================
# API URLs
# ==========================
TWELVE_DATA_URL = "https://api.twelvedata.com"


# ==========================
# Validate Environment
# ==========================
def validate_environment():

    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    if not CHAT_ID:
        raise ValueError("TELEGRAM_CHAT_ID is not set")

    if not TWELVE_DATA_API_KEY:
        raise ValueError("TWELVE_DATA_API_KEY is not set")


# ==========================
# Get Current Market Quote
# ==========================
def get_quote(symbol):

    url = f"{TWELVE_DATA_URL}/quote"

    params = {
        "symbol": symbol,
        "apikey": TWELVE_DATA_API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "code" in data:
        raise ValueError(
            f"API error for {symbol}: "
            f"{data.get('message', 'Unknown error')}"
        )

    return data


# ==========================
# Get Daily History
# ==========================
def get_daily_history(symbol):

    url = f"{TWELVE_DATA_URL}/time_series"

    params = {
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 7,
        "apikey": TWELVE_DATA_API_KEY
    }

    response = requests.get(
        url,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    if "code" in data:
        raise ValueError(
            f"History API error for {symbol}: "
            f"{data.get('message', 'Unknown error')}"
        )

    return data.get("values", [])


# ==========================
# Calculate Weekly Change
# ==========================
def calculate_weekly_change(symbol, current_price):

    history = get_daily_history(symbol)

    if len(history) < 5:
        return None

    # Twelve Data returns newest candle first.
    # Index 0 = latest completed daily candle.
    previous_week_close = float(history[4]["close"])

    if previous_week_close == 0:
        return None

    weekly_change = (
        (current_price - previous_week_close)
        / previous_week_close
    ) * 100

    return weekly_change


# ==========================
# Format Price
# ==========================
def format_price(value, symbol):

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

    if float(value) > 0:
        return "🟢"

    if float(value) < 0:
        return "🔴"

    return "⚪"


# ==========================
# Build Market Update
# ==========================
def build_market_update():

    today = datetime.now().strftime("%d %B %Y")

    message = f"""📊 DAILY MARKET UPDATE
📅 {today}

"""

    for display_name, api_symbol in SYMBOLS.items():

        try:

            quote = get_quote(api_symbol)

            current_price = float(quote["close"])
            high = float(quote["high"])
            low = float(quote["low"])

            previous_close = quote.get("previous_close")

            if previous_close:
                previous_close = float(previous_close)

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

            emoji = direction_emoji(daily_change)

            message += (
                f"{emoji} {display_name}\n"
                f"💰 Price: "
                f"{format_price(current_price, display_name)}\n"
                f"📈 Day High: "
                f"{format_price(high, display_name)}\n"
                f"📉 Day Low: "
                f"{format_price(low, display_name)}\n"
                f"🔒 Previous Close: "
                f"{format_price(previous_close, display_name) if previous_close else 'N/A'}\n"
                f"📊 Daily Change: "
                f"{format_percentage(daily_change)}\n"
                f"📅 Weekly Change: "
                f"{format_percentage(weekly_change)}\n\n"
            )

        except Exception as error:

            print(
                f"Failed to retrieve {display_name}: {error}"
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

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()

    print("Daily market update sent successfully!")


# ==========================
# Main
# ==========================
if __name__ == "__main__":

    validate_environment()

    market_message = build_market_update()

    print(market_message)

    send_message(market_message)
