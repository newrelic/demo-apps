# AI Agent - Autonomous Tool Execution Agent

Autonomous reasoning engine powered by PydanticAI that executes multi-step system operations using LLM-based tool calling and A/B model comparison.

## Features

- **Autonomous Tool Workflows**: Executes multi-step system operations through intelligent tool orchestration
- **Dual Model Support**: A/B testing with two LLM models (mistral:7b-instruct and ministral-3:8b-instruct-2512-q8_0)
- **MCP Tool Calling**: Integrates with MCP server for generic system operation tools
- **Metrics Collection**: Tracks performance metrics for model comparison
- **Chat Interface**: Interactive chat with system prompts and tool integration
- **New Relic Instrumentation**: Full APM monitoring with distributed tracing

## Architecture

### Technology Stack

- **Framework**: FastAPI 0.128.0 + uvicorn 0.40.0
- **AI Engine**: PydanticAI 1.39.1 (LLM agent framework)
- **HTTP Client**: httpx 0.28.1 (async)
- **Data Validation**: Pydantic 2.12.5
- **Monitoring**: New Relic Python Agent 11.2.0
- **Deployment**: Docker + uvicorn ASGI server

### Project Structure

```
ai-agent/
├── app.py               # FastAPI application and endpoints
├── agent.py             # PydanticAI agent implementation
├── models.py            # Pydantic models for requests/responses
├── prompts.py           # System prompts for tool execution and chat modes
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
└── newrelic.ini         # New Relic APM configuration
```

### Internal Architecture

```
Flask UI          AI Agent         Model Router      Ollama A/B       MCP Server
   |                 |                 |                 |                 |
   |--POST /tools--->|                 |                 |                 |
   |                 |--select_model()->|                 |                 |
   |                 |                 |--generate()---->|                 |
   |                 |                 |<--response------|                 |
   |                 |--call_tool()----|-----------------|--system_health->|
   |                 |                 |                 |<--status--------|
   |                 |--generate()-----|--analyze------->|                 |
   |                 |                 |<--action_plan---|                 |
   |                 |--call_tool()----|-----------------|--service_restart|
   |<--ToolResult----|                 |                 |                 |
```

**Key Components**:

1. **Model Router**: Selects between Model A and Model B based on query parameter
2. **PydanticAI Agent**: Orchestrates reasoning, tool calls, and response generation
3. **MCP Client**: HTTP client for calling MCP server tools
4. **Metrics Tracker**: In-memory storage for model performance metrics

## API Reference

### Endpoints

#### `POST /repair?model={a|b}`
Trigger tool execution workflow with specified model.

**Query Parameters**:
- `model` (required): `"a"` for mistral:7b-instruct or `"b"` for ministral-3:8b-instruct-2512-q8_0

**Response**:
```json
{
  "success": true,
  "model": "mistral:7b-instruct",
  "latency_seconds": 2.45,
  "reasoning": "Detected api-gateway service degraded...",
  "actions_taken": [
    "Checked system health status",
    "Retrieved service logs",
    "Restarted api-gateway service",
    "Verified service health"
  ],
  "final_status": "healthy",
  "tools_used": ["check_system_health", "get_service_logs", "restart_service"]
}
```

#### `POST /repair/compare`
Run tool execution workflow with both models and compare results.

**Response**:
```json
{
  "model_a": { /* RepairResult */ },
  "model_b": { /* RepairResult */ },
  "comparison": {
    "faster_model": "ministral-3:8b-instruct-2512-q8_0",
    "latency_difference": 0.3
  }
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
  "response": "The system is currently healthy. All 8 containers are running...",
  "model": "mistral:7b-instruct",
  "latency_seconds": 0.52
}
```

#### `GET /status`
Health check and agent status.

**Response**:
```json
{
  "status": "healthy",
  "uptime_seconds": 3600,
  "models": {
    "model_a": "http://ollama-model-a:11434",
    "model_b": "http://ollama-model-b:11434"
  }
}
```

#### `GET /metrics`
Detailed performance metrics for both models.

