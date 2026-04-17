import logging
import os
import random
import time
import uuid

import newrelic.agent
from flask import Flask, jsonify, request

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Error rate for random failures on /api/process (1%)
ERROR_RATE = float(os.getenv('ERROR_RATE', '0.01'))


# ---------------------------------------------------------------------------
# Custom exception hierarchy — gives NR Errors Inbox realistic stack traces
# ---------------------------------------------------------------------------

class BeaverError(Exception):
    """Base exception for all Busy Beavers backend errors."""


class DamConstructionError(BeaverError):
    """Raised when a dam segment fails its structural integrity check."""


class LogSupplyError(BeaverError):
    """Raised when the log supply queue is exhausted or corrupted."""


# ---------------------------------------------------------------------------
# Internal processing helpers (creates multi-frame stack traces)
# ---------------------------------------------------------------------------

def _check_structural_integrity(segment_id: str, load_factor: float) -> None:
    """Validate that a dam segment can support the given load factor."""
    if load_factor > 0.95:
        raise DamConstructionError(
            "Dam structural integrity check failed: load factor exceeds 0.95 threshold"
        )


def _validate_log_supply(task_id: str, log_count: int) -> None:
    """Ensure sufficient logs are available for the given task."""
    if log_count < 1:
        raise LogSupplyError(
            "Log supply queue exhausted: no available logs for task"
        )
    logger.debug("Log supply validated: task_id=%s logs=%d", task_id, log_count)


def process_beaver_task(task_id: str) -> dict:
    """
    Core processing pipeline for a beaver task.
    Validates log supply, checks structural integrity, then finalises the task.
    """
    logger.info("Processing beaver task: task_id=%s", task_id)

    # Simulate log supply check
    log_count = random.randint(0, 20)
    _validate_log_supply(task_id, log_count)

    # Simulate structural check with a randomly high load factor when error is forced
    load_factor = random.uniform(0.1, 0.85)
    _check_structural_integrity(task_id, load_factor)

    # Simulate work
    duration_ms = random.randint(20, 120)
    time.sleep(duration_ms / 1000)

    return {
        "task_id": task_id,
        "logs_used": log_count,
        "load_factor": round(load_factor, 3),
        "duration_ms": duration_ms,
    }


def process_beaver_task_force_error(task_id: str) -> None:
    """Force a realistic error through the full call stack."""
    logger.info("Forcing error for task: task_id=%s", task_id)

    log_count = 0  # will trigger LogSupplyError path 50% of the time
    if random.random() < 0.5:
        _validate_log_supply(task_id, log_count)
    else:
        _check_structural_integrity(task_id, load_factor=0.99)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route('/health')
def health():
    newrelic.agent.ignore_transaction()
    return jsonify({"status": "healthy", "service": "backend"})


@app.route('/api/status')
def status():
    logger.info("Status check requested")
    return jsonify({
        "service": "busy-beavers-backend",
        "status": "operational",
        "error_rate_setting": ERROR_RATE,
    })


@app.route('/api/process', methods=['POST'])
def process():
    """
    Normal transaction endpoint.
    Has a configurable random chance (default 1%) of raising a realistic error.
    """
    task_id = str(uuid.uuid4())[:8]
    logger.info("Received process request: task_id=%s remote_addr=%s", task_id, request.remote_addr)

    start = time.time()
    try:
        # Randomly inject an error at the configured rate
        if random.random() < ERROR_RATE:
            logger.warning("Random error injection triggered: task_id=%s", task_id)
            process_beaver_task_force_error(task_id)

        result = process_beaver_task(task_id)
        elapsed = round((time.time() - start) * 1000)
        logger.info(
            "Task completed successfully: task_id=%s elapsed_ms=%d logs_used=%d",
            task_id, elapsed, result["logs_used"]
        )
        return jsonify({"status": "success", "task_id": task_id, "elapsed_ms": elapsed, **result})

    except BeaverError as exc:
        elapsed = round((time.time() - start) * 1000)
        newrelic.agent.notice_error()
        logger.exception(
            "Task failed with BeaverError: task_id=%s elapsed_ms=%d error=%s",
            task_id, elapsed, str(exc)
        )
        return jsonify({"status": "error", "task_id": task_id, "error": str(exc)}), 500

    except Exception as exc:
        elapsed = round((time.time() - start) * 1000)
        logger.exception(
            "Unexpected error processing task: task_id=%s elapsed_ms=%d", task_id, elapsed
        )
        return jsonify({"status": "error", "task_id": task_id, "error": "Internal server error"}), 500


@app.route('/api/fail', methods=['POST'])
def fail():
    """Always raises a realistic error — used by the Error button and load gen."""
    task_id = str(uuid.uuid4())[:8]
    logger.info("Error endpoint called: task_id=%s remote_addr=%s", task_id, request.remote_addr)

    try:
        process_beaver_task_force_error(task_id)
        # Should not reach here, but handle gracefully
        return jsonify({"status": "error", "task_id": task_id, "error": "Expected error did not fire"}), 500

    except BeaverError as exc:
        newrelic.agent.notice_error()
        logger.exception(
            "Intentional BeaverError raised: task_id=%s error=%s", task_id, str(exc)
        )
        return jsonify({"status": "error", "task_id": task_id, "error": str(exc)}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
