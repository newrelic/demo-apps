# Locust Tests - Load Generation for New Relic Telemetry

Load generation suite using Locust that creates background telemetry by simulating user interactions with the Flask UI and AI agent. Provides realistic traffic for New Relic distributed tracing and AI monitoring demonstrations.

## Features

- **Flask UI Traffic Generation**: Simulates users accessing chat and repair pages
- **A/B Model Comparison**: 50/50 split traffic between Model A and Model B
- **Repair Workflow Testing**: Automated repair triggers with performance tracking
- **Chat Interface Load**: Simulates user chat interactions with both models
- **Passive Load Generation**: Background telemetry generation with weighted prompt distribution
- **Web UI**: Real-time metrics dashboard on port 8089
- **HTTP API**: Programmatic control for automated testing

## Architecture

### Technology Stack

- **Framework**: Locust 2.43.0 (distributed load testing)
- **Base Image**: locustio/locust:2.20.0
- **Deployment**: Docker with exposed web UI (8089) and worker ports (5557)

### Project Structure

```
locust-tests/
├── locustfile.py            # User classes and load scenarios
├── requirements.txt          # Python dependencies (locust~=2.43.0)
└── Dockerfile               # Container configuration
```

### Internal Architecture - User Classes

```
┌─────────────────────────────────────────────────────────────┐
│                      Locust Load Generator                   │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  TargetAppUser (Business Traffic)                      │ │
│  │  • wait_time: between(1, 3)                            │ │
│  │  • Tasks: health(3), orders(2), products(2), ...      │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│                   └──> http://target-app:8000/               │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ModelAUser (AI Agent - Model A)                       │ │
│  │  • wait_time: constant_pacing(30)                      │ │
│  │  • Repair trigger: 20% probability                     │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│                   └──> http://ai-agent:8001/repair?model=a  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  ModelBUser (AI Agent - Model B)                       │ │
│  │  • wait_time: constant_pacing(30)                      │ │
│  │  • Repair trigger: 20% probability                     │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│                   └──> http://ai-agent:8001/repair?model=b  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PassiveLoadUser (Demo Data Generation)                │ │
│  │  • wait_time: constant_pacing(18) [~3.3 req/min]      │ │
│  │  • Prompt Mix: Tool(40%), Simple(50%), Error(10%)     │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│                   └──> Both /chat?model=a and /chat?model=b │
│                                                              │
└──────────────────────────────────────────────────────────────┘

                         Metrics Dashboard
                   http://localhost:8089 (Web UI)
```

**Key Components**:

1. **TargetAppUser**: Simulates standard application traffic
2. **ModelAUser/ModelBUser**: A/B split for agent repair workflows (50/50)
3. **ChatModelAUser/ChatModelBUser**: Chat interface load testing
4. **PassiveLoadUser**: New Relic demo data generation with prompt variety
5. **Locust Web UI**: Real-time statistics and control interface

## User Classes Reference

### 1. TargetAppUser - Business Traffic

**Purpose**: Simulate realistic business traffic to the target application

**Configuration**:
- **Host**: `http://target-app:8000`
- **Wait Time**: `between(1, 3)` seconds (random between tasks)
- **Task Distribution**:
  - `get_health()` - Weight: 3 (most frequent)
  - `get_orders()` - Weight: 2
  - `get_products()` - Weight: 2
  - `create_order()` - Weight: 1 (POST /orders)
  - `get_specific_product()` - Weight: 1 (GET /products/:id)

**Traffic Pattern**:
```
3 health checks
2 order fetches
2 product browses
1 order creation
1 specific product lookup
= 9 total requests per cycle (1-3s between cycles)
```

**Use Case**: Load testing target-app under normal conditions, detecting failures

### 2. ModelAUser - AI Agent Repair (Model A)

**Purpose**: Test AI agent repair workflows using Model A (mistral:7b-instruct)

**Configuration**:
- **Host**: `http://ai-agent:8001`
- **Wait Time**: `constant_pacing(30)` (runs every 30 seconds)
- **Repair Trigger Probability**: 20%

