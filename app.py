#!/usr/bin/env python3
"""
DollarProFx Flask Application
Serves the frontend, provides API endpoints, and handles verification.
"""

import os
import sys
import json
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, render_template, jsonify, request, send_from_directory
import config

# ── Logging Setup ───────────────────────────────────────────────────
LOG_DIR = config.LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)

log_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

file_handler = logging.FileHandler(
    os.path.join(LOG_DIR, f"flask_{datetime.now().strftime('%Y%m%d')}.log"),
    encoding="utf-8"
)
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)

logger = logging.getLogger("DollarProFx_Flask")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ── Flask App ───────────────────────────────────────────────────────
app = Flask(__name__, static_folder=".", static_url_path="")
app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", "dollarprofx-dev-key-change-in-prod")

# ── Security Headers ──────────────────────────────────────────────
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses."""
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self';"
    )
    return response


# ── Helper Functions ───────────────────────────────────────────────
def load_json_file(filepath: str, default=None) -> dict:
    """Safely load a JSON file."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading {filepath}: {e}")
    return default if default is not None else {}


def validate_email(email: str) -> bool:
    """Basic email validation."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip().lower()
    if len(email) > 254:
        return False
    if "@" not in email or "." not in email:
        return False
    if email.count("@") != 1:
        return False
    local, domain = email.rsplit("@", 1)
    if not local or not domain:
        return False
    if ".." in domain or domain.startswith(".") or domain.endswith("."):
        return False
    return True


# ── Routes ─────────────────────────────────────────────────────────
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


# ── API Endpoints ──────────────────────────────────────────────────
@app.route("/api/signal", methods=["GET"])
def get_signal():
    """Return the latest signal data for the dashboard."""
    try:
        signal_data = load_json_file(config.SIGNAL_FILE, {
            "latest_signal": None,
            "signal_history": [],
            "opening_range": {"high": None, "low": None, "date": None},
            "active_trade": None,
            "session_status": "WAITING",
            "last_updated": None,
            "current_gold_price": None
        })

        return jsonify({
            "success": True,
            "data": signal_data
        })
    except Exception as e:
        logger.error(f"Error in /api/signal: {e}")
        return jsonify({
            "success": False,
            "error": "Failed to load signal data"
        }), 500


@app.route("/api/verify", methods=["POST"])
def verify_account():
    """
    Verify EXNESS email against users.json.
    Returns success if email exists in the approved users list.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Invalid request"}), 400

        email = data.get("email", "").strip().lower()

        # Validate email format
        if not validate_email(email):
            logger.warning(f"Invalid email format attempted: {email[:50] if email else 'empty'}")
            return jsonify({
                "success": False,
                "error": "Invalid email address format"
            }), 400

        # Load users.json
        users_data = load_json_file(config.USERS_FILE, {"users": []})
        approved_emails = [u.get("email", "").strip().lower() for u in users_data.get("users", [])]

        # Check if email is approved
        if email in approved_emails:
            logger.info(f"Account verified: {email}")
            return jsonify({
                "success": True,
                "message": "Account verified successfully"
            })
        else:
            logger.warning(f"Verification failed for: {email}")
            return jsonify({
                "success": False,
                "error": "Account not found in approved list"
            })

    except Exception as e:
        logger.error(f"Error in /api/verify: {e}")
        return jsonify({
            "success": False,
            "error": "Verification service temporarily unavailable"
        }), 500


@app.route("/api/config", methods=["GET"])
def get_public_config():
    """Return public configuration values for the frontend."""
    return jsonify({
        "success": True,
        "data": {
            "telegram_link": config.TELEGRAM_CHANNEL_LINK,
            "partner_link": config.EXNESS_PARTNER_LINK,
            "session_start": "2:30 PM WAT",
            "session_end": "8:45 PM WAT",
            "symbol": config.SYMBOL,
            "timeframe": "M15"
        }
    })


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })


# ── Error Handlers ─────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({"success": False, "error": "Internal server error"}), 500


# ── Security: Block direct access to sensitive files ─────────────
@app.route("/users.json")
def block_users_json():
    """Prevent direct access to users.json."""
    return jsonify({"success": False, "error": "Access denied"}), 403


@app.route("/signal.json")
def block_signal_json():
    """Prevent direct access to signal.json."""
    return jsonify({"success": False, "error": "Access denied"}), 403


# ── Main ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
