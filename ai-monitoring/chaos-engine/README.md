# Chaos Engine - Automated Failure Injection

Automated chaos engineering service that randomly injects failures into the target-app to demonstrate autonomous AI-driven repair capabilities.

## Features

- **Scheduled Random Failures**: Weighted randomization across 3 failure scenarios
- **Configurable Intervals**: Adjustable chaos injection frequency (default: 180s)
- **Automatic Recovery**: Clears failure state after 30s to allow repair testing
- **Graceful Startup**: 60s stabilization period before first injection
- **Weighted Scenarios**: Crash (30%), Slowdown (40%), Config Error (30%)
- **Signal Handling**: Graceful shutdown with state cleanup

## Architecture

### Technology Stack

- **Runtime**: Python 3.11
- **Docker Client**: docker 7.1.0 (Docker SDK for Python)
- **Scheduling**: Custom interval-based scheduler
- **Deployment**: Docker with shared failure state volume

### Project Structure

```
chaos-engine/
├── engine.py                    # Main orchestrator and event loop
├── scheduler.py                 # Timing and weighted scenario selection
├── scenarios/
│   ├── crash_scenarios.py       # Container exit injection
│   ├── slowdown_scenarios.py    # Response delay injection (10-30s)
│   └── config_scenarios.py      # Configuration error injection
├── requirements.txt             # Python dependencies
└── Dockerfile                   # Container configuration
```

### Internal Architecture - Injection Cycle

```
Startup (t=0)
    |
    v
Wait 60s (target-app stabilization)
    |
    v
Clear failure state to "healthy"
    |
    v
┌───────────────────────────────────┐
│  Main Chaos Loop                  │
│                                   │
│  1. Check if interval elapsed     │
│  2. Select weighted scenario      │
│  3. Write failure to state file   │
│  4. Wait 30s (recovery period)    │
│  5. Clear state to "healthy"      │
│  6. Wait for next interval        │
└───────┬───────────────────────────┘
        │
        └──> Repeat every 180s (configurable)

Scenarios (Weighted Random):
┌─────────────────┬──────────┬─────────────────────┐
│ Crash           │ 30%      │ mode: "crash"       │
│ Slowdown        │ 40%      │ mode: "slow" (10-30s) │
│ Config Error    │ 30%      │ mode: "config_error"│
└─────────────────┴──────────┴─────────────────────┘
```

**Key Components**:

1. **ChaosScheduler**: Manages timing and weighted scenario selection
2. **Scenario Injectors**: Write failure modes to shared state file
3. **Signal Handler**: Ensures graceful shutdown with state cleanup
4. **Recovery Manager**: Automatically clears failures after 30s

## Scenario Reference

### 1. Crash Scenario (30% Probability)

**Purpose**: Test AI agent's ability to detect and restart crashed containers

**Injection**:
```python
{
  "mode": "crash",
  "delay": 0,
  "timestamp": 1704617280.5,
  "injected_by": "chaos-engine"
}
```

**Behavior**:
- Target-app middleware reads state and calls `os._exit(1)`
- Container terminates immediately
- Docker restart policy brings container back
- AI agent should detect crash and verify recovery

**Expected AI Response**: Detect container exit via `docker_ps()`, verify restart

### 2. Slowdown Scenario (40% Probability)

**Purpose**: Test AI agent's ability to detect performance degradation

**Injection**:
```python
{
  "mode": "slow",
  "delay": 15,  # Random 10-30 seconds
  "timestamp": 1704617280.5,
  "injected_by": "chaos-engine"
}
```

**Behavior**:
- Target-app middleware calls `asyncio.sleep(delay)` before processing
- All requests hang for 10-30 seconds
- May cause client timeouts (Locust tests)
- Container remains running but unresponsive

**Expected AI Response**: Detect slow response times, restart container to clear state

### 3. Configuration Error Scenario (30% Probability)

**Purpose**: Test AI agent's ability to diagnose and fix configuration issues

**Injection**:
```python
{
  "mode": "config_error",
  "delay": 0,
  "timestamp": 1704617280.5,
  "injected_by": "chaos-engine"
}
```

**Behavior**:
- Target-app middleware raises `HTTPException(500)` simulating missing `DATABASE_URL`
- All requests return 500 Internal Server Error
- Health check fails
- Container remains running

**Expected AI Response**: Detect 500 errors in logs, set `DATABASE_URL` env var, restart container

## Scenario Summary Table

| Scenario | Probability | State File Content | Target Behavior | Expected AI Action |
|----------|-------------|-------------------|-----------------|-------------------|
| **Crash** | 30% | `mode: "crash"` | Container exits (code 1) | Detect exit, restart container |
| **Slowdown** | 40% | `mode: "slow", delay: 10-30` | Requests hang 10-30s | Detect slowness, restart to clear |
| **Config Error** | 30% | `mode: "config_error"` | All requests return 500 | Detect 500s, set DATABASE_URL, restart |

## Dependencies

### Upstream Services
None - chaos-engine initiates failures

