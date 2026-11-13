# ReliState Developer Playground

A small Flask app that exercises New Relic APM with feature flags, simulated errors and latency, and automated traffic. Part of the *Observability as Code with New Relic + Terraform* curriculum. Version `1.0.0`.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Docker Compose: relistate                               │
│                                                          │
│  ┌──────────────────┐   HTTP    ┌────────────────────┐   │
│  │  relistate-web   │ ◄──────── │ relistate-loadgen  │   │
│  │  Flask/Gunicorn  │           │  Python requests   │   │
│  │  :8000 (APM)     │           └────────────────────┘   │
│  └────────┬─────────┘                                    │
│           │ SQLite (volume: relistate-data)              │
└───────────┴──────────────────────────────────────────────┘
```

| Service | Port | NR Agent | Description |
|---------|------|----------|-------------|
| `relistate-web` | 8000 (bound to `127.0.0.1`) | Yes (APM) | Flask app with feature flags, simulated errors, and simulated latency |
| `relistate-loadgen` | — | No | Sends a weighted mix of requests to `relistate-web` |

## Prerequisites

- Docker and Docker Compose
- Optional: a New Relic ingest license key, to send data to New Relic

## Quick Start

```bash
cp .env.example .env
# Optional: add your New Relic ingest license key and set NEW_RELIC_MONITOR_MODE=true in .env

docker compose up --build -d
docker compose ps
```

Open **http://localhost:8000/console**.

```bash
docker compose logs --tail=30 relistate-loadgen
docker compose down
```

The traffic generator sends roughly one request every five seconds by default. All data is demo-only. The port is bound to `127.0.0.1`, so the app is not reachable from other machines.

### Running without Docker

```bash
python -m pip install -r app/requirements.txt
python -m flask --app app.app run --no-debug --port 8000
```

Do not use `--debug`. The Flask debugger reserves the `/console` path.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/console` | Developer playground UI |
| GET | `/healthz` | Health check |
| GET | `/api/v1/flags/evaluate?flag=` | Evaluate a feature flag (`dark_mode_beta`, `express_checkout`) |
| POST | `/api/v1/flags/rules` | Update a flag: `{"flag": "...", "enabled": true}` |
| POST | `/api/v1/auth/agent-token` | Mock token endpoint, protected by the `X-Agent-Secret` header |
| GET or POST | `/simulate/error?rate=0..1` | Returns a random 500 or 503 at the given rate (default `1`) |
| GET or POST | `/simulate/slow?latency_ms=0..5000` | Adds latency (random 1.5–3.0 s if omitted) |

### Test the API

```bash
curl -i http://localhost:8000/healthz
curl -i 'http://localhost:8000/api/v1/flags/evaluate?flag=dark_mode_beta'
curl -i -X POST http://localhost:8000/api/v1/flags/rules -H 'Content-Type: application/json' -d '{"flag":"express_checkout","enabled":true}'
curl -i -X POST http://localhost:8000/api/v1/auth/agent-token -H 'X-Agent-Secret: local-demo-secret'
curl -i 'http://localhost:8000/simulate/error?rate=0.5'
curl -i 'http://localhost:8000/simulate/slow?latency_ms=2500'
```

`local-demo-secret` and `mock.jwt.demo-only` are fake values for demonstration. The logs contain *fabricated* fields that resemble PII, solely for log-masking exercises. Do not expose this app to the public internet without protection.

## Load Generation

The `relistate-loadgen` service sends requests in this proportion:

| Request | Share |
|---------|-------|
| Flag evaluation | 75% |
| Console page | 15% |
| Flag update | 8% |
| Health check | 2% |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEW_RELIC_LICENSE_KEY` | No | empty | New Relic ingest license key |
| `NEW_RELIC_MONITOR_MODE` | No | `false` | Set `true` to report data once a license key is present |
| `NEW_RELIC_APP_NAME` | No | `ReliState-Demo` | APM application name |
| `NEW_RELIC_DISTRIBUTED_TRACING_ENABLED` | No | `true` | Enables distributed tracing |
| `NEW_RELIC_LOG` | No | `stdout` | Agent log destination |
| `NEW_RELIC_LOG_LEVEL` | No | `info` | Agent log level |
| `ENVIRONMENT` | No | `development` | Added to log events and APM attributes |
| `SERVICE_TIER` | No | `tier-1` | Added to APM attributes |
| `OWNER_TEAM` | No | `platform` | Added to APM attributes |
| `DEMO_API_SECRET` | No | `local-demo-secret` | Demo-only secret for the mock token endpoint |
| `TRAFFIC_INTERVAL_SECONDS` | No | `5` | Seconds between load generator requests |

## New Relic Features Demonstrated

- **APM**: transactions, errors, and throughput from Gunicorn workers, started with `newrelic-admin run-program`
- **Custom attributes**: `environment`, `service_tier`, and `owner_team` are added to every request
- **Distributed tracing**: enabled through `newrelic.ini` and the environment
- **Application logging**: structured JSON events written to stdout for log forwarding and masking exercises
- **Browser monitoring**: the agent injects browser JavaScript into HTML pages served through Gunicorn. Enable and configure browser monitoring in New Relic to see it.

## Stopping

```bash
docker compose down
```

`docker compose down -v` also deletes the SQLite database in the `relistate-data` volume.

## Data Storage

SQLite is embedded in Python, so there is no separate database container. Both Gunicorn workers share the database file, which lives in the named Docker volume.

## Planned Terraform Lessons

Terraform configurations for the Observability as Code lessons are planned as future work. They are not included in this demo yet.