**Response**:
```json
{
  "model_a": {
    "total_requests": 42,
    "successful_requests": 40,
    "failed_requests": 2,
    "average_latency_seconds": 1.23,
    "success_rate": 0.95
  },
  "model_b": {
    "total_requests": 38,
    "successful_requests": 37,
    "failed_requests": 1,
    "average_latency_seconds": 0.87,
    "success_rate": 0.97
  }
}
```

## Dependencies

### Upstream Services
- **ollama-model-a** (Port 11434): Mistral 7B Instruct model for reliable reasoning
- **ollama-model-b** (Port 11435): Phi-3 Mini model for efficient reasoning
- **mcp-server** (Port 8002): Tool interface for Docker and Locust control

### Downstream Services
- **flask-ui** (Port 8501): User interface consuming agent APIs

### External Dependencies
None - all dependencies are internal services

## Local Development

### Prerequisites

- Python 3.11+
- Running Ollama services (Model A and Model B)
- Running MCP server
- Docker (for target containers)

### Running Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OLLAMA_MODEL_A_URL=http://localhost:11434/v1
export OLLAMA_MODEL_B_URL=http://localhost:11435/v1
export MODEL_A_NAME=mistral:7b-instruct
export MODEL_B_NAME=ministral-3:8b-instruct-2512-q8_0
export MCP_SERVER_URL=http://localhost:8002
export AGENT_PORT=8001

# Run service
python app.py
```

**Expected Output**:
```
====================================================================
🤖 AI Agent Service Starting
====================================================================
Model A: mistral:7b-instruct at http://ollama-model-a:11434/v1
Model B: ministral-3:8b-instruct-2512-q8_0 at http://ollama-model-b:11434/v1
MCP Server: http://mcp-server:8002
====================================================================
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
```

### Testing

```bash
# Test agent health
curl http://localhost:8001/status

# Test tool execution workflow
curl -X POST "http://localhost:8001/repair?model=a"

# Test chat
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the system status?", "model": "a"}'

# Test metrics
curl http://localhost:8001/metrics
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OLLAMA_MODEL_A_URL` | Yes | - | URL for Model A Ollama instance |
| `OLLAMA_MODEL_B_URL` | Yes | - | URL for Model B Ollama instance |
| `MODEL_A_NAME` | Yes | - | Model name (e.g., mistral:7b-instruct) |
| `MODEL_B_NAME` | Yes | - | Model name (e.g., ministral-3:8b-instruct-2512-q8_0) |
| `MCP_SERVER_URL` | Yes | - | MCP server URL for tool calling |
| `AGENT_PORT` | No | 8001 | Port to run agent service |
| `NEW_RELIC_LICENSE_KEY` | No | - | New Relic ingest license key |
| `NEW_RELIC_APP_NAME` | No | - | Application name for APM |

### System Prompts

System prompts are defined in `prompts.py`:

- **REPAIR_SYSTEM_PROMPT**: Instructions for autonomous tool execution workflow
- **CHAT_SYSTEM_PROMPT**: Instructions for interactive chat mode

Both prompts include:
- Available MCP tools and their usage
- Expected workflow (check → diagnose → execute → verify)
- Constraints (safe operations, prefer graceful actions)

## Troubleshooting

### Service-Specific Issues

#### Agent Not Responding

**Symptom**: Tool execution requests hang or timeout

**Diagnosis**:
```bash
# Check agent logs
docker logs aim-ai-agent

# Verify agent is running
curl http://localhost:8001/status

# Check upstream dependencies
curl http://localhost:11434/api/tags  # Model A
curl http://localhost:11435/api/tags  # Model B
curl http://localhost:8002/health     # MCP Server
```

**Solutions**:
```bash
# Restart agent
docker-compose restart ai-agent

# Check for memory issues (see root README Troubleshooting)
docker stats --no-stream aim-ai-agent
```

#### Model Timeout Errors

**Symptom**: `HTTPException: Model timeout` in logs

**Cause**: Ollama model taking too long to respond (>30s)

**Solutions**:
```bash
# Check Ollama model health
docker logs aim-ollama-model-a
docker logs aim-ollama-model-b

