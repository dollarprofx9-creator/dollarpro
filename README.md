# XAUUSD Signal System

A production-ready automated trading signal system for **XAU/USD (Gold/US Dollar)** using the **Opening Range Breakout** strategy on the **M15 timeframe**.

![Dashboard](https://img.shields.io/badge/Dashboard-Live-brightgreen)
![Strategy](https://img.shields.io/badge/Strategy-Opening%20Range%20Breakout-blue)
![Timeframe](https://img.shields.io/badge/Timeframe-M15-orange)

---

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [How the Strategy Works](#how-the-strategy-works)
- [Take Profit & Stop Loss Behavior](#take-profit--stop-loss-behavior)
- [Monetization](#monetization)
- [Landing Page](#landing-page)
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
- **Tracks TP/SL hits** and prevents invalid re-entries
- Sends **Telegram alerts** for new signals, TP hits, and SL hits
- Prevents **duplicate signals**
- Auto-resets for each new trading day
- Displays everything on a beautiful **dark-themed HTML dashboard**
- Includes a **professional landing page** with Telegram CTAs

### Trading Session

- **Start:** 2:30 PM WAT
- **End:** 8:45 PM WAT
- **Timezone:** WAT (West Africa Time, UTC+1)

---

## Project Structure

```
xauusd-signal-system/
├── .github/
│   └── workflows/
│       └── signal.yml          # GitHub Actions workflow (runs every minute)
├── landing.html                # Professional homepage with Telegram CTAs
├── index.html                  # Dashboard HTML with auth & paywall
├── style.css                   # Dashboard styles (dark theme + monetization UI)
├── script.js                   # Dashboard JS (auth, payments, auto-refresh)
├── signal.json                 # Signal data storage (updated by Python)
├── generate_signal.py          # Main Python signal generator
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

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

### 4. Duplicate Prevention

- No duplicate BUY signals are sent
- No duplicate SELL signals are sent
- A new signal is only generated when a valid **opposite** breakout occurs

### 5. Daily Reset

All state is automatically reset at the start of each new trading day:
- Opening Range is cleared
- Active signals are reset
- History is preserved

---

## Take Profit & Stop Loss Behavior

### When Take Profit is Hit:

1. The trade is marked as **TP Hit** in the system state
2. A Telegram notification is sent with the exit details
3. **No new signal is generated in the same direction** for the remainder of that move
4. The system continues monitoring until 8:45 PM WAT
5. Only a confirmed opposite breakout (candle close beyond the opposite OR boundary) can generate a new signal
6. If no opposite breakout occurs before 8:45 PM WAT, the session ends and resets for the next day

**Example:**
```
BUY Signal at 2650.00
  ↓
Price reaches TP at 2662.00
  ↓
TP HIT notification sent
  ↓
System blocks new BUY signals
  ↓
Waits for SELL breakout (close below OR Low)
  ↓
If SELL breakout occurs → Generate SELL
  ↓
If no SELL breakout by 8:45 PM → Session ends
```

### When Stop Loss is Hit:

1. The trade is marked as **SL Hit** in the system state
2. A Telegram notification is sent with the exit details
3. **Do NOT instantly reverse** the position
4. Continue monitoring the market
5. Only generate the opposite signal after a **confirmed candle close** beyond the opposite side of the Opening Range

**Example:**
```
BUY Signal → Stop Loss Hit at 2647.00
  ↓
SL HIT notification sent
  ↓
Do NOT generate SELL instantly
  ↓
Continue monitoring
  ↓
Later candle closes below OR Low
  ↓
NOW generate SELL signal
```

### Session State Machine

The system tracks the current session state:

| State | Description |
|-------|-------------|
| `waiting` | No active trade, monitoring for first breakout |
| `active` | Trade is open, monitoring for TP/SL hit |
| `tp_hit` | Take Profit was hit, blocking same-direction re-entry |
| `sl_hit` | Stop Loss was hit, waiting for opposite breakout |
| `session_ended` | Trading session has ended |

---

## Monetization

The dashboard includes a **built-in subscription system** with three tiers:

### Free Tier (Starter)
- Dashboard access
- Current price display
- Session countdown
- **No live signals** (blurred)
- **No signal history** (locked)
- **No alerts**

### Pro Tier — $29/month
- Everything in Free
- **Real-time BUY/SELL signals** with Entry, SL, TP
- **Full signal history** table
- **Telegram alerts**
- **Email alerts**
- Opening Range visualization
- Performance stats

### Elite Tier — $79/month
- Everything in Pro
- Priority 24/7 support
- Strategy customization
- API access
- White-label option
- Multi-timeframe analysis
- Personal onboarding call

### Production Payment Integration

To accept real payments, integrate:
- **Stripe** (Global)
- **PayPal** (Wide acceptance)
- **Flutterwave / Paystack** (Africa-focused)

You'll need a backend to handle webhooks, store user tiers, and manage subscriptions securely.

---

## Landing Page

The project includes a professional landing page (`landing.html`) designed to convert visitors into Telegram channel members and dashboard users.

### Features:
- **Modern hero section** with animated signal card preview
- **"Join Our Free Telegram Channel"** CTA prominently displayed
- **How It Works** section explaining the daily trading session
- **Why Choose Us** highlighting key benefits
- **FAQ section** with accordion interaction
- **Professional footer** with navigation
- Fully responsive (desktop, tablet, mobile)
- Same dark theme as the dashboard

### Setting Up the Telegram Link:

Replace `YOUR_CHANNEL_LINK` in `landing.html` with your actual Telegram invite link:

```html
<!-- Find and replace all instances of: -->
<a href="https://t.me/YOUR_CHANNEL_LINK" target="_blank">

<!-- With your actual link, e.g.: -->
<a href="https://t.me/xauusd_signals_free" target="_blank">
```

There are **4 places** to update:
1. Navigation bar "Join Telegram" button
2. Hero section primary CTA button
3. Telegram CTA section button
4. Footer Telegram link

---

## Installation

### Prerequisites

- A **GitHub account**
- A **Twelve Data API** account (free tier available)
- A **Telegram Bot** (free via @BotFather)
- A **Telegram Channel** for broadcasting signals

### Step 1: Fork or Create Repository

1. Create a new repository on GitHub
2. Upload all files from this project to the repository

### Step 2: Configure GitHub Secrets

See [GitHub Secrets](#github-secrets) section below.

### Step 3: Set Up GitHub Pages

1. Go to **Settings** → **Pages**
2. Select **Deploy from a branch**
3. Choose **main** branch and **/(root)** folder
4. Click **Save**

### Step 4: Update Telegram Links

Replace all `YOUR_CHANNEL_LINK` placeholders in `landing.html` with your actual Telegram channel invite link.

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
| `TELEGRAM_CHAT_ID` | Chat ID to send alerts to | Use [@userinfobot](https://t.me/userinfobot) or your channel |

### Getting Your Telegram Chat ID

**For a Channel:**
1. Add your bot as an administrator to your channel
2. Send a test message in the channel
3. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. Look for `"chat":{"id":-1001234567890` — that's your Chat ID

**For a Private Chat:**
1. Message [@userinfobot](https://t.me/userinfobot)
2. It will reply with your User ID

---

## Deployment

### GitHub Actions (Automated)

The system runs automatically via GitHub Actions:

1. Go to **Actions** tab in your repository
2. The workflow `XAUUSD Signal Generator` will run every minute
3. You can also trigger it manually with **Run workflow**

### GitHub Pages (Dashboard + Landing Page)

Both pages are hosted on GitHub Pages:

- **Landing Page:** `https://YOUR_USERNAME.github.io/xauusd-signal-system/landing.html`
- **Dashboard:** `https://YOUR_USERNAME.github.io/xauusd-signal-system/index.html`

> **Note:** Set your repository's GitHub Pages source to the **main** branch.

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

> **Note:** GitHub Actions scheduling has ~1 minute granularity.

---

## How to Customize

### Change Trading Session Time

Edit `generate_signal.py`:

```python
SESSION_START_HOUR = 14
SESSION_START_MINUTE = 30
SESSION_END_HOUR = 20
SESSION_END_MINUTE = 45
```

### Change Risk:Reward Ratio

```python
RISK_REWARD_RATIO = 2.0  # e.g., 1.5, 3.0
```

### Change Pricing Tiers

Edit `script.js`:

```javascript
PRICING: {
    pro: { price: 29, period: 'month' },
    elite: { price: 79, period: 'month' }
}
```

### Update Telegram Channel Link

Replace all instances in `landing.html`:

```html
<a href="https://t.me/YOUR_CHANNEL_LINK" target="_blank">
```

---

## Troubleshooting

### No Signals Being Generated

1. **Check GitHub Actions logs** for error messages
2. **Verify API key** is correct in GitHub Secrets
3. **Check trading session** time (2:30 PM - 8:45 PM WAT)
4. **Verify OR formed** — check `signal.json` for `opening_range.formed`

### Telegram Messages Not Received

1. **Verify bot token** format: `123456:ABC-DEF...`
2. **Verify chat ID** — for channels, it starts with `-100`
3. **Test your bot** via: `https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>&text=Test`
4. **Ensure bot is admin** in your channel

### Dashboard Not Updating

1. **Check GitHub Pages** is enabled in Settings
2. **Check signal.json** is being committed by Actions
3. **Hard refresh** the page: `Ctrl+Shift+R`

### API Rate Limits

Twelve Data free tier: **8 calls/minute, 800/day**

The script makes 2 API calls per run. Consider upgrading if you hit limits.

### Weekend Behavior

On Saturday/Sunday:
- Script skips processing
- Dashboard shows "Weekend" status
- No API calls made

---

## License

This project is provided as-is for educational and trading research purposes. Use at your own risk. Past performance does not guarantee future results.

---

**Happy Trading!**
