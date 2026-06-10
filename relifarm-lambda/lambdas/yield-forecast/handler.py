"""
ReliFarm — yield-forecast Lambda
================================

Receives a sector + manual override flag from the browser dashboard, evaluates
seasonal trends and current moisture against an analytic crop-health model,
and forwards the forecast to the valve-scheduler Lambda.

Distributed tracing
-------------------
The New Relic Lambda Layer (configured in Terraform) wraps this handler
automatically, accepts inbound `traceparent` / `tracestate` headers from API
Gateway, and re-emits them on `requests` calls thanks to the agent's auto-
instrumentation. We *also* call `newrelic.agent.insert_distributed_trace_headers`
explicitly so trace propagation is unambiguous and resilient to library swaps.
"""
import json
import logging
import math
import os
import random
from datetime import datetime, timezone

import newrelic.agent  # type: ignore
import requests  # type: ignore

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VALVE_SCHEDULER_URL = os.environ["VALVE_SCHEDULER_URL"]
HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "8"))


# --- forecast model ---------------------------------------------------------
def _seasonal_growth_index(now: datetime) -> float:
    """0.0 (dormant) → 1.0 (peak growing season). Sin wave keyed to day-of-year."""
    doy = now.timetuple().tm_yday
    raw = math.sin((doy - 80.0) / 365.0 * 2.0 * math.pi)
    return max(0.05, (raw + 1.0) / 2.0)


def _calculate_yield_health(soil_moisture_pct: float, soil_temp_c: float, now: datetime) -> float:
    """
    Composite 0–100 score. Penalizes both drought and water-logging; favors
    temperatures in the 18–26 C band; weighted by seasonal growth index.
    """
    moisture_score = 100.0 - abs(soil_moisture_pct - 42.0) * 2.5
    moisture_score = max(0.0, min(100.0, moisture_score))

    temp_optimum = 22.0
    temp_score = 100.0 - abs(soil_temp_c - temp_optimum) * 4.0
    temp_score = max(0.0, min(100.0, temp_score))

    growth = _seasonal_growth_index(now)
    composite = 0.55 * moisture_score + 0.30 * temp_score + 15.0 * growth
    composite += random.gauss(0.0, 1.5)
    return round(max(0.0, min(100.0, composite)), 2)


# --- helpers ----------------------------------------------------------------
def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, traceparent, tracestate, newrelic",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
        "body": json.dumps(body),
    }


def _outbound_trace_headers() -> list[tuple[str, str]]:
    """W3C Trace Context + NR DT headers, explicitly fetched from the active span."""
    headers: list[tuple[str, str]] = []
    newrelic.agent.insert_distributed_trace_headers(headers)
    return headers


def lambda_handler(event, context):
    logger.info("yield-forecast invoked")

    # API Gateway proxy event: body is a JSON string (or None for OPTIONS preflight).
    if event.get("httpMethod") == "OPTIONS":
        return _response(204, {})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        newrelic.agent.notice_error()
        logger.exception("malformed request body")
        return _response(400, {"error": "malformed JSON", "details": str(exc)})

    sector_id = body.get("sector_id")
    soil_moisture = body.get("soil_moisture_pct")
    soil_temp = body.get("soil_temp_c")
    triggered_by = body.get("triggered_by", "manual")
    emergency_override = body.get("emergency_override")

    if not sector_id or soil_moisture is None or soil_temp is None:
        return _response(
            400,
            {"error": "missing required fields: sector_id, soil_moisture_pct, soil_temp_c"},
        )

    now = datetime.now(timezone.utc)
    yield_health = _calculate_yield_health(float(soil_moisture), float(soil_temp), now)
    growth = _seasonal_growth_index(now)

    newrelic.agent.add_custom_attribute("relifarm.sector_id", sector_id)
    newrelic.agent.add_custom_attribute("relifarm.yield_health", yield_health)
    newrelic.agent.add_custom_attribute("relifarm.seasonal_growth_index", round(growth, 3))
    newrelic.agent.add_custom_attribute("relifarm.triggered_by", triggered_by)

    forecast_payload = {
        "sector_id": sector_id,
        "soil_moisture_pct": soil_moisture,
        "soil_temp_c": soil_temp,
        "yield_health": yield_health,
        "seasonal_growth_index": round(growth, 3),
        "triggered_by": triggered_by,
    }
    if emergency_override is not None:
        forecast_payload["emergency_override"] = emergency_override

    # ----- propagate W3C trace context to valve-scheduler -----
    outbound_headers = dict(_outbound_trace_headers())
    outbound_headers["Content-Type"] = "application/json"
    logger.info(
        "forwarding to valve-scheduler trace_headers=%s",
        {k: v for k, v in outbound_headers.items() if k.lower() in ("traceparent", "tracestate")},
    )

    try:
        resp = requests.post(
            VALVE_SCHEDULER_URL,
            json=forecast_payload,
            headers=outbound_headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        newrelic.agent.notice_error()
        logger.exception("valve-scheduler call failed")
        return _response(502, {"error": "valve-scheduler unreachable", "details": str(exc)})

    try:
        scheduler_body = resp.json()
    except ValueError:
        scheduler_body = {"raw": resp.text}

    return _response(
        resp.status_code,
        {
            "forecast": forecast_payload,
            "scheduler_response": scheduler_body,
        },
    )
