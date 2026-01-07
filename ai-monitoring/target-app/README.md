# Target App - Intentionally Fragile Microservice

FastAPI microservice designed to be intentionally fragile for demonstrating autonomous system repair. Features three coordinated failure modes triggered by the chaos engine.

## Features

- **Three Failure Modes**: Crash, slow response (10-30s delays), and configuration errors
- **Middleware-Based Injection**: Failure logic injected via FastAPI middleware
- **Shared State Coordination**: Synchronized with chaos-engine via shared file
- **Business Logic Endpoints**: Simulated orders and products APIs
- **Health Check**: Always-available health endpoint for monitoring

## Architecture

### Technology Stack

- **Framework**: FastAPI 0.128.0
- **Server**: uvicorn 0.40.0 (ASGI)
- **Validation**: Pydantic 2.12.5
- **Logging**: python-json-logger 4.0.0
- **Deployment**: Docker with shared failure state volume

### Project Structure

```
target-app/
├── app.py                  # Main FastAPI application
├── state.py                # Failure state file manager
├── endpoints/
│   ├── health.py           # Health check endpoint
│   ├── orders.py           # Orders API (GET/POST)
│   └── products.py         # Products API (GET)
├── failures/
│   ├── crash_handler.py    # Container exit logic
│   ├── slow_response.py    # Artificial delay injection
│   └── config_error.py     # Configuration error simulation
├── requirements.txt        # Python dependencies
└── Dockerfile              # Container configuration
```

### Internal Architecture - Failure Flow

```
                         Incoming Request
                                |
                                v
                    [Middleware Intercept]
                                |
                                v
                    Read /tmp/failure_state.json
                                |
                    ┌───────────┴───────────┐
                    |                       |
            mode == "crash"          mode == "slow"
                    |                       |
                    v                       v
            os._exit(1)          asyncio.sleep(delay)
            [Container Dies]                |
                                            v
                                    [Continue to handler]
                                            |
                        ┌───────────────────┴───────────────────┐
                        |                                       |
                mode == "config_error"                  mode == "healthy"
                        |                                       |
                        v                                       v
            Raise HTTPException(500)                    Normal Processing
            "DATABASE_URL missing"                      [Business Logic]
```

## Failure Modes

### 1. Container Crash

**Trigger**: Chaos engine writes `{"mode": "crash"}` to failure state file

**Behavior**:
- Middleware calls `os._exit(1)`
- Container terminates immediately
- Docker restart policy brings it back
- Health check becomes unavailable

**Recovery**:
```bash
# Agent detects via docker_ps (container exited)
# Agent calls docker_restart("target-app")
# Container restarts, state resets to healthy
```

**Test Manually**:
```bash
# Inject crash
docker exec aim-target-app python -c "
import json
json.dump({'mode': 'crash'}, open('/tmp/failure_state.json', 'w'))
"

# Trigger by making any request
curl http://localhost:8000/health
# Container exits immediately
```

### 2. Slow Response / Timeout

**Trigger**: Chaos engine writes `{"mode": "slow", "delay": 15}` (10-30s range)

**Behavior**:
- Middleware calls `asyncio.sleep(delay)` before processing request
- Request hangs for 10-30 seconds
- May cause client timeouts
- Container remains running

**Recovery**:
```bash
# Agent detects via slow response time
# Agent calls docker_restart("target-app") to clear state
# Or waits for chaos engine to reset
```

**Test Manually**:
```bash
# Inject slowdown
docker exec aim-target-app python -c "
import json
json.dump({'mode': 'slow', 'delay': 10}, open('/tmp/failure_state.json', 'w'))
"

# Test - should take 10+ seconds
time curl http://localhost:8000/health
```

### 3. Configuration Error

**Trigger**: Chaos engine writes `{"mode": "config_error"}`

**Behavior**:
- Middleware raises `HTTPException(500)` simulating missing `DATABASE_URL`
- All requests return 500 Internal Server Error
- Health check also fails
- Container remains running

**Recovery**:
```bash
# Agent detects via 500 errors in logs
# Agent calls docker_update_env("target-app", "DATABASE_URL", "value")
# Agent calls docker_restart("target-app")
```