# Verify model memory (see root README for Ollama troubleshooting)
docker stats aim-ollama-model-a aim-ollama-model-b

# Restart Ollama services
docker-compose restart ollama-model-a ollama-model-b
```

#### MCP Tool Call Failures

**Symptom**: Tool execution workflow fails with "Tool call failed" error

**Diagnosis**:
```bash
# Check MCP server health
curl http://localhost:8002/health

# View MCP server logs
docker logs aim-mcp-server

# Test tool directly
curl -X POST http://localhost:8002/tools/docker_ps
```

**Solutions**:
```bash
# Restart MCP server
docker-compose restart mcp-server

# Verify Docker socket access (MCP server needs /var/run/docker.sock)
docker inspect aim-mcp-server | grep -A5 "Mounts"
```

#### Metrics Not Updating

**Symptom**: `/metrics` endpoint shows stale data

**Cause**: Metrics are stored in-memory and reset on restart

**Solution**: Metrics are ephemeral by design. For persistent metrics, integrate with New Relic APM or add database storage.

### Debugging

```bash
# View live logs
docker logs -f aim-ai-agent

# Access container shell
docker exec -it aim-ai-agent /bin/bash

# Test agent endpoints
curl http://localhost:8001/status
curl http://localhost:8001/metrics

# Check New Relic instrumentation
docker logs aim-ai-agent | grep -i newrelic
```

## Production Recommendations

### Security

1. **API Rate Limiting**: Add rate limiting to prevent abuse
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)

   @app.post("/repair")
   @limiter.limit("10/minute")
   async def repair_endpoint(...):
       ...
   ```

2. **Authentication**: Add API key or JWT authentication for production
   ```python
   from fastapi.security import APIKeyHeader
   api_key_header = APIKeyHeader(name="X-API-Key")
   ```

3. **Input Validation**: Validate all user inputs (model parameter, chat messages)
   - Already implemented via Pydantic models

### Performance

1. **Connection Pooling**: Use httpx connection pooling for MCP calls
   ```python
   # Already implemented in agent.py
   client = httpx.AsyncClient()
   ```

2. **Caching**: Cache frequent tool call results (e.g., container status)
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=100, ttl=5)
   def get_container_status():
       ...
   ```

3. **Async Tool Calls**: Parallelize independent tool calls
   ```python
   import asyncio
   results = await asyncio.gather(
       call_tool("check_system_health"),
       call_tool("get_service_logs", {"service": "api-gateway"})
   )
   ```

### Monitoring

1. **Custom Metrics**: Add New Relic custom events
   ```python
   import newrelic.agent

   newrelic.agent.record_custom_event('AIToolWorkflow', {
       'model': model_name,
       'success': result.success,
       'latency_seconds': result.latency_seconds
   })
   ```

2. **Error Tracking**: Log all exceptions with context
   ```python
   import logging
   logger.error(f"Tool execution failed: {e}", extra={'model': model, 'user_id': user_id})
   ```

3. **Health Checks**: Implement comprehensive health check
   ```python
   @app.get("/health")
   async def health_check():
       # Check Ollama connectivity
       # Check MCP server connectivity
       # Check memory usage
       return {"status": "healthy", "checks": {...}}
   ```

### Scalability

1. **Horizontal Scaling**: Run multiple agent instances
   - Stateless design supports load balancing
   - Consider external metrics storage (Redis, PostgreSQL)

2. **Queue-Based Workflows**: Use message queue for tool execution requests
   ```python
   # Add Celery or RabbitMQ for async workflow processing
   from celery import Celery
   app = Celery('ai-agent')

   @app.task
   def async_tool_workflow(model: str):
       ...
   ```

3. **Model Selection Strategy**: Implement intelligent model routing
   - Route simple tasks to faster Model B
   - Route complex tasks to more accurate Model A
   - Use past performance metrics for routing decisions

## License

Built for New Relic AI Monitoring Demo

## Tech Stack

- PydanticAI 1.39.1
- FastAPI 0.128.0
- httpx 0.28.1
- Pydantic 2.12.5
- New Relic Python Agent 11.2.0
- uvicorn 0.40.0
