import logging
import os
import time

import newrelic.agent
import requests
from flask import Flask, jsonify, render_template, request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class BackendProxyError(Exception):
    """Raised when the backend returns a 5xx response."""


BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:5001')
NR_API_KEY = os.getenv('NEW_RELIC_API_KEY', '')
NR_APP_NAME = os.getenv('NEW_RELIC_APP_NAME', 'busy-beavers_frontend')

NR_GRAPHQL_URL = "https://api.newrelic.com/graphql"


# ---------------------------------------------------------------------------
# NerdGraph helpers
# ---------------------------------------------------------------------------

def _create_change_marker(app_name: str) -> dict:
    """Execute the changeTrackingCreateEvent mutation with an embedded entity search."""
    mutation = """
    mutation {
      changeTrackingCreateEvent(
        changeTrackingEvent: {
          categoryAndTypeData: {
            categoryFields: { deployment: { version: "1.0.0" } }
            kind: { category: "deployment", type: "basic" }
          }
          user: "busy-beavers-demo"
          shortDescription: "Manual Change Marker"
          description: "Manual Change for Busy Beavers Demo App"
          groupId: "busy-beavers"
          customAttributes: { environment: "beaver-demo" }
          entitySearch: { query: "name = '%s' AND domain = 'APM'" }
        }
      ) {
        changeTrackingEvent {
          changeTrackingId
          entity { name guid }
          customAttributes
        }
        messages
      }
    }
    """ % app_name.replace("'", "\\'")

    headers = {"Api-Key": NR_API_KEY, "Content-Type": "application/json"}
    resp = requests.post(NR_GRAPHQL_URL, json={"query": mutation}, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/health')
def health():
    newrelic.agent.ignore_transaction()
    return jsonify({"status": "healthy", "service": "frontend"})


@app.route('/')
def index():
    logger.info("Homepage loaded: remote_addr=%s", request.remote_addr)
    return render_template('index.html')


@app.route('/api/transaction', methods=['POST'])
def transaction():
    """Proxy a normal transaction to the backend."""
    logger.info("Normal transaction requested: remote_addr=%s", request.remote_addr)
    start = time.time()
    try:
        resp = requests.post(f"{BACKEND_URL}/api/process", json={}, timeout=10)
        elapsed = round((time.time() - start) * 1000)
        data = resp.json()
        status_code = resp.status_code
        if status_code == 200:
            logger.info(
                "Transaction completed: task_id=%s elapsed_ms=%d backend_ms=%d",
                data.get("task_id"), elapsed, data.get("elapsed_ms", 0)
            )
        else:
            logger.warning(
                "Transaction returned error from backend: task_id=%s status=%d",
                data.get("task_id"), status_code
            )
        return jsonify(data), status_code
    except Exception as exc:
        elapsed = round((time.time() - start) * 1000)
        logger.exception("Transaction proxy failed: elapsed_ms=%d error=%s", elapsed, exc)
        return jsonify({"status": "error", "error": "Backend unreachable"}), 503


@app.route('/api/error', methods=['POST'])
def trigger_error():
    """Proxy an intentional error to the backend."""
    logger.info("Error trigger requested: remote_addr=%s", request.remote_addr)
    start = time.time()
    try:
        resp = requests.post(f"{BACKEND_URL}/api/fail", json={}, timeout=10)
        elapsed = round((time.time() - start) * 1000)
        data = resp.json()
        if resp.status_code >= 500:
            raise BackendProxyError("Backend processing error: dam construction or log supply failure")
        return jsonify(data), resp.status_code
    except BackendProxyError:
        elapsed = round((time.time() - start) * 1000)
        newrelic.agent.notice_error()
        logger.exception(
            "Backend error propagated to frontend: elapsed_ms=%d", elapsed
        )
        return jsonify({"status": "error", "error": "Backend processing error"}), 500
    except Exception as exc:
        elapsed = round((time.time() - start) * 1000)
        logger.exception("Error proxy failed: elapsed_ms=%d error=%s", elapsed, exc)
        return jsonify({"status": "error", "error": "Backend unreachable"}), 503


@app.route('/api/change-marker', methods=['POST'])
def change_marker():
    """Create a New Relic change marker via NerdGraph."""
    logger.info("Change marker requested: remote_addr=%s app_name=%s", request.remote_addr, NR_APP_NAME)

    if not NR_API_KEY:
        logger.error("Change marker skipped: NEW_RELIC_API_KEY not configured")
        return jsonify({"status": "error", "error": "New Relic API key not configured"}), 400

    try:
        result = _create_change_marker(NR_APP_NAME)
        event = (
            result.get("data", {})
            .get("changeTrackingCreateEvent", {})
            .get("changeTrackingEvent", {})
        )
        messages = (
            result.get("data", {})
            .get("changeTrackingCreateEvent", {})
            .get("messages", [])
        )
        tracking_id = event.get("changeTrackingId")
        entity = event.get("entity", {})
        logger.info(
            "Change marker created: tracking_id=%s entity=%s messages=%s",
            tracking_id, entity.get("name"), messages
        )
        return jsonify({
            "status": "success",
            "tracking_id": tracking_id,
            "entity": entity,
            "messages": messages,
        })

    except Exception as exc:
        logger.exception("Failed to create change marker: error=%s", exc)
        return jsonify({"status": "error", "error": str(exc)}), 500


@app.route('/api/null', methods=['POST'])
def null_action():
    """No-op endpoint — rage click target. Returns 200 with no meaningful action."""
    logger.info("Null action called: remote_addr=%s", request.remote_addr)
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
