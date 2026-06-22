"""
ReliFarm core-engine — FastAPI service.

Source of truth for all sector / tractor state. Receives commits from the
valve-scheduler Lambda and exposes telemetry to the web dashboard.

Distributed tracing
-------------------
The New Relic Python agent (started by `newrelic-admin run-program`) auto-
instruments FastAPI and psycopg2. It also reads incoming W3C `traceparent` /
`tracestate` headers on every request, so the trace from
`browser → yield-forecast → valve-scheduler → core-engine → postgres`
joins automatically. We additionally extract the trace id from the agent's
linking metadata and persist it on `irrigation_executions.trace_id` so demo
viewers can pivot from a Postgres row straight to the matching trace in NR.
"""
import asyncio
import logging
import pathlib

import newrelic.agent
import psycopg2
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from . import db, simulator
from .models import (
    IrrigationExecutionCreate,
    IrrigationExecutionRead,
    SectorRead,
    TractorRead,
)

# init.sql is shipped alongside the app at /app/db/init.sql in the container.
# It uses CREATE IF NOT EXISTS / ON CONFLICT DO NOTHING, so re-running it on
# every boot is safe — works for fresh RDS instances and for warm restarts.
_INIT_SQL_PATH = pathlib.Path(__file__).resolve().parent.parent / "db" / "init.sql"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("relifarm.core")

app = FastAPI(title="ReliFarm core-engine", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_background_task: asyncio.Task | None = None

# Retry budget for "wait for Postgres to be reachable" during cold start.
# When the EC2 self-host workaround path is active, the Postgres host can
# take 1-3 minutes to finish dnf-installing and starting on first boot.
# We don't gate FastAPI's startup hook on this — /health stays 200 from
# t=0 — so App Runner sees a healthy service right away. The bootstrap
# task runs concurrently and races against this deadline.
_BOOTSTRAP_DEADLINE_SECONDS = 300
_BOOTSTRAP_BACKOFF_INITIAL = 2.0
_BOOTSTRAP_BACKOFF_MAX = 15.0


@app.on_event("startup")
async def _startup() -> None:
    # Configure the pool without opening connections — non-blocking, returns
    # immediately even if Postgres isn't up yet. See db.init_pool().
    db.init_pool()
    global _background_task
    _background_task = asyncio.create_task(_bootstrap_then_simulate())
    logger.info("core-engine accepting requests; DB bootstrap running in background")


async def _bootstrap_then_simulate() -> None:
    """Run schema bootstrap with retry, then start the simulator loop.

    Splitting this off the FastAPI startup hook keeps the lifespan event
    fast so App Runner's `/health` probe responds immediately. If Postgres
    isn't reachable yet, schema bootstrap retries with exponential backoff;
    once it succeeds, the simulator coroutine takes over.
    """
    await _bootstrap_schema_with_retry()
    await simulator.run_simulation_loop()


async def _bootstrap_schema_with_retry() -> None:
    if not _INIT_SQL_PATH.is_file():
        logger.warning("init.sql not found at %s — skipping schema bootstrap", _INIT_SQL_PATH)
        return

    sql = _INIT_SQL_PATH.read_text()
    deadline = asyncio.get_event_loop().time() + _BOOTSTRAP_DEADLINE_SECONDS
    delay = _BOOTSTRAP_BACKOFF_INITIAL
    attempt = 0
    last_err: Exception | None = None

    while asyncio.get_event_loop().time() < deadline:
        attempt += 1
        try:
            with db.cursor() as cur:
                cur.execute(sql)
            if attempt > 1:
                logger.info("schema bootstrap complete on attempt %d (%s)", attempt, _INIT_SQL_PATH)
            else:
                logger.info("schema bootstrap complete (%s)", _INIT_SQL_PATH)
            return
        except psycopg2.OperationalError as exc:
            last_err = exc
            remaining = deadline - asyncio.get_event_loop().time()
            logger.warning(
                "Postgres not reachable yet (bootstrap attempt %d, %.0fs remaining): %s",
                attempt,
                max(remaining, 0),
                str(exc).strip().splitlines()[0],
            )
            if remaining <= 0:
                break
            await asyncio.sleep(min(delay, remaining))
            delay = min(delay * 1.5, _BOOTSTRAP_BACKOFF_MAX)

    logger.error(
        "schema bootstrap failed after %d attempts in %ds — last error: %s",
        attempt,
        _BOOTSTRAP_DEADLINE_SECONDS,
        last_err,
    )
    newrelic.agent.notice_error()


@app.on_event("shutdown")
async def _shutdown() -> None:
    if _background_task is not None:
        _background_task.cancel()
    db.close_pool()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/sectors", response_model=list[SectorRead])
def list_sectors() -> list[dict]:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT sector_id, crop_type, area_hectares, soil_moisture_pct,
                   soil_temp_c, valve_open, last_updated
              FROM sectors
             ORDER BY sector_id
            """
        )
        return cur.fetchall()


@app.get("/sectors/{sector_id}", response_model=SectorRead)
def get_sector(sector_id: str) -> dict:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT sector_id, crop_type, area_hectares, soil_moisture_pct,
                   soil_temp_c, valve_open, last_updated
              FROM sectors
             WHERE sector_id = %s
            """,
            (sector_id,),
        )
        row = cur.fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail=f"sector '{sector_id}' not found")
        return row


