#!/usr/bin/env python3
"""
XAUUSD Signal Generator - v2.0
==============================
Production-ready trading signal system with:
- Opening Range Breakout strategy (M15)
- TP Hit tracking (no same-direction re-entry after TP)
- SL Hit handling (wait for opposite breakout, no instant reversal)
- Full session state machine (active, tp_hit, sl_hit, waiting)
- Daily auto-reset
- Weekend handling
- Telegram integration
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

SESSION_START_HOUR = 14
SESSION_START_MINUTE = 30
SESSION_END_HOUR = 20
SESSION_END_MINUTE = 45

OR_START_HOUR = 14
OR_START_MINUTE = 30
OR_END_HOUR = 14
OR_END_MINUTE = 45

RISK_REWARD_RATIO = 2.0
SYMBOL = "XAU/USD"
TIMEFRAME = "15min"
WAT_TZ = tz.gettz("Africa/Lagos")
UTC_TZ = tz.gettz("UTC")
SIGNAL_FILE = "signal.json"

TWELVEDATA_BASE_URL = "https://api.twelvedata.com"
TELEGRAM_BASE_URL = "https://api.telegram.org/bot"

# =============================================================================
# LOGGING
# =============================================================================

def log(message: str, level: str = "INFO") -> None:
    now = datetime.now(WAT_TZ).strftime("%Y-%m-%d %H:%M:%S WAT")
    print(f"[{now}] [{level}] {message}")

# =============================================================================
# TIME UTILITIES
# =============================================================================

def get_current_wat_time() -> datetime:
    return datetime.now(WAT_TZ)

def is_trading_session_active(now: datetime = None) -> bool:
    if now is None:
        now = get_current_wat_time()
    current_time = now.time()
    session_start = datetime.strptime(f"{SESSION_START_HOUR:02d}:{SESSION_START_MINUTE:02d}", "%H:%M").time()
    session_end = datetime.strptime(f"{SESSION_END_HOUR:02d}:{SESSION_END_MINUTE:02d}", "%H:%M").time()
    return session_start <= current_time <= session_end

def is_opening_range_period(now: datetime = None) -> bool:
    if now is None:
        now = get_current_wat_time()
    current_time = now.time()
    or_start = datetime.strptime(f"{OR_START_HOUR:02d}:{OR_START_MINUTE:02d}", "%H:%M").time()
    or_end = datetime.strptime(f"{OR_END_HOUR:02d}:{OR_END_MINUTE:02d}", "%H:%M").time()
    return or_start <= current_time <= or_end

def is_weekend(now: datetime = None) -> bool:
    if now is None:
        now = get_current_wat_time()
    return now.weekday() >= 5

def format_wat_time(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    wat_dt = dt.astimezone(WAT_TZ)
    return wat_dt.strftime("%I:%M %p WAT")

def format_wat_date(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC_TZ)
    wat_dt = dt.astimezone(WAT_TZ)
    return wat_dt.strftime("%d %b %Y")

def get_session_countdown(now: datetime = None) -> str:
    if now is None:
        now = get_current_wat_time()
    session_end = now.replace(hour=SESSION_END_HOUR, minute=SESSION_END_MINUTE, second=0, microsecond=0)
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
    try:
        with open(SIGNAL_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except IOError as e:
        log(f"Error saving signal file: {e}", "ERROR")
        return False

def create_default_signal_data() -> dict:
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
            "signal_date": None,
            "status": "waiting",        # waiting, active, tp_hit, sl_hit, session_ended
            "tp_hit": False,
            "sl_hit": False,
            "exit_price": None,
            "exit_time": None
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
    api_key = os.environ.get("TWELVEDATA_API_KEY", "")
    if not api_key:
        log("TWELVEDATA_API_KEY not found in environment!", "ERROR")
    return api_key

def get_telegram_credentials() -> tuple:
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token:
        log("TELEGRAM_BOT_TOKEN not found in environment!", "ERROR")
    if not chat_id:
        log("TELEGRAM_CHAT_ID not found in environment!", "ERROR")
    return bot_token, chat_id

def fetch_xauusd_candles(api_key: str, interval: str = "15min", outputsize: int = 50) -> list:
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
    if not api_key:
        return None
    url = f"{TWELVEDATA_BASE_URL}/price"
    params = {"symbol": "XAU/USD", "apikey": api_key}
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
# SIGNAL LOGIC
# =============================================================================

def find_opening_range_candle(candles: list, target_date: str) -> dict:
    or_datetime_prefix = f"{target_date} 14:30:00"
    or_datetime_prefix_alt = f"{target_date} 14:30"
    for candle in candles:
        dt = candle.get("datetime", "")
        if or_datetime_prefix in dt or or_datetime_prefix_alt in dt:
            log(f"Found Opening Range candle: {dt}")
            return candle
    return None

def calculate_take_profit(entry: float, stop_loss: float, position: str) -> float:
    risk = abs(entry - stop_loss)
    reward = risk * RISK_REWARD_RATIO
    if position == "BUY":
        return entry + reward
    return entry - reward

def format_price(price: float) -> str:
    return f"{price:.2f}"

def build_signal_message(signal_type: str, entry: float, stop_loss: float,
                         take_profit: float, signal_time: str, signal_date: str) -> str:
    emoji = "🟢" if signal_type == "BUY" else "🔴"
    return f"""📊 <b>XAUUSD SIGNAL</b>

