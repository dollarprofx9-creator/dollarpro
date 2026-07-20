"""
DollarProFx Signal Generation Engine
Generates XAUUSD ORBS (Opening Range Breakout Strategy) signals.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    TWELVEDATA_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    SYMBOL,
    TIMEFRAME,
    TIMEZONE,
    TRADING_SESSION_START,
    TRADING_SESSION_END,
    OPENING_RANGE_OPEN,
    OPENING_RANGE_CLOSE,
    RISK_REWARD_RATIO,
    SIGNAL_FILE,
    USERS_FILE,
    LOGS_DIR,
    TELEGRAM_BUY_TEMPLATE,
    TELEGRAM_SELL_TEMPLATE,
    TELEGRAM_SL_TEMPLATE,
    TELEGRAM_TP_TEMPLATE,
)

# =============================================================================
# LOGGING SETUP
# =============================================================================

def setup_logging():
    """Configure logging for the signal engine."""
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"signal_engine_{datetime.now().strftime('%Y%m%d')}.log")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# =============================================================================
# FILE OPERATIONS
# =============================================================================

def load_json(filepath):
    """Load JSON data from file with error handling."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"File not found: {filepath}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {filepath}: {e}")
        return {}


def save_json(filepath, data):
    """Save JSON data to file atomically."""
    try:
        temp_file = filepath + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, filepath)
        logger.info(f"Saved data to {filepath}")
        return True
    except Exception as e:
        logger.error(f"Failed to save {filepath}: {e}")
        return False


# =============================================================================
# TWELVE DATA API
# =============================================================================

def fetch_m15_candles(symbol="XAU/USD", interval="15min", outputsize=100):
    """
    Fetch M15 candle data from Twelve Data API.
    Retries on failure with exponential backoff.
    """
    if not TWELVEDATA_API_KEY:
        logger.error("TWELVEDATA_API_KEY not set")
        return None

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVEDATA_API_KEY,
        "timezone": TIMEZONE,
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=30)

            if response.status_code == 429:
                logger.warning(f"Rate limit hit. Retrying in {2 ** attempt}s...")
                time.sleep(2 ** attempt)
                continue

            response.raise_for_status()
            data = response.json()

            if "values" not in data:
                if "message" in data:
                    logger.error(f"Twelve Data API error: {data['message']}")
                else:
                    logger.error(f"Unexpected Twelve Data response: {data}")
                return None

            logger.info(f"Successfully fetched {len(data['values'])} candles")
            return data["values"]

        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    logger.error("All API request attempts failed")
    return None


# =============================================================================
# TELEGRAM BOT
# =============================================================================

