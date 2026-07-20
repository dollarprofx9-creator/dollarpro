# DollarProFx - XAUUSD ORBS Signal Platform

A complete, production-ready web application for automated XAUUSD (Gold/US Dollar) trading signals using the Opening Range Breakout Strategy (ORBS).

## 🎯 Overview

DollarProFx provides free, automated XAUUSD trading signals with:
- **Opening Range Breakout Strategy** on M15 timeframe
- **Confirmed candle closes only** — no wick breakouts
- **Automatic Telegram delivery** of BUY/SELL signals
- **Real-time SL/TP monitoring** with instant updates
- **Professional risk management** with 1:2 risk-reward ratio
- **Live web dashboard** with automatic refresh
- **Account verification system** for EXNESS partnership

## 📁 Project Structure

```
dollarprofx/
├── index.html              # Homepage with live dashboard
├── style.css               # Main stylesheet (dark theme, gold accents)
├── script.js               # Homepage JavaScript (dashboard, animations)
├── verification.html       # EXNESS account verification page
├── verification.js         # Verification flow logic
├── verification.css        # Verification page styles
├── generate_signal.py      # Core signal generation engine
├── app.py                  # Flask backend application
├── config.py               # Centralized configuration
├── users.json              # Approved EXNESS email addresses
├── signal.json             # Signal state storage
├── requirements.txt        # Python dependencies
├── README.md               # This file
└── .github/
    └── workflows/
        └── signal.yml      # GitHub Actions workflow
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- GitHub account
- Telegram Bot
- Twelve Data API account

### 1. Clone & Install

```bash
git clone <your-repo-url>
cd dollarprofx
pip install -r requirements.txt
```

### 2. Configure GitHub Secrets

Go to **Settings → Secrets and variables → Actions** and add:

| Secret | Description |
|--------|-------------|
| `TWELVEDATA_API_KEY` | Your Twelve Data API key |
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram channel/chat ID |

### 3. Update Links (Optional)

Edit `config.py` to customize:
- `TELEGRAM_CHANNEL_LINK` — Your Telegram channel URL
- `EXNESS_PARTNER_LINK` — Your EXNESS partner link
- `SESSION_START_TIME` / `SESSION_END_TIME` — Trading hours
- `RISK_REWARD_RATIO` — Default is 2.0 (1:2)

### 4. Add Approved Emails

Edit `users.json` to add verified EXNESS email addresses:

```json
{
  "users": [
    {"email": "dollarprofx@gmail.com"},
    {"email": "user@example.com"}
  ]
}
```

### 5. Run Locally

```bash
python app.py
```

Visit `http://localhost:5000`

### 6. Deploy

#### Option A: Flask Deployment (Recommended)
Deploy `app.py` to any Python hosting platform:
- Heroku
- PythonAnywhere
- DigitalOcean App Platform
- Railway
- Render

Set the environment variables for:
- `TWELVEDATA_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `FLASK_SECRET_KEY` (generate a random string)

#### Option B: GitHub Actions (Signal Engine)
The GitHub Actions workflow (`signal.yml`) runs automatically:
- Every minute during trading hours (2:00 PM - 9:00 PM WAT, Mon-Fri)
- Updates `signal.json` when signals change
- Commits changes back to the repository

**Enable the workflow:**
1. Go to **Actions** tab in your GitHub repo
2. Click "I understand my workflows, go ahead and enable them"
3. The workflow will run on schedule

## 📊 Trading Strategy

### Opening Range Breakout Strategy (ORBS)

**Market:** XAU/USD (Gold)
**Timeframe:** M15 (15-minute candles)
**Session:** 2:30 PM — 8:45 PM WAT (Mon-Fri)

### How It Works

1. **Opening Range Detection (2:15-2:30 PM WAT)**
   - The M15 candle that opens at 2:15 PM and closes at 2:30 PM WAT is identified
   - Its High and Low become the Opening Range levels for the session
   - These levels remain FIXED until the next trading day

2. **Breakout Monitoring (After 2:30 PM WAT)**
   - Every completed M15 candle is analyzed
   - **BUY Signal:** Generated when an M15 candle CLOSES above Opening Range High
   - **SELL Signal:** Generated when an M15 candle CLOSES below Opening Range Low
   - **Wick breakouts are IGNORED** — only confirmed closes trigger signals

3. **Risk Management**
   - **BUY SL:** Opening Range Low
   - **SELL SL:** Opening Range High
   - **TP:** Calculated using 1:2 risk-reward ratio
   - Example: If entry is 3368.45 and SL is 3361.20 (risk = 7.25), TP = 3368.45 + (7.25 × 2) = 3382.95

4. **Trade Management**
   - If SL is hit: Mark as "SL Hit", send Telegram update, wait for opposite breakout
   - If TP is hit: Mark as "TP Hit", send Telegram update, wait for opposite breakout
   - **No immediate reversal** — only confirmed opposite breakouts generate new signals
   - No new trades after 8:45 PM WAT

5. **Duplicate Prevention**
   - Never send duplicate BUY signals
   - Never send duplicate SELL signals
   - New signal only after confirmed opposite breakout

## 🔧 Configuration

All configurable values are in `config.py`:

```python
# Trading
SYMBOL = "XAU/USD"
TIMEFRAME = "15min"
RISK_REWARD_RATIO = 2.0

