import hmac
import json
import logging
import os
import random
import sqlite3
import sys
import time
from datetime import datetime, timezone
from contextlib import contextmanager

from flask import Flask, jsonify, render_template, request

try:
    import newrelic.agent as nr_agent
except ImportError:
    nr_agent = None  # Local Flask can run without the New Relic agent.

app = Flask(__name__)
DB_PATH = os.getenv("DATABASE_PATH", "/tmp/relistate-demo.sqlite3")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
SERVICE_TIER = os.getenv("SERVICE_TIER", "tier-1")
OWNER_TEAM = os.getenv("OWNER_TEAM", "platform")
DEMO_API_SECRET = os.getenv("DEMO_API_SECRET", "local-demo-secret")

logger = logging.getLogger("relistate")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.propagate = False


def log_event(event, **fields):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "level": "info",
        "event": event,
        "environment": ENVIRONMENT,
        **fields,
    }
    logger.info(json.dumps(record))


def connect_db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    return sqlite3.connect(DB_PATH, timeout=10)


@contextmanager
def database():
    connection = connect_db()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_flags():
    with database() as db:
        db.execute("CREATE TABLE IF NOT EXISTS flags (name TEXT PRIMARY KEY, enabled INTEGER NOT NULL)")
        db.executemany(
            "INSERT OR IGNORE INTO flags (name, enabled) VALUES (?, ?)",
            [("dark_mode_beta", 1), ("express_checkout", 0)],
        )


initialize_flags()


@app.before_request
def add_metadata():
    if nr_agent is not None:
        nr_agent.add_custom_attribute("environment", ENVIRONMENT)
        nr_agent.add_custom_attribute("service_tier", SERVICE_TIER)
        nr_agent.add_custom_attribute("owner_team", OWNER_TEAM)


@app.get("/console")
def home():
    return render_template("console.html")


@app.get("/healthz")
def health():
    return jsonify({"status": "healthy"}), 200


@app.get("/api/v1/flags/evaluate")
def evaluate_flag():
    flag_name = request.args.get("flag", "dark_mode_beta")
    time.sleep(0.01)
    with database() as db:
        row = db.execute("SELECT enabled FROM flags WHERE name = ?", (flag_name,)).fetchone()

    if row is None:
        return jsonify({"error": "Unknown feature flag"}), 404

    enabled = bool(row[0])
    # Deliberately fake values for the log-masking lesson. No real secrets here.
    log_event(
        "flag_eval", flag=flag_name, enabled=enabled,
        developer_email="demo.user@example.com",
        workspace_token="demo-token-PLACEHOLDER",
    )
    return jsonify({"flag": flag_name, "enabled": enabled}), 200


@app.post("/api/v1/flags/rules")
def update_flag():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Expected a JSON object"}), 400

    flag_name = data.get("flag")
    enabled = data.get("enabled")
    if not isinstance(flag_name, str):
        return jsonify({"error": "Flag must be a string"}), 400
    if not isinstance(enabled, bool):
        return jsonify({"error": "Enabled must be true or false"}), 400

    with database() as db:
        result = db.execute(
            "UPDATE flags SET enabled = ? WHERE name = ?",
            (int(enabled), flag_name),
        )
    if result.rowcount == 0:
        return jsonify({"error": "Unknown feature flag"}), 404

    log_event("flag_rule_updated", flag=flag_name, enabled=enabled)
    return jsonify({
        "message": "Feature flag updated", "flag": flag_name, "enabled": enabled
    }), 201


@app.post("/api/v1/auth/agent-token")
def agent_token():
    provided_secret = request.headers.get("X-Agent-Secret", "")
    if not hmac.compare_digest(provided_secret, DEMO_API_SECRET):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({
        "token": "mock.jwt.demo-only",
        "token_type": "Bearer",
        "message": "Not a real authentication token",
    }), 200


@app.route("/simulate/error", methods=["GET", "POST"])
def simulate_error():
    try:
        rate = float(request.args.get("rate", "1"))
    except ValueError:
        return jsonify({"error": "rate must be a number from 0 to 1"}), 400
    if not 0 <= rate <= 1:
        return jsonify({"error": "rate must be between 0 and 1"}), 400

    if random.random() >= rate:
        return jsonify({"status": "success", "message": "No error this time"}), 200

    code = random.choice([500, 503])
    log_event("simulated_failure", status_code=code)
    return jsonify({"status": "error", "message": "Simulated server failure"}), code


@app.route("/simulate/slow", methods=["GET", "POST"])
def simulate_slow():
    value = request.args.get("latency_ms")
    if value is None:
        delay = random.uniform(1.5, 3.0)
    else:
        try:
            milliseconds = int(value)
        except ValueError:
            return jsonify({"error": "latency_ms must be an integer"}), 400
        if not 0 <= milliseconds <= 5000:
            return jsonify({"error": "latency_ms must be from 0 to 5000"}), 400
        delay = milliseconds / 1000

    time.sleep(delay)
    log_event("slow_request", delay_seconds=round(delay, 2))
    return jsonify({
        "status": "success",
        "message": "Slow request completed",
        "delay_seconds": round(delay, 2),
    }), 200