def send_telegram_message(message):
    """
    Send a message via Telegram Bot API.
    Retries on failure with exponential backoff.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram credentials not configured")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Telegram API error: {result}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram request failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)

    logger.error("All Telegram send attempts failed")
    return False


# =============================================================================
# TIME UTILITIES
# =============================================================================

def get_wat_now():
    """Get current time in WAT (Africa/Lagos)."""
    import pytz
    wat = pytz.timezone(TIMEZONE)
    return datetime.now(wat)


def parse_time_str(time_str):
    """Parse a time string in HH:MM format."""
    return datetime.strptime(time_str, "%H:%M").time()


def is_trading_session_active():
    """Check if current time is within the trading session."""
    now = get_wat_now()
    current_time = now.time()
    start_time = parse_time_str(TRADING_SESSION_START)
    end_time = parse_time_str(TRADING_SESSION_END)

    # Check if it's a weekend (Saturday=5, Sunday=6)
    if now.weekday() >= 5:
        return False

    return start_time <= current_time <= end_time


def is_opening_range_period():
    """Check if current time is during the opening range candle period."""
    now = get_wat_now()
    current_time = now.time()
    or_open = parse_time_str(OPENING_RANGE_OPEN)
    or_close = parse_time_str(OPENING_RANGE_CLOSE)

    return or_open <= current_time <= or_close


def get_opening_range_candle_time():
    """Get the datetime for the opening range candle close time today."""
    now = get_wat_now()
    or_close_time = parse_time_str(OPENING_RANGE_CLOSE)
    return datetime.combine(now.date(), or_close_time).replace(tzinfo=now.tzinfo)


def format_date(dt):
    """Format datetime as 'DD MMM YYYY'."""
    return dt.strftime("%d %b %Y")


def format_time(dt):
    """Format datetime as 'HH:MM AM/PM WAT'."""
    return dt.strftime("%I:%M %p WAT")


# =============================================================================
# SIGNAL ENGINE
# =============================================================================

def find_opening_range_candle(candles, target_date):
    """
    Find the M15 candle that opens at 2:15 PM WAT and closes at 2:30 PM WAT.
    Returns the candle with high and low values.
    """
    or_open_time = parse_time_str(OPENING_RANGE_OPEN)
    or_close_time = parse_time_str(OPENING_RANGE_CLOSE)

    for candle in candles:
        try:
            candle_dt = datetime.strptime(candle["datetime"], "%Y-%m-%d %H:%M:%S")
            candle_time = candle_dt.time()
            candle_date = candle_dt.date()

            # Match the candle that opens at 14:15 and closes at 14:30
            if candle_date == target_date and candle_time == or_close_time:
                # This candle represents the 14:15-14:30 period
                return {
                    "high": float(candle["high"]),
                    "low": float(candle["low"]),
                    "open": float(candle["open"]),
                    "close": float(candle["close"]),
                    "datetime": candle["datetime"]
                }
        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping invalid candle: {e}")
            continue

    return None


def find_completed_candles_after(candles, target_date, after_time):
    """
    Find all completed M15 candles after the specified time on the target date.
    Only returns candles that are fully closed (not the current forming candle).
    """
    completed = []
    now = get_wat_now()

    for candle in candles:
        try:
            candle_dt = datetime.strptime(candle["datetime"], "%Y-%m-%d %H:%M:%S")
            candle_time = candle_dt.time()
            candle_date = candle_dt.date()

            # Only consider candles from target date, after opening range close
            if candle_date == target_date and candle_time > after_time:
                # Only include candles that have fully closed (not current candle)
                # A candle is completed if its close time is at least 15 minutes ago
                candle_close_time = candle_dt
                if (now - candle_close_time).total_seconds() >= 900:  # 15 minutes
                    completed.append({
                        "high": float(candle["high"]),
                        "low": float(candle["low"]),
                        "open": float(candle["open"]),
                        "close": float(candle["close"]),
                        "datetime": candle["datetime"]
                    })
        except (KeyError, ValueError) as e:
            logger.warning(f"Skipping invalid candle: {e}")
            continue

    # Sort by datetime ascending
    completed.sort(key=lambda x: x["datetime"])
    return completed


def calculate_tp(direction, entry, stop_loss):
    """Calculate Take Profit based on 1:2 Risk-Reward ratio."""
    risk = abs(entry - stop_loss)
    reward = risk * RISK_REWARD_RATIO

    if direction == "BUY":
        return entry + reward
    else:  # SELL
        return entry - reward


def generate_signal(direction, entry, stop_loss, take_profit, candle_datetime):
    """Generate a signal dictionary."""
    dt = datetime.strptime(candle_datetime, "%Y-%m-%d %H:%M:%S")

    return {
        "direction": direction,
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "take_profit": round(take_profit, 2),
        "date": format_date(dt),
        "time": dt.strftime("%I:%M %p") + " WAT",
        "status": "ACTIVE",
        "raw_datetime": candle_datetime
    }


def check_tp_sl_hit(current_price, signal):
    """Check if Take Profit or Stop Loss has been hit."""
    direction = signal["direction"]
    tp = signal["take_profit"]
    sl = signal["stop_loss"]

    if direction == "BUY":
        if current_price >= tp:
            return "TP_HIT"
        elif current_price <= sl:
            return "SL_HIT"
    else:  # SELL
        if current_price <= tp:
            return "TP_HIT"
        elif current_price >= sl:
            return "SL_HIT"

    return "ACTIVE"


def send_signal_telegram(signal):
    """Send a new signal notification to Telegram."""
    if signal["direction"] == "BUY":
        message = TELEGRAM_BUY_TEMPLATE.format(
            entry=signal["entry"],
            stop_loss=signal["stop_loss"],
            take_profit=signal["take_profit"],
            date=signal["date"],
            time=signal["time"]
        )
    else:
        message = TELEGRAM_SELL_TEMPLATE.format(
            entry=signal["entry"],
            stop_loss=signal["stop_loss"],
            take_profit=signal["take_profit"],
            date=signal["date"],
            time=signal["time"]
        )

    return send_telegram_message(message)


def send_tp_telegram(signal):
    """Send a Take Profit update to Telegram."""
    message = TELEGRAM_TP_TEMPLATE.format(
        direction=signal["direction"],
        date=signal["date"],
        time=signal["time"]
    )
    return send_telegram_message(message)


def send_sl_telegram(signal):
    """Send a Stop Loss update to Telegram."""
    message = TELEGRAM_SL_TEMPLATE.format(
        direction=signal["direction"],
        date=signal["date"],
        time=signal["time"]
    )
    return send_telegram_message(message)


# =============================================================================
# MAIN SIGNAL ENGINE
# =============================================================================

def run_signal_engine():
    """
    Main signal engine logic.
    This function runs every minute via GitHub Actions.
    """
    logger.info("=" * 60)
    logger.info("DollarProFx Signal Engine - Starting Run")
    logger.info("=" * 60)

    now = get_wat_now()
    today = now.date()

    # Load signal data
    signal_data = load_json(SIGNAL_FILE)
    if not signal_data:
        signal_data = {
            "latest_signal": {
                "direction": "WAITING",
                "entry": None,
                "stop_loss": None,
                "take_profit": None,
                "date": None,
                "time": None,
                "status": "WAITING",
                "opening_range_high": None,
                "opening_range_low": None,
                "session_start": TRADING_SESSION_START,
                "session_end": TRADING_SESSION_END
            },
            "signal_history": [],
            "session_state": {
                "date": None,
                "opening_range_high": None,
                "opening_range_low": None,
                "active_trade": None,
                "last_signal_direction": None
            }
        }

    session_state = signal_data.get("session_state", {})

    # Check if it's a new trading day - reset session state
    stored_date_str = session_state.get("date")
    if stored_date_str:
        stored_date = datetime.strptime(stored_date_str, "%Y-%m-%d").date()
        if stored_date != today:
            logger.info(f"New trading day detected. Resetting session state.")
            session_state = {
                "date": today.strftime("%Y-%m-%d"),
                "opening_range_high": None,
                "opening_range_low": None,
                "active_trade": None,
                "last_signal_direction": None
            }
            signal_data["session_state"] = session_state

            # Reset latest signal to WAITING
            signal_data["latest_signal"] = {
                "direction": "WAITING",
                "entry": None,
                "stop_loss": None,
                "take_profit": None,
                "date": None,
                "time": None,
                "status": "WAITING",
                "opening_range_high": None,
                "opening_range_low": None,
                "session_start": TRADING_SESSION_START,
                "session_end": TRADING_SESSION_END
            }
    else:
        # First run - initialize
        session_state["date"] = today.strftime("%Y-%m-%d")
        signal_data["session_state"] = session_state

    # Check if we're in the trading session
    if not is_trading_session_active():
        logger.info("Outside trading session. No action needed.")
        save_json(SIGNAL_FILE, signal_data)
        return

    # Fetch M15 candles
    candles = fetch_m15_candles()
    if not candles:
        logger.error("Failed to fetch candle data. Exiting.")
        save_json(SIGNAL_FILE, signal_data)
        return

    # Get current gold price from the most recent candle
    try:
        latest_candle = candles[0]
        current_price = float(latest_candle["close"])
    except (IndexError, KeyError, ValueError) as e:
        logger.error(f"Failed to get current price: {e}")
        save_json(SIGNAL_FILE, signal_data)
        return

    # Update current price in signal data
    signal_data["latest_signal"]["current_price"] = current_price

    # Step 1: Identify Opening Range if not already done
    or_high = session_state.get("opening_range_high")
    or_low = session_state.get("opening_range_low")

    if or_high is None or or_low is None:
        logger.info("Opening Range not yet identified. Searching...")
        or_candle = find_opening_range_candle(candles, today)

        if or_candle:
            or_high = or_candle["high"]
            or_low = or_candle["low"]
            session_state["opening_range_high"] = or_high
            session_state["opening_range_low"] = or_low
            signal_data["session_state"] = session_state

            signal_data["latest_signal"]["opening_range_high"] = or_high
            signal_data["latest_signal"]["opening_range_low"] = or_low

            logger.info(f"Opening Range identified: High={or_high}, Low={or_low}")
        else:
            logger.info("Opening Range candle not yet available. Waiting...")
            save_json(SIGNAL_FILE, signal_data)
            return

    # Step 2: Check if there's an active trade and monitor TP/SL
    active_trade = session_state.get("active_trade")

    if active_trade:
        logger.info(f"Active trade: {active_trade['direction']} @ {active_trade['entry']}")

        # Check TP/SL
        result = check_tp_sl_hit(current_price, active_trade)

        if result == "TP_HIT":
            logger.info(f"Take Profit HIT for {active_trade['direction']} trade!")

            # Update signal status
            active_trade["status"] = "TP_HIT"
            signal_data["latest_signal"]["status"] = "TP_HIT"
            signal_data["latest_signal"]["result"] = "Take Profit Reached"

            # Move to history
            signal_data["signal_history"].insert(0, active_trade.copy())

            # Clear active trade
            session_state["active_trade"] = None
            signal_data["session_state"] = session_state

            # Send Telegram notification
            send_tp_telegram(active_trade)

            save_json(SIGNAL_FILE, signal_data)
            return

        elif result == "SL_HIT":
            logger.info(f"Stop Loss HIT for {active_trade['direction']} trade!")

            # Update signal status
            active_trade["status"] = "SL_HIT"
            signal_data["latest_signal"]["status"] = "SL_HIT"
            signal_data["latest_signal"]["result"] = "Stop Loss Hit"

            # Move to history
            signal_data["signal_history"].insert(0, active_trade.copy())

            # Clear active trade
            session_state["active_trade"] = None
            signal_data["session_state"] = session_state

            # Send Telegram notification
            send_sl_telegram(active_trade)

            save_json(SIGNAL_FILE, signal_data)
            return

        else:
            logger.info(f"Trade still ACTIVE. Current price: {current_price}")
            save_json(SIGNAL_FILE, signal_data)
            return

    # Step 3: Monitor for new breakout signals
    # Only if no active trade exists
    or_close_time = parse_time_str(OPENING_RANGE_CLOSE)
    completed_candles = find_completed_candles_after(candles, today, or_close_time)

    if not completed_candles:
        logger.info("No completed candles after Opening Range yet. Waiting...")
        save_json(SIGNAL_FILE, signal_data)
        return

    # Check the most recent completed candle for breakout
    last_completed = completed_candles[-1]
    last_direction = session_state.get("last_signal_direction")

    candle_close = last_completed["close"]
    candle_high = last_completed["high"]
    candle_low = last_completed["low"]
    candle_datetime = last_completed["datetime"]

    logger.info(f"Last completed candle: Close={candle_close}, High={candle_high}, Low={candle_low}")

    # Check for BUY signal - candle must CLOSE above Opening Range High
    if candle_close > or_high:
        if last_direction != "BUY":
            logger.info(f"BUY SIGNAL DETECTED! Close {candle_close} > OR High {or_high}")

            entry = candle_close
            stop_loss = or_low
            take_profit = calculate_tp("BUY", entry, stop_loss)

            signal = generate_signal("BUY", entry, stop_loss, take_profit, candle_datetime)

            # Update session state
            session_state["active_trade"] = signal
            session_state["last_signal_direction"] = "BUY"
            signal_data["session_state"] = session_state

            # Update latest signal
            signal_data["latest_signal"] = signal
            signal_data["latest_signal"]["opening_range_high"] = or_high
            signal_data["latest_signal"]["opening_range_low"] = or_low
            signal_data["latest_signal"]["current_price"] = current_price

            # Send Telegram
            send_signal_telegram(signal)

            save_json(SIGNAL_FILE, signal_data)
            return
        else:
            logger.info("BUY breakout detected but duplicate prevention active.")

    # Check for SELL signal - candle must CLOSE below Opening Range Low
    elif candle_close < or_low:
        if last_direction != "SELL":
            logger.info(f"SELL SIGNAL DETECTED! Close {candle_close} < OR Low {or_low}")

            entry = candle_close
            stop_loss = or_high
            take_profit = calculate_tp("SELL", entry, stop_loss)

            signal = generate_signal("SELL", entry, stop_loss, take_profit, candle_datetime)

            # Update session state
            session_state["active_trade"] = signal
            session_state["last_signal_direction"] = "SELL"
            signal_data["session_state"] = session_state

            # Update latest signal
            signal_data["latest_signal"] = signal
            signal_data["latest_signal"]["opening_range_high"] = or_high
            signal_data["latest_signal"]["opening_range_low"] = or_low
            signal_data["latest_signal"]["current_price"] = current_price

            # Send Telegram
            send_signal_telegram(signal)

            save_json(SIGNAL_FILE, signal_data)
            return
        else:
            logger.info("SELL breakout detected but duplicate prevention active.")

    else:
        logger.info(f"No breakout. Candle close {candle_close} within OR range [{or_low}, {or_high}]")

    save_json(SIGNAL_FILE, signal_data)
    logger.info("Signal engine run complete.")


if __name__ == "__main__":
    run_signal_engine()