# Session Times (WAT = UTC+1)
SESSION_START_TIME = time(14, 30)      # 2:30 PM
SESSION_END_TIME = time(20, 45)        # 8:45 PM
OPENING_RANGE_START = time(14, 15)     # 2:15 PM
OPENING_RANGE_END = time(14, 30)       # 2:30 PM

# Links
TELEGRAM_CHANNEL_LINK = "https://t.me/dollarproforex"
EXNESS_PARTNER_LINK = "https://one.exnessonelink.com/a/c_9x6wufu5w3"

# API Keys (from environment)
TWELVEDATA_API_KEY = os.environ.get("TWELVEDATA_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
```

## 📱 Telegram Integration

### Setting Up Your Bot

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token
4. Add the bot to your channel as an admin
5. Get your channel ID:
   - Send a message in your channel
   - Visit: `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Look for `"chat":{"id":-100xxxxxxxxxx}`

### Signal Format

**BUY Signal:**
```
📊 XAUUSD SIGNAL

🟢 BUY

Entry: 3368.45
Stop Loss: 3361.20
Take Profit: 3382.95

Timeframe: M15
Date: 20 Jul 2026
Signal Time: 3:15 PM WAT
Session: 2:30 PM – 8:45 PM WAT
```

**SELL Signal:**
```
📊 XAUUSD SIGNAL

🔴 SELL

Entry: 3368.45
Stop Loss: 3375.70
Take Profit: 3353.95

Timeframe: M15
Date: 20 Jul 2026
Signal Time: 3:15 PM WAT
Session: 2:30 PM – 8:45 PM WAT
```

## 🔐 Security

- **API keys** are read from environment variables/GitHub Secrets only
- **users.json** is blocked from direct access (`/users.json` returns 403)
- **signal.json** is blocked from direct access (`/signal.json` returns 403)
- **Security headers** are added to all responses (CSP, X-Frame-Options, etc.)
- **Input validation** on all user inputs (email verification)
- **No payment system** anywhere on the website

## 📝 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Homepage |
| `/verification` | GET | Verification page |
| `/api/signal` | GET | Latest signal data |
| `/api/verify` | POST | Verify EXNESS email |
| `/api/config` | GET | Public configuration |
| `/api/health` | GET | Health check |

## 🛠️ Troubleshooting

### GitHub Actions Not Running
- Check if Actions are enabled in repository settings
- Verify secrets are configured correctly
- Check the Actions tab for error logs

### No Signals Generated
- Verify `TWELVEDATA_API_KEY` is valid
- Check if it's a trading day (Mon-Fri)
- Check if current time is within session hours
- Review logs in the `logs/` directory

### Telegram Messages Not Sending
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Ensure bot is admin in the channel
- Check `TELEGRAM_CHAT_ID` format (should be negative for channels)
- Check Telegram API status

### Verification Not Working
- Ensure email is in `users.json`
- Check email format (case-insensitive matching)
- Verify Flask backend is running
- Check browser console for API errors

### CORS Issues
- The Flask app serves frontend files directly, so CORS shouldn't be an issue
- If deploying separately, configure CORS headers in `app.py`

## 📄 License

This project is proprietary. All rights reserved.

## 🤝 Support

- **Telegram:** [@dollarproforex](https://t.me/dollarproforex)
- **Email:** dollarprofx@gmail.com

---

**DollarProFx** — Trade smarter, not harder.
