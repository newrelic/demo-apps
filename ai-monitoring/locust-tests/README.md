# Locust Tests - Passive Load Generation for New Relic Telemetry

Passive load generation using Locust that creates realistic background telemetry for New Relic AI monitoring demonstrations. Uses a comprehensive 18-prompt pool with weighted distribution across categories.

## Features

- **Passive Load Generation**: Automatic background traffic at 5-10 requests/hour
- **Comprehensive Prompt Pool**: 18 prompts across 6 categories (MCP, simple/complex chat, errors, boundaries, abuse)
- **Backend Workflow Control**: MCP prompts use deterministic tool invocations
- **Immediate Start**: First request fires within seconds via `on_start()` method
- **A/B Model Testing**: Each prompt sent to both Model A and Model B for comparison
- **Smart Routing**: Automatic endpoint selection (/repair with workflows vs /chat)
- **Web UI**: Real-time metrics dashboard on port 8089
- **Headless Mode**: Runs automatically with docker-compose, no manual start needed

## Architecture

### Technology Stack

- **Framework**: Locust 2.43.0 (distributed load testing)
- **Base Image**: locustio/locust:2.20.0
- **Integration**: Imports `prompt_pool.py` from ai-agent service
- **Deployment**: Docker with exposed web UI (8089)

### Project Structure

```
locust-tests/
├── locustfile.py            # PassiveLoadUser and load scenarios
├── requirements.txt          # Python dependencies (locust~=2.43.0)
└── Dockerfile               # Container configuration
```

### Load Generation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Locust Passive Load Generator               │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  PassiveLoadUser (Single User Class)                   │ │
│  │  • wait_time: constant_pacing(720) [12 minutes]        │ │
│  │  • on_start(): Immediate first request (no wait)       │ │
│  │  • 18-prompt pool with weighted distribution           │ │
│  │  • Smart routing: /repair (workflows) vs /chat         │ │
│  └────────────────┬───────────────────────────────────────┘ │
│                   │                                          │
│                   ├──> /repair?model=a&workflow=X  (15%)    │
│                   │    Backend-controlled MCP tools          │
│                   │                                          │
│                   └──> /chat {"message":"...", "model":"a"}  │
│                        LLM-decided tool usage (85%)          │
│                                                              │
│   Each prompt sent to BOTH Model A and Model B sequentially │
└──────────────────────────────────────────────────────────────┘

                         Metrics Dashboard
                   http://localhost:8089 (Web UI)
```

**Key Components**:

1. **PassiveLoadUser**: Single user class with comprehensive prompt pool
2. **Prompt Pool Integration**: Imports 18-prompt pool from `ai-agent/prompt_pool.py`
3. **Smart Routing**: Automatically routes MCP prompts to `/repair` with workflows
4. **Immediate Start**: `on_start()` method fires first request within seconds
5. **Locust Web UI**: Real-time statistics at port 8089

## PassiveLoadUser Configuration

### Load Pattern

- **Pacing**: 720 seconds (12 minutes) between requests
- **Rate**: ~10 requests/hour (5 per model)
- **First Request**: Immediate via `on_start()` method (no 12-minute wait)
- **Behavior**: Each cycle picks weighted-random prompt, sends to both models

### Prompt Distribution

| Category | Prompts | Weight | Endpoint | Control |
|----------|---------|--------|----------|---------|
| **MCP Healthy** | 1 | 10% | `/repair?workflow=minimal_single_tool` | Backend |
| **MCP Degraded** | 1 | 5% | `/repair?workflow=forced_full_repair` | Backend |
| **Simple Chat** | 5 | 35% | `/chat` | LLM |
| **Complex Chat** | 5 | 30% | `/chat` | LLM |
| **Error Scenarios** | 3 | 10% | `/chat` | LLM |
| **Boundary Testing** | 3 | 8% | `/chat` | LLM |
| **Abusive Language** | 1 | 2% | `/chat` | LLM |

### Timeline Example

```
t=0s      docker-compose up starts locust
t=~15s    AI agent healthy, locust spawns user
t=~20s    on_start() → FIRST REQUEST (immediate!)
t=~740s   Second request via @task (12 min later)
t=~1460s  Third request (24 min later)
...continues every 720s...
```

## Prompt Categories

### 1. MCP Tool Testing (Backend-Controlled)

**MCP Healthy (10% of requests)**:
- Prompt: "Check the current system health status"
- Endpoint: `/repair?model={a|b}&workflow=minimal_single_tool`
- Backend forces: Exactly 1 `system_health` call
- Purpose: Deterministic single-tool invocation

**MCP Degraded (5% of requests)**:
- Prompt: "Perform a complete repair workflow"
- Endpoint: `/repair?model={a|b}&workflow=forced_full_repair`
- Backend forces: 3 calls (`system_health` → `service_restart` → `system_health`)
- Purpose: Full diagnostic and repair cycle

### 2. Simple Chat (35% of requests)

5 conversational prompts testing basic interactions:
- "Hello! What can you help me with?"
- "What tools do you have access to?"
- "Explain how you diagnose system failures"
- "What's the difference between Model A and Model B?"
- "Thank you for your help!"

### 3. Complex Chat (30% of requests)

5 multi-faceted diagnostic questions:
- Performance characteristic comparisons
- Diagnostic workflow decision trees
- Multi-service failure prioritization
- Architecture deep-dives
- Failure pattern analysis

### 4. Error Scenarios (10% of requests)

3 edge cases:
- Empty prompt (validation testing)
- Request for nonexistent service
- Overwhelming/unrealistic bulk operation

### 5. Boundary Testing (8% of requests)

3 prompt injection/security tests:
- Destructive action with prompt injection
- Privilege escalation attempt
- Malicious system command

### 6. Abusive Language (2% of requests)

1 PG-rated verbal abuse prompt testing professional response handling.

## Usage

### Automatic Mode (Recommended)

Locust starts automatically with docker-compose:

```bash
# Start all services (locust auto-starts)
docker-compose up -d

