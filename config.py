"""
DollarProFx Configuration Module
Centralized configuration for easy administrator changes.
"""

import os

# =============================================================================
# ADMINISTRATOR CONFIGURATION
# Update these values as needed without editing multiple files
# =============================================================================

# Telegram channel link (update with your actual channel link)
TELEGRAM_CHANNEL_LINK = "https://t.me/your_channel_name"

# EXNESS partner link (update with your actual partner link)
EXNESS_PARTNER_LINK = "https://your-partner-link.com"

# Trading session times (WAT timezone)
TRADING_SESSION_START = "14:30"  # 2:30 PM WAT
TRADING_SESSION_END = "20:45"    # 8:45 PM WAT

# Opening Range candle times (WAT timezone)
OPENING_RANGE_OPEN = "14:15"     # 2:15 PM WAT
OPENING_RANGE_CLOSE = "14:30"    # 2:30 PM WAT

# Risk-to-Reward ratio
RISK_REWARD_RATIO = 2.0

# Trading symbol
SYMBOL = "XAU/USD"

# Timeframe
TIMEFRAME = "15min"

# Timezone
TIMEZONE = "Africa/Lagos"  # WAT

# =============================================================================
# API CONFIGURATION (Read from Environment / GitHub Secrets)
# =============================================================================

TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# =============================================================================
# FILE PATHS
# =============================================================================

USERS_FILE = "users.json"
SIGNAL_FILE = "signal.json"
LOGS_DIR = "logs"

# =============================================================================
# TELEGRAM MESSAGE TEMPLATES
# =============================================================================

TELEGRAM_BUY_TEMPLATE = """📊 XAUUSD SIGNAL

🟢 BUY

Entry: {entry:.2f}
Stop Loss: {stop_loss:.2f}
Take Profit: {take_profit:.2f}

Timeframe: M15
Date: {date}
Signal Time: {time} WAT
Session: 2:30 PM – 8:45 PM WAT"""

TELEGRAM_SELL_TEMPLATE = """📊 XAUUSD SIGNAL

🔴 SELL

Entry: {entry:.2f}
Stop Loss: {stop_loss:.2f}
Take Profit: {take_profit:.2f}

Timeframe: M15
Date: {date}
Signal Time: {time} WAT
Session: 2:30 PM – 8:45 PM WAT"""

TELEGRAM_SL_TEMPLATE = """⚠️ XAUUSD TRADE UPDATE

The previous {direction} trade has been closed at Stop Loss.

Date: {date}
Time: {time} WAT

We are now monitoring the market for the next confirmed breakout.
No new trade is active at this time."""

TELEGRAM_TP_TEMPLATE = """🎯 XAUUSD TRADE UPDATE

The previous {direction} trade has reached Take Profit.
Trade closed successfully.

Date: {date}
Time: {time} WAT

We are now monitoring the market for the next confirmed breakout."""
