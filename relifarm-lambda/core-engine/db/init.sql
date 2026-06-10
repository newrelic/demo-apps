-- =============================================================================
-- ReliFarm core-engine schema
-- Bootstrapped on first Postgres container start (via docker-entrypoint-initdb.d)
-- =============================================================================

CREATE TABLE IF NOT EXISTS sectors (
    sector_id         TEXT PRIMARY KEY,
    crop_type         TEXT NOT NULL,
    area_hectares     NUMERIC(8, 2) NOT NULL,
    soil_moisture_pct NUMERIC(5, 2) NOT NULL,
    soil_temp_c       NUMERIC(5, 2) NOT NULL,
    valve_open        BOOLEAN NOT NULL DEFAULT FALSE,
    last_updated      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tractors (
    tractor_id     TEXT PRIMARY KEY,
    latitude       NUMERIC(9, 6) NOT NULL,
    longitude      NUMERIC(9, 6) NOT NULL,
    fuel_pct       NUMERIC(5, 2) NOT NULL,
    status         TEXT NOT NULL,
    last_updated   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS irrigation_executions (
    execution_id      BIGSERIAL PRIMARY KEY,
    sector_id         TEXT NOT NULL REFERENCES sectors(sector_id),
    triggered_by      TEXT NOT NULL,
    yield_health      NUMERIC(5, 2) NOT NULL,
    water_volume_l    NUMERIC(8, 2) NOT NULL,
    duration_seconds  INTEGER NOT NULL,
    trace_id          TEXT,
    executed_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_executions_sector ON irrigation_executions(sector_id);
CREATE INDEX IF NOT EXISTS idx_executions_executed_at ON irrigation_executions(executed_at DESC);

-- Seed: 6 farm sectors + 3 tractors
INSERT INTO sectors (sector_id, crop_type, area_hectares, soil_moisture_pct, soil_temp_c, valve_open) VALUES
    ('NW-A1', 'corn',     42.50, 38.20, 21.40, FALSE),
    ('NW-A2', 'soybean',  35.10, 41.60, 20.80, FALSE),
    ('NE-B1', 'wheat',    28.75, 33.10, 22.10, FALSE),
    ('NE-B2', 'corn',     51.00, 29.80, 23.50, FALSE),
    ('SW-C1', 'alfalfa',  18.20, 47.30, 19.90, FALSE),
    ('SE-D1', 'soybean',  39.40, 35.60, 21.80, FALSE)
ON CONFLICT (sector_id) DO NOTHING;

INSERT INTO tractors (tractor_id, latitude, longitude, fuel_pct, status) VALUES
    ('T-001', 41.878100, -93.097700, 87.30, 'idle'),
    ('T-002', 41.879200, -93.098100, 64.10, 'tilling'),
    ('T-003', 41.877400, -93.096900, 92.50, 'idle')
ON CONFLICT (tractor_id) DO NOTHING;
