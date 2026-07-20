#!/usr/bin/env python3
"""
DollarProFx Signal Engine
Core trading logic for XAUUSD ORBS (Opening Range Breakout Strategy).

This script:
1. Fetches M15 candle data from Twelve Data
2. Identifies the Opening Range (2:15 PM - 2:30 PM WAT)
3. Monitors confirmed candle closes for breakouts
4. Generates BUY/SELL signals with proper risk management
5. Detects Stop Loss and Take Profit hits
6. Sends Telegram notifications
7. Updates signal.json
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime, timedelta, time as dt_time
from typing import Optional, Dict, Any, List, Tuple
import pytz

import config

# ── Logging Setup ───────────────────────────────────────────────────
LOG_DIR = config.LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

log_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

# File handler
file_handler = logging.FileHandler(
    os.path.join(LOG_DIR, f"signal_engine_{datetime.now().strftime('%Y%m%d')}.log"),
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

logger = logging.getLogger("DollarProFx")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ── Timezone Handling ───────────────────────────────────────────────
WAT = pytz.timezone(config.WAT_TIMEZONE)
UTC = pytz.utc


def get_wat_now() -> datetime:
    """Get current time in WAT timezone."""
    return datetime.now(WAT)


def get_wat_date(dt: datetime) -> datetime:
    """Convert datetime to WAT timezone."""
    if dt.tzinfo is None:
        dt = UTC.localize(dt)
    return dt.astimezone(WAT)


# ── Twelve Data API ────────────────────────────────────────────────
class TwelveDataClient:
    """Client for Twelve Data API with retry logic."""

    BASE_URL = "https://api.twelvedata.com"

    def __init__(self, api_key: str):
        self.api_key = api_key
        if not api_key:
            logger.error("TWELVEDATA_API_KEY is not set!")

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Make API request with retry logic."""
        params["apikey"] = self.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        for attempt in range(config.API_RETRY_ATTEMPTS):
            try:
                response = requests.get(url, params=params, timeout=30)

                if response.status_code == 429:
                    logger.warning(f"Rate limited. Waiting {config.API_RETRY_DELAY * (attempt + 1)}s...")
                    time.sleep(config.API_RETRY_DELAY * (attempt + 1))
                    continue

                response.raise_for_status()
                data = response.json()

                if "code" in data and data.get("code") != 200:
                    logger.error(f"API error: {data}")
                    return None

                return data

            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                logger.warning(f"Connection error (attempt {attempt + 1})")
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error: {e}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return None

            time.sleep(config.API_RETRY_DELAY)

        logger.error("All retry attempts failed")
        return None

    def get_time_series(self, symbol: str, interval: str, 
                        start_date: str, end_date: str) -> Optional[List[Dict]]:
        """Fetch historical candle data."""
        params = {
            "symbol": symbol,
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "format": "JSON",
            "timezone": "UTC"
        }

        data = self._make_request("time_series", params)
        if data and "values" in data:
            return data["values"]
        return None

    def get_quote(self, symbol: str) -> Optional[Dict]:
        """Get latest quote/price."""
        params = {"symbol": symbol}
        return self._make_request("quote", params)