**Workflow**:
1. Check agent status: `GET /status`
2. 20% chance: Trigger repair: `POST /repair?model=a` (timeout: 120s)
3. Validate repair success in response JSON
4. Wait 30 seconds, repeat

**Use Case**: A/B testing for Model A performance metrics

### 3. ModelBUser - AI Agent Repair (Model B)

**Purpose**: Test AI agent repair workflows using Model B (ministral-3:8b-instruct-2512-q8_0)

**Configuration**:
- **Host**: `http://ai-agent:8001`
- **Wait Time**: `constant_pacing(30)` (runs every 30 seconds)
- **Repair Trigger Probability**: 20%

**Workflow**: Identical to ModelAUser, but uses `?model=b` query parameter

**Use Case**: A/B testing for Model B performance metrics, comparison with Model A

### 4. ChatModelAUser - Chat Interface (Model A)

**Purpose**: Simulate chat interactions with Model A

**Configuration**:
- **Host**: `http://ai-agent:8001`
- **Wait Time**: `constant_pacing(45)` (chat every 45 seconds)
- **Message Pool**: 5 predefined questions about system status

**Sample Messages**:
- "What is the current system status?"
- "How many containers are running?"
- "Tell me about the target application."
- "What tools do you have access to?"
- "How do you diagnose failures?"

**Use Case**: Test chat endpoint responsiveness, Model A latency

### 5. ChatModelBUser - Chat Interface (Model B)

**Purpose**: Simulate chat interactions with Model B

**Configuration**: Identical to ChatModelAUser, but uses `"model": "b"` in payload

**Use Case**: Chat endpoint A/B comparison

### 6. PassiveLoadUser - Demo Data Generation

**Purpose**: Generate realistic AI monitoring data for New Relic demos

**Configuration**:
- **Host**: `http://ai-agent:8001`
- **Wait Time**: `constant_pacing(18)` (~3.3 request cycles per minute)
- **Behavior**: Sends same prompt to **both** Model A and Model B sequentially

**Prompt Distribution**:

| Category | Weight | Count | Examples |
|----------|--------|-------|----------|
| **Tool Prompts** | 40% | 15 prompts | "Check the current system status", "What containers are running?", "Show me docker container status" |
| **Simple Prompts** | 50% | 16 prompts | "Hello", "What can you help me with?", "Explain what you do" |
| **Error Prompts** | 10% | 8 prompts | Empty message, 5000 char string, emoji spam, control characters |

**Workflow Per Cycle**:
1. Select prompt based on weighted distribution
2. Send to Model A: `POST /chat {"message": prompt, "model": "a"}`
3. Send to Model B: `POST /chat {"message": prompt, "model": "b"}`
4. Wait 18 seconds, repeat

**Use Case**: Continuous demo data generation, error handling testing, A/B comparison data

## User Class Summary Table

| User Class | Target | Wait Time | Request Rate | A/B Split | Use Case |
|------------|--------|-----------|--------------|-----------|----------|
| **TargetAppUser** | target-app:8000 | between(1,3) | ~20-60/min | N/A | Business traffic simulation |
| **ModelAUser** | ai-agent:8001 | constant_pacing(30) | 2/min | 50% (Model A) | Repair workflow A/B testing |
| **ModelBUser** | ai-agent:8001 | constant_pacing(30) | 2/min | 50% (Model B) | Repair workflow A/B testing |
| **ChatModelAUser** | ai-agent:8001 | constant_pacing(45) | 1.3/min | 50% (Model A) | Chat endpoint testing |
| **ChatModelBUser** | ai-agent:8001 | constant_pacing(45) | 1.3/min | 50% (Model B) | Chat endpoint testing |
| **PassiveLoadUser** | ai-agent:8001 | constant_pacing(18) | 6.7/min (both) | 100% (both) | Demo data generation |

## Dependencies

### Upstream Services
None - locust-tests generates load

### Downstream Services
- **target-app** (Port 8000): Receives business traffic simulation
- **ai-agent** (Port 8001): Receives repair and chat requests

