# MCP Server - Model Context Protocol Tool Interface

FastMCP server that exposes Docker container management and Locust load testing as tools for the AI agent via the Model Context Protocol.

## Features

- **Docker Container Management**: List, inspect, restart, and read logs from Docker containers
- **Environment Variable Updates**: Modify container environment variables dynamically
- **Locust Integration**: Start, stop, and monitor load tests
- **HTTP API**: RESTful endpoints for all MCP tools
- **Docker Socket Access**: Direct control of Docker daemon
- **New Relic Instrumentation**: Full APM monitoring with distributed tracing

## Architecture

### Technology Stack

- **Framework**: FastAPI 0.128.0 + FastMCP 2.14.2
- **Docker Client**: docker 7.1.0 (Docker SDK for Python)
- **HTTP Client**: httpx 0.28.1 (for Locust API)
- **WebSockets**: websockets 15.0 (MCP protocol)
- **Server**: uvicorn 0.40.0 (ASGI)
- **Monitoring**: New Relic Python Agent 11.2.0
- **Deployment**: Docker with mounted Docker socket

### Project Structure

```
mcp-server/
├── server.py            # FastMCP server and FastAPI app
├── config.py            # Environment configuration
├── tools/
│   ├── docker_tools.py  # Docker container management tools
│   └── locust_tools.py  # Load testing control tools
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
└── newrelic.ini        # New Relic APM configuration
```

### Internal Architecture

```
AI Agent                MCP Server              Docker Socket
   |                        |                        |
   |--call_tool()---------->|                        |
   |   docker_ps()          |--docker.containers.--->|
   |                        |    list()              |
   |                        |<--container_list-------|
   |<--containers-----------|                        |
   |                        |                        |
   |--call_tool()---------->|                        |
   |   docker_restart()     |--container.restart()-->|
   |                        |<--success--------------|
   |<--result---------------|                        |

                            Locust API
                                |
   |--call_tool()---------->|                        |
   |   locust_start_test()  |--POST /swarm---------->|
   |                        |<--test_started---------|
   |<--result---------------|                        |
```

**Key Components**:

1. **FastMCP Server**: MCP protocol handler for agent-to-server communication
2. **Docker Client**: Manages Docker containers via socket
3. **Locust HTTP Client**: Controls load testing via Locust API
4. **FastAPI Wrapper**: Exposes tools as HTTP endpoints

## Tool Reference

### Docker Tools

#### `docker_container_list()`
List all Docker containers with their status.

**Returns**:
```python
[
  {
    "id": "abc123...",
    "name": "aim-ai-agent",
    "status": "running",
    "image": "aim-ai-agent:latest",
    "ports": {"8001/tcp": [{"HostPort": "8001"}]}
  },
  ...
]
```

#### `docker_logs(service_name: str, lines: int = 100)`
Read container logs.

**Parameters**:
- `service_name`: Container name (e.g., "api-gateway" or "auth-service")
- `lines`: Number of log lines to return (default: 100)

**Returns**: Log output as string

#### `docker_restart(service_name: str)`
Restart a container.

**Parameters**:
- `service_name`: Container name

**Returns**: Success/failure message

#### `docker_inspect(service_name: str)`
Get detailed container information.

**Parameters**:
- `service_name`: Container name

**Returns**: Full container configuration (env vars, mounts, network, etc.)

#### `docker_update_env(service_name: str, key: str, value: str)`
Update environment variable and restart container.

**Parameters**:
- `service_name`: Container name
- `key`: Environment variable name
- `value`: New value

**Returns**: Success/failure message

**Note**: This stops the container, updates docker-compose.yml, and restarts it.

### Locust Tools

#### `locust_start_test(users: int, spawn_rate: int, duration: int = 0)`
Start a load test.

**Parameters**:
- `users`: Number of concurrent users
- `spawn_rate`: Users spawned per second
- `duration`: Test duration in seconds (0 = run until stopped)

**Returns**:
```python
{
  "status": "started",
  "users": 10,
  "spawn_rate": 2,
  "duration": 60
}
```