# ── Telegram Bot ───────────────────────────────────────────────────
class TelegramNotifier:
    """Telegram bot for sending trade signals and updates."""

    BASE_URL = "https://api.telegram.org/bot{token}"

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = self.BASE_URL.format(token=bot_token)

        if not bot_token or not chat_id:
            logger.error("Telegram credentials not set!")

    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        """Send message to Telegram with retry logic."""
        if not self.bot_token or not self.chat_id:
            logger.error("Cannot send Telegram message: credentials missing")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        for attempt in range(config.API_RETRY_ATTEMPTS):
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
                logger.warning(f"Telegram send failed (attempt {attempt + 1}): {e}")
                time.sleep(config.API_RETRY_DELAY)

        logger.error("Failed to send Telegram message after all retries")
        return False

    def format_buy_signal(self, entry: float, sl: float, tp: float, 
                          date_str: str, time_str: str) -> str:
        """Format BUY signal message."""
        return f"""📊 <b>XAUUSD SIGNAL</b>

🟢 <b>BUY</b>

Entry: {entry:.2f}
Stop Loss: {sl:.2f}
Take Profit: {tp:.2f}

Timeframe: M15
Date: {date_str}
Signal Time: {time_str}
Session: 2:30 PM – 8:45 PM WAT"""

    def format_sell_signal(self, entry: float, sl: float, tp: float,
                           date_str: str, time_str: str) -> str:
        """Format SELL signal message."""
        return f"""📊 <b>XAUUSD SIGNAL</b>

🔴 <b>SELL</b>

Entry: {entry:.2f}
Stop Loss: {sl:.2f}
Take Profit: {tp:.2f}

Timeframe: M15
Date: {date_str}
Signal Time: {time_str}
Session: 2:30 PM – 8:45 PM WAT"""

    def format_sl_update(self, direction: str, date_str: str, time_str: str) -> str:
        """Format Stop Loss hit message."""
        return f"""⚠️ <b>XAUUSD TRADE UPDATE</b>

The previous {direction} trade has been closed at Stop Loss.

Date: {date_str}
Time: {time_str}

We are now monitoring the market for the next confirmed breakout.

No new trade is active at this time."""

    def format_tp_update(self, direction: str, date_str: str, time_str: str) -> str:
        """Format Take Profit hit message."""
        return f"""🎯 <b>XAUUSD TRADE UPDATE</b>

The previous {direction} trade has reached Take Profit.

Trade closed successfully.

Date: {date_str}
Time: {time_str}

We are now monitoring the market for the next confirmed breakout."""


# ── Signal State Management ────────────────────────────────────────
class SignalState:
    """Manages signal state persistence in signal.json."""

    def __init__(self, filepath: str = config.SIGNAL_FILE):
        self.filepath = filepath
        self._data = self._load()

    def _load(self) -> Dict:
        """Load state from file."""
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading signal.json: {e}")

        return self._default_state()

    def _default_state(self) -> Dict:
        """Return default state structure."""
        return {
            "latest_signal": None,
            "signal_history": [],
            "opening_range": {
                "high": None,
                "low": None,
                "date": None
            },
            "active_trade": None,
            "session_status": "WAITING",
            "last_updated": None,
            "current_gold_price": None
        }

    def save(self) -> bool:
        """Save state to file."""
        try:
            self._data["last_updated"] = get_wat_now().isoformat()
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            logger.error(f"Error saving signal.json: {e}")
            return False

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value

    def add_to_history(self, signal: Dict):
        """Add signal to history, keeping last 50 entries."""
        history = self._data.get("signal_history", [])
        history.insert(0, signal)
        self._data["signal_history"] = history[:50]

    def reset_for_new_day(self):
        """Reset state for a new trading day."""
        self._data["opening_range"] = {"high": None, "low": None, "date": None}
        self._data["active_trade"] = None
        self._data["session_status"] = "WAITING"
        logger.info("State reset for new trading day")


