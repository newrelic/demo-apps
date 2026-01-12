# AI Agent - Autonomous Tool Execution Agent

Autonomous reasoning engine powered by **LangChain** that executes multi-step system operations using LLM-based tool calling and A/B model comparison with enhanced New Relic observability.

## Features

- **Autonomous Tool Workflows**: Executes multi-step system operations through intelligent tool orchestration
- **LangChain Integration**: Native LangChain agent with Ollama and MCP tool support
- **Dual Model Support**: A/B testing with two LLM models (mistral:7b-instruct and ministral-3:8b-instruct-2512-q8_0)
- **Backend Workflow Control**: Deterministic tool invocations via workflow parameters
- **MCP Tool Calling**: Integrates with MCP server for generic system operation tools
- **LLM Feedback Events**: Automatic binary rating generation with smart heuristics
- **Token Counting**: tiktoken-based client-side token counting for accurate metrics
- **Metrics Collection**: Tracks performance metrics for model comparison
- **Chat Interface**: Interactive chat with system prompts and tool integration
- **New Relic Instrumentation**: Full APM monitoring with distributed tracing

## Architecture

### Technology Stack

- **Framework**: FastAPI 0.128.0 + uvicorn 0.40.0
- **AI Engine**: LangChain 0.3.11 (LLM agent framework)
- **Ollama Integration**: langchain-openai 0.2.14 (using OpenAI-compatible API)
- **Token Counting**: tiktoken 0.8.0 (client-side token counting)
- **Community Tools**: langchain-community 0.3.12
- **HTTP Client**: httpx 0.28.1 (async)
- **Data Validation**: Pydantic 2.12.5
- **Monitoring**: New Relic Python Agent 11.2.0
- **Deployment**: Docker + uvicorn ASGI server

### Project Structure

```
ai-agent/
├── app.py                  # FastAPI application and endpoints
├── langchain_agent.py      # LangChain agent implementation (ReAct pattern)
├── mcp_tools.py            # MCP tool integration for LangChain
├── observability.py        # New Relic LLM feedback events & token counting
├── workflows.py            # Backend-controlled workflow definitions
├── prompt_pool.py          # 18-prompt comprehensive testing pool
├── cache.py                # Caching utilities for agent responses
├── models.py               # Pydantic models for requests/responses
├── prompts.py              # System prompts for tool execution and chat modes
├── requirements.txt        # Python dependencies (LangChain stack)
├── Dockerfile              # Container configuration
└── newrelic.ini            # New Relic APM configuration
```

### Internal Architecture

```
Flask UI          AI Agent         LangChain        Ollama A/B       MCP Server
   |                 |               Router              |                 |
   |--POST /repair-->|                 |                 |                 |
   |  workflow=      |--select_model()->|                |                 |
   |  minimal_single |                 |--generate()---->|                 |
   |                 |                 |<--response------|                 |
   |                 |--call_tool()----|-----------------|--system_health->|
   |                 |                 |                 |<--status--------|
   |                 |--generate()-----|--analyze------->|                 |
   |                 |                 |<--action_plan---|                 |
   |                 |--record_feedback|                 |                 |
   |<--RepairResult--|                 |                 |                 |
```

**Key Components**:

1. **Model Router**: Selects between Model A and Model B based on query parameter
2. **LangChain Agent**: ReAct pattern agent with tool calling and reasoning
3. **MCP Tool Integration**: Native LangChain tool wrappers for MCP server calls
4. **Observability Layer**: New Relic feedback events, token counting, trace correlation
5. **Workflow Engine**: Backend-controlled tool invocations for deterministic testing
6. **Metrics Tracker**: In-memory storage for model performance metrics

## API Reference

### Endpoints

#### `POST /repair?model={a|b}&workflow={workflow_name}`
Trigger tool execution workflow with specified model and optional backend-controlled workflow.