#### `locust_get_stats()`
Get current load test statistics.

**Returns**:
```python
{
  "state": "running",
  "total_requests": 1234,
  "total_failures": 5,
  "requests_per_second": 25.3,
  "average_response_time": 45.2
}
```

#### `locust_stop_test()`
Stop the currently running load test.

**Returns**: Success message

## HTTP API Endpoints

All MCP tools are also exposed as REST endpoints:

- `POST /tools/check_system_health` - Check overall system health
- `POST /tools/get_service_logs` - Get service logs (body: `{"service": "api-gateway", "lines": 100}`)
- `POST /tools/restart_service` - Restart service (body: `{"service": "auth-service"}`)
- `POST /tools/check_database_status` - Check database connection and performance
- `POST /tools/update_configuration` - Update service config (body: `{"service": "api-gateway", "key": "VAR", "value": "val"}`)
- `POST /tools/run_diagnostics` - Run comprehensive system diagnostics
- `GET /health` - Health check

## Dependencies

### Upstream Services
None - MCP server provides generic system operation tools

### Downstream Services
- **ai-agent** (Port 8001): Main consumer of MCP tools

### External Dependencies
None - All tools return mock data for demonstration purposes

## Local Development

### Prerequisites

- Python 3.11+
- FastMCP framework
- New Relic Python Agent (optional)

### Running Standalone

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MCP_PORT=8002
export NEW_RELIC_LICENSE_KEY=your_license_key  # Optional
export NEW_RELIC_APP_NAME=aim-demo_mcp-server  # Optional

# Run service
python server.py
```

**Expected Output**:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8002 (Press CTRL+C to quit)
```

### Testing

```bash
# Test health
curl http://localhost:8002/health

# Test system operation tools
curl -X POST http://localhost:8002/tools/check_system_health

curl -X POST http://localhost:8002/tools/get_service_logs \
  -H "Content-Type: application/json" \
  -d '{"service": "api-gateway", "lines": 50}'

curl -X POST http://localhost:8002/tools/restart_service \
  -H "Content-Type: application/json" \
  -d '{"service": "auth-service"}'

curl -X POST http://localhost:8002/tools/check_database_status

curl -X POST http://localhost:8002/tools/run_diagnostics
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MCP_PORT` | No | 8002 | Port to run MCP server |
| `NEW_RELIC_LICENSE_KEY` | No | - | New Relic ingest license key |
| `NEW_RELIC_APP_NAME` | No | - | Application name for APM |

### Docker Socket Mount

The Dockerfile mounts the Docker socket:
```yaml
# In docker-compose.yml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro  # Read-only recommended
```

**Security Note**: Mounting the Docker socket gives the container significant control over the host. In production, consider:
- Read-only mount (`:ro`)
- Docker socket proxy (e.g., tecnativa/docker-socket-proxy)
- Least-privilege alternative (e.g., Docker API with restricted permissions)

## Troubleshooting

### Service-Specific Issues

#### Permission Denied for Docker Socket

**Symptom**: `PermissionError: [Errno 13] Permission denied: '/var/run/docker.sock'`

**Cause**: Container user doesn't have access to Docker socket

**Solutions**:
```bash
# On host: Add socket permissions (Linux)
sudo chmod 666 /var/run/docker.sock

# Or add user to docker group (Linux)
sudo usermod -aG docker $USER

# On macOS: Ensure Docker Desktop is running
# Socket permissions are managed by Docker Desktop
```

#### Docker Commands Failing

**Symptom**: `docker.errors.DockerException: Error while fetching server API version`

**Diagnosis**:
```bash
# Check if socket is mounted
docker exec aim-mcp-server ls -la /var/run/docker.sock

# Test Docker connectivity from inside container
docker exec aim-mcp-server python -c "import docker; print(docker.from_env().ping())"
```

**Solutions**:
```bash
# Verify mount in docker-compose.yml
docker-compose config | grep -A2 "mcp-server" | grep docker.sock

# Restart MCP server
docker-compose restart mcp-server

# Check Docker daemon is running
docker ps
```

