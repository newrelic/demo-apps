# Busy Beavers 🦫

A minimal New Relic "busybox" demo — two Python/Flask services and a Selenium load generator that automatically lights up APM, Logs in Context, Errors Inbox, and Change Tracking in your New Relic account.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose: busy-beavers                           │
│                                                         │
│  ┌──────────┐   HTTP    ┌──────────┐                    │
│  │ frontend │ ────────► │ backend  │                    │
│  │  :5000   │           │  :5001   │                    │
│  └────▲─────┘           └──────────┘                    │
│       │ Selenium                                        │
│  ┌────┴──────┐                                          │
│  │  loadgen  │  ~20 tx/min, 1-2% error rate             │
│  └───────────┘                                          │
└─────────────────────────────────────────────────────────┘
```

| Service | Port | NR Agent | Description |
|---------|------|----------|-------------|
| `frontend` | 5000 | Yes (browser + APM) | Beaver-themed UI + NerdGraph change marker |
| `backend` | 5001 | Yes (APM) | Transaction processing + realistic error simulation |
| `loadgen` | — | No | Selenium headless Chrome driving the frontend |

## Prerequisites

- Docker + Docker Compose
- A New Relic account with:
  - License key (ingest)
  - User API key (NerdGraph — for change marker button)

## Quick Start

```bash
cp .env.example .env
# Edit .env with your New Relic credentials

docker compose up --build
```

Open **http://localhost:5000** — the dam control panel.

## UI Buttons

| Button | Endpoint | What it does |
|--------|----------|--------------|
| 🦫 **Normal Txn** | `POST /api/transaction` | Sends a normal transaction through the backend |
| 🌊 **Error** | `POST /api/error` | Forces a `DamConstructionError` / `LogSupplyError` into NR Errors Inbox |
| 🌲 **Change Marker** | `POST /api/change-marker` | Creates a NerdGraph deployment marker with static attributes |
| 🪵 **Null** | `POST /api/null` | No-op — rage-click target (load gen clicks this 5-8× per visit) |

## Load Generation

The `loadgen` service runs 2 concurrent Selenium users in headless Chrome.
Each user visits the frontend and clicks a button every ~6 seconds (± jitter):

| Action | Weight | Notes |
|--------|--------|-------|
| Normal Txn | 97% | Backend has an additional 1% random error rate |
| Null (rage click) | 2% | 5-8 rapid clicks per visit |
| Error | 1% | Direct error trigger |

Combined throughput: **~20 transactions/minute** at **~1–2% error rate**.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEW_RELIC_LICENSE_KEY` | Yes | NR ingest license key |
| `NEW_RELIC_API_KEY` | Yes | NR User API key (for change marker) |
| `NEW_RELIC_APP_NAME_FRONTEND` | No | Default: `busy-beavers_frontend` |
| `NEW_RELIC_APP_NAME_BACKEND` | No | Default: `busy-beavers_backend` |
| `LOADGEN_USERS` | No | Concurrent Selenium users (default: `2`) |
| `LOADGEN_INTERVAL` | No | Base seconds between requests (default: `6`) |

## New Relic Features Demonstrated

- **APM** — throughput, response time, Apdex for both services
- **Distributed Tracing** — frontend → backend spans
- **Logs in Context** — structured logs linked to traces on both services
- **Errors Inbox** — realistic `DamConstructionError` / `LogSupplyError` with multi-frame stack traces
- **Browser Monitoring** — auto-injected on the frontend
- **Change Tracking** — deployments created via the 🌲 button using NerdGraph
- **Rage Clicks** — captured by Browser via the 🪵 Null button

## Stopping

```bash
docker compose down
```