@app.get("/tractors", response_model=list[TractorRead])
def list_tractors() -> list[dict]:
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT tractor_id, latitude, longitude, fuel_pct, status, last_updated
              FROM tractors
             ORDER BY tractor_id
            """
        )
        return cur.fetchall()


@app.get("/executions", response_model=list[IrrigationExecutionRead])
def list_executions(limit: int = 25) -> list[dict]:
    limit = max(1, min(limit, 200))
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT execution_id, sector_id, triggered_by, yield_health,
                   water_volume_l, duration_seconds, trace_id, executed_at
              FROM irrigation_executions
             ORDER BY executed_at DESC
             LIMIT %s
            """,
            (limit,),
        )
        return cur.fetchall()


@app.post("/executions", response_model=IrrigationExecutionRead, status_code=201)
def create_execution(payload: IrrigationExecutionCreate) -> dict:
    """
    Persist an irrigation execution and flip the sector's valve open.
    The synthetic monitor occasionally sends `emergency_override` set, which
    is the demo's intentional 500 path — surfaces in NR error analytics.
    """
    if payload.emergency_override:
        # Intentional internal-server-error path for the demo.
        newrelic.agent.notice_error()
        logger.error(
            "emergency_override='%s' received — raising synthetic 500",
            payload.emergency_override,
        )
        raise HTTPException(
            status_code=500,
            detail="ReliFarm core-engine simulated failure: emergency_override is not allowed",
        )

    # Capture the live trace id from the agent so we can persist it alongside the row.
    linking = newrelic.agent.get_linking_metadata() or {}
    trace_id = payload.trace_id or linking.get("trace.id")

    with db.cursor() as cur:
        cur.execute("SELECT 1 FROM sectors WHERE sector_id = %s", (payload.sector_id,))
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail=f"sector '{payload.sector_id}' not found")

        cur.execute(
            """
            INSERT INTO irrigation_executions
                (sector_id, triggered_by, yield_health, water_volume_l, duration_seconds, trace_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING execution_id, sector_id, triggered_by, yield_health,
                      water_volume_l, duration_seconds, trace_id, executed_at
            """,
            (
                payload.sector_id,
                payload.triggered_by,
                payload.yield_health,
                payload.water_volume_l,
                payload.duration_seconds,
                trace_id,
            ),
        )
        row = cur.fetchone()

        cur.execute(
            "UPDATE sectors SET valve_open = TRUE, last_updated = NOW() WHERE sector_id = %s",
            (payload.sector_id,),
        )

        # Custom span attribute makes the row pivot-friendly in NR.
        newrelic.agent.add_custom_attribute("relifarm.sector_id", payload.sector_id)
        newrelic.agent.add_custom_attribute("relifarm.triggered_by", payload.triggered_by)
        newrelic.agent.add_custom_attribute("relifarm.execution_id", row["execution_id"])

        logger.info(
            "execution committed sector=%s by=%s trace_id=%s",
            payload.sector_id,
            payload.triggered_by,
            trace_id,
        )
        return row


@app.post("/sectors/{sector_id}/close-valve", status_code=204, response_class=Response)
def close_valve(sector_id: str) -> Response:
    with db.cursor() as cur:
        cur.execute(
            "UPDATE sectors SET valve_open = FALSE, last_updated = NOW() WHERE sector_id = %s",
            (sector_id,),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"sector '{sector_id}' not found")
    return Response(status_code=204)