{emoji} <b>{signal_type}</b>

<b>Entry:</b> {format_price(entry)}
<b>Stop Loss:</b> {format_price(stop_loss)}
<b>Take Profit:</b> {format_price(take_profit)}

<b>Timeframe:</b> M15
<b>Date:</b> {signal_date}
<b>Signal Time:</b> {signal_time}
<b>Session:</b> 2:30 PM - 8:45 PM WAT"""

def build_tp_message(signal_type: str, entry: float, take_profit: float,
                     exit_price: float, exit_time: str) -> str:
    emoji = "🟢" if signal_type == "BUY" else "🔴"
    profit = abs(exit_price - entry)
    return f"""📊 <b>XAUUSD UPDATE</b>

{emoji} <b>{signal_type} — TAKE PROFIT HIT</b> ✅

<b>Entry:</b> {format_price(entry)}
<b>Take Profit:</b> {format_price(take_profit)}
<b>Exit Price:</b> {format_price(exit_price)}
<b>Profit:</b> +{format_price(profit)} pips

<b>Exit Time:</b> {exit_time}
<b>Status:</b> Trade closed. Monitoring for next opportunity."""

def build_sl_message(signal_type: str, entry: float, stop_loss: float,
                     exit_price: float, exit_time: str) -> str:
    emoji = "🟢" if signal_type == "BUY" else "🔴"
    loss = abs(entry - exit_price)
    return f"""📊 <b>XAUUSD UPDATE</b>

{emoji} <b>{signal_type} — STOP LOSS HIT</b> ⚠️

<b>Entry:</b> {format_price(entry)}
<b>Stop Loss:</b> {format_price(stop_loss)}
<b>Exit Price:</b> {format_price(exit_price)}
<b>Loss:</b> -{format_price(loss)} pips

