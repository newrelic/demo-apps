import hmac
import json
import logging
import os
import random
import sqlite3
import sys
import time
import uuid
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

# Fictional catalog kept in code: no external database or services required.
PRODUCTS = (
    {"id": "aurora", "name": "Aurora Headphones", "category": "Audio", "price_cents": 12900,
     "emoji": "🎧", "color": "lavender", "tag": "Bestseller", "description": "Your daily soundtrack, elevated."},
    {"id": "orbit", "name": "Orbit Desk Light", "category": "Desk", "price_cents": 5900,
     "emoji": "💡", "color": "peach", "tag": "New drop", "description": "A little glow for every workspace."},
    {"id": "nova", "name": "Nova Travel Mug", "category": "Lifestyle", "price_cents": 3400,
     "emoji": "☕", "color": "mint", "tag": "Fan favorite", "description": "Warm drinks. Big ideas."},
    {"id": "pulse", "name": "Pulse Smart Band", "category": "Wellness", "price_cents": 9900,
     "emoji": "⌚", "color": "sky", "tag": "Limited", "description": "Stay in sync with your day."},
    {"id": "arc", "name": "Arc Keyboard", "category": "Desk", "price_cents": 8900,
     "emoji": "⌨️", "color": "sand", "tag": "Editor's pick", "description": "Make every keystroke count."},
    {"id": "breeze", "name": "Breeze Mini Speaker", "category": "Audio", "price_cents": 6900,
     "emoji": "🔊", "color": "pink", "tag": "Just landed", "description": "A big sound in a small package."},
)
PRODUCT_BY_ID = {item["id"]: item for item in PRODUCTS}

# Defaults apply only when a flag row is first created. Existing databases keep their stored values.
DEFAULT_FLAGS = {"dark_mode_beta": False, "express_checkout": True, "free_shipping_banner": True}

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


def initialize_database():
    with database() as db:
        db.execute("CREATE TABLE IF NOT EXISTS flags (name TEXT PRIMARY KEY, enabled INTEGER NOT NULL)")
        db.execute("""CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY, item_count INTEGER NOT NULL, total_cents INTEGER NOT NULL,
            created_at TEXT NOT NULL)""")
        db.executemany(
            "INSERT OR IGNORE INTO flags (name, enabled) VALUES (?, ?)",
            [(name, int(enabled)) for name, enabled in DEFAULT_FLAGS.items()],
        )


initialize_database()


@app.before_request
def add_metadata():
    if nr_agent is not None:
        nr_agent.add_custom_attribute("environment", ENVIRONMENT)
        nr_agent.add_custom_attribute("service_tier", SERVICE_TIER)
        nr_agent.add_custom_attribute("owner_team", OWNER_TEAM)


@app.get("/")
def storefront():
    log_event("storefront_view", path="/")
    return render_template("storefront.html")


@app.get("/console")
def console():
    return render_template("console.html")


@app.get("/healthz")
def health():
    return jsonify({"status": "healthy"}), 200


@app.get("/api/v1/products")
def products():
    log_event("catalog_browse", count=len(PRODUCTS))
    return jsonify(products=PRODUCTS), 200


@app.get("/api/v1/flags/evaluate")
def evaluate_flag():
    flag_name = request.args.get("flag", "dark_mode_beta")
    time.sleep(0.01)  # Deliberately measurable ~10 ms flag-evaluation transaction.
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


@app.post("/api/v1/checkout")
def checkout():
    """Simulated checkout: records a fictional order. Never accepts card details or charges anyone."""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        return jsonify({"error": "Expected JSON with items list"}), 400
    if not payload["items"] or len(payload["items"]) > 20:
        return jsonify({"error": "Cart must contain 1 to 20 line items"}), 400

    total_cents = 0
    item_count = 0
    for line in payload["items"]:
        if not isinstance(line, dict):
            return jsonify({"error": "Each item must be an object"}), 400
        item_id = line.get("id")
        product = PRODUCT_BY_ID.get(item_id) if isinstance(item_id, str) else None
        quantity = line.get("quantity")
        if product is None or type(quantity) is not int or not 1 <= quantity <= 10:
            return jsonify({"error": "Invalid product or quantity (1–10)"}), 400
        total_cents += product["price_cents"] * quantity
        item_count += quantity
    if item_count > 30:
        return jsonify({"error": "Cart exceeds demo quantity limit"}), 400

    # Prices come from the server-side catalog, never from the client.
    order_id = "RS-" + uuid.uuid4().hex[:8].upper()
    with database() as db:
        db.execute(
            "INSERT INTO orders (id, item_count, total_cents, created_at) VALUES (?, ?, ?, ?)",
            (order_id, item_count, total_cents, datetime.now(timezone.utc).isoformat()),
        )
    log_event("checkout_complete", order_id=order_id, item_count=item_count,
              total_cents=total_cents, payment="demo-only")
    return jsonify({
        "order_id": order_id, "status": "confirmed-demo", "item_count": item_count,
        "total_cents": total_cents, "charged": False,
    }), 201


@app.get("/api/v1/demo/stats")
def demo_stats():
    with database() as db:
        order_count, total_cents = db.execute(
            "SELECT COUNT(*), COALESCE(SUM(total_cents), 0) FROM orders").fetchone()
    return jsonify(demo_orders=order_count, total_cents=total_cents), 200


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