**Query Parameters**:
- `model` (required): `"a"` for mistral:7b-instruct or `"b"` for ministral-3:8b-instruct-2512-q8_0
- `workflow` (optional): Backend workflow name (`minimal_single_tool`, `forced_full_repair`, etc.)
  - If specified: Backend forces specific tool sequence (deterministic)
  - If omitted: LLM decides tool usage (autonomous)

**Response**:
```json
{
  "success": true,
  "model_used": "mistral:7b-instruct-v0.3",
  "latency_seconds": 2.45,
  "actions_taken": [
    "Checked system health status",
    "Retrieved service logs",
    "Restarted api-gateway service",
    "Verified service health"
  ],
  "containers_restarted": ["api-gateway"],
  "final_status": "System is healthy",
  "tool_calls": [
    {
      "tool_name": "system_health",
      "arguments": {},
      "success": true,
      "result": "..."
    }
  ]
}
```

#### `POST /chat`
Interactive chat with the agent.

**Request**:
```json
{
  "message": "What is the current system status?",
  "model": "a"
}
```

**Response**:
```json
{
  "response": "The system is currently healthy. All services are running...",
  "model_used": "mistral:7b-instruct-v0.3",
  "latency_seconds": 0.52
}
```

#### `GET /health`
Health check and service status.

**Response**:
```json
{
  "status": "healthy",
  "service": "ai-agent",
  "version": "2.0.0-langchain",
  "uptime_seconds": 3600
}
```

#### `GET /status`
Detailed agent status with model information.

**Response**:
```json
{
  "status": "healthy",
  "models": {
    "model_a": {
      "url": "http://ollama-model-a:11434",
      "name": "mistral:7b-instruct-v0.3"
    },
    "model_b": {
      "url": "http://ollama-model-b:11434",
      "name": "ministral-3:8b-instruct-2512-q8_0"
    }
  },
  "mcp_server": "http://mcp-server:8002"
}
```

## Backend Workflow Control

The agent supports **deterministic tool invocations** via workflow parameters:

### Available Workflows

| Workflow | Description | Tool Sequence |
|----------|-------------|---------------|
| `minimal_single_tool` | Single health check | `system_health` (1 call) |
| `forced_full_repair` | Complete repair cycle | `system_health` → `service_restart` → `system_health` (3 calls) |
| `repair_deterministic` | Conditional repair | Health check, diagnose if needed, restart, verify |
| `repair_open_ended` | LLM-controlled | Agent decides tool sequence based on context |

**Usage**:
```bash
# Backend-controlled (deterministic)
curl -X POST "http://localhost:8001/repair?model=a&workflow=minimal_single_tool"

# LLM-controlled (autonomous)
curl -X POST "http://localhost:8001/repair?model=a"
```

## New Relic Observability

### LLM Feedback Events

Every AI request automatically generates a feedback event with binary rating:

**Smart Heuristics**:
- Failures → `thumbs_down` (100%)
- Very slow (>60s) → `thumbs_down` (80%)
- Very fast (<5s) → `thumbs_up` (90%)
- Multiple tools (2+) → `thumbs_up` (85%)
- Single tool call → `thumbs_up` (75%)
- No tools → `thumbs_up` (70%)

**Implementation**:
```python
# In langchain_agent.py:215-349
trace_id = newrelic.agent.current_trace_id()

rating, category, message = generate_feedback_rating(
    success=True,
    latency_seconds=2.34,
    tool_count=2,
    error=None
)

record_feedback_event(
    trace_id=trace_id,
    rating=rating,  # "thumbs_up" or "thumbs_down"
    category=category,
    message=message,
    metadata={'model_variant': 'a', 'tool_count': 2, ...}
)
```

### Token Count Callback

Custom tiktoken-based callback registered for accurate token tracking:

