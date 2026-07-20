"""
DollarProFx Flask Application
Serves the frontend and provides API endpoints.
"""

import os
import json
import logging
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

from config import (
    SIGNAL_FILE,
    USERS_FILE,
    TELEGRAM_CHANNEL_LINK,
    EXNESS_PARTNER_LINK,
    TRADING_SESSION_START,
    TRADING_SESSION_END,
    TIMEZONE,
    LOGS_DIR
)

# =============================================================================
# FLASK APP SETUP
# =============================================================================

app = Flask(__name__, static_folder=".", template_folder=".")
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dollarprofx-secret-key-2026")
CORS(app)

# Logging setup
os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "flask_app.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

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
    """Save JSON data to file."""
    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save {filepath}: {e}")
        return False


# =============================================================================
# SECURITY HELPERS
# =============================================================================

def is_valid_email(email):
    """Validate email address format."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def sanitize_email(email):
    """Sanitize email input."""
    return email.strip().lower()


# =============================================================================
# ROUTES - STATIC PAGES
# =============================================================================

@app.route("/")
def index():
    """Serve the homepage."""
    return send_from_directory(".", "index.html")


@app.route("/verification")
def verification():
    """Serve the verification page."""
    return send_from_directory(".", "verification.html")


@app.route("/live-signals")
def live_signals():
    """Serve the live signals dashboard page."""
    return send_from_directory(".", "index.html")


# =============================================================================
# ROUTES - STATIC ASSETS
# =============================================================================

@app.route("/style.css")
def serve_css():
    """Serve CSS file."""
    return send_from_directory(".", "style.css")


@app.route("/script.js")
def serve_js():
    """Serve JavaScript file."""
    return send_from_directory(".", "script.js")


@app.route("/verification.css")
def serve_verification_css():
    """Serve verification CSS file."""
    return send_from_directory(".", "verification.css")


@app.route("/verification.js")
def serve_verification_js():
    """Serve verification JavaScript file."""
    return send_from_directory(".", "verification.js")


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route("/api/signal", methods=["GET"])
def get_signal():
    """
    Get the latest signal data.
    Returns signal information without exposing sensitive data.
    """
    signal_data = load_json(SIGNAL_FILE)

    if not signal_data:
        return jsonify({
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
            "session_end": TRADING_SESSION_END,
            "current_price": None,
            "signal_history": []
        })

    latest = signal_data.get("latest_signal", {})
    history = signal_data.get("signal_history", [])

    # Sanitize response - never expose internal state
    response = {
        "direction": latest.get("direction", "WAITING"),
        "entry": latest.get("entry"),
        "stop_loss": latest.get("stop_loss"),
        "take_profit": latest.get("take_profit"),
        "date": latest.get("date"),
        "time": latest.get("time"),
        "status": latest.get("status", "WAITING"),
        "opening_range_high": latest.get("opening_range_high"),
        "opening_range_low": latest.get("opening_range_low"),
        "session_start": TRADING_SESSION_START,
        "session_end": TRADING_SESSION_END,
        "current_price": latest.get("current_price"),
        "signal_history": history[:10]  # Return last 10 signals
    }

    return jsonify(response)


@app.route("/api/verify", methods=["POST"])
def verify_account():
    """
    Verify an EXNESS email address against the approved users list.
    Returns verification result without exposing the full users list.
    """
    try:
        data = request.get_json()

        if not data:
            logger.warning("Verification attempt with no data")
            return jsonify({"verified": False, "message": "No data provided"}), 400

        email = data.get("email", "").strip()

        if not email:
            logger.warning("Verification attempt with empty email")
            return jsonify({"verified": False, "message": "Email is required"}), 400

        if not is_valid_email(email):
            logger.warning(f"Invalid email format attempted: {email}")
            return jsonify({"verified": False, "message": "Invalid email format"}), 400

        email = sanitize_email(email)

        # Load approved users
        users_data = load_json(USERS_FILE)
        approved_emails = [user.get("email", "").strip().lower() for user in users_data.get("users", [])]

        if email in approved_emails:
            logger.info(f"Account verified: {email}")
            return jsonify({
                "verified": True,
                "message": "Account verified successfully"
            })
        else:
            logger.warning(f"Verification failed for: {email}")
            return jsonify({
                "verified": False,
                "message": "Account not found in approved list"
            })

    except Exception as e:
        logger.error(f"Verification error: {e}")
        return jsonify({"verified": False, "message": "Server error occurred"}), 500


@app.route("/api/config", methods=["GET"])
def get_config():
    """
    Get public configuration values for the frontend.
    Only returns non-sensitive configuration.
    """
    return jsonify({
        "telegram_channel_link": TELEGRAM_CHANNEL_LINK,
        "exness_partner_link": EXNESS_PARTNER_LINK,
        "trading_session_start": TRADING_SESSION_START,
        "trading_session_end": TRADING_SESSION_END,
        "timezone": TIMEZONE,
        "symbol": "XAU/USD",
        "timeframe": "M15"
    })


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "False").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
