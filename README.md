# XAUUSD Signal System

A production-ready automated trading signal system for **XAU/USD (Gold/US Dollar)** using the **Opening Range Breakout** strategy on the **M15 timeframe**.

![Dashboard](https://img.shields.io/badge/Dashboard-Live-brightgreen)
![Strategy](https://img.shields.io/badge/Strategy-Opening%20Range%20Breakout-blue)
![Timeframe](https://img.shields.io/badge/Timeframe-M15-orange)

---

## Table of Contents

- [Overview](#overview)
- [How the Strategy Works](#how-the-strategy-works)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [GitHub Secrets](#github-secrets)
- [Deployment](#deployment)
- [GitHub Actions](#github-actions)
- [GitHub Pages](#github-pages)
- [How to Customize](#how-to-customize)
- [Troubleshooting](#troubleshooting)

---

## Overview

This system automatically:

- Fetches real-time XAUUSD M15 candle data from **Twelve Data API**
- Detects the **Opening Range** (first M15 candle of the session: 2:30-2:45 PM WAT)
- Monitors for **confirmed breakout signals** (candle close beyond OR high/low)
- Calculates **Stop Loss** and **Take Profit** with a **1:2 Risk:Reward ratio**
- Sends **Telegram alerts** for new signals
- Prevents **duplicate signals**
- Auto-resets for each new trading day
- Displays everything on a beautiful **dark-themed HTML dashboard**

### Trading Session

- **Start:** 2:30 PM WAT
- **End:** 8:45 PM WAT
- **Timezone:** WAT (West Africa Time, UTC+1)

---

## How the Strategy Works

### 1. Opening Range Formation

At the start of each trading session (2:30 PM WAT), the system identifies the **first M15 candle** (2:30-2:45 PM WAT) and records:

- **Opening Range High** — the highest price of that candle
- **Opening Range Low** — the lowest price of that candle

### 2. Signal Generation

The system monitors subsequent M15 candles for **confirmed breakouts**:

| Signal | Condition |
|--------|-----------|
| **BUY** | An M15 candle **CLOSES** above the Opening Range High |
| **SELL** | An M15 candle **CLOSES** below the Opening Range Low |

> **Important:** Only candle **close** confirmation is used. Wick breakouts are ignored.

### 3. Stop Loss & Take Profit

| Position | Stop Loss | Take Profit |
|----------|-----------|-------------|
| **BUY** | Opening Range Low | Entry + (Risk × 2) |
| **SELL** | Opening Range High | Entry - (Risk × 2) |

**Risk:Reward Ratio:** 1:2

### 4. Stop Loss Behavior

If a Stop Loss is hit:

1. **Do NOT** instantly reverse the position
2. Continue monitoring the market
3. Only generate the opposite signal after a **confirmed candle close** beyond the opposite side of the Opening Range

**Example:**
```
BUY Signal → Stop Loss Hit → Wait → Candle closes below OR Low → SELL Signal
```

### 5. Duplicate Prevention

- No duplicate BUY signals are sent
- No duplicate SELL signals are sent
- A new signal is only generated when a valid **opposite** breakout occurs

### 6. Daily Reset

All state is automatically reset at the start of each new trading day:
- Opening Range is cleared
- Active signals are reset
- History is preserved

---

## Project Structure

```
xauusd-signal-system/
├── .github/
│   └── workflows/
│       └── signal.yml          # GitHub Actions workflow (runs every minute)
├── index.html                  # Dashboard HTML
├── style.css                   # Dashboard styles (dark theme)
├── script.js                   # Dashboard JavaScript (auto-refresh)
├── signal.json                 # Signal data storage (updated by Python)
├── generate_signal.py          # Main Python signal generator
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## Installation

### Prerequisites

- A **GitHub account**
- A **Twelve Data API** account (free tier available)
- A **Telegram Bot** (free via @BotFather)

### Step 1: Fork or Create Repository

1. Create a new repository on GitHub
2. Upload all files from this project to the repository

### Step 2: Install Python Dependencies Locally (Optional)

If you want to run the script locally for testing:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/xauusd-signal-system.git
cd xauusd-signal-system

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Run Locally (Optional)

```bash
# Set environment variables
export TWELVEDATA_API_KEY="your_api_key_here"
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"

# Run the signal generator
python generate_signal.py
```

---

## GitHub Secrets

You must configure the following **GitHub Secrets** in your repository:

### How to Add Secrets

1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret below

### Required Secrets

| Secret Name | Description | How to Get |
|-------------|-------------|------------|
| `TWELVEDATA_API_KEY` | API key for Twelve Data | [twelvedata.com](https://twelvedata.com) — Sign up free |
| `TELEGRAM_BOT_TOKEN` | Token for your Telegram bot | Message [@BotFather](https://t.me/BotFather) on Telegram |
| `TELEGRAM_CHAT_ID` | Chat ID to send alerts to | Use [@userinfobot](https://t.me/userinfobot) or [@raw_data_bot](https://t.me/raw_data_bot) |

### Getting Your Telegram Chat ID

**Method 1 — Using @userinfobot:**
1. Open Telegram and search for `@userinfobot`
2. Start the bot
3. It will reply with your User ID (this is your Chat ID for private messages)

**Method 2 — Using your bot:**
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"chat":{"id":123456789` — the number is your Chat ID

> **Note:** For group chats, add your bot to the group first, then use Method 2.

---

## Deployment

### GitHub Actions (Automated)

The system runs automatically via GitHub Actions:

1. Go to **Actions** tab in your repository
2. The workflow `XAUUSD Signal Generator` will run every minute
3. You can also trigger it manually with **Run workflow**

### GitHub Pages (Dashboard)

To host the dashboard on GitHub Pages:

1. Go to **Settings** → **Pages**
2. Under **Source**, select **Deploy from a branch**
3. Select the **main** branch and **/(root)** folder
4. Click **Save**
5. Your dashboard will be available at: `https://YOUR_USERNAME.github.io/xauusd-signal-system/`

> **Note:** It may take a few minutes for GitHub Pages to deploy.

---

## GitHub Actions

### Workflow Details

The workflow (`.github/workflows/signal.yml`) runs every minute and:

1. Checks out the repository
2. Sets up Python 3.11
3. Installs dependencies from `requirements.txt`
4. Runs `generate_signal.py` with your API keys
5. Commits `signal.json` back to the repo **only if it changed**

### Workflow Schedule

```yaml
schedule:
  - cron: '*/1 * * * *'  # Every minute
```

> **Note:** GitHub Actions scheduling has ~1 minute granularity. The actual interval may vary slightly.

### Manual Trigger

You can manually trigger the workflow:

1. Go to **Actions** tab
2. Select **XAUUSD Signal Generator**
3. Click **Run workflow**

---

## How to Customize

### Change Trading Session Time

Edit `generate_signal.py`:

```python
# Trading session times (WAT)
SESSION_START_HOUR = 14      # Change this
SESSION_START_MINUTE = 30    # Change this
SESSION_END_HOUR = 20        # Change this
SESSION_END_MINUTE = 45      # Change this

# Opening Range times
OR_START_HOUR = 14
OR_START_MINUTE = 30
OR_END_HOUR = 14
OR_END_MINUTE = 45
```

Also update the dashboard in `script.js`:

```javascript
sessionStart: { hour: 14, minute: 30 },
sessionEnd: { hour: 20, minute: 45 }
```

And update the HTML in `index.html`:

```html
<span class="session-time">2:30 PM - 8:45 PM WAT</span>
```

### Change Risk:Reward Ratio

Edit `generate_signal.py`:

```python
RISK_REWARD_RATIO = 2.0  # Change to your desired ratio (e.g., 1.5, 3.0)
```

Update the dashboard in `index.html`:

```html
<span class="detail-value">1:2</span>
```

### Change Symbol

Edit `generate_signal.py`:

```python
SYMBOL = "XAU/USD"  # Change to any Twelve Data supported symbol
```

> **Note:** You may also need to update the dashboard labels in `index.html`.

### Change Timeframe

Edit `generate_signal.py`:

```python
TIMEFRAME = "15min"  # Options: 1min, 5min, 15min, 30min, 1h, etc.
```

Update the dashboard in `index.html`:

```html
<span class="ticker-value">M15</span>
```

### Change Timezone

Edit `generate_signal.py`:

```python
WAT_TZ = tz.gettz("Africa/Lagos")  # Change to your timezone
```

Update the GitHub Actions workflow:

```yaml
env:
  TZ: Africa/Lagos  # Change to your timezone
```

---

## Troubleshooting

### No Signals Being Generated

1. **Check GitHub Actions logs:**
   - Go to **Actions** tab → Select a workflow run → Check logs
   - Look for error messages from the Python script

2. **Verify API key:**
   - Ensure `TWELVEDATA_API_KEY` is set correctly in GitHub Secrets
   - Test your API key: `https://api.twelvedata.com/price?symbol=XAU/USD&apikey=YOUR_KEY`

3. **Check trading session:**
   - Signals are only generated between 2:30 PM and 8:45 PM WAT
   - No signals on weekends (Saturday/Sunday)

4. **Verify Opening Range formed:**
   - The OR candle (2:30-2:45 PM WAT) must be available in the data
   - Check `signal.json` to see if `opening_range.formed` is `true`

### Telegram Messages Not Received

1. **Verify bot token:**
   - Ensure `TELEGRAM_BOT_TOKEN` is correct (format: `123456:ABC-DEF...`)

2. **Verify chat ID:**
   - Ensure `TELEGRAM_CHAT_ID` is correct
   - For private chats, it should be a number (e.g., `123456789`)
   - For groups, it may start with `-` (e.g., `-1001234567890`)

3. **Test your bot:**
   - Send a test message via: `https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=Test`

### Dashboard Not Updating

1. **Check GitHub Pages is enabled:**
   - Go to **Settings** → **Pages** → Verify source is set

2. **Check signal.json is being committed:**
   - Verify the GitHub Actions workflow is committing changes
   - Check if `signal.json` was updated in recent commits

3. **Browser cache:**
   - Hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
   - The dashboard adds cache-busting query parameters automatically

4. **CORS issues:**
   - If testing locally, you may need to serve files via a local server:
   ```bash
   python -m http.server 8000
   ```

### API Rate Limits

Twelve Data free tier limits:
- **8 API calls per minute**
- **800 API calls per day**

The script makes 2 API calls per run (price + time series). Running every minute uses:
- ~120 calls per hour during session
- ~960 calls per day (8-hour session)

> **Tip:** If you hit rate limits, consider reducing the schedule frequency or upgrading your Twelve Data plan.

### Weekend Behavior

On weekends (Saturday and Sunday):
- The script detects the weekend and skips processing
- No API calls are made
- The dashboard shows "Weekend" status
- Everything resets on Monday

### Data Gaps

If Twelve Data returns incomplete data:
- The script logs a warning
- The Opening Range may not form until sufficient data is available
- The system gracefully handles missing candles

---

## License

This project is provided as-is for educational and trading research purposes. Use at your own risk. Past performance does not guarantee future results.

---

## Support

For issues or questions:
1. Check the **Troubleshooting** section above
2. Review GitHub Actions logs for error details
3. Verify all secrets are configured correctly

---

**Happy Trading!**