### External Dependencies
None - all traffic is internal to Docker network

## Local Development

### Prerequisites

- Python 3.11+
- Running target-app on port 8000
- Running ai-agent on port 8001
- Access to Docker network (if running in containers)

### Running Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (optional, defaults shown)
export TARGET_APP_URL=http://localhost:8000
export AI_AGENT_URL=http://localhost:8001

# Run Locust with all user classes
locust -f locustfile.py --host http://localhost:8000

# Run only specific user class
locust -f locustfile.py TargetAppUser --host http://localhost:8000

# Run headless (no web UI)
locust -f locustfile.py --headless --users 10 --spawn-rate 2 --run-time 5m
```

**Expected Output**:
```
[2025-01-07 12:00:00] locust.main: Starting web interface at http://0.0.0.0:8089
[2025-01-07 12:00:00] locust.main: Starting Locust 2.43.0
```

### Accessing Web UI

Navigate to `http://localhost:8089` and configure:

1. **Number of users**: Total concurrent users to simulate
2. **Spawn rate**: Users added per second
3. **Host**: Target base URL (auto-configured per user class)

Click "Start swarming" to begin load test.

### Testing

```bash
# Test locustfile syntax
locust -f locustfile.py --check

# Run quick sanity test (10 users for 30 seconds)
locust -f locustfile.py --headless --users 10 --spawn-rate 2 --run-time 30s

# Test specific user class
locust -f locustfile.py PassiveLoadUser --headless --users 5 --run-time 1m
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TARGET_APP_URL` | No | http://target-app:8000 | Target application base URL |
| `AI_AGENT_URL` | No | http://ai-agent:8001 | AI agent service base URL |

### Wait Time Strategies

Locust provides several wait time strategies used in this locustfile:

- **`between(min, max)`**: Random wait time between min and max seconds (TargetAppUser)
- **`constant_pacing(seconds)`**: Fixed interval between task executions (ModelAUser, ModelBUser, etc.)

### Task Weights

Modify task weights in `locustfile.py` to adjust traffic distribution:

```python
class TargetAppUser(HttpUser):
    @task(3)  # Runs 3x more often than weight-1 tasks
    def get_health(self):
        ...

    @task(1)  # Baseline weight
    def create_order(self):
        ...
```

## Locust HTTP API Reference

Locust exposes an HTTP API for programmatic control (used by MCP server):

### Start Load Test

```bash
POST http://localhost:8089/swarm
Content-Type: application/x-www-form-urlencoded

user_count=10&spawn_rate=2&host=http://target-app:8000
```

**Response**:
```json
{
  "message": "Swarming started",
  "success": true
}
```

### Get Statistics

```bash
GET http://localhost:8089/stats/requests
```

**Response**:
```json
{
  "stats": [
    {
      "name": "GET /health",
      "method": "GET",
      "num_requests": 450,
      "num_failures": 5,
      "avg_response_time": 12.3,
      "max_response_time": 245,
      "requests_per_second": 15.2
    },
    ...
  ],
  "total_rps": 45.6,
  "fail_ratio": 0.012,
  "state": "running"
}
```

### Stop Load Test

```bash
GET http://localhost:8089/stop
```

**Response**:
```json
{
  "message": "Test stopped",
  "success": true
}
```

### Reset Statistics

```bash
GET http://localhost:8089/stats/reset
```

## Troubleshooting

### Service-Specific Issues

#### High Failure Rate

**Symptom**: Many requests failing in Locust UI (red in stats table)

**Diagnosis**:
```bash
# Check Locust logs
docker logs aim-locust

# Check target service health
curl http://localhost:8000/health
curl http://localhost:8001/status

# View failure details in Locust UI
# Navigate to http://localhost:8089 → Failures tab
```

**Solutions**:
```bash
# Reduce load (fewer users or lower spawn rate)
# In Locust UI: Stop → Adjust users → Start

# Increase target service resources
docker stats aim-target-app aim-ai-agent

# Check if chaos-engine is injecting failures
docker logs aim-chaos-engine | grep "Injecting"
```