### Downstream Services
- **target-app**: Consumes failure state via shared file

### External Dependencies
- **Failure State File**: `/tmp/failure_state.json` (shared volume with target-app)

## Local Development

### Prerequisites

- Python 3.11+
- Write access to shared failure state file
- Running target-app instance to inject failures into

### Running Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CHAOS_INTERVAL=180
export CHAOS_ENABLED=true
export FAILURE_STATE_FILE=/tmp/failure_state.json

# Run chaos engine
python engine.py
```

**Expected Output**:
```
============================================================
🌪️  Chaos Engine Starting
============================================================
Chaos enabled: True
Chaos interval: 180s
Recovery period: 30s
Failure state file: /tmp/failure_state.json
============================================================
INFO:     Waiting 60s for target-app to stabilize...
INFO:     Clearing failure state to healthy
INFO:     ✓ Failure state cleared
============================================================
💥 Injecting SLOWDOWN failure
============================================================
WARNING:  🐌 CHAOS: Injecting SLOWDOWN scenario (15s delay)
INFO:     ✓ Slowdown scenario written to /tmp/failure_state.json
INFO:     Waiting 30s for failure to manifest...
INFO:     Clearing failure state to healthy
INFO:     Waiting 180s until next chaos cycle...
```

### Testing

```bash
# Verify chaos engine functionality
python -m pytest tests/

# Manually test single scenario
python -c "
from pathlib import Path
from scenarios.crash_scenarios import inject_crash
inject_crash(Path('/tmp/failure_state.json'))
"

# Check injected state
cat /tmp/failure_state.json
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CHAOS_INTERVAL` | No | 180 | Seconds between chaos injections |
| `CHAOS_ENABLED` | No | true | Enable/disable chaos injection |
| `FAILURE_STATE_FILE` | No | /tmp/failure_state.json | Path to shared failure state file |

### Timing Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **Startup Wait** | 60s | Allow target-app to stabilize before first injection |
| **Recovery Period** | 30s | Time to let failure manifest before clearing |
| **Chaos Interval** | 180s (default) | Time between successive injections |

### Scenario Weights

Modify scenario weights in `engine.py:93-97`:

```python
scenarios = [
    ("CRASH", 0.30, lambda: inject_crash(FAILURE_STATE_FILE)),       # 30%
    ("SLOWDOWN", 0.40, lambda: inject_slowdown(FAILURE_STATE_FILE)), # 40%
    ("CONFIG_ERROR", 0.30, lambda: inject_config_error(FAILURE_STATE_FILE)), # 30%
]
```

## Troubleshooting

### Service-Specific Issues

#### Chaos Too Aggressive

**Symptom**: System never stabilizes, failures injected too frequently

**Cause**: `CHAOS_INTERVAL` too short or recovery period insufficient

**Solutions**:
```bash
# Increase interval to 5 minutes
docker-compose stop chaos-engine
# Edit docker-compose.yml:
#   CHAOS_INTERVAL=300

docker-compose up -d chaos-engine

# Or temporarily disable chaos
docker-compose stop chaos-engine

# Or adjust interval at runtime
docker exec aim-chaos-engine kill -USR1 1  # Not supported, requires restart
```

#### Chaos Not Running

**Symptom**: No failures being injected, target-app always healthy

**Diagnosis**:
```bash
# Check chaos-engine logs
docker logs aim-chaos-engine

# Verify chaos is enabled
docker exec aim-chaos-engine printenv CHAOS_ENABLED

# Check scheduler is running
docker exec aim-chaos-engine ps aux | grep engine.py
```

**Solutions**:
```bash
# Restart chaos-engine
docker-compose restart chaos-engine

# Verify CHAOS_ENABLED=true in docker-compose.yml
docker-compose config | grep -A5 chaos-engine | grep CHAOS_ENABLED

# Check failure state file permissions
docker exec aim-chaos-engine ls -la /tmp/failure_state.json
```

#### Failure State Stuck

**Symptom**: Failure state not clearing after 30s recovery period

**Cause**: Chaos engine crashed or stopped during injection

**Solutions**:
```bash
# Manually clear state
docker exec aim-chaos-engine python -c "
import json
json.dump({'mode': 'healthy'}, open('/tmp/failure_state.json', 'w'))
"

# Verify state cleared
docker exec aim-chaos-engine cat /tmp/failure_state.json

# Restart chaos engine
docker-compose restart chaos-engine
```

#### Wrong Scenario Distribution

**Symptom**: One scenario appearing more/less than expected probability

**Cause**: Random distribution over small sample size or weights misconfigured

**Diagnosis**:
```bash
# Count scenario occurrences in logs (last 100 lines)
docker logs aim-chaos-engine --tail 100 | grep "Injecting" | \
  awk '{print $NF}' | sort | uniq -c

# Expected over 100 injections: ~30 CRASH, ~40 SLOWDOWN, ~30 CONFIG_ERROR
```

**Solutions**:
- Wait for more samples (law of large numbers)
- Verify weights in `engine.py:93-97` sum to 1.0
- Restart to reset random seed: `docker-compose restart chaos-engine`

### Debugging

```bash
# View live logs
docker logs -f aim-chaos-engine