# ── Trading Session Logic ──────────────────────────────────────────
class TradingSession:
    """Manages trading session timing and state."""

    def __init__(self):
        self.wat_now = get_wat_now()

    def is_trading_day(self) -> bool:
        """Check if today is a trading day (Mon-Fri)."""
        return self.wat_now.weekday() < 5  # 0=Mon, 4=Fri

    def is_session_active(self) -> bool:
        """Check if we're within the trading session."""
        if not self.is_trading_day():
            return False

        current_time = self.wat_now.time()
        start = config.SESSION_START_TIME
        end = config.SESSION_END_TIME

        return start <= current_time <= end

    def is_before_session(self) -> bool:
        """Check if we're before the session starts."""
        if not self.is_trading_day():
            return False
        current_time = self.wat_now.time()
        return current_time < config.SESSION_START_TIME

    def is_after_session(self) -> bool:
        """Check if session has ended for the day."""
        if not self.is_trading_day():
            return True
        current_time = self.wat_now.time()
        return current_time > config.SESSION_END_TIME

    def is_opening_range_time(self) -> bool:
        """Check if we're in the opening range period."""
        if not self.is_trading_day():
            return False
        current_time = self.wat_now.time()
        return config.OPENING_RANGE_START <= current_time <= config.OPENING_RANGE_END

    def is_after_opening_range(self) -> bool:
        """Check if opening range candle has closed."""
        if not self.is_trading_day():
            return False
        current_time = self.wat_now.time()
        return current_time > config.OPENING_RANGE_END

    def get_session_countdown(self) -> str:
        """Get countdown until session ends."""
        if self.is_after_session():
            return "Session Ended"

        end_dt = datetime.combine(self.wat_now.date(), config.SESSION_END_TIME)
        end_dt = WAT.localize(end_dt)

        if end_dt < self.wat_now:
            return "Session Ended"

        diff = end_dt - self.wat_now
        hours, remainder = divmod(int(diff.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}"

    def get_date_str(self) -> str:
        """Get formatted date string."""
        return self.wat_now.strftime("%d %b %Y")

    def get_time_str(self) -> str:
        """Get formatted time string."""
        return self.wat_now.strftime("%I:%M %p WAT")


# ── Candle Data Processing ─────────────────────────────────────────
def parse_candle(candle: Dict) -> Dict:
    """Parse a candle from Twelve Data format."""
    return {
        "datetime": candle.get("datetime"),
        "open": float(candle.get("open", 0)),
        "high": float(candle.get("high", 0)),
        "low": float(candle.get("low", 0)),
        "close": float(candle.get("close", 0)),
        "volume": int(candle.get("volume", 0))
    }


def find_opening_range_candle(candles: List[Dict], session: TradingSession) -> Optional[Dict]:
    """
    Find the M15 candle that opens at 2:15 PM WAT and closes at 2:30 PM WAT.
    The candle datetime from Twelve Data is in UTC, so we convert to WAT.
    """
    target_date = session.wat_now.date()

    # Opening range: 2:15 PM - 2:30 PM WAT = 1:15 PM - 1:30 PM UTC
    or_start_utc = UTC.localize(datetime.combine(target_date, dt_time(13, 15)))
    or_end_utc = UTC.localize(datetime.combine(target_date, dt_time(13, 30)))

    for candle in candles:
        try:
            # Parse candle datetime (UTC from Twelve Data)
            candle_dt = datetime.strptime(candle["datetime"], "%Y-%m-%d %H:%M:%S")
            candle_dt = UTC.localize(candle_dt)

            # Check if this candle falls within our opening range window
            if or_start_utc <= candle_dt < or_end_utc:
                parsed = parse_candle(candle)
                parsed["datetime"] = candle_dt
                logger.info(f"Found Opening Range candle: High={parsed['high']}, Low={parsed['low']}")
                return parsed

        except (ValueError, KeyError) as e:
            logger.warning(f"Error parsing candle datetime: {e}")
            continue

    return None


def get_post_or_candles(candles: List[Dict], session: TradingSession) -> List[Dict]:
    """
    Get all M15 candles that closed AFTER the opening range (after 2:30 PM WAT).
    Only include COMPLETED candles (not the one currently forming).
    """
    target_date = session.wat_now.date()
    or_end_utc = datetime.combine(target_date, dt_time(13, 30))
    or_end_utc = UTC.localize(or_end_utc)

    post_candles = []

    for candle in candles:
        try:
            candle_dt = datetime.strptime(candle["datetime"], "%Y-%m-%d %H:%M:%S")
            candle_dt = UTC.localize(candle_dt)

            # Only include candles that closed after 2:30 PM WAT (1:30 PM UTC)
            if candle_dt >= or_end_utc:
                parsed = parse_candle(candle)
                parsed["datetime"] = candle_dt
                post_candles.append(parsed)

        except (ValueError, KeyError) as e:
            continue

    # Sort by datetime ascending
    post_candles.sort(key=lambda x: x["datetime"])

    # Remove the last candle if it's still forming (incomplete)
    # A candle is complete if its close time is in the past
    now_utc = datetime.now(UTC)
    complete_candles = []
    for c in post_candles:
        # M15 candle: if datetime is 13:30, it closes at 13:45
        candle_close_time = c["datetime"] + timedelta(minutes=15)
        if candle_close_time <= now_utc:
            complete_candles.append(c)

    return complete_candles


# ── Signal Generation Logic ────────────────────────────────────────
class SignalEngine:
    """Core signal generation engine implementing ORBS strategy."""

    def __init__(self):
        self.client = TwelveDataClient(config.TWELVEDATA_API_KEY)
        self.telegram = TelegramNotifier(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID)
        self.state = SignalState()
        self.session = TradingSession()

    def fetch_candles(self) -> Optional[List[Dict]]:
        """Fetch M15 candles for today."""
        today = self.session.wat_now.date()
        start_date = today.strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")

        logger.info(f"Fetching M15 candles from {start_date} to {end_date}")

        candles = self.client.get_time_series(
            symbol=config.SYMBOL,
            interval=config.TIMEFRAME,
            start_date=start_date,
            end_date=end_date
        )

        if candles:
            logger.info(f"Fetched {len(candles)} candles")
        else:
            logger.warning("No candles returned from API")

        return candles

    def fetch_current_price(self, candles: Optional[List[Dict]] = None) -> Optional[float]:
        """Fetch current gold price. Tries quote endpoint first, falls back to latest candle."""
        # Try quote endpoint first
        quote = self.client.get_quote(config.SYMBOL)
        if quote:
            logger.info(f"Quote API response: {quote}")
            # Try multiple possible price fields
            price_fields = ["price", "close", "bid", "ask", "last"]
            for field in price_fields:
                if field in quote:
                    try:
                        price = float(quote[field])
                        logger.info(f"Current price from '{field}': {price:.2f}")
                        self.state.set("current_gold_price", price)
                        return price
                    except (ValueError, TypeError):
                        continue
            logger.warning(f"Quote response missing price fields. Response: {quote}")
        else:
            logger.warning("Quote API returned no data")

        # Fallback: use latest candle close price (if candles provided)
        if candles and len(candles) > 0:
            try:
                latest = parse_candle(candles[0])
                price = latest["close"]
                logger.info(f"Current price from latest candle: {price:.2f}")
                self.state.set("current_gold_price", price)
                return price
            except Exception as e:
                logger.warning(f"Failed to get price from candles: {e}")

        return None

    def calculate_take_profit(self, entry: float, sl: float, direction: str) -> float:
        """Calculate Take Profit using 1:2 risk-reward ratio."""
        risk = abs(entry - sl)
        if direction == "BUY":
            return entry + (risk * config.RISK_REWARD_RATIO)
        else:  # SELL
            return entry - (risk * config.RISK_REWARD_RATIO)

    def check_trade_status(self, current_price: float) -> Optional[str]:
        """
        Check if active trade has hit SL or TP.
        Returns: "SL_HIT", "TP_HIT", or None
        """
        active = self.state.get("active_trade")
        if not active:
            return None

        direction = active["direction"]
        sl = active["stop_loss"]
        tp = active["take_profit"]

        logger.info(f"SL/TP Check: direction={direction}, current={current_price:.2f}, "
                   f"sl={sl:.2f}, tp={tp:.2f}")

        if direction == "BUY":
            if current_price <= sl:
                logger.info(f"BUY SL HIT: {current_price:.2f} <= {sl:.2f}")
                return "SL_HIT"
            if current_price >= tp:
                logger.info(f"BUY TP HIT: {current_price:.2f} >= {tp:.2f}")
                return "TP_HIT"
        else:  # SELL
            if current_price >= sl:
                logger.info(f"SELL SL HIT: {current_price:.2f} >= {sl:.2f}")
                return "SL_HIT"
            if current_price <= tp:
                logger.info(f"SELL TP HIT: {current_price:.2f} <= {tp:.2f}")
                return "TP_HIT"

        logger.info(f"No SL/TP hit. Price {current_price:.2f} within range.")
        return None

    def handle_sl_hit(self):
        """Handle Stop Loss hit."""
        active = self.state.get("active_trade")
        if not active:
            return

        direction = active["direction"]
        date_str = self.session.get_date_str()
        time_str = self.session.get_time_str()

        # Update active trade status
        active["status"] = "SL_HIT"
        active["close_time"] = time_str
        active["close_date"] = date_str

        # Add to history
        self.state.add_to_history(active.copy())

        # Clear active trade
        self.state.set("active_trade", None)
        self.state.set("latest_signal", None)
        self.state.set("session_status", "MONITORING")

        # Send Telegram update
        message = self.telegram.format_sl_update(direction, date_str, time_str)
        self.telegram.send_message(message)

        logger.info(f"SL HIT on {direction} trade. Trade closed.")
        self.state.save()

    def handle_tp_hit(self):
        """Handle Take Profit hit."""
        active = self.state.get("active_trade")
        if not active:
            return

        direction = active["direction"]
        date_str = self.session.get_date_str()
        time_str = self.session.get_time_str()

        # Update active trade status
        active["status"] = "TP_HIT"
        active["close_time"] = time_str
        active["close_date"] = date_str

        # Add to history
        self.state.add_to_history(active.copy())

        # Clear active trade
        self.state.set("active_trade", None)
        self.state.set("latest_signal", None)
        self.state.set("session_status", "MONITORING")

        # Send Telegram update
        message = self.telegram.format_tp_update(direction, date_str, time_str)
        self.telegram.send_message(message)

        logger.info(f"TP HIT on {direction} trade. Trade closed successfully.")
        self.state.save()

    def generate_buy_signal(self, entry: float, or_low: float, or_high: float) -> Dict:
        """Generate a BUY signal."""
        sl = or_low  # Stop Loss = Opening Range Low
        tp = self.calculate_take_profit(entry, sl, "BUY")

        date_str = self.session.get_date_str()
        time_str = self.session.get_time_str()

        signal = {
            "direction": "BUY",
            "entry": round(entry, 2),
            "stop_loss": round(sl, 2),
            "take_profit": round(tp, 2),
            "date": date_str,
            "time": time_str,
            "status": "ACTIVE",
            "opening_range_high": round(or_high, 2),
            "opening_range_low": round(or_low, 2)
        }

        return signal

    def generate_sell_signal(self, entry: float, or_low: float, or_high: float) -> Dict:
        """Generate a SELL signal."""
        sl = or_high  # Stop Loss = Opening Range High
        tp = self.calculate_take_profit(entry, sl, "SELL")

        date_str = self.session.get_date_str()
        time_str = self.session.get_time_str()

        signal = {
            "direction": "SELL",
            "entry": round(entry, 2),
            "stop_loss": round(sl, 2),
            "take_profit": round(tp, 2),
            "date": date_str,
            "time": time_str,
            "status": "ACTIVE",
            "opening_range_high": round(or_high, 2),
            "opening_range_low": round(or_low, 2)
        }

        return signal

    def send_new_signal(self, signal: Dict):
        """Send new signal via Telegram."""
        date_str = signal["date"]
        time_str = signal["time"]

        if signal["direction"] == "BUY":
            message = self.telegram.format_buy_signal(
                signal["entry"], signal["stop_loss"], signal["take_profit"],
                date_str, time_str
            )
        else:
            message = self.telegram.format_sell_signal(
                signal["entry"], signal["stop_loss"], signal["take_profit"],
                date_str, time_str
            )

        self.telegram.send_message(message)

    def run(self):
        """Main execution loop."""
        logger.info("=" * 60)
        logger.info("DollarProFx Signal Engine Started")
        logger.info(f"Current WAT Time: {self.session.wat_now.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        # Check if it's a trading day
        if not self.session.is_trading_day():
            logger.info("Weekend - no trading. Exiting.")
            self.state.set("session_status", "WEEKEND")
            self.state.save()
            return

        # Check if session has ended
        if self.session.is_after_session():
            logger.info("Trading session has ended for today.")
            self.state.set("session_status", "SESSION_ENDED")

            # If there's still an active trade, close it at current price
            active = self.state.get("active_trade")
            if active:
                active["status"] = "SESSION_CLOSED"
                active["close_time"] = self.session.get_time_str()
                active["close_date"] = self.session.get_date_str()
                self.state.add_to_history(active.copy())
                self.state.set("active_trade", None)
                self.state.set("latest_signal", None)

            self.state.save()
            return

        # Fetch current price for dashboard (quote API only, no candles yet)
        current_price = self.fetch_current_price()
        if current_price:
            logger.info(f"Current Gold Price: {current_price:.2f}")

        # Check if there's an active trade - monitor SL/TP
        active_trade = self.state.get("active_trade")
        if active_trade:
            if not current_price:
                logger.warning("Active trade exists but current price unavailable. Cannot check SL/TP.")
                self.state.save()
                return

            logger.info(f"Checking SL/TP for active {active_trade['direction']} trade: "
                       f"Entry={active_trade['entry']:.2f}, "
                       f"SL={active_trade['stop_loss']:.2f}, "
                       f"TP={active_trade['take_profit']:.2f}, "
                       f"Current={current_price:.2f}")

            trade_status = self.check_trade_status(current_price)
            logger.info(f"Trade status check result: {trade_status}")

            if trade_status == "SL_HIT":
                logger.info("STOP LOSS DETECTED! Handling SL hit...")
                self.handle_sl_hit()
                return  # Don't check for new signals after SL
            elif trade_status == "TP_HIT":
                logger.info("TAKE PROFIT DETECTED! Handling TP hit...")
                self.handle_tp_hit()
                return  # Don't check for new signals after TP
            else:
                logger.info(f"Active {active_trade['direction']} trade still running... "
                           f"Current: {current_price:.2f}, SL: {active_trade['stop_loss']:.2f}, "
                           f"TP: {active_trade['take_profit']:.2f}")
                self.state.save()
                return
        else:
            logger.info("No active trade. Checking for new breakouts...")

        # Before session starts
        if self.session.is_before_session():
            logger.info("Before trading session. Waiting for 2:30 PM WAT.")
            self.state.set("session_status", "BEFORE_SESSION")
            self.state.save()
            return

        # During opening range period
        if self.session.is_opening_range_time():
            logger.info("In opening range period (2:15-2:30 PM WAT). Waiting for candle to close.")
            self.state.set("session_status", "OPENING_RANGE")
            self.state.save()
            return

        # Fetch candles
        candles = self.fetch_candles()
        if not candles:
            logger.error("Failed to fetch candles. Will retry next cycle.")
            return

        # Update current price using latest candle (more accurate than quote)
        if candles and len(candles) > 0:
            try:
                latest = parse_candle(candles[0])
                price = latest["close"]
                logger.info(f"Updated current price from latest candle: {price:.2f}")
                self.state.set("current_gold_price", price)
            except Exception as e:
                logger.warning(f"Failed to update price from candles: {e}")

        # Find opening range candle
        or_candle = find_opening_range_candle(candles, self.session)

        if not or_candle:
            logger.warning("Opening Range candle not found yet. Waiting...")
            self.state.set("session_status", "WAITING_OR")
            self.state.save()
            return

        # Store opening range
        or_high = or_candle["high"]
        or_low = or_candle["low"]
        stored_or = self.state.get("opening_range")

        if not stored_or or stored_or.get("date") != self.session.get_date_str():
            self.state.set("opening_range", {
                "high": round(or_high, 2),
                "low": round(or_low, 2),
                "date": self.session.get_date_str()
            })
            logger.info(f"Opening Range set: High={or_high:.2f}, Low={or_low:.2f}")
        else:
            or_high = stored_or["high"]
            or_low = stored_or["low"]

        # Get completed candles after opening range
        post_candles = get_post_or_candles(candles, self.session)

        if not post_candles:
            logger.info("No completed candles after opening range yet.")
            self.state.set("session_status", "MONITORING")
            self.state.save()
            return

        logger.info(f"Monitoring {len(post_candles)} completed post-OR candles")

        # Check for breakouts on completed candles only
        # We process candles in order to find the FIRST valid breakout
        last_signal_direction = None
        if self.state.get("latest_signal"):
            last_signal_direction = self.state.get("latest_signal").get("direction")

        # Also check if we had a previous trade that closed
        # After SL/TP, we need an opposite breakout
        previous_trade = None
        if self.state.get("signal_history"):
            recent = self.state.get("signal_history")[0] if self.state.get("signal_history") else None
            if recent and recent.get("status") in ["SL_HIT", "TP_HIT", "SESSION_CLOSED"]:
                previous_trade = recent
                logger.info(f"Previous closed trade detected: {recent.get('direction')} - {recent.get('status')}")

        logger.info(f"Breakout check: last_signal={last_signal_direction}, "
                   f"previous_trade={previous_trade.get('direction') if previous_trade else None}, "
                   f"OR_High={or_high:.2f}, OR_Low={or_low:.2f}")

        for candle in post_candles:
            close_price = candle["close"]
            candle_time = candle["datetime"]

            # BUY signal: candle closes ABOVE Opening Range High
            if close_price > or_high:
                # Prevent duplicate BUY signals
                if last_signal_direction == "BUY":
                    logger.info(f"BUY breakout detected at {close_price:.2f} but duplicate prevention active")
                    continue

                # After a BUY trade closed (SL/TP), we need a SELL breakout next (opposite)
                if previous_trade and previous_trade.get("direction") == "BUY":
                    logger.info("Previous BUY trade closed. Waiting for SELL breakout.")
                    continue

                logger.info(f"🟢 BUY SIGNAL CONFIRMED! Close={close_price:.2f} > OR High={or_high:.2f}")

                signal = self.generate_buy_signal(close_price, or_low, or_high)
                self.state.set("latest_signal", signal)
                self.state.set("active_trade", signal)
                self.state.set("session_status", "ACTIVE_TRADE")

                self.send_new_signal(signal)
                self.state.save()
                return

            # SELL signal: candle closes BELOW Opening Range Low
            elif close_price < or_low:
                # Prevent duplicate SELL signals
                if last_signal_direction == "SELL":
                    logger.info(f"SELL breakout detected at {close_price:.2f} but duplicate prevention active")
                    continue

                # After a SELL trade closed (SL/TP), we need a BUY breakout next (opposite)
                if previous_trade and previous_trade.get("direction") == "SELL":
                    logger.info("Previous SELL trade closed. Waiting for BUY breakout.")
                    continue

                logger.info(f"🔴 SELL SIGNAL CONFIRMED! Close={close_price:.2f} < OR Low={or_low:.2f}")

                signal = self.generate_sell_signal(close_price, or_low, or_high)
                self.state.set("latest_signal", signal)
                self.state.set("active_trade", signal)
                self.state.set("session_status", "ACTIVE_TRADE")

                self.send_new_signal(signal)
                self.state.save()
                return

        # No breakout detected
        logger.info(f"No confirmed breakout. OR High={or_high:.2f}, OR Low={or_low:.2f}")
        self.state.set("session_status", "MONITORING")
        self.state.save()


def main():
    """Entry point."""
    engine = SignalEngine()
    engine.run()


if __name__ == "__main__":
    main()