**Test Manually**:
```bash
# Inject config error
docker exec aim-target-app python -c "
import json
json.dump({'mode': 'config_error'}, open('/tmp/failure_state.json', 'w'))
"

# Test - should return 500
curl http://localhost:8000/health
# {"detail": "Configuration error: DATABASE_URL not set"}
```

## Failure Modes Summary Table

| Mode | Trigger | Container State | Health Check | Recovery Action | Recovery Time |
|------|---------|-----------------|--------------|-----------------|---------------|
| **crash** | `{"mode": "crash"}` | Exits (code 1) | ❌ Unavailable | Restart container | ~2-5s |
| **slow** | `{"mode": "slow", "delay": N}` | ✅ Running | ⚠️ Slow (N seconds) | Restart or wait | Variable |
| **config_error** | `{"mode": "config_error"}` | ✅ Running | ❌ 500 error | Set env var + restart | ~5-10s |
| **healthy** | `{"mode": "healthy"}` | ✅ Running | ✅ 200 OK | None needed | - |

## API Reference

### Endpoints

#### `GET /health`
Health check endpoint - always available but may fail based on failure mode.

**Response (healthy)**:
```json
{
  "status": "healthy",
  "service": "target-app"
}
```

**Response (config error)**:
```json
{
  "detail": "Configuration error: DATABASE_URL not set"
}
```

#### `GET /orders`
List all orders (simulated data).

**Response**:
```json
[
  {
    "id": 1,
    "product": "Widget",
    "quantity": 5,
    "total": 99.95
  },
  ...
]
```

#### `POST /orders`
Create a new order.

**Request**:
```json
{
  "product": "Widget",
  "quantity": 3,
  "price": 19.99
}
```

**Response**:
```json
{
  "id": 42,
  "product": "Widget",
  "quantity": 3,
  "total": 59.97,
  "created_at": "2025-01-07T12:00:00Z"
}
```

#### `GET /products`
List all products (simulated catalog).

**Response**:
```json
[
  {
    "id": 1,
    "name": "Widget",
    "price": 19.99,
    "in_stock": true
  },
  ...
]
```

#### `GET /debug/state`
View current failure state (debug endpoint).

**Response**:
```json
{
  "mode": "slow",
  "delay": 15,
  "timestamp": "2025-01-07T12:00:00Z"
}
```

## Dependencies

### Upstream Services
None - this is a target service

### Downstream Services
- **ai-agent**: Monitors and repairs this service
- **locust-tests**: Generates load traffic
- **chaos-engine**: Coordinates failure injection

### External Dependencies
- **Failure State File**: `/tmp/failure_state.json` (shared volume with chaos-engine)

## Local Development

### Prerequisites

- Python 3.11+
- Access to shared `/tmp` directory for failure state

### Running Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/db
export LOG_LEVEL=INFO
export FAILURE_STATE_FILE=/tmp/failure_state.json

# Initialize failure state (healthy)
echo '{"mode": "healthy"}' > /tmp/failure_state.json

# Run service
python app.py
```

**Expected Output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### Testing

```bash
# Test health check
curl http://localhost:8000/health

# Test business endpoints
curl http://localhost:8000/orders
curl http://localhost:8000/products

# Test POST endpoint
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"product": "Widget", "quantity": 2, "price": 19.99}'

# Check current failure state
curl http://localhost:8000/debug/state
```

### Testing Failure Modes Locally

```bash
# Test crash mode
echo '{"mode": "crash"}' > /tmp/failure_state.json
curl http://localhost:8000/health  # Process exits

# Test slow mode (restart service first)
python app.py &
echo '{"mode": "slow", "delay": 5}' > /tmp/failure_state.json
time curl http://localhost:8000/health  # Takes 5+ seconds

# Test config error mode
echo '{"mode": "config_error"}' > /tmp/failure_state.json
curl http://localhost:8000/health  # Returns 500