#### Locust Not Starting

**Symptom**: Container exits or web UI unreachable at port 8089

**Diagnosis**:
```bash
# Check container status
docker-compose ps locust

# View logs
docker logs aim-locust

# Verify port binding
netstat -an | grep 8089
```

**Solutions**:
```bash
# Restart Locust
docker-compose restart locust

# Check for port conflicts
lsof -i :8089  # macOS/Linux
# If port in use, stop conflicting process or change port in docker-compose.yml

# Verify locustfile syntax
docker exec aim-locust locust -f /locust/locustfile.py --check
```

#### Model A/B Not Splitting Evenly

**Symptom**: One model receiving significantly more traffic than the other

**Cause**: Unequal user counts for ModelAUser vs ModelBUser

**Solutions**:
```bash
# In Locust UI when starting test:
# - Set equal number of ModelAUser and ModelBUser
# - Example: 10 total users = 5 ModelAUser + 5 ModelBUser

# Or use PassiveLoadUser which always sends to both models equally
locust -f locustfile.py PassiveLoadUser --users 10
```

#### Timeouts in Repair Workflows

**Symptom**: Many "Repair Workflow" requests timing out (>120s)

**Cause**: Ollama models taking too long to respond or AI agent hung

**Diagnosis**:
```bash
# Check Ollama model health
docker logs aim-ollama-model-a --tail 50
docker logs aim-ollama-model-b --tail 50

# Check AI agent logs
docker logs aim-ai-agent --tail 50

# Monitor model memory usage
docker stats aim-ollama-model-a aim-ollama-model-b
```

**Solutions**:
```bash
# Restart Ollama models
docker-compose restart ollama-model-a ollama-model-b

# Increase timeout in locustfile.py (requires code change)
# Change timeout=120 to timeout=300 for repair tasks

# Reduce repair trigger probability from 20% to 10%
# Edit locustfile.py: if random.random() < 0.1:
```

#### PassiveLoadUser Not Generating Data

**Symptom**: PassiveLoadUser running but no chat requests visible

**Diagnosis**:
```bash
# Check if PassiveLoadUser is active
# Locust UI → Workers tab → verify PassiveLoadUser count

# View request names in Locust UI
# Should see "Tool Prompt (Model A/B)", "Simple Prompt (Model A/B)", etc.

# Check AI agent logs
docker logs aim-ai-agent | grep "/chat"
```

**Solutions**:
```bash
# Ensure only PassiveLoadUser is running
locust -f locustfile.py PassiveLoadUser --users 10

# Verify AI_AGENT_URL is correct
docker exec aim-locust printenv AI_AGENT_URL

# Test chat endpoint manually
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello", "model": "a"}'
```

### Debugging

```bash
# View live logs
docker logs -f aim-locust

# Access container shell
docker exec -it aim-locust /bin/bash

# Test locustfile syntax
docker exec aim-locust locust -f /locust/locustfile.py --check

# View real-time Locust stats
curl http://localhost:8089/stats/requests | jq

# Monitor load test from terminal (watch)
watch -n 2 'curl -s http://localhost:8089/stats/requests | jq ".stats[] | {name, requests: .num_requests, failures: .num_failures}"'
```

## Production Recommendations

### Security

1. **Disable in Production**: Load testing should NOT run against production
   ```yaml
   # docker-compose.yml - comment out or remove locust service
   # locust:
   #   ...
   ```

2. **API Authentication**: Add auth to Locust HTTP API
   ```python
   # In docker-compose.yml
   environment:
     - LOCUST_BASIC_AUTH=username:password
   ```

3. **Rate Limiting**: Protect target services from accidental overload
   - Set reasonable user and spawn rate limits in Locust UI
   - Implement rate limiting on target services (slowapi, nginx)

### Performance

1. **Distributed Mode**: Run Locust in master-worker mode for higher load
   ```yaml
   # docker-compose.yml
   locust-master:
     command: locust --master
   locust-worker-1:
     command: locust --worker --master-host=locust-master
   locust-worker-2:
     command: locust --worker --master-host=locust-master
   ```

