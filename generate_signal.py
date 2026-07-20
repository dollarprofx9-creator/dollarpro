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
import traceback

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

    def get_latest_candles(self, symbol: str, interval: str, outputsize: int = 2) -> Optional[List[Dict]]:
        """Fetch the latest N candles from time_series endpoint."""
        params = {
            "symbol": symbol,
            "interval": interval,
            "outputsize": outputsize,
            "format": "JSON",
            "timezone": "UTC"
        }
        data = self._make_request("time_series", params)
        if data and "values" in data:
            return data["values"]
        return None


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
    """
    Manages signal state persistence in signal.json.

    APPROACH: Fresh start each run.
    - Loads ONLY signal_history from existing file (preserves trade record)
    - Everything else resets to current run values
    - Prevents stale state from blocking new signals
    """

    def __init__(self, filepath: str = config.SIGNAL_FILE):
        self.filepath = filepath
        self._data = self._fresh_start()

    def _fresh_start(self) -> Dict:
        """
        Start fresh each run. Only preserve signal_history from old file.
        All other fields get current run values (not stale data).
        """
        preserved_history = []

        # Try to load ONLY the history from existing file
        try:
            if os.path.exists(self.filepath):
                with open(self.filepath, "r", encoding="utf-8") as f:
                    old_data = json.load(f)
                    preserved_history = old_data.get("signal_history", [])
                    logger.info(f"Loaded {len(preserved_history)} historical trades from signal.json")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load old signal.json: {e}. Starting with empty history.")

        # Build fresh state with preserved history only
        fresh_state = {
            "latest_signal": None,           # Reset - no stale signal
            "signal_history": preserved_history,  # Keep trade record
            "opening_range": {
                "high": None,
                "low": None,
                "date": None
            },
            "active_trade": None,            # Reset - no stale trade
            "session_status": "WAITING",     # Reset - fresh status
            "last_updated": None,
            "current_gold_price": None       # Will be updated this run
        }

        logger.info(f"Fresh state initialized. History preserved: {len(preserved_history)} trades")
        return fresh_state

    def save(self) -> bool:
        """Save current state to file (overwrites old content completely)."""
        try:
            self._data["last_updated"] = get_wat_now().isoformat()
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.info(f"✅ signal.json saved successfully: {self.filepath}")
            return True
        except IOError as e:
            logger.error(f"❌ Error saving signal.json: {e}")
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
        logger.info(f"Trade added to history. Total history: {len(history)} trades")

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

    logger.info(f"Searching for OR candle between {or_start_utc} and {or_end_utc}")
    logger.info(f"Total candles fetched: {len(candles)}")

    for i, candle in enumerate(candles[:10]):  # Log first 10 candles
        logger.info(f"Candle {i}: datetime={candle.get('datetime')}, open={candle.get('open')}, high={candle.get('high')}, low={candle.get('low')}, close={candle.get('close')}")

    for candle in candles:
        try:
            # Parse candle datetime (UTC from Twelve Data)
            candle_dt = datetime.strptime(candle["datetime"], "%Y-%m-%d %H:%M:%S")
            candle_dt = UTC.localize(candle_dt)

            # Check if this candle falls within our opening range window
            logger.debug(f"Checking candle at {candle_dt} against OR window {or_start_utc} - {or_end_utc}")
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

    logger.info(f"Looking for post-OR candles after {or_end_utc}")
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

    def fetch_current_price(self) -> Optional[Dict]:
        """
        Fetch latest 2 M15 candles from Twelve Data time_series endpoint.
        Returns the latest candle dict with OHLC values.
        Uses latest["close"] as current_gold_price.
        """
        logger.info("=" * 50)
        logger.info("Fetching latest candles from Twelve Data")
        logger.info(f"URL: https://api.twelvedata.com/time_series")
        logger.info(f"Params: symbol={config.SYMBOL}, interval={config.TIMEFRAME}, outputsize=2")

        candles = self.client.get_latest_candles(
            symbol=config.SYMBOL,
            interval=config.TIMEFRAME,
            outputsize=2
        )

        if not candles or len(candles) < 2:
            logger.error("Failed to fetch latest candles from time_series endpoint")
            return None

        logger.info(f"Raw API response candles count: {len(candles)}")

        # Parse candles exactly like the dashboard
        latest = parse_candle(candles[0])
        previous = parse_candle(candles[1])

        logger.info(f"Latest candle: datetime={latest['datetime']}, open={latest['open']:.2f}, high={latest['high']:.2f}, low={latest['low']:.2f}, close={latest['close']:.2f}")
        logger.info(f"Previous candle: datetime={previous['datetime']}, open={previous['open']:.2f}, high={previous['high']:.2f}, low={previous['low']:.2f}, close={previous['close']:.2f}")

        # Use latest close as current market price (same as dashboard)
        current_price = latest["close"]
        logger.info(f"Current market price (latest close): {current_price:.2f}")

        # Save to signal.json
        self.state.set("current_gold_price", round(current_price, 2))
        logger.info(f"Saved current_gold_price={round(current_price, 2)} to signal.json")

        # Return the full latest candle for SL/TP detection
        return latest

    def calculate_take_profit(self, entry: float, sl: float, direction: str) -> float:
        """Calculate Take Profit using 1:2 risk-reward ratio."""
        risk = abs(entry - sl)
        if direction == "BUY":
            return entry + (risk * config.RISK_REWARD_RATIO)
        else:  # SELL
            return entry - (risk * config.RISK_REWARD_RATIO)

    def check_trade_status(self, latest_candle: Dict) -> Optional[str]:
        """
        Check if active trade has hit SL or TP using the latest completed candle's High and Low.
        This detects if price touched SL or TP at ANY point during the candle.

        BUY trades:
            - SL_HIT if latest.low <= stop_loss (price dropped to SL)
            - TP_HIT if latest.high >= take_profit (price rose to TP)

        SELL trades:
            - SL_HIT if latest.high >= stop_loss (price rose to SL)
            - TP_HIT if latest.low <= take_profit (price dropped to TP)

        Returns: "SL_HIT", "TP_HIT", or None
        """
        active = self.state.get("active_trade")
        if not active:
            return None

        direction = active["direction"]
        sl = active["stop_loss"]
        tp = active["take_profit"]

        candle_high = latest_candle["high"]
        candle_low = latest_candle["low"]
        candle_close = latest_candle["close"]

        logger.info("=" * 50)
        logger.info("SL/TP DETECTION USING CANDLE HIGH/LOW")
        logger.info(f"Trade: {direction}, Entry={active['entry']:.2f}, SL={sl:.2f}, TP={tp:.2f}")
        logger.info(f"Latest candle: High={candle_high:.2f}, Low={candle_low:.2f}, Close={candle_close:.2f}")

        if direction == "BUY":
            logger.info(f"BUY check: low({candle_low:.2f}) <= sl({sl:.2f})? {candle_low <= sl}")
            logger.info(f"BUY check: high({candle_high:.2f}) >= tp({tp:.2f})? {candle_high >= tp}")

            if candle_low <= sl:
                logger.info(f"🚨 BUY SL HIT: Candle low {candle_low:.2f} touched Stop Loss {sl:.2f}")
                return "SL_HIT"
            if candle_high >= tp:
                logger.info(f"🎯 BUY TP HIT: Candle high {candle_high:.2f} touched Take Profit {tp:.2f}")
                return "TP_HIT"
        else:  # SELL
            logger.info(f"SELL check: high({candle_high:.2f}) >= sl({sl:.2f})? {candle_high >= sl}")
            logger.info(f"SELL check: low({candle_low:.2f}) <= tp({tp:.2f})? {candle_low <= tp}")

            if candle_high >= sl:
                logger.info(f"🚨 SELL SL HIT: Candle high {candle_high:.2f} touched Stop Loss {sl:.2f}")
                return "SL_HIT"
            if candle_low <= tp:
                logger.info(f"🎯 SELL TP HIT: Candle low {candle_low:.2f} touched Take Profit {tp:.2f}")
                return "TP_HIT"

        logger.info(f"✅ No SL/TP hit. Candle range {candle_low:.2f}-{candle_high:.2f} within safe zone.")
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
        logger.info("✅ signal.json updated successfully (SL_HIT recorded)")

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
        logger.info("✅ signal.json updated successfully (TP_HIT recorded)")

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

        try:
            self._run_internal()
        except Exception as e:
            logger.error(f"CRITICAL ERROR in signal engine: {e}")
            logger.error(traceback.format_exc())
        finally:
            # Always save state, even on error
            logger.info("Saving state to signal.json...")
            self.state.save()
            logger.info("State saved.")

    def _run_internal(self):

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

        # Fetch latest 2 M15 candles from Twelve Data time_series
        latest_candle = self.fetch_current_price()
        if latest_candle:
            logger.info(f"Current Gold Price (latest close): {latest_candle['close']:.2f}")

        # Check if there's an active trade - monitor SL/TP using latest candle High/Low
        active_trade = self.state.get("active_trade")
        if active_trade:
            if not latest_candle:
                logger.warning("Active trade exists but latest candle unavailable. Cannot check SL/TP.")
                self.state.save()
                return

            logger.info(f"Checking SL/TP for active {active_trade['direction']} trade: "
                       f"Entry={active_trade['entry']:.2f}, "
                       f"SL={active_trade['stop_loss']:.2f}, "
                       f"TP={active_trade['take_profit']:.2f}")

            trade_status = self.check_trade_status(latest_candle)
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
                           f"SL: {active_trade['stop_loss']:.2f}, "
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
        logger.info("✅ signal.json updated successfully (MONITORING status)")


def main():
    """Entry point."""
    engine = SignalEngine()
    engine.run()


if __name__ == "__main__":
    main()