#### Locust API Not Reachable

**Symptom**: `httpx.ConnectError: All connection attempts failed`

**Diagnosis**:
```bash
# Test Locust API directly
curl http://localhost:8089/stats/requests

# Check Locust container is running
docker-compose ps locust

# View Locust logs
docker logs aim-locust
```

**Solutions**:
```bash
# Restart Locust
docker-compose restart locust

# Verify network connectivity (should be on aim-network)
docker inspect aim-mcp-server | grep NetworkMode
docker inspect aim-locust | grep NetworkMode
```

### Debugging

```bash
# View live logs
docker logs -f aim-mcp-server

# Access container shell
docker exec -it aim-mcp-server /bin/bash

# Test MCP server health
curl http://localhost:8002/health

# Test specific tools
curl -X POST http://localhost:8002/tools/docker_ps

# Check New Relic instrumentation
docker logs aim-mcp-server | grep -i newrelic
```

## Production Recommendations

### Security

1. **Docker Socket Proxy**: Use a proxy instead of direct socket mount
   ```yaml
   # Use tecnativa/docker-socket-proxy
   docker-socket-proxy:
     image: tecnativa/docker-socket-proxy
     environment:
       CONTAINERS: 1
       SERVICES: 1
       TASKS: 1
     volumes:
       - /var/run/docker.sock:/var/run/docker.sock:ro
   ```

2. **Read-Only Socket**: Mount Docker socket as read-only
   ```yaml
   volumes:
     - /var/run/docker.sock:/var/run/docker.sock:ro
   ```

3. **Least Privilege**: Restrict Docker API permissions
   - Only expose necessary endpoints
   - Use Docker API authorization plugins
   - Consider Kubernetes RBAC for production

4. **Authentication**: Add API key authentication
   ```python
   from fastapi.security import APIKeyHeader
   api_key_header = APIKeyHeader(name="X-API-Key")
   ```

### Performance

1. **Connection Pooling**: Reuse Docker client connections
   ```python
   # Already implemented in server.py
   docker_client = docker.from_env()
   ```

2. **Async Operations**: Use async Docker library for better concurrency
   ```python
   import aiodocker
   docker = aiodocker.Docker()
   ```

3. **Caching**: Cache frequent queries (container list, stats)
   ```python
   from functools import lru_cache

   @lru_cache(maxsize=10, ttl=5)
   def get_container_list():
       ...
   ```

### Monitoring

1. **Custom Metrics**: Track tool usage
   ```python
   import newrelic.agent

   newrelic.agent.record_custom_metric('MCP/docker_restart/count', 1)
   ```

2. **Error Tracking**: Log Docker API errors
   ```python
   import logging
   logger.error(f"Docker restart failed: {e}", extra={'container': service_name})
   ```

3. **Health Checks**: Implement comprehensive health check
   ```python
   @app.get("/health")
   async def health_check():
       # Check Docker connectivity
       # Check Locust connectivity
       # Check disk space
       return {"status": "healthy", "checks": {...}}
   ```

### Scalability

1. **Horizontal Scaling**: Run multiple MCP server instances
   - Stateless design supports load balancing
   - All state is in Docker daemon and Locust

2. **Rate Limiting**: Protect against tool abuse
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)

   @app.post("/tools/docker_restart")
   @limiter.limit("10/minute")
   async def docker_restart(...):
       ...
   ```

3. **Timeouts**: Add timeouts to Docker operations
   ```python
   try:
       container.restart(timeout=10)
   except docker.errors.APIError as e:
       if "timeout" in str(e):
           logger.error("Container restart timed out")
   ```

## License

Built for New Relic AI Monitoring Demo

## Tech Stack

- FastMCP 2.14.2
- FastAPI 0.128.0
- docker 7.1.0
- httpx 0.28.1
- websockets 15.0
- New Relic Python Agent 11.2.0
- uvicorn 0.40.0