2. **Resource Limits**: Prevent Locust from consuming too much host resources
   ```yaml
   # docker-compose.yml
   locust:
     deploy:
       resources:
         limits:
           memory: 512M
           cpus: '1.0'
   ```

3. **Connection Pooling**: Already handled by Locust's httpx client
   - Default: 10 connections per user
   - Adjust with `pool_connections` parameter if needed

### Monitoring

1. **Export Metrics**: Send Locust metrics to monitoring system
   ```bash
   # Use Locust's built-in Prometheus exporter
   locust --modern-ui --web-port 8089 --prometheus-port 9646

   # Or export to CSV periodically
   locust --csv=results --headless --run-time=10m
   ```

2. **Custom Metrics**: Track business-specific metrics
   ```python
   import newrelic.agent

   @task
   def create_order(self):
       response = self.client.post("/orders", ...)
       if response.status_code == 200:
           newrelic.agent.record_custom_metric('Orders/Created', 1)
   ```

3. **Alerting**: Alert on high failure rates or response time degradation
   - Monitor Locust `/stats/requests` endpoint
   - Alert if `fail_ratio > 0.05` (5% failures)
   - Alert if `avg_response_time > 1000` (1s average)

### Scalability

1. **Horizontal Scaling**: Add more Locust workers
   ```bash
   # Scale workers to 5 instances
   docker-compose up -d --scale locust-worker=5
   ```

2. **Adaptive Load**: Adjust load based on target capacity
   ```python
   # Custom LoadTestShape for gradual ramp-up
   from locust import LoadTestShape

   class StagesShape(LoadTestShape):
       stages = [
           {"duration": 60, "users": 10, "spawn_rate": 1},
           {"duration": 120, "users": 50, "spawn_rate": 5},
           {"duration": 180, "users": 100, "spawn_rate": 10},
       ]
   ```

3. **Persistent Results**: Store test results in database
   ```python
   # Use Locust's event hooks to export to PostgreSQL/InfluxDB
   from locust import events

   @events.request.add_listener
   def on_request(request_type, name, response_time, **kwargs):
       # Export to DB
       pass
   ```

## Advanced Usage

### Custom User Class

Create a new user class for specific testing scenarios:

```python
class CustomWorkflowUser(HttpUser):
    """Test a specific workflow end-to-end."""
    host = AI_AGENT_URL
    wait_time = between(5, 10)

    @task
    def full_repair_cycle(self):
        # 1. Check status
        self.client.get("/status")

        # 2. Trigger repair
        response = self.client.post("/repair?model=a", timeout=120)

        # 3. Verify metrics updated
        metrics = self.client.get("/metrics").json()
        assert metrics["model_a"]["total_requests"] > 0
```

### Running Specific Scenario

```bash
# Run only target-app traffic (no AI agent load)
locust -f locustfile.py TargetAppUser --host http://target-app:8000

# Run only Model A repair testing
locust -f locustfile.py ModelAUser --host http://ai-agent:8001

# Run A/B comparison (equal weights)
locust -f locustfile.py ModelAUser ModelBUser --host http://ai-agent:8001

# Run passive load for 30 minutes (demo data)
locust -f locustfile.py PassiveLoadUser --headless --users 10 --run-time 30m
```

### Exporting Results

```bash
# Export to CSV (runs headless)
locust -f locustfile.py --headless --users 50 --spawn-rate 5 --run-time 10m \
  --csv=results --csv-full-history

# Generates:
# - results_stats.csv
# - results_stats_history.csv
# - results_failures.csv
# - results_exceptions.csv

# Export to HTML report (requires --html flag)
locust -f locustfile.py --headless --users 50 --run-time 10m --html=report.html
```

## License

Built for New Relic AI Monitoring Demo

## Tech Stack

- Locust 2.43.0 (distributed load testing framework)
- Python 3.11
- httpx (HTTP client with connection pooling)
