#!/usr/bin/env python3
"""
XAUUSD Signal Generator
=======================
A production-ready trading signal system for XAU/USD on the M15 timeframe.
Uses the Opening Range Breakout strategy with strict candle close confirmation.

Features:
- Downloads real-time XAUUSD data from Twelve Data API
- Detects Opening Range (2:30 PM - 2:45 PM WAT)
- Monitors for confirmed breakout signals
- Calculates Stop Loss and Take Profit (1:2 R:R)
- Sends Telegram alerts
- Prevents duplicate signals
- Auto-resets daily
- Handles weekends and market closures
"""

import os
import sys
import json
import math
import time
import requests
from datetime import datetime, timedelta
from dateutil import tz

# =============================================================================
# CONFIGURATION
# =============================================================================

# Trading session times (WAT - West Africa Time, UTC+1)
SESSION_START_HOUR = 14      # 2:30 PM WAT
SESSION_START_MINUTE = 30
SESSION_END_HOUR = 20        # 8:45 PM WAT
SESSION_END_MINUTE = 45

# Opening Range: first M15 candle of the session
OR_START_HOUR = 14           # 2:30 PM WAT
OR_START_MINUTE = 30
OR_END_HOUR = 14             # 2:45 PM WAT
OR_END_MINUTE = 45

# Risk Reward Ratio
RISK_REWARD_RATIO = 2.0

# Symbol
SYMBOL = "XAU/USD"
TIMEFRAME = "15min"

# Timezone
WAT_TZ = tz.gettz("Africa/Lagos")
UTC_TZ = tz.gettz("UTC")

# Files
SIGNAL_FILE = "signal.json"

# API Endpoints
TWELVEDATA_BASE_URL = "https://api.twelvedata.com"
TELEGRAM_BASE_URL = "https://api.telegram.org/bot"

# =============================================================================
# LOGGING UTILITY
# =============================================================================

def log(message: str, level: str = "INFO") -> None:
    """Print a timestamped log message."""
    now = datetime.now(WAT_TZ).strftime("%Y-%m-%d %H:%M:%S WAT")
    print(f"[{now}] [{level}] {message}")


# =============================================================================
# TIME UTILITIES
# =============================================================================

def get_current_wat_time() -> datetime:
    """Get current time in WAT timezone."""
    return datetime.now(WAT_TZ)


def is_trading_session_active(now: datetime = None) -> bool:
    """
    Check if current time is within the trading session.
    Session: 2:30 PM WAT to 8:45 PM WAT
    """
    if now is None:
        now = get_current_wat_time()

    current_time = now.time()
    session_start = datetime.strptime(
        f"{SESSION_START_HOUR:02d}:{SESSION_START_MINUTE:02d}", "%H:%M"
    ).time()
    session_end = datetime.strptime(
        f"{SESSION_END_HOUR:02d}:{SESSION_END_MINUTE:02d}", "%H:%M"
    ).time()

    return session_start <= current_time <= session_end


def is_opening_range_period(now: datetime = None) -> bool:
    """
    Check if current time is within the Opening Range formation period.
    Opening Range: 2:30 PM - 2:45 PM WAT
    """
    if now is None:
        now = get_current_wat_time()

    current_time = now.time()
    or_start = datetime.strptime(
        f"{OR_START_HOUR:02d}:{OR_START_MINUTE:02d}", "%H:%M"
    ).time()
    or_end = datetime.strptime(
        f"{OR_END_HOUR:02d}:{OR_END_MINUTE:02d}", "%H:%M"
    ).time()

    return or_start <= current_time <= or_end


def is_weekend(now: datetime = None) -> bool:
    """Check if today is Saturday or Sunday."""
    if now is None:
        now = get_current_wat_time()
    return now.weekday() >= 5  # Saturday=5, Sunday=6


def format_wat_time(dt: datetime) -> str:
    """Format datetime to WAT time string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    wat_dt = dt.astimezone(WAT_TZ)
    return wat_dt.strftime("%I:%M %p WAT")


def format_wat_date(dt: datetime) -> str:
    """Format datetime to WAT date string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    wat_dt = dt.astimezone(WAT_TZ)
    return wat_dt.strftime("%d %b %Y")