```python
# In app.py:76-85
application = newrelic.agent.register_application(timeout=10.0)
newrelic.agent.set_llm_token_count_callback(token_count_callback, application=application)

# In observability.py:46-103
def token_count_callback(model: str, content: Any) -> int:
    """
    New Relic calls this with message content (strings) to count tokens.
    We use tiktoken with cl100k_base encoding for accurate token counts.
    """
    encoder = _get_tiktoken_encoder(model)
    return len(encoder.encode(content))
```

## Dependencies

### Upstream Services
- **ollama-model-a** (Port 11434): Mistral 7B Instruct model for reliable reasoning
- **ollama-model-b** (Port 11435): Ministral 3:8b q8_0 model for efficient reasoning
- **mcp-server** (Port 8002): Tool interface for system operations

### Downstream Services
- **flask-ui** (Port 8501): User interface consuming agent APIs
- **locust** (Port 8089): Passive load generation with prompt pool

## Local Development

### Prerequisites

- Python 3.11+
- Running Ollama services (Model A and Model B)
- Running MCP server

### Running Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OLLAMA_MODEL_A_URL=http://localhost:11434
export OLLAMA_MODEL_B_URL=http://localhost:11435
export MODEL_A_NAME=mistral:7b-instruct-v0.3
export MODEL_B_NAME=ministral-3:8b-instruct-2512-q8_0
export MCP_SERVER_URL=http://localhost:8002
export AGENT_PORT=8001

# Run service
python app.py
```

### Testing

```bash
# Test agent health
curl http://localhost:8001/health

# Test backend-controlled workflow
curl -X POST "http://localhost:8001/repair?model=a&workflow=minimal_single_tool"

# Test autonomous workflow
curl -X POST "http://localhost:8001/repair?model=b"

# Test chat
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the system status?", "model": "a"}'

# Test status
curl http://localhost:8001/status
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_MODEL_A_URL` | Yes | - | URL for Model A Ollama instance |
| `OLLAMA_MODEL_B_URL` | Yes | - | URL for Model B Ollama instance |
| `MODEL_A_NAME` | Yes | - | Model name (e.g., mistral:7b-instruct-v0.3) |
| `MODEL_B_NAME` | Yes | - | Model name (e.g., ministral-3:8b-instruct-2512-q8_0) |
| `MCP_SERVER_URL` | Yes | - | MCP server URL for tool calling |
| `AGENT_PORT` | No | 8001 | Port to run agent service |
| `NEW_RELIC_LICENSE_KEY` | No | - | New Relic ingest license key |
| `NEW_RELIC_APP_NAME` | No | aim-demo_ai-agent | Application name for APM |

## Troubleshooting

### Agent Not Responding

**Symptom**: Tool execution requests hang or timeout

```bash
# Check agent logs
docker logs aim-ai-agent

# Verify agent is running
curl http://localhost:8001/health

# Check upstream dependencies
curl http://localhost:11434/api/tags  # Model A
curl http://localhost:11435/api/tags  # Model B
curl http://localhost:8002/health     # MCP Server
```

### Model Timeout Errors

**Symptom**: `HTTPException: Model timeout` in logs

```bash
# Check Ollama model health
docker logs aim-ollama-model-a
docker logs aim-ollama-model-b

# Verify model memory
docker stats aim-ollama-model-a aim-ollama-model-b

# Restart Ollama services
docker-compose restart ollama-model-a ollama-model-b
```

### MCP Tool Call Failures

**Symptom**: Tool execution workflow fails

```bash
# Check MCP server health
curl http://localhost:8002/health

# View MCP server logs
docker logs aim-mcp-server

# Restart MCP server
docker-compose restart mcp-server

## Tech Stack

- LangChain 0.3.11
- langchain-openai 0.2.14 (using Ollama's OpenAI-compatible API)
- tiktoken 0.8.0 (token counting)
- langchain-community 0.3.12
- FastAPI 0.128.0
- httpx 0.28.1
- Pydantic 2.12.5
- New Relic Python Agent 11.2.0
- uvicorn 0.40.0
