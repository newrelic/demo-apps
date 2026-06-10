"""
ReliFarm — valve-scheduler Lambda
=================================

Consumes the yield-forecast output, computes water volume + valve duration
for the requested sector, and POSTs an irrigation execution record to the
core-engine backend.

Distributed tracing
-------------------
Inbound trace context is accepted automatically by the New Relic Lambda
layer. Outbound headers to the core-engine are produced explicitly via
`newrelic.agent.insert_distributed_trace_headers` so the chain
`yield-forecast → valve-scheduler → core-engine → postgres` is unbroken.
"""
import json
import logging
import os

import newrelic.agent  # type: ignore
import requests  # type: ignore

logger = logging.getLogger()
logger.setLevel(logging.INFO)

CORE_ENGINE_URL = os.environ["CORE_ENGINE_URL"]
HTTP_TIMEOUT_SECONDS = float(os.environ.get("HTTP_TIMEOUT_SECONDS", "8"))


# --- scheduling model -------------------------------------------------------
def _allocate_water(yield_health: float, soil_moisture_pct: float, area_hectares: float) -> dict:
    """
    Lower yield_health + lower moisture => more water. Bounded so a single
    valve cycle never exceeds 4500 L or 600 s, even under extreme inputs.
    """
    deficit = max(0.0, 50.0 - soil_moisture_pct)              # how dry vs target 50%
    health_gap = max(0.0, 80.0 - yield_health)                # how far below "healthy" 80
    base_litres_per_hectare = 38.0 + 1.8 * deficit + 0.9 * health_gap
    water_volume_l = round(min(4500.0, base_litres_per_hectare * area_hectares), 2)

    duration_seconds = int(min(600, max(45, water_volume_l / 12.5)))
    return {"water_volume_l": water_volume_l, "duration_seconds": duration_seconds}


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
    headers: list[tuple[str, str]] = []
    newrelic.agent.insert_distributed_trace_headers(headers)
    return headers


def lambda_handler(event, context):
    logger.info("valve-scheduler invoked")

    if event.get("httpMethod") == "OPTIONS":
        return _response(204, {})

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        newrelic.agent.notice_error()
        logger.exception("malformed forecast payload")
        return _response(400, {"error": "malformed JSON", "details": str(exc)})

    sector_id = body.get("sector_id")
    yield_health = body.get("yield_health")
    soil_moisture = body.get("soil_moisture_pct")
    triggered_by = body.get("triggered_by", "forecast")
    emergency_override = body.get("emergency_override")

    if not sector_id or yield_health is None or soil_moisture is None:
        return _response(
            400,
            {"error": "missing required fields: sector_id, yield_health, soil_moisture_pct"},
        )

    # We do not have area on the wire; assume default 35 ha unless caller provides it.
    area_hectares = float(body.get("area_hectares", 35.0))
    allocation = _allocate_water(float(yield_health), float(soil_moisture), area_hectares)

    newrelic.agent.add_custom_attribute("relifarm.sector_id", sector_id)
    newrelic.agent.add_custom_attribute("relifarm.water_volume_l", allocation["water_volume_l"])
    newrelic.agent.add_custom_attribute("relifarm.duration_seconds", allocation["duration_seconds"])

    execution_payload = {
        "sector_id": sector_id,
        "triggered_by": triggered_by,
        "yield_health": float(yield_health),
        "water_volume_l": allocation["water_volume_l"],
        "duration_seconds": allocation["duration_seconds"],
    }
    if emergency_override is not None:
        execution_payload["emergency_override"] = emergency_override

    # ----- propagate W3C trace context to core-engine -----
    outbound_headers = dict(_outbound_trace_headers())
    outbound_headers["Content-Type"] = "application/json"

    try:
        resp = requests.post(
            f"{CORE_ENGINE_URL.rstrip('/')}/executions",
            json=execution_payload,
            headers=outbound_headers,
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        newrelic.agent.notice_error()
        logger.exception("core-engine call failed")
        return _response(502, {"error": "core-engine unreachable", "details": str(exc)})

    try:
        engine_body = resp.json()
    except ValueError:
        engine_body = {"raw": resp.text}

    return _response(
        resp.status_code,
        {
            "schedule": execution_payload,
            "core_engine_response": engine_body,
        },
    )