# Access container shell
docker exec -it aim-chaos-engine /bin/bash

# Check current failure state
docker exec aim-chaos-engine cat /tmp/failure_state.json

# View scheduler status (check last injection time)
docker logs aim-chaos-engine | grep "Marked injection"

# Test scenario manually
docker exec aim-chaos-engine python -c "
from pathlib import Path
from scenarios.slowdown_scenarios import inject_slowdown
inject_slowdown(Path('/tmp/failure_state.json'), delay=5)
"
```

## Production Recommendations

### Security

1. **Disable in Production**: Chaos engineering should NOT run in production
   ```yaml
   # docker-compose.yml
   chaos-engine:
     environment:
       - CHAOS_ENABLED=false
   ```

2. **Access Control**: Restrict who can modify `CHAOS_ENABLED` environment variable
   - Use secrets management (AWS Secrets Manager, HashiCorp Vault)
   - Limit Docker Compose file edit permissions

3. **Rate Limiting**: Add maximum injection frequency cap
   ```python
   MIN_INTERVAL = 60  # Never inject more than once per minute
   ```

### Performance

1. **Resource Limits**: Chaos-engine is lightweight, but set limits
   ```yaml
   # docker-compose.yml
   chaos-engine:
     deploy:
       resources:
         limits:
           memory: 128M
           cpus: '0.1'
   ```

2. **Optimize State File I/O**: Use atomic writes
   ```python
   import tempfile
   import shutil

   with tempfile.NamedTemporaryFile('w', delete=False) as tmp:
       json.dump(state, tmp)
   shutil.move(tmp.name, state_file)
   ```

### Monitoring

1. **Custom Metrics**: Track chaos injection events
   ```python
   import newrelic.agent

   newrelic.agent.record_custom_event('ChaosInjection', {
       'scenario': scenario_name,
       'timestamp': time.time(),
       'interval': CHAOS_INTERVAL
   })
   ```

2. **Alerting**: Alert when chaos-engine stops unexpectedly
   - Monitor container uptime via Docker health checks
   - Alert if no logs in last `CHAOS_INTERVAL * 2` seconds

3. **Audit Logging**: Log all injections to external system
   ```python
   import logging
   import logging.handlers

   # Add syslog handler
   handler = logging.handlers.SysLogHandler(address='/dev/log')
   logger.addHandler(handler)
   ```

### Scalability

1. **Multiple Target Support**: Extend to inject failures across multiple services
   ```python
   TARGETS = [
       {"name": "target-app", "state_file": "/tmp/failure_state.json"},
       {"name": "target-db", "state_file": "/tmp/db_failure_state.json"},
   ]
   ```

2. **Scenario Plugins**: Dynamic scenario loading
   ```python
   import importlib

   # Load scenarios from scenarios/ directory
   for module in Path('scenarios').glob('*_scenarios.py'):
       importlib.import_module(f'scenarios.{module.stem}')
   ```

3. **Distributed Chaos**: Coordinate chaos across multiple environments
   - Use message queue (RabbitMQ, Kafka) for event coordination
   - Centralized chaos controller with multiple agents

## Advanced Usage

### Custom Scenarios

Create a new scenario file:

```python
# scenarios/network_scenarios.py
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def inject_network_partition(state_file: Path):
    """Inject network partition failure."""
    logger.warning("🌐 CHAOS: Injecting NETWORK PARTITION scenario")

    import time
    state = {
        "mode": "network_partition",
        "delay": 0,
        "timestamp": time.time(),
        "injected_by": "chaos-engine"
    }

    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
        logger.info(f"✓ Network partition scenario written to {state_file}")
    except Exception as e:
        logger.error(f"Failed to write network partition scenario: {e}")
```

Register in `engine.py`:

```python
from scenarios.network_scenarios import inject_network_partition

scenarios = [
    ("CRASH", 0.25, lambda: inject_crash(FAILURE_STATE_FILE)),
    ("SLOWDOWN", 0.30, lambda: inject_slowdown(FAILURE_STATE_FILE)),
    ("CONFIG_ERROR", 0.25, lambda: inject_config_error(FAILURE_STATE_FILE)),
    ("NETWORK_PARTITION", 0.20, lambda: inject_network_partition(FAILURE_STATE_FILE)),
]
```

### Dynamic Interval Adjustment

Adjust chaos frequency based on system load:

```python
def get_dynamic_interval():
    """Calculate interval based on system metrics."""
    # Example: slow down if many failures detected
    active_failures = check_active_failures()
    if active_failures > 2:
        return CHAOS_INTERVAL * 2  # Double interval if system stressed
    return CHAOS_INTERVAL

# In main loop:
scheduler = ChaosScheduler(interval=get_dynamic_interval())
```

## License

Built for New Relic AI Monitoring Demo

## Tech Stack

- Python 3.11
- docker 7.1.0 (Docker SDK for Python)
- Custom scheduler with weighted randomization