<b>Exit Time:</b> {exit_time}
<b>Status:</b> Trade stopped out. Waiting for opposite breakout."""

def should_reset_for_new_day(data: dict, now: datetime) -> bool:
    or_date = data.get("opening_range", {}).get("date")
    today_str = now.strftime("%Y-%m-%d")
    if or_date is None:
        return True
    return or_date != today_str

def reset_daily_state(data: dict, now: datetime) -> dict:
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
        "signal_date": None,
        "status": "waiting",
        "tp_hit": False,
        "sl_hit": False,
        "exit_price": None,
        "exit_time": None
    }
    data["latest_signal"] = None
    return data

def check_tp_sl_hit(current_state: dict, latest_candle: dict, or_high: float, or_low: float,
                    bot_token: str, chat_id: str) -> dict:
    """
    Check if current active trade has hit TP or SL.
    Returns updated current_state.
    """
    position = current_state.get("position")
    entry = current_state.get("entry")
    tp = current_state.get("take_profit")
    sl = current_state.get("stop_loss")
    status = current_state.get("status", "waiting")

    if status != "active" or not position or not entry:
        return current_state

    latest_high = latest_candle["high"]
    latest_low = latest_candle["low"]
    latest_close = latest_candle["close"]
    candle_time = format_wat_time(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))

    tp_hit = False
    sl_hit = False
    exit_price = None

    if position == "BUY":
        # TP hit: price reached or exceeded TP level
        if latest_high >= tp:
            tp_hit = True
            exit_price = tp
            log(f"BUY TP HIT! Entry: {entry}, TP: {tp}, Exit: {exit_price}")
        # SL hit: price reached or went below SL
        elif latest_low <= sl:
            sl_hit = True
            exit_price = sl
            log(f"BUY SL HIT! Entry: {entry}, SL: {sl}, Exit: {exit_price}")

    elif position == "SELL":
        # TP hit: price reached or went below TP
        if latest_low <= tp:
            tp_hit = True
            exit_price = tp
            log(f"SELL TP HIT! Entry: {entry}, TP: {tp}, Exit: {exit_price}")
        # SL hit: price reached or exceeded SL
        elif latest_high >= sl:
            sl_hit = True
            exit_price = sl
            log(f"SELL SL HIT! Entry: {entry}, SL: {sl}, Exit: {exit_price}")

    if tp_hit:
        current_state["status"] = "tp_hit"
        current_state["tp_hit"] = True
        current_state["exit_price"] = exit_price
        current_state["exit_time"] = candle_time

        # Send TP notification
        message = build_tp_message(position, entry, tp, exit_price, candle_time)
        send_telegram_message(bot_token, chat_id, message)

        # Update latest signal with exit info
        if data.get("latest_signal"):
            data["latest_signal"]["exit_price"] = exit_price
            data["latest_signal"]["exit_time"] = candle_time
            data["latest_signal"]["result"] = "TP_HIT"

    elif sl_hit:
        current_state["status"] = "sl_hit"
        current_state["sl_hit"] = True
        current_state["exit_price"] = exit_price
        current_state["exit_time"] = candle_time

        # Send SL notification
        message = build_sl_message(position, entry, sl, exit_price, candle_time)
        send_telegram_message(bot_token, chat_id, message)

        if data.get("latest_signal"):
            data["latest_signal"]["exit_price"] = exit_price
            data["latest_signal"]["exit_time"] = candle_time
            data["latest_signal"]["result"] = "SL_HIT"

    return current_state

# =============================================================================
# MAIN SIGNAL PROCESSING
# =============================================================================

def process_signals() -> bool:
    global data
    now = get_current_wat_time()
    today_str = now.strftime("%Y-%m-%d")

    log(f"Starting signal processing at {now.strftime('%Y-%m-%d %H:%M:%S WAT')}")

    data = load_signal_data()
    data["session_info"]["is_active"] = is_trading_session_active(now)
    data["session_info"]["countdown"] = get_session_countdown(now)

    if is_weekend(now):
        log("Weekend detected - markets closed. Skipping.")
        data["market_data"]["current_price"] = None
        data["market_data"]["last_updated"] = now.isoformat()
        save_signal_data(data)
        return False

    api_key = get_twelve_data_api_key()
    bot_token, chat_id = get_telegram_credentials()

    if not api_key:
        log("Missing API key. Cannot proceed.", "ERROR")
        save_signal_data(data)
        return False

    # Fetch current price
    current_price = fetch_current_price(api_key)
    if current_price:
        data["market_data"]["current_price"] = current_price
        data["market_data"]["last_updated"] = now.isoformat()

    # Reset for new day
    if should_reset_for_new_day(data, now):
        data = reset_daily_state(data, now)

    # Session not active yet
    if not is_trading_session_active(now):
        log("Trading session not active yet.")
        save_signal_data(data)
        return False

    # Fetch candles
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
        or_candle = find_opening_range_candle(candles, today_str)
        if or_candle:
            or_high = or_candle["high"]
            or_low = or_candle["low"]
            data["opening_range"]["high"] = or_high
            data["opening_range"]["low"] = or_low
            data["opening_range"]["date"] = today_str
            data["opening_range"]["formed"] = True
            log(f"Opening Range formed - High: {or_high}, Low: {or_low}")
        else:
            log("Opening Range candle not yet available.")
            save_signal_data(data)
            return False

    # =====================================================================
    # STEP 2: Filter today's candles and get latest
    # =====================================================================
    today_candles = [c for c in candles if today_str in c["datetime"]]
    if len(today_candles) < 2:
        log("Not enough candles from today to evaluate.")
        save_signal_data(data)
        return False

    or_candle = today_candles[0]
    latest_candle = today_candles[-1]

    if latest_candle["datetime"] == or_candle["datetime"]:
        log("Latest candle is still the OR candle. No breakout possible yet.")
        save_signal_data(data)
        return False

    latest_close = latest_candle["close"]
    latest_high = latest_candle["high"]
    latest_low = latest_candle["low"]

    log(f"Latest candle - Close: {latest_close}, High: {latest_high}, Low: {latest_low}")
    log(f"OR - High: {or_high}, Low: {or_low}")

    # =====================================================================
    # STEP 3: Check TP/SL on active trade FIRST
    # =====================================================================
    current_state = data.get("current_state", {})
    status = current_state.get("status", "waiting")

    if status == "active":
        current_state = check_tp_sl_hit(current_state, latest_candle, or_high, or_low, bot_token, chat_id)
        data["current_state"] = current_state
        status = current_state["status"]

        if status == "tp_hit":
            log("TP was hit. No new same-direction signals for this move.")
            save_signal_data(data)
            return True

    # =====================================================================
    # STEP 4: Generate new signals (only if not blocked)
    # =====================================================================
    active_position = current_state.get("position")
    tp_hit = current_state.get("tp_hit", False)
    signal_generated = False

    # BUY signal: close above OR High
    if latest_close > or_high:
        # Block if: already in BUY, or TP was hit on a previous BUY
        if active_position == "BUY" and (status == "active" or tp_hit):
            if tp_hit:
                log("BUY breakout detected but TP was already hit on this move. Waiting for opposite breakout.")
            else:
                log("BUY condition met but already in BUY position. No duplicate.")
        elif active_position == "SELL" and status == "active":
            log("BUY breakout while in SELL. Closing SELL and generating BUY.")
            # This is an opposite breakout - generate new BUY
            signal_generated = generate_buy_signal(data, latest_candle, or_low, bot_token, chat_id, now)
        elif status in ["waiting", "sl_hit"]:
            # Fresh signal or after SL hit
            signal_generated = generate_buy_signal(data, latest_candle, or_low, bot_token, chat_id, now)

    # SELL signal: close below OR Low
    elif latest_close < or_low:
        if active_position == "SELL" and (status == "active" or tp_hit):
            if tp_hit:
                log("SELL breakout detected but TP was already hit on this move. Waiting for opposite breakout.")
            else:
                log("SELL condition met but already in SELL position. No duplicate.")
        elif active_position == "BUY" and status == "active":
            log("SELL breakout while in BUY. Closing BUY and generating SELL.")
            signal_generated = generate_sell_signal(data, latest_candle, or_high, bot_token, chat_id, now)
        elif status in ["waiting", "sl_hit"]:
            signal_generated = generate_sell_signal(data, latest_candle, or_high, bot_token, chat_id, now)
    else:
        log(f"No breakout. Price {latest_close} within OR range ({or_low} - {or_high}).")

    save_signal_data(data)

    if signal_generated:
        log("Signal processing complete. New signal generated.")
    else:
        log("Signal processing complete. No new signal.")

    return signal_generated

def generate_buy_signal(data: dict, latest_candle: dict, stop_loss: float,
                        bot_token: str, chat_id: str, now: datetime) -> bool:
    entry = latest_candle["close"]
    take_profit = calculate_take_profit(entry, stop_loss, "BUY")

    signal_time = format_wat_time(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))
    signal_date = format_wat_date(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))

    data["current_state"] = {
        "active_signal": True,
        "position": "BUY",
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "signal_time": signal_time,
        "signal_date": signal_date,
        "status": "active",
        "tp_hit": False,
        "sl_hit": False,
        "exit_price": None,
        "exit_time": None
    }

    data["latest_signal"] = {
        "type": "BUY",
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "time": signal_time,
        "date": signal_date,
        "timestamp": now.isoformat(),
        "result": None,
        "exit_price": None,
        "exit_time": None
    }

    data["signal_history"].insert(0, data["latest_signal"])
    data["signal_history"] = data["signal_history"][:100]

    log(f"BUY SIGNAL - Entry: {entry}, SL: {stop_loss}, TP: {take_profit}")

    message = build_signal_message("BUY", entry, stop_loss, take_profit, signal_time, signal_date)
    send_telegram_message(bot_token, chat_id, message)

    return True

def generate_sell_signal(data: dict, latest_candle: dict, stop_loss: float,
                         bot_token: str, chat_id: str, now: datetime) -> bool:
    entry = latest_candle["close"]
    take_profit = calculate_take_profit(entry, stop_loss, "SELL")

    signal_time = format_wat_time(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))
    signal_date = format_wat_date(datetime.strptime(latest_candle["datetime"], "%Y-%m-%d %H:%M:%S"))

    data["current_state"] = {
        "active_signal": True,
        "position": "SELL",
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "signal_time": signal_time,
        "signal_date": signal_date,
        "status": "active",
        "tp_hit": False,
        "sl_hit": False,
        "exit_price": None,
        "exit_time": None
    }

    data["latest_signal"] = {
        "type": "SELL",
        "entry": entry,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "time": signal_time,
        "date": signal_date,
        "timestamp": now.isoformat(),
        "result": None,
        "exit_price": None,
        "exit_time": None
    }

    data["signal_history"].insert(0, data["latest_signal"])
    data["signal_history"] = data["signal_history"][:100]

    log(f"SELL SIGNAL - Entry: {entry}, SL: {stop_loss}, TP: {take_profit}")

    message = build_signal_message("SELL", entry, stop_loss, take_profit, signal_time, signal_date)
    send_telegram_message(bot_token, chat_id, message)

    return True

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