def get_session_countdown(now: datetime = None) -> str:
    """Get countdown string until session ends."""
    if now is None:
        now = get_current_wat_time()

    session_end = now.replace(
        hour=SESSION_END_HOUR, minute=SESSION_END_MINUTE, second=0, microsecond=0
    )

    if now > session_end:
        return "Session ended"

    diff = session_end - now
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60
    return f"{hours}h {minutes}m remaining"


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def load_signal_data() -> dict:
    """Load signal data from JSON file."""
    if not os.path.exists(SIGNAL_FILE):
        log("Signal file not found, creating default.", "WARN")
        return create_default_signal_data()

    try:
        with open(SIGNAL_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log(f"Error loading signal file: {e}", "ERROR")
        return create_default_signal_data()


def save_signal_data(data: dict) -> bool:
    """Save signal data to JSON file."""
    try:
        with open(SIGNAL_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except IOError as e:
        log(f"Error saving signal file: {e}", "ERROR")
        return False


def create_default_signal_data() -> dict:
    """Create default signal data structure."""
    return {
        "latest_signal": None,
        "signal_history": [],
        "opening_range": {
            "high": None,
            "low": None,
            "date": None,
            "formed": False
        },
        "current_state": {
            "active_signal": None,
            "position": None,
            "entry": None,
            "stop_loss": None,
            "take_profit": None,
            "signal_time": None,
            "signal_date": None
        },
        "market_data": {
            "current_price": None,
            "last_updated": None
        },
        "session_info": {
            "session_start": f"{SESSION_START_HOUR:02d}:{SESSION_START_MINUTE:02d}",
            "session_end": f"{SESSION_END_HOUR:02d}:{SESSION_END_MINUTE:02d}",
            "timezone": "Africa/Lagos",
            "is_active": False,
            "countdown": ""
        }
    }


# =============================================================================
# API FUNCTIONS
# =============================================================================

def get_twelve_data_api_key() -> str:
    """Get Twelve Data API key from environment."""
    api_key = os.environ.get("TWELVEDATA_API_KEY", "")
    if not api_key:
        log("TWELVEDATA_API_KEY not found in environment!", "ERROR")
    return api_key


def get_telegram_credentials() -> tuple:
    """Get Telegram bot token and chat ID from environment."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not bot_token:
        log("TELEGRAM_BOT_TOKEN not found in environment!", "ERROR")
    if not chat_id:
        log("TELEGRAM_CHAT_ID not found in environment!", "ERROR")

    return bot_token, chat_id


def fetch_xauusd_candles(api_key: str, interval: str = "15min", outputsize: int = 50) -> list:
    """
    Fetch XAUUSD candlestick data from Twelve Data API.

    Args:
        api_key: Twelve Data API key
        interval: Candle interval (default 15min)
        outputsize: Number of candles to fetch

    Returns:
        List of candle dictionaries with datetime, open, high, low, close
    """
    if not api_key:
        log("Cannot fetch candles: API key missing", "ERROR")
        return []

    url = f"{TWELVEDATA_BASE_URL}/time_series"
    params = {
        "symbol": "XAU/USD",
        "interval": interval,
        "outputsize": outputsize,
        "apikey": api_key,
        "timezone": "Africa/Lagos"
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "values" not in data:
            log(f"Unexpected API response: {data}", "ERROR")
            return []

        candles = []
        for item in data["values"]:
            candle = {
                "datetime": item.get("datetime", ""),
                "open": float(item.get("open", 0)),
                "high": float(item.get("high", 0)),
                "low": float(item.get("low", 0)),
                "close": float(item.get("close", 0))
            }
            candles.append(candle)

        # Sort by datetime ascending (oldest first)
        candles.sort(key=lambda x: x["datetime"])
        log(f"Fetched {len(candles)} candles from Twelve Data")
        return candles

    except requests.exceptions.RequestException as e:
        log(f"Network error fetching candles: {e}", "ERROR")
        return []
    except (KeyError, ValueError) as e:
        log(f"Data parsing error: {e}", "ERROR")
        return []


def fetch_current_price(api_key: str) -> float:
    """
    Fetch current XAUUSD price from Twelve Data API.

    Args:
        api_key: Twelve Data API key

    Returns:
        Current price as float, or None on failure
    """
    if not api_key:
        return None

    url = f"{TWELVEDATA_BASE_URL}/price"
    params = {
        "symbol": "XAU/USD",
        "apikey": api_key
    }

    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        price = float(data.get("price", 0))
        if price > 0:
            return price
        return None
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        log(f"Error fetching current price: {e}", "ERROR")
        return None


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """
    Send a message via Telegram Bot API.

    Args:
        bot_token: Telegram bot token
        chat_id: Target chat ID
        message: Message text (supports Markdown)

    Returns:
        True if sent successfully, False otherwise
    """
    if not bot_token or not chat_id:
        log("Cannot send Telegram message: credentials missing", "ERROR")
        return False

    url = f"{TELEGRAM_BASE_URL}{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        log("Telegram message sent successfully")
        return True
    except requests.exceptions.RequestException as e:
        log(f"Error sending Telegram message: {e}", "ERROR")
        return False


# =============================================================================
# SIGNAL GENERATION LOGIC
# =============================================================================

def find_opening_range_candle(candles: list, target_date: str) -> dict:
    """
    Find the Opening Range candle from the fetched data.
    The Opening Range is the first M15 candle of the session: 2:30 PM - 2:45 PM WAT.

    Args:
        candles: List of candle data
        target_date: Date string in YYYY-MM-DD format

    Returns:
        Opening range candle dict or None
    """
    # Expected OR candle datetime format: "YYYY-MM-DD 14:30:00"
    or_datetime_prefix = f"{target_date} 14:30:00"
    or_datetime_prefix_alt = f"{target_date} 14:30"

    for candle in candles:
        dt = candle.get("datetime", "")
        if or_datetime_prefix in dt or or_datetime_prefix_alt in dt:
            log(f"Found Opening Range candle: {dt}")
            return candle

    return None


def calculate_take_profit(entry: float, stop_loss: float, position: str) -> float:
    """
    Calculate Take Profit based on 1:2 Risk:Reward ratio.

    Args:
        entry: Entry price
        stop_loss: Stop loss price
        position: "BUY" or "SELL"

    Returns:
        Take profit price
    """
    risk = abs(entry - stop_loss)
    reward = risk * RISK_REWARD_RATIO

    if position == "BUY":
        return entry + reward
    else:  # SELL
        return entry - reward


def format_price(price: float) -> str:
    """Format price to 2 decimal places."""
    return f"{price:.2f}"


def build_telegram_message(signal_type: str, entry: float, stop_loss: float, 
                           take_profit: float, signal_time: str, signal_date: str) -> str:
    """
    Build formatted Telegram message for a trading signal.

    Args:
        signal_type: "BUY" or "SELL"
        entry: Entry price
        stop_loss: Stop loss price
        take_profit: Take profit price
        signal_time: Signal time string
        signal_date: Signal date string

    Returns:
        Formatted HTML message string
    """
    emoji = "🟢" if signal_type == "BUY" else "🔴"

    message = f"""📊 <b>XAUUSD SIGNAL</b>

{emoji} <b>{signal_type}</b>

<b>Entry:</b> {format_price(entry)}
<b>Stop Loss:</b> {format_price(stop_loss)}
<b>Take Profit:</b> {format_price(take_profit)}

<b>Timeframe:</b> M15
<b>Date:</b> {signal_date}
<b>Signal Time:</b> {signal_time}
<b>Session:</b> 2:30 PM - 8:45 PM WAT"""

    return message


def should_reset_for_new_day(data: dict, now: datetime) -> bool:
    """
    Check if we should reset state for a new trading day.
    Reset if:
    - The stored OR date is different from today
    - OR is marked as formed but it's a new day
    """
    or_date = data.get("opening_range", {}).get("date")
    today_str = now.strftime("%Y-%m-%d")

    if or_date is None:
        return True

    return or_date != today_str


def reset_daily_state(data: dict, now: datetime) -> dict:
    """Reset all daily state for a new trading day."""
    log("Resetting state for new trading day")

    data["opening_range"] = {
        "high": None,
        "low": None,
        "date": now.strftime("%Y-%m-%d"),
        "formed": False
    }
    data["current_state"] = {
        "active_signal": None,
        "position": None,
        "entry": None,
        "stop_loss": None,
        "take_profit": None,
        "signal_time": None,
        "signal_date": None
    }
    data["latest_signal"] = None

    return data


# =============================================================================
# MAIN SIGNAL PROCESSING
# =============================================================================

def process_signals() -> bool:
    """
    Main signal processing function.
    Orchestrates the entire signal generation pipeline.

    Returns:
        True if signal data was updated, False otherwise
    """
    now = get_current_wat_time()
    today_str = now.strftime("%Y-%m-%d")

    log(f"Starting signal processing at {now.strftime('%Y-%m-%d %H:%M:%S WAT')}")

    # Load existing signal data
    data = load_signal_data()

    # Update session info
    data["session_info"]["is_active"] = is_trading_session_active(now)
    data["session_info"]["countdown"] = get_session_countdown(now)

    # Check if it's weekend
    if is_weekend(now):
        log("Weekend detected - markets closed. Skipping.")
        data["market_data"]["current_price"] = None
        data["market_data"]["last_updated"] = now.isoformat()
        save_signal_data(data)
        return False

    # Get API credentials
    api_key = get_twelve_data_api_key()
    bot_token, chat_id = get_telegram_credentials()

    if not api_key:
        log("Missing API key. Cannot proceed.", "ERROR")
        save_signal_data(data)
        return False

    # Fetch current price for dashboard
    current_price = fetch_current_price(api_key)
    if current_price:
        data["market_data"]["current_price"] = current_price
        data["market_data"]["last_updated"] = now.isoformat()

    # Check if we need to reset for a new day
    if should_reset_for_new_day(data, now):
        data = reset_daily_state(data, now)

    # If session hasn't started yet, just update price and exit
    if not is_trading_session_active(now):
        log("Trading session not active yet.")
        save_signal_data(data)
        return False

    # Fetch candle data
    candles = fetch_xauusd_candles(api_key, interval=TIMEFRAME, outputsize=50)
    if not candles:
        log("No candle data available. Skipping.")
        save_signal_data(data)
        return False

    # =====================================================================
    # STEP 1: Detect/Confirm Opening Range
    # =====================================================================
    opening_range = data.get("opening_range", {})
    or_formed = opening_range.get("formed", False)
    or_high = opening_range.get("high")
    or_low = opening_range.get("low")

    if not or_formed:
        # Try to find the OR candle
        or_candle = find_opening_range_candle(candles, today_str)

        if or_candle:
            # We found the OR candle - store it
            or_high = or_candle["high"]
            or_low = or_candle["low"]

            data["opening_range"]["high"] = or_high
            data["opening_range"]["low"] = or_low
            data["opening_range"]["date"] = today_str
            data["opening_range"]["formed"] = True

            log(f"Opening Range formed - High: {or_high}, Low: {or_low}")
        else:
            # OR candle not yet available (might be too early or data gap)
            log("Opening Range candle not yet available.")
            save_signal_data(data)
            return False

    # =====================================================================
    # STEP 2: Monitor for Breakout Signals
    # =====================================================================

    # Get current active state
    current_state = data.get("current_state", {})
    active_position = current_state.get("position")  # "BUY", "SELL", or None

    # We need at least the OR candle + one more candle to check for breakouts
    # Filter candles to only those from today
    today_candles = []
    for c in candles:
        if today_str in c["datetime"]:
            today_candles.append(c)

    if len(today_candles) < 2:
        log("Not enough candles from today to evaluate breakouts.")
        save_signal_data(data)
        return False

    # The OR candle is the first one
    or_candle = today_candles[0]

    # Check subsequent candles for breakouts (skip the OR candle itself)
    # We look at the MOST RECENT closed candle
    latest_candle = today_candles[-1]

    # Skip if the latest candle IS the OR candle (no breakout possible yet)
    if latest_candle["datetime"] == or_candle["datetime"]:
        log("Latest candle is still the OR candle. No breakout possible yet.")
        save_signal_data(data)
        return False

    latest_close = latest_candle["close"]
    latest_high = latest_candle["high"]
    latest_low = latest_candle["low"]

    log(f"Latest candle close: {latest_close}, OR High: {or_high}, OR Low: {or_low}")

    signal_generated = False
    new_position = None

    # Check for BUY signal: candle CLOSE above OR High
    if latest_close > or_high:
        if active_position != "BUY":
            # New BUY signal
            new_position = "BUY"
            entry = latest_close
            stop_loss = or_low
            take_profit = calculate_take_profit(entry, stop_loss, "BUY")

            signal_time = format_wat_time(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))
            signal_date = format_wat_date(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))

            # Update current state
            data["current_state"] = {
                "active_signal": True,
                "position": "BUY",
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "signal_time": signal_time,
                "signal_date": signal_date
            }

            # Update latest signal
            data["latest_signal"] = {
                "type": "BUY",
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "time": signal_time,
                "date": signal_date,
                "timestamp": now.isoformat()
            }

            # Add to history
            data["signal_history"].insert(0, data["latest_signal"])
            # Keep only last 100 signals
            data["signal_history"] = data["signal_history"][:100]

            log(f"BUY SIGNAL generated - Entry: {entry}, SL: {stop_loss}, TP: {take_profit}")

            # Send Telegram alert
            message = build_telegram_message("BUY", entry, stop_loss, take_profit, signal_time, signal_date)
            send_telegram_message(bot_token, chat_id, message)

            signal_generated = True
        else:
            log("BUY condition met but already in BUY position. No duplicate.")

    # Check for SELL signal: candle CLOSE below OR Low
    elif latest_close < or_low:
        if active_position != "SELL":
            # New SELL signal
            new_position = "SELL"
            entry = latest_close
            stop_loss = or_high
            take_profit = calculate_take_profit(entry, stop_loss, "SELL")

            signal_time = format_wat_time(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))
            signal_date = format_wat_date(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))

            # Update current state
            data["current_state"] = {
                "active_signal": True,
                "position": "SELL",
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "signal_time": signal_time,
                "signal_date": signal_date
            }

            # Update latest signal
            data["latest_signal"] = {
                "type": "SELL",
                "entry": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "time": signal_time,
                "date": signal_date,
                "timestamp": now.isoformat()
            }

            # Add to history
            data["signal_history"].insert(0, data["latest_signal"])
            # Keep only last 100 signals
            data["signal_history"] = data["signal_history"][:100]

            log(f"SELL SIGNAL generated - Entry: {entry}, SL: {stop_loss}, TP: {take_profit}")

            # Send Telegram alert
            message = build_telegram_message("SELL", entry, stop_loss, take_profit, signal_time, signal_date)
            send_telegram_message(bot_token, chat_id, message)

            signal_generated = True
        else:
            log("SELL condition met but already in SELL position. No duplicate.")
    else:
        log(f"No breakout. Price {latest_close} within OR range ({or_low} - {or_high}).")

    # Save updated data
    save_signal_data(data)

    if signal_generated:
        log(f"Signal processing complete. New {new_position} signal generated.")
    else:
        log("Signal processing complete. No new signal.")

    return signal_generated


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    try:
        updated = process_signals()
        sys.exit(0 if updated else 0)
    except Exception as e:
        log(f"Unhandled exception: {e}", "CRITICAL")
        import traceback
        traceback.print_exc()
        sys.exit(1)