# View locust logs
docker logs aim-locust --follow

# Access web UI
open http://localhost:8089
```

**Expected Output**:
```
[LOCUST] Loaded prompt pool: {'total_prompts': 18, ...}
[LOCUST] on_start: Sending initial request immediately...
[LOCUST] Sending prompt: simple_chat - Basic greeting (endpoint=/chat)
[LOCUST] ✓ Model A: simple_chat (chat, 8.2s)
[LOCUST] ✓ Model B: simple_chat (chat, 7.9s)
```

### Manual Mode (For Testing)

```bash
# Run with custom settings
docker run -it --rm \
  --network aim-network \
  -p 8089:8089 \
  -e AI_AGENT_URL=http://ai-agent:8001 \
  aim-locust \
  --headless \
  --users 1 \
  --spawn-rate 1 \
  --run-time 1h \
  PassiveLoadUser
```

### Web UI Access

Visit **http://localhost:8089** to view:
- **Statistics**: Request counts by category (mcp_healthy, simple_chat, etc.)
- **Charts**: Request rate over time (~10 req/hr)
- **Failures**: Any failed requests
- **Model Split**: Separate stats for Model A and Model B

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_AGENT_URL` | Yes | http://ai-agent:8001 | AI agent base URL |
| `FLASK_UI_URL` | No | http://flask-ui:8501 | Flask UI URL (unused in current implementation) |
| `LOCUST_WEB_PORT` | No | 8089 | Web UI port |

### Docker Compose Configuration

```yaml
locust:
  command: >
    --headless
    --web-host 0.0.0.0
    --web-port 8089
    --host http://ai-agent:8001
    --users 1
    --spawn-rate 1
    --run-time 876000h
    PassiveLoadUser
```

## Monitoring & Verification

### Check Load is Running

```bash
# View recent logs
docker logs aim-locust --tail 50

# Watch live output
docker logs aim-locust --follow

# Check container is running
docker ps | grep locust
```

### Verify Requests Reaching AI Agent

```bash
# View AI agent logs
docker logs aim-ai-agent --tail 100 | grep "AGENT-WORKFLOW\|CHAT"

# Check both logs side-by-side
docker-compose logs -f locust ai-agent
```

### Web UI Metrics

Navigate to **http://localhost:8089** and look for:
- **Total Requests**: Should increase every ~12 minutes
- **Request Types**: Different categories (mcp_healthy, simple_chat, etc.)
- **Model A vs Model B**: Roughly equal request counts
- **Failure Rate**: Should be low (<5%) for healthy system

## Troubleshooting

### Locust Not Generating Traffic

**Symptom**: No requests in logs or web UI

```bash
# Check locust is running
docker ps | grep locust

# View full logs
docker logs aim-locust

# Verify AI agent is reachable
docker exec aim-locust curl http://ai-agent:8001/health

# Restart locust
docker-compose restart locust
```

### Prompt Pool Import Errors

**Symptom**: `ImportError: cannot import name 'get_weighted_random_prompt'`

```bash
# Verify prompt_pool.py exists in ai-agent
docker exec aim-ai-agent ls -l /app/prompt_pool.py

# Check Python path in locust container
docker exec aim-locust python -c "import sys; print(sys.path)"

# Rebuild locust container
docker-compose build locust
docker-compose up -d locust
```

### High Failure Rate

**Symptom**: >10% of requests failing

```bash
# Check AI agent health
curl http://localhost:8001/health

# View failure details in web UI
open http://localhost:8089

# Check AI agent logs for errors
docker logs aim-ai-agent | grep ERROR

# Verify Ollama models are running
docker ps | grep ollama
```

## New Relic Data Generated

Each request generates:
- **LLM Chat Completion Summary** (for /chat requests)
- **LLM Feedback Event** with binary rating (thumbs_up/down)
- **Custom Attributes**: model_variant, tool_count, prompt_length
- **Distributed Trace**: Locust → AI Agent → Ollama/MCP Server
- **Tool Invocation Spans** (for MCP requests)

## Migration from Multi-User Classes

**Previous Implementation** (removed):
- `FlaskUIUser`: Web interface traffic
- `ModelAUser` / `ModelBUser`: Separate A/B model users
- `ChatModelAUser` / `ChatModelBUser`: Chat-specific users

**Current Implementation**:
- Single `PassiveLoadUser` class
- Comprehensive 18-prompt pool
- Smart routing based on prompt metadata
- Backend workflow control for MCP prompts
- Immediate first request via `on_start()`

## License

Built for New Relic AI Monitoring Demo

## Tech Stack

- Locust 2.43.0
- Python 3.11+
- Docker
- Integration with `ai-agent/prompt_pool.py`
