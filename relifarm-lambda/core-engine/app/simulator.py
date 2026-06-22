"""
Local mathematical simulation of farm telemetry — no external weather APIs.

Soil moisture follows: baseline_drift + diurnal_sin + valve_recharge + noise
Soil temperature follows: seasonal_offset + diurnal_sin + noise
Tractor position follows a small bounded random walk.
"""
import asyncio
import logging
import math
import os
import random
import time
from datetime import datetime, timezone

from . import db

logger = logging.getLogger("relifarm.simulator")

# Day-of-year baseline temperature for Iowa-like climate (degrees C).
_SEASONAL_BASELINE_C = 18.0
_DIURNAL_AMPLITUDE_C = 6.0
_DIURNAL_AMPLITUDE_MOISTURE = 3.5

# Bounded geographic walk centered roughly on Story County, IA.
_TRACTOR_LAT_BOUND = (41.870, 41.890)
_TRACTOR_LON_BOUND = (-93.110, -93.080)


def _diurnal_factor(now: datetime) -> float:
    """Sin wave keyed to hour-of-day; peaks ~14:00 local."""
    hour = now.hour + now.minute / 60.0
    return math.sin((hour - 8.0) / 24.0 * 2.0 * math.pi)


def _seasonal_factor(now: datetime) -> float:
    """Sin wave keyed to day-of-year; peaks ~July 1."""
    doy = now.timetuple().tm_yday
    return math.sin((doy - 80.0) / 365.0 * 2.0 * math.pi)


def _tick_sectors() -> None:
    now = datetime.now(timezone.utc)
    diurnal = _diurnal_factor(now)
    seasonal = _seasonal_factor(now)

    with db.cursor() as cur:
        cur.execute("SELECT sector_id, soil_moisture_pct, soil_temp_c, valve_open FROM sectors")
        rows = cur.fetchall()

        for row in rows:
            sector_id = row["sector_id"]
            moisture = float(row["soil_moisture_pct"])
            temp = float(row["soil_temp_c"])
            valve_open = bool(row["valve_open"])

            # Moisture: continuous evaporative loss + valve recharge + diurnal influence.
            evaporation_loss = 0.18 + 0.12 * max(diurnal, 0)
            recharge = 1.40 if valve_open else 0.0
            noise = random.gauss(0.0, 0.25)
            new_moisture = moisture - evaporation_loss + recharge + noise
            new_moisture = max(8.0, min(72.0, new_moisture))

            # Temperature: seasonal baseline + diurnal swing + noise.
            new_temp = (
                _SEASONAL_BASELINE_C
                + 4.0 * seasonal
                + _DIURNAL_AMPLITUDE_C * diurnal
                + random.gauss(0.0, 0.4)
            )

            cur.execute(
                """
                UPDATE sectors
                   SET soil_moisture_pct = %s,
                       soil_temp_c = %s,
                       last_updated = NOW()
                 WHERE sector_id = %s
                """,
                (round(new_moisture, 2), round(new_temp, 2), sector_id),
            )


def _tick_tractors() -> None:
    with db.cursor() as cur:
        cur.execute("SELECT tractor_id, latitude, longitude, fuel_pct, status FROM tractors")
        rows = cur.fetchall()

        for row in rows:
            lat = float(row["latitude"]) + random.gauss(0.0, 0.00040)
            lon = float(row["longitude"]) + random.gauss(0.0, 0.00040)
            lat = max(_TRACTOR_LAT_BOUND[0], min(_TRACTOR_LAT_BOUND[1], lat))
            lon = max(_TRACTOR_LON_BOUND[0], min(_TRACTOR_LON_BOUND[1], lon))

            fuel = max(0.0, float(row["fuel_pct"]) - random.uniform(0.05, 0.20))
            status = row["status"]
            if fuel < 5.0:
                fuel = 100.0
                status = "refueling"
            elif random.random() < 0.05:
                status = random.choice(["idle", "tilling", "seeding", "harvesting"])

            cur.execute(
                """
                UPDATE tractors
                   SET latitude = %s,
                       longitude = %s,
                       fuel_pct = %s,
                       status = %s,
                       last_updated = NOW()
                 WHERE tractor_id = %s
                """,
                (round(lat, 6), round(lon, 6), round(fuel, 2), status, row["tractor_id"]),
            )


async def run_simulation_loop() -> None:
    """Background coroutine — ticks every SIMULATION_INTERVAL_SECONDS."""
    interval = float(os.environ.get("SIMULATION_INTERVAL_SECONDS", "5"))
    logger.info("Sensor simulation loop started (interval=%.1fs)", interval)
    while True:
        try:
            started = time.monotonic()
            _tick_sectors()
            _tick_tractors()
            elapsed = time.monotonic() - started
            logger.debug("Simulation tick complete (%.3fs)", elapsed)
        except Exception:
            logger.exception("Simulation tick failed")
        await asyncio.sleep(interval)
