# DollarProFx - XAUUSD ORBS Signal Platform

A complete, production-ready web application that generates automated XAUUSD trading signals using the Opening Range Breakout Strategy (ORBS).

## Overview

DollarProFx provides free, high-quality XAUUSD breakout signals with clear Entry, Stop Loss, and Take Profit levels delivered automatically during the trading session (2:30 PM - 8:45 PM WAT).

### Key Features

- **Automated ORBS Strategy**: Identifies the Opening Range from the 2:15-2:30 PM WAT M15 candle and monitors for confirmed breakouts
- **Real-Time Signal Delivery**: Instant Telegram notifications with precise trade levels
- **Professional Risk Management**: 1:2 Risk-Reward ratio on every signal
- **Duplicate Prevention**: No duplicate BUY or SELL signals in the same direction
- **TP/SL Monitoring**: Automatic detection and notification when Take Profit or Stop Loss is hit
- **Account Verification**: Secure EXNESS partner linking system
- **Responsive Design**: Premium dark theme with gold accents, optimized for desktop, tablet, and mobile

## Technologies

- **Frontend**: HTML5, CSS3, JavaScript (Vanilla)
- **Backend**: Python 3, Flask
- **APIs**: Twelve Data API (M15 candle data), Telegram Bot API (signal delivery)
- **Automation**: GitHub Actions (runs every minute during trading hours)
- **Deployment**: Flask + Gunicorn

## Project Structure

```
dollarprofx/
├── index.html              # Homepage with hero, features, FAQ
├── style.css               # Main stylesheet (dark theme, glassmorphism, gold accents)
├── script.js               # Frontend JavaScript (signals, countdown, FAQ, navigation)
├── verification.html       # Account verification page
├── verification.css      # Verification page styles
├── verification.js       # Verification flow logic
├── app.py                  # Flask backend (API endpoints, file serving)
├── generate_signal.py    # Core signal generation engine
├── config.py             # Centralized configuration
├── users.json            # Approved EXNESS email addresses (admin-managed)
├── signal.json           # Latest signal data and history
├── requirements.txt      # Python dependencies
├── README.md             # This file
└── .github/
    └── workflows/
        └── signal.yml    # GitHub Actions workflow (runs every minute)
```

## Installation

### Prerequisites

- Python 3.11+
- pip

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/dollarprofx.git
cd dollarprofx
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set environment variables:
```bash
export TWELVEDATA_API_KEY="your_twelve_data_api_key"
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token"
export TELEGRAM_CHAT_ID="your_telegram_chat_id"
export FLASK_SECRET_KEY="your_secret_key"
```

5. Run the Flask application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`.

## Required Python Packages

See `requirements.txt`:
- Flask==3.0.0
- requests==2.31.0
- python-telegram-bot==20.7
- pytz==2024.1
- gunicorn==21.2.0

## GitHub Secrets Configuration

The following secrets must be configured in your GitHub repository settings:

| Secret | Description |
|--------|-------------|
| `TWELVEDATA_API_KEY` | Your Twelve Data API key for fetching XAU/USD M15 candles |
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | The Telegram chat ID where signals will be sent |

### Setting Up GitHub Secrets

1. Go to your repository on GitHub
2. Click **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Add each secret name and value

## GitHub Actions Setup

The workflow file `.github/workflows/signal.yml` is already configured. It will:

1. Run every minute automatically
2. Install Python dependencies
3. Execute the signal generation script
4. Update `signal.json` only if changes occurred
5. Commit and push updates when necessary

No additional configuration is needed beyond the GitHub Secrets.

## Deployment

### Flask Deployment

For production deployment, use Gunicorn:

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Platform-Specific Deployment

**Heroku:**
```bash
heroku create your-app-name
git push heroku main
```

**PythonAnywhere:**
Upload files and configure WSGI to point to `app.py`.

**VPS/Dedicated Server:**
Use systemd or supervisor to run Gunicorn as a service behind Nginx.

## Trading Strategy Explanation

### Opening Range Breakout Strategy (ORBS)

1. **Opening Range Identification**: Every trading day at 2:15 PM WAT, the system identifies the M15 candle that closes at 2:30 PM WAT. The High and Low of this candle become the Opening Range.

2. **Breakout Monitoring**: After 2:30 PM WAT, the system monitors every completed M15 candle:
   - **BUY Signal**: Generated when an M15 candle CLOSES above the Opening Range High
   - **SELL Signal**: Generated when an M15 candle CLOSES below the Opening Range Low

3. **Signal Parameters**:
   - Entry: The closing price of the breakout candle
   - Stop Loss: Opening Range Low (for BUY) / Opening Range High (for SELLS)
   - Take Profit: Calculated using 1:2 Risk-Reward ratio

4. **Trade Management**:
   - If SL is hit: Mark trade as closed, send update, wait for opposite breakout
   - If TP is hit: Mark trade as closed, send update, wait for opposite breakout
   - No immediate reversal - only confirmed opposite breakouts generate new signals

5. **Session Rules**:
   - Trading: 2:30 PM - 8:45 PM WAT
   - No signals on weekends
   - All states reset at the start of each trading day

## How to Update the Telegram Link

1. Open `config.py`
2. Find the line: `TELEGRAM_CHANNEL_LINK = "https://t.me/your_channel_name"`
3. Replace with your actual Telegram channel link
4. Also update all instances in `index.html` and `verification.html`

## How to Update the EXNESS Partner Link

1. Open `config.py`
2. Find the line: `EXNESS_PARTNER_LINK = "https://your-partner-link.com"`
3. Replace with your actual EXNESS partner link
4. The partner link is also displayed in `verification.html` for users to copy

## How to Add or Remove Approved Emails

1. Open `users.json`
2. Add or remove entries in the `users` array:
```json
{
  "users": [
    {
      "email": "user@example.com"
    }
  ]
}
```
3. Commit and push the changes

**Important**: Only administrators should modify `users.json`. Users cannot register themselves or access this file through the frontend.

## Troubleshooting

### Signal Engine Not Running
- Check GitHub Actions tab for workflow run status
- Verify GitHub Secrets are correctly configured
- Check logs in the `logs/` directory

### Telegram Messages Not Sending
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Ensure the bot has permission to send messages to the chat
- Check that `TELEGRAM_CHAT_ID` is correct (use @userinfobot to find your ID)

### Twelve Data API Errors
- Verify `TWELVEDATA_API_KEY` is valid and active
- Check API rate limits on your Twelve Data plan
- The engine has built-in retry logic for temporary failures

### Website Not Loading
- Ensure Flask is running and accessible
- Check that all static files (CSS, JS) are in the correct directory
- Verify port 5000 (or your configured port) is not blocked

### Verification Not Working
- Ensure the email exists in `users.json`
- Check that `users.json` is readable by the Flask application
- Verify the API endpoint `/api/verify` is accessible

## Security Notes

- API keys and tokens are never hardcoded in the frontend
- `users.json` is never exposed through the frontend
- All user input is validated and sanitized
- The application uses Flask's built-in security features
- GitHub Secrets are the only source for sensitive credentials

## License

This project is proprietary. All rights reserved.

## Disclaimer

Trading involves significant risk of loss. Past performance is not indicative of future results. Always trade responsibly and never risk more than you can afford to lose. DollarProFx signals are for informational purposes only and do not constitute financial advice.

## Contact

- Email: contact@dollarprofx.com
- Telegram: https://t.me/your_channel_name
