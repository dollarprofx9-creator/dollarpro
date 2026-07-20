"""
DollarProFx Configuration
Centralized configuration for easy administrator changes.
"""

import os
from datetime import time

# ── Trading Configuration ──────────────────────────────────────────
SYMBOL = "XAU/USD"                    # Trading symbol
TIMEFRAME = "15min"                    # Candle timeframe for Twelve Data
RISK_REWARD_RATIO = 2.0               # Fixed 1:2 risk-to-reward ratio

# ── Trading Session (WAT Timezone) ─────────────────────────────────
# WAT is UTC+1 (no DST)
SESSION_START_TIME = time(14, 30)     # 2:30 PM WAT
SESSION_END_TIME = time(20, 45)       # 8:45 PM WAT
OPENING_RANGE_START = time(14, 15)    # 2:15 PM WAT (candle open)
OPENING_RANGE_END = time(14, 30)      # 2:30 PM WAT (candle close)

# ── External Links ─────────────────────────────────────────────────
TELEGRAM_CHANNEL_LINK = "https://t.me/dollarproforex"
EXNESS_PARTNER_LINK = "https://one.exnessonelink.com/a/c_9x6wufu5w3"

# ── API Keys (from environment / GitHub Secrets) ────────────────────
TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ── File Paths ──────────────────────────────────────────────────────
USERS_FILE = "users.json"
SIGNAL_FILE = "signal.json"
LOG_DIR = "logs"

# ── Timezone ───────────────────────────────────────────────────────
WAT_TIMEZONE = "Africa/Lagos"  # WAT timezone identifier

# ── API Settings ───────────────────────────────────────────────────
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY = 2  # seconds
MAX_CANDLES_FETCH = 100

# ── Signal Engine Settings ─────────────────────────────────────────
SIGNAL_CHECK_INTERVAL = 60  # seconds between checks (GitHub Actions runs every minute)