# Reset to healthy
echo '{"mode": "healthy"}' > /tmp/failure_state.json
curl http://localhost:8000/health  # Returns 200
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | - | Database connection string (not actually used) |
| `LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `FAILURE_STATE_FILE` | No | /tmp/failure_state.json | Path to shared failure state file |

### Failure State File Format

```json
{
  "mode": "healthy|crash|slow|config_error",
  "delay": 15,  // Only for "slow" mode
  "timestamp": "2025-01-07T12:00:00Z"
}
```

## Troubleshooting

### Service-Specific Issues

#### Container Keeps Crashing

**Symptom**: Container restarts every few seconds

**Cause**: Failure state stuck in "crash" mode

**Solutions**:
```bash
# Clear failure state
docker exec aim-target-app python -c "
import json
json.dump({'mode': 'healthy'}, open('/tmp/failure_state.json', 'w'))
"

# Or restart with fresh volume
docker-compose down -v
docker-compose up -d target-app

# Check chaos engine is not re-injecting
docker logs aim-chaos-engine
```

#### All Requests Return 500

**Symptom**: Every endpoint returns Internal Server Error

**Cause**: Failure state in "config_error" mode

**Solutions**:
```bash
# Check current state
curl http://localhost:8000/debug/state

# Clear failure state
docker exec aim-target-app python -c "
import json
json.dump({'mode': 'healthy'}, open('/tmp/failure_state.json', 'w'))
"

# Restart container
docker-compose restart target-app
```

#### Extremely Slow Responses

**Symptom**: All requests take 10-30 seconds

**Cause**: Failure state in "slow" mode with high delay

**Solutions**:
```bash
# Check state and delay
curl http://localhost:8000/debug/state

# Clear failure state
docker exec aim-target-app python -c "
import json
json.dump({'mode': 'healthy'}, open('/tmp/failure_state.json', 'w'))
"

# Future requests will be normal (no restart needed)
```

### Debugging

```bash
# View live logs
docker logs -f aim-target-app

# Access container shell
docker exec -it aim-target-app /bin/bash

# Check failure state
docker exec aim-target-app cat /tmp/failure_state.json

# Test health
curl http://localhost:8000/health

# Monitor with watch
watch -n 1 'curl -s http://localhost:8000/health | jq'
```

## Production Recommendations

### Security

1. **Remove Debug Endpoints**: Disable `/debug/state` in production
   ```python
   if os.getenv("ENV") != "production":
       app.include_router(debug_router)
   ```

2. **Input Validation**: Add request validation for POST endpoints
   - Already implemented via Pydantic models

3. **Rate Limiting**: Add rate limiting to prevent abuse
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   ```

### Performance

1. **Remove Failure Middleware**: Disable in production
   ```python
   if os.getenv("ENABLE_FAILURES", "false") == "true":
       app.middleware("http")(failure_middleware)
   ```

2. **Connection Pooling**: Add database connection pooling (if using real DB)
   ```python
   from sqlalchemy.pool import QueuePool
   engine = create_engine(DATABASE_URL, poolclass=QueuePool)
   ```

3. **Async Endpoints**: Use async database queries
   ```python
   @app.get("/orders")
   async def get_orders():
       async with async_session() as session:
           ...
   ```

### Monitoring

1. **APM Integration**: Add New Relic instrumentation (optional)
   ```bash
   pip install newrelic
   newrelic-admin run-program uvicorn app:app
   ```

2. **Custom Metrics**: Track business metrics
   ```python
   import newrelic.agent
   newrelic.agent.record_custom_metric('Orders/Created', 1)
   ```

3. **Health Check Details**: Add more health check information
   ```python
   @app.get("/health")
   async def health_check():
       return {
           "status": "healthy",
           "version": "1.0.0",
           "uptime_seconds": time.time() - start_time
       }
   ```

### Scalability

1. **Horizontal Scaling**: Run multiple instances
   - Remove failure injection middleware
   - Use load balancer (nginx, HAProxy)
   - Shared database for orders (not file-based state)

2. **Caching**: Add Redis caching for product catalog
   ```python
   @lru_cache(maxsize=100, ttl=3600)
   def get_products():
       ...
   ```

## License

Built for New Relic AI Monitoring Demo

## Tech Stack

- FastAPI 0.128.0
- uvicorn 0.40.0
- Pydantic 2.12.5
- python-json-logger 4.0.0
