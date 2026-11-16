# ReliState Supply: E-Commerce Storefront + Developer Console

A small Flask app that exercises New Relic APM with a customer-facing storefront, a developer console, feature flags, simulated errors and latency, and automated traffic. Part of the *Observability as Code with New Relic + Terraform* curriculum. Version `1.1.0`.

The storefront is a fictional shop called **ReliState Supply**. It has a product catalog, category filters, a shopping bag, and a simulated checkout. No payments are collected, no customer accounts exist, and no real orders are fulfilled. The developer console at `/console` keeps the incident simulator, feature flag controls, and browser monitoring demo used in the lessons.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│  Docker Compose: relistate-terraform-demo                │
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
| `relistate-web` | 8000 (bound to `127.0.0.1`) | Yes (APM) | Flask app: storefront at `/`, developer console at `/console`, flags, simulated errors, and latency |
| `relistate-loadgen` | — | No | Sends a weighted mix of storefront, console, flag, and checkout requests to `relistate-web` |

### Pages

| URL | Audience | What it shows |
|-----|----------|---------------|
| `/` | Customers (demo) | Storefront: hero, category filters, product grid, shopping bag, simulated checkout |
| `/console` | Developers and instructors | Control room: incident simulator, feature flags, browser monitoring demo |

Feature flags control parts of the storefront. `free_shipping_banner` toggles the announcement bar, `dark_mode_beta` toggles dark theme, and `express_checkout` changes the checkout button label. Change them in `/console` and reload `/`.

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

Open these local-only URLs:

- Storefront: **http://localhost:8000/**
- Developer console: **http://localhost:8000/console**
- Health check: **http://localhost:8000/healthz**

Try the storefront: filter the catalog, add items to the bag, and place a demo order. The bag is stored in your browser's local storage. Each demo order is written to the SQLite database.

```bash
docker compose logs --tail=30 relistate-loadgen
docker compose logs --tail=30 relistate-web
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
| GET | `/` | Customer-facing storefront |
| GET | `/console` | Developer console UI |
| GET | `/healthz` | Health check |
| GET | `/api/v1/products` | Fictional product catalog (six items) |
| POST | `/api/v1/checkout` | Simulated checkout: `{"items": [{"id": "nova", "quantity": 2}]}`. Records a fictional order, charges nothing |
| GET | `/api/v1/demo/stats` | Count and total of simulated demo orders |
| GET | `/api/v1/flags/evaluate?flag=` | Evaluate a feature flag (`dark_mode_beta`, `express_checkout`, `free_shipping_banner`) |
| POST | `/api/v1/flags/rules` | Update a flag: `{"flag": "...", "enabled": true}` |
| POST | `/api/v1/auth/agent-token` | Mock token endpoint, protected by the `X-Agent-Secret` header |
| GET or POST | `/simulate/error?rate=0..1` | Returns a random 500 or 503 at the given rate (default `1`) |
| GET or POST | `/simulate/slow?latency_ms=0..5000` | Adds latency (random 1.5–3.0 s if omitted) |

### Test the API

```bash
curl -i http://localhost:8000/healthz
curl -s http://localhost:8000/api/v1/products
curl -i -X POST http://localhost:8000/api/v1/checkout -H 'Content-Type: application/json' -d '{"items":[{"id":"nova","quantity":2}]}'
curl -s http://localhost:8000/api/v1/demo/stats
curl -i 'http://localhost:8000/api/v1/flags/evaluate?flag=dark_mode_beta'
curl -i -X POST http://localhost:8000/api/v1/flags/rules -H 'Content-Type: application/json' -d '{"flag":"express_checkout","enabled":true}'
curl -i -X POST http://localhost:8000/api/v1/auth/agent-token -H 'X-Agent-Secret: local-demo-secret'
curl -i 'http://localhost:8000/simulate/error?rate=0.5'
curl -i 'http://localhost:8000/simulate/slow?latency_ms=2500'
```

`local-demo-secret` and `mock.jwt.demo-only` are fake values for demonstration. The checkout endpoint records only fictional orders: it never accepts card details or addresses. The logs contain *fabricated* fields that resemble PII, solely for log-masking exercises. Do not expose this app to the public internet without protection.

## Load Generation

The `relistate-loadgen` service sends requests in this proportion:

| Request | Share |
|---------|-------|
| Flag evaluation (three flags, equal chance) | 75% |
| Storefront visit (catalog browse; 25% of visits add a demo checkout) or console page | 15% |
| Flag update | 8% |
| Health check | 2% |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEW_RELIC_LICENSE_KEY` | No | empty | New Relic ingest license key |
| `NEW_RELIC_MONITOR_MODE` | No | `false` | Set `true` to report data once a license key is present |
| `NEW_RELIC_APP_NAME` | No | `ReliState-Terraform-Demo` | APM application name |
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
- **Business-style transactions**: storefront visits, catalog browsing, flag evaluations, and simulated checkouts (`POST /api/v1/checkout`) for throughput and latency dashboards
- **Distributed tracing**: enabled through `newrelic.ini` and the environment
- **Application logging**: structured JSON events written to stdout (`storefront_view`, `catalog_browse`, `checkout_complete`, `flag_eval`, and others) for log forwarding and masking exercises
- **Browser monitoring**: the agent injects browser JavaScript into HTML pages served through Gunicorn. Enable and configure browser monitoring in New Relic to see it. The console has a deliberate JavaScript error for the browser lesson.

## Using with the Terraform Series

This app is the shared target for the planned *Observability as Code with New Relic + Terraform* lessons. Use the storefront for customer-journey and browser monitoring examples. Use the console for incident, flag, and latency scenarios. The routes and log event names above are stable, so NRQL queries and Terraform resources can refer to them. Terraform configurations are future work and are not included in this demo yet.

## Stopping

```bash
docker compose down
```

`docker compose down -v` also deletes the SQLite database in the `relistate-data` volume, including demo orders and flag state.

## Data Storage

SQLite is embedded in Python, so there is no separate database container. Both Gunicorn workers share the database file, which lives in the named Docker volume. The volume stores feature flags and simulated orders. Flag defaults are applied only when the database is first created, so an existing volume keeps its stored flag values.

## Security and Boundaries

The console can modify demo flags and trigger intentional server errors **without authentication**. The storefront and checkout are fictional: there are no payments, customer accounts, delivery addresses, or external databases. This is safe only in a localhost or otherwise restricted training environment. **Do not expose this application on the public Internet without adding authentication and authorization, rate limiting, CSRF safeguards, and normal deployment hardening.**
