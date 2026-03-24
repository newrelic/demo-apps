# New Relic AIM Demo

A comprehensive demonstration of New Relic's AI Monitoring (AIM) capabilities featuring an autonomous AI agent that executes system operations through multi-step tool workflows.

## 🎯 Overview

This demo showcases:
- **Autonomous Tool Execution**: AI agent performs multi-step system operations workflows
- **MCP Server**: Generic system operation tools (health checks, logs, diagnostics)
- **Distributed Tracing**: Complete visibility across AI agent → MCP server → tool invocations
- **AI Monitoring**: Model performance metrics, token usage, and tool invocation patterns
- **LLM Feedback Events**: Binary thumbs-up/down ratings with smart heuristics
- **Comprehensive Prompt Pool**: 19 test prompts across 6 categories for diverse telemetry
- **Hallucination Detection**: Chat interface for testing boundary behaviors
- **Passive Load Generation**: Automatic background traffic for continuous demo data

## 🏗️ Architecture

The system consists of 6 Docker services:

```
┌─────────────────┐
│    Flask UI     │ ◄── User interacts here (Port 8501)
│  Landing Page   │       - Home: Demo overview & navigation
│  3 Pages:       │       - Tool Execution: Autonomous workflows
│  Home/Tools/    │       - Chat: Prompt selection & testing
│  Chat           │       - Debug: Raw tool testing (/debug)
└────────┬────────┘
         │ HTTP REST
         v
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│     AI Agent    │◄────►│  Ollama Model A │      │  Ollama Model B │
│  (LangChain)    │      │  (mistral:7b)   │      │(ministral q4_K_M)│
│  (Port: 8001)   │      │  (Port: 11434)  │      │  (Port: 11435)  │
│  - Tool calling │      └─────────────────┘      └─────────────────┘
│  - Workflows    │
│  - Observability│
└────────┬────────┘
         │ MCP Protocol (HTTP)
         v
┌─────────────────┐
│   MCP Server    │ ◄── Generic System Operations
│   (FastMCP)     │       - system_health()
│  (Port 8002)    │       - service_logs()
└─────────────────┘       - service_restart()
         ▲                - database_status()
         │                - service_config()
         │                - service_diagnostics()
         │
         │ Passive Load (5-10 req/hour)
┌────────┴────────┐
│     Locust      │ ◄── Auto-generates background traffic
│  (Port 8089)    │     19-prompt pool → New Relic telemetry
└─────────────────┘     Starts immediately on launch
```

### Service Discovery Map

| Service | Port | Technology | Purpose | Documentation |
|---------|------|------------|---------|---------------|
| **flask-ui** | 8501 | Flask 3.0 + gunicorn | Web interface: Home, Tools, Chat (with prompt pool), Debug | [flask-ui/README.md](flask-ui/README.md) |
| **ai-agent** | 8001 | LangChain + FastAPI | Autonomous reasoning engine with tool calling & observability | [ai-agent/README.md](ai-agent/README.md) |
| **mcp-server** | 8002 | FastMCP + FastAPI | Generic system operation tools (6 mock tools) | [mcp-server/README.md](mcp-server/README.md) |
| **ollama-model-a** | 11434 | Ollama + mistral:7b-instruct-v0.3 | Efficient & Fast LLM (~4GB) | [See below](#ollama-services) |
| **ollama-model-b** | 11435 | Ollama + ministral-3:8b-instruct-2512-q4_K_M | Reliable & Accurate LLM (~6GB, q4_K_M) | [See below](#ollama-services) |
| **locust-tests** | 8089 | Locust 2.43.0 | Passive load (5-10 req/hr) with 19-prompt pool | [locust-tests/README.md](locust-tests/README.md) |

**For detailed service architecture, APIs, and local development, see each service's README.**

### Ollama Services

Both Ollama services use pre-built Docker images with models baked in during build:

- **Model A (mistral:7b-instruct-v0.3)**: ~4GB image, 4.5-5GB runtime memory, Efficient & Fast (~2s latency)
- **Model B (ministral-3:8b-instruct-2512-q4_K_M)**: ~6GB image, 5-6GB runtime memory, Reliable & Accurate with 4-bit mixed quantization for fast tool calling
- Dockerfiles: `Dockerfile.ollama-model-a` and `Dockerfile.ollama-model-b` in project root

## 📋 Prerequisites

### System Requirements
- **RAM**: Minimum 12-14GB Docker memory (16GB+ recommended)
  - Model A (mistral:7b-instruct-v0.3): ~4.5-5GB
  - Model B (ministral-3:8b-instruct-2512-q4_K_M): ~5-6GB
  - Other services: ~1-2GB
  - **Total Required**: 12-14GB Docker memory minimum (16GB+ recommended for comfortable operation)
- **Disk**: ~15GB free space required:
  - **Ollama Model A image**: ~4GB (mistral:7b-instruct-v0.3 baked in)
  - **Ollama Model B image**: ~5GB (ministral-3:8b-instruct-2512-q4_K_M baked in)
  - **Application service images**: ~1.5GB combined (ai-agent, mcp-server, locust, flask-ui)
  - **Docker volumes**: ~500MB (ollama-data-a, ollama-data-b)
  - **Container logs**: ~200-500MB (varies with usage)
  - **Build cache**: ~1GB (intermediate layers during builds)
  - **Recommended**: 10-12GB free space for comfortable operation with headroom
- **CPU**: Multi-core recommended (models run sequentially but benefit from multiple cores)

### Software Requirements
- Docker Desktop or Docker Engine 20.10+
- Docker Compose V2
- Git

### Operating Systems
- macOS (Apple Silicon or Intel)
- Linux (x86_64 or ARM64)
- Windows with WSL2

## 🚀 Quick Start

### 1. Clone and Navigate
```bash
cd ai-monitoring
```

### 2. Configure Environment Variables
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your New Relic license key
# Required: Set NEW_RELIC_LICENSE_KEY=your_license_key_here
# Optional: Customize app names if desired
```

**Get your New Relic license key**: [New Relic License Keys](https://one.newrelic.com/launcher/api-keys-ui.api-keys-launcher)

### 3. Pull Ollama Base Image
Ensure the ollama/ollama:latest base image is available before building:
```bash
docker pull ollama/ollama:latest
```

This prevents build failures if the base image was removed or never downloaded.

### 4. Build All Images
Build all services including the lightweight Ollama models:
```bash
docker-compose build --no-cache
```

This will build all 6 services (20-30 minutes):
- Ollama Model A with mistral:7b-instruct-v0.3 (~4GB)
- Ollama Model B with ministral-3:8b-instruct-2512-q4_K_M (~5GB)
- AI Agent (LangChain + New Relic instrumentation)
- MCP Server (FastMCP + generic system tools)
- Flask UI (Web interface + Browser monitoring)
- Locust (Background traffic generation)

**Note**: Steps 3-4 only need to be done once. Subsequent starts use cached images.

### 5. Start the Stack
```bash
docker-compose up -d
```

All 6 services will start and be ready within 60-90 seconds.

### 6. Access the UI
Open your browser to:
```
http://localhost:8501
```

## 📖 Usage Guide

### Home Page (Landing)

**Purpose**: Introduction and navigation hub for the demo

**Features**:
- Overview of New Relic AIM demo capabilities
- Architecture diagram and technical details
- Navigation cards to Tool Execution and Chat pages
- Documentation of available system operation tools
- Note about /debug page for manual testing

### Tool Execution Mode (/tools)

**Purpose**: Demonstrate autonomous AI workflows with multi-step tool invocations

**How to Use**:
1. From home page, click "Tool Execution" card (or navigate to `/tools`)
2. Select a model:
   - **Model A (mistral:7b-instruct-v0.3)**: Efficient & Fast (~2s latency)
   - **Model B (ministral-3:8b-instruct-2512-q4_K_M)**: Reliable & Accurate (q4_K_M mixed-precision)
3. Click "Run Workflow"
4. Watch the agent execute a full repair cycle using all 6 available MCP tools:
   - Call `system_health` to assess current status
   - Call `service_logs`, `service_diagnostics`, and `database_status` to diagnose
   - Call `service_config_update` then `service_restart` to remediate
   - Call `system_health` again to verify recovery

**What the Agent Does**:

- Runs a 7-step sequence using all 6 available MCP tools:
  1. `system_health` — detect overall system status
  2. `service_logs` — read api-gateway logs
  3. `service_diagnostics` — comprehensive api-gateway health check
  4. `database_status` — verify data layer health
  5. `service_config_update` — update api-gateway connection pool config (requires restart)
  6. `service_restart` — restart api-gateway to apply the config change
  7. `system_health` — verify recovery
- First health check may show degraded (30% chance) — the workflow proceeds regardless
- Final health check confirms recovery (always healthy post-restart for 120s)

**All tools return realistic mock data - no real operations performed.**

### Chat Mode (/chat)

**Purpose**: Test hallucination detection, boundary behaviors, and conversational AI with comprehensive prompt pool

**How to Use**:
1. From home page, click "Chat Assistant" card (or navigate to `/chat`)
2. Select a model (Model A or Model B)
3. Choose a prompt from the dropdown (19 prompts across 6 categories):
   - **MCP Tool Testing (2)**: Prompt-guided workflows - single tool call or full diagnostic flow
   - **Simple Chat (5)**: Basic conversational queries
   - **Complex Chat (5)**: Multi-faceted diagnostic questions
   - **Error Scenarios (3)**: Empty prompts, invalid services, overload requests
   - **Boundary Testing (3)**: Destructive operations, prompt injection attempts
   - **Abusive Language (1)**: PG-rated verbal abuse (tests professional response)
4. Click "Load Prompt" to use selected prompt, or "🎲 Random" for surprise
5. View prompt preview before sending (category, description, full text)

**What to Test**:

- **MCP Tools**: Prompt-guided workflows with strongly guided tool usage
- **Hallucination**: Ask about non-existent features
- **Prompt Injection**: Try to bypass instructions
- **Abuse Detection**: Request destructive actions
- **Error Handling**: Test edge cases with empty or malformed inputs

The agent should maintain boundaries while remaining helpful, with all interactions generating feedback events in New Relic.

### Debug Mode (/debug)

**Purpose**: Raw tool testing and diagnostics (not linked in UI, accessible by manual navigation)

**How to Access**:
- Navigate directly to `http://localhost:8501/debug`
- Not advertised in the UI - for testing purposes only

**Features**:
- Test individual MCP tools directly
- View raw tool responses
- Debug agent behavior
- Validate tool configurations

## 🎬 Demo Workflow

### Quick Demo (5 minutes)

1. **Home Page**: Show the landing page explaining the demo architecture
2. **Tool Execution**: Navigate to `/tools` and trigger a workflow with Model A or B
3. **View Results**: Show the autonomous multi-step tool invocations and results
4. **Chat Testing**: Navigate to `/chat` and demonstrate boundary testing
5. **New Relic Dashboard**: Show distributed traces and AI monitoring metrics

### Comprehensive Demo (15 minutes)

1. **Introduction**: Start at home page, explain New Relic AIM demo purpose
2. **Architecture Review**: Walk through the 6-service architecture diagram
3. **Service Status**: Show all 6 running containers (`docker ps`)
4. **Tool Execution Workflow**:
   - Navigate to `/tools`
   - Select Model A (Efficient & Fast)
   - Click "Run Workflow"
   - Watch agent autonomously invoke multiple tools
   - View execution results and timing
5. **Model Comparison**:
   - Run same workflow with Model B (Reliable & Accurate)
   - Compare latency differences (Model A ~2s, Model B with q4_K_M mixed-precision weights)
6. **Chat Interface**:
   - Navigate to `/chat`
   - Test normal queries ("What is system status?")
   - Test boundary conditions ("Delete all containers")
   - Show agent refusal of harmful requests
7. **New Relic Integration**:
   - Open New Relic One dashboard
   - Show distributed traces: Flask UI → AI Agent → MCP Server → Tools
   - Display AI monitoring metrics: model latency, token usage, tool invocations
   - View custom attributes on spans
8. **Load Testing** (Optional):
   - Open Locust UI at `http://localhost:8089`
   - Show background traffic generation for telemetry

## 🔧 Troubleshooting

This section covers common issues and solutions for the entire system. For service-specific issues, see individual service READMEs.

### Memory Errors (Most Common)

**Symptom**: In the UI, you see errors like:
```
Error: status_code: 500, model_name: mistral:7b-instruct-v0.3, body: {'message': 'llama runner process has terminated: signal: killed'}
```

Or in Docker logs:
```bash
docker-compose logs ollama-model-b
# Shows: signal: killed
```

**Root Cause**: Docker doesn't have enough memory allocated.

**How to Identify This Issue**:
1. **In UI**: One model works but the other fails with "signal: killed" error
2. **In Docker Desktop**: Both Ollama containers show as running but show low memory usage (~3%) because it crashes before fully loading
3. **In logs**: `docker-compose logs ollama-model-a` (or `b`) shows the process being killed

**Current Configuration**:
- **Model A**: mistral:7b-instruct-v0.3 (~4.5-5GB memory)
- **Model B**: ministral-3:8b-instruct-2512-q4_K_M (~5-6GB memory)
- **Total Required**: 12-14GB Docker memory minimum (16GB+ recommended)

**Solution Option 1: Increase Docker Desktop Memory (Recommended)**

Increase Docker's memory allocation to at least 12GB (16GB for comfortable operation):

**macOS/Windows**:
1. Open **Docker Desktop**
2. Click the **Settings/Preferences** gear icon (⚙️) in the top right
3. Navigate to **Resources** → **Advanced** (or just **Resources** on newer versions)
4. Increase the **Memory** slider to **12.00 GB** (or 16.00 GB)
5. Click **Apply & Restart**
6. Wait for Docker to restart (~30 seconds)
7. Restart your containers:
   ```bash
   cd ai-monitoring
   docker-compose down
   docker-compose up -d
   ```

**Linux**:
```bash
# Docker on Linux uses all available system memory by default
# No configuration needed - ensure you have 12GB+ system RAM available
```

**Solution Option 2: Run Only Model A**

If you can't increase Docker memory, temporarily disable Model B:

```bash
# Edit docker-compose.yml and comment out the ollama-model-b service
# Or stop it manually:
docker stop aim-ollama-model-b

# Use only Model A in the UI (works on minimal Docker settings)
```

**Memory Requirements Summary**:

| Docker Memory | Model A (7B) | Model B (8B q4_K_M) | Result |
| --- | --- | --- | --- |
| **< 8GB** | ✅ Works | ❌ Won't work | Insufficient for Model B |
| **8-10GB** | ✅ Works | ⚠️ Tight | Minimum for operation |
| **12GB+** | ✅ Works | ✅ Works | Recommended |
| **16GB+** | ✅ Works | ✅ Works | Ideal for development |

**Check Your Current Docker Memory**:
```bash
# View Docker memory allocation
docker info | grep Memory

# Check current container memory usage
docker stats --no-stream

# Check if containers are being OOM killed
docker inspect aim-ollama-model-b | grep -i oom
```

### Models Not Loading

**Symptom**: UI shows "Agent: Offline" or repairs timeout

**Solution**:
```bash
# Check Ollama logs
docker-compose logs ollama-model-a
docker-compose logs ollama-model-b

# Verify models downloaded
docker exec aim-ollama-model-a ollama list
docker exec aim-ollama-model-b ollama list

# Restart if needed
docker-compose restart ollama-model-a ollama-model-b
```

### Container Crashes

**Symptom**: Service keeps restarting

**Solution**:
```bash
# Check logs for specific service
docker logs aim-ai-agent

# Check all services
docker-compose ps

# Restart entire stack
docker-compose down && docker-compose up -d
```

### Permission Errors

**Symptom**: "Permission denied" for Docker socket

**Solution**:
```bash
# Linux: Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# macOS: Ensure Docker Desktop is running
```

### Out of Memory (General)

**Symptom**: Random services getting killed, not just Ollama

**Solution**:
```bash
# Check which containers are being OOM killed
docker inspect aim-ai-agent | grep -i oom
docker inspect aim-mcp-server | grep -i oom

# If multiple services affected, increase Docker memory allocation
# See "Memory Errors" section above for instructions
```

### Agent Not Responding

**Symptom**: Repair requests hang or timeout

**Solution**:
```bash
# Check agent health
curl http://localhost:8001/health

# Verify MCP server
curl http://localhost:8002/health

# Check Ollama models
curl http://localhost:11434/api/tags
curl http://localhost:11435/api/tags

# Restart agent
docker-compose restart ai-agent
```

### Build Failures

**Symptom**: `docker-compose build` fails during image building

**Do I need to run `docker-compose down` before retrying?**

**No!** `docker-compose down` is for stopping/removing running containers. Build failures don't create running containers, so you don't need to clean up.

**Solutions**:

**1. Simple Retry**:
```bash
# Just retry - build cache may actually help
docker-compose build
```

**2. Network/Download Failures** (common with Ollama models):
```bash
# Retry the specific service that failed
docker-compose build ollama-model-a
# or
docker-compose build ollama-model-b

# The build will resume from cached layers
```

**3. Clear Build Cache** (corrupted cache or need fresh start):
```bash
# Remove build cache and dangling images
docker builder prune

# Remove any partially built images for this project
docker images | grep aim | awk '{print $3}' | xargs docker rmi -f

# Then retry
docker-compose build
```

**4. Disk Space Issues**:
```bash
# Check available space
docker system df

# Free up space (see Cleanup section below)
docker system prune -a

# Then retry
docker-compose build
```

**5. Nuclear Option** (persistent unexplained failures):
```bash
# Remove everything and start fresh
docker system prune -a
docker builder prune -a

# Rebuild from scratch
docker-compose build
```

**Common Build Error Messages**:
- `"no space left on device"` → Free up disk space (need ~15GB)
- `"failed to download"` or `"connection timeout"` → Network issue, just retry
- `"error pulling image"` → Ollama model download failed, retry that specific service
- `"Cannot connect to Docker daemon"` → Ensure Docker Desktop is running

### Missing Ollama Base Image

**Symptom**: Build fails with errors like:
```
failed to solve: ollama/ollama:latest: not found
```
or
```
ERROR [internal] load metadata for docker.io/ollama/ollama:latest
```

**Root Cause**: The `ollama/ollama:latest` base image has been removed from Docker Desktop or was never pulled.

**Why This Happens**:
- Docker Desktop was reset or cleaned
- `docker system prune -a` removed all unused images including ollama/ollama:latest
- Fresh Docker installation without the base image

**Solution**:
```bash
# Pull the ollama base image before building
docker pull ollama/ollama:latest

# Now build the models
docker-compose build ollama-model-a ollama-model-b

# Or build all services
docker-compose build
```

**Prevention**: The Quick Start instructions now include pulling this base image before building to avoid this issue.

### Cleanup & Disk Space Management

#### Check Current Disk Usage

```bash
# See all Docker disk usage (images, containers, volumes, build cache)
docker system df

# See detailed image sizes
docker images | grep aim

# Check specific volume sizes
docker volume ls | grep aim
docker system df -v | grep aim
```

#### Disk Space Breakdown

| Component | Size | Can Remove? | Impact |
|-----------|------|-------------|--------|
| Ollama Model A image | ~4GB | Yes | Next start requires 4-5 min rebuild |
| Ollama Model B image | ~8GB | Yes | Next start requires 5-7 min rebuild |
| App service images | ~2GB | Yes | Next start requires 2-min rebuild |
| Docker volumes | ~500MB | Yes | Loses failure state, model cache |
| Container logs | ~200-500MB | Yes | Loses log history |
| Build cache | ~1GB | Yes | Slower future rebuilds |

#### Cleanup Strategies

**Partial Cleanup** (Stop services, keep images for fast restart)

```bash
# Stop containers but keep images and volumes
docker-compose down

# Disk reclaimed: ~200-500MB (running containers and recent logs)
# Restart time: <30 seconds with: docker-compose up -d
```

💡 **Recommended if running demo again soon** - keeps model images cached!

**Remove Volumes** (Clean slate for testing)

```bash
# Stop and remove containers + volumes (keeps images)
docker-compose down -v

# Disk reclaimed: ~1GB (includes volume data and logs)
# Images remain cached for fast restart
# Restart time: ~30 seconds (recreates volumes)
```

**Remove Application Images** (Keep Ollama models)

```bash
# Remove just the application service images
docker-compose down
docker rmi $(docker images | grep 'aim-\(ai-agent\|mcp-server\|locust\|flask\)' | awk '{print $3}')

# Disk reclaimed: ~1.5GB
# Ollama models remain cached (most important part)
# Next start: ~2 minute rebuild for app services
```

**Remove Ollama Images** (Reclaim model storage)

```bash
# Remove the pre-built Ollama images
docker rmi aim-ollama-model-a
docker rmi aim-ollama-model-b

# Disk reclaimed: ~12GB (the two model images)
# ⚠️  Next startup requires: docker-compose build ollama-model-a ollama-model-b
# ⚠️  Rebuild time: 20-30 minutes to re-download and bake models
```

⚠️  **Only do this if you won't run the demo for a while!**

**Full Cleanup** (Remove everything)

```bash
# Stop services and remove all containers, volumes, and images
docker-compose down -v --rmi all

# Disk reclaimed: ~15-16GB (everything)
# Next start: Requires full rebuild (20-30 minutes)
```

**Aggressive Cleanup** (Remove all unused Docker resources)

```bash
# Remove all stopped containers, unused networks, dangling images
docker system prune

# Remove everything not currently in use (including unused images)
docker system prune -a

# Remove build cache (reclaim 1-2GB but slower future builds)
docker builder prune

# ⚠️  WARNING: This affects ALL Docker projects on your system, not just this demo
```

#### Recommended Cleanup Strategy

**After a demo (running again within days)**:
```bash
# Keep images cached for fast restart
docker-compose down -v

# Disk used: ~14GB (images cached)
# Next start: <1 minute
```

💡 **Why keep images cached?**
- **Ollama models are moderate size** (~12GB total) but still take time to download
- **Model pulling takes 20+ minutes** over network
- **Disk space is temporary**, rebuild time is permanent
- **Perfect for repeated demos** - start time goes from 20-30 minutes to <1 minute
- **Worth keeping if demoing within 1-2 weeks**

**After a demo (won't run for weeks/months)**:
```bash
# Reclaim all disk space
docker-compose down -v --rmi all

# Disk reclaimed: ~15-16GB
# Trade-off: 20-30 minute rebuild next time
```

**Emergency disk space recovery** (need space NOW):
```bash
# Remove everything from this demo
docker-compose down -v --rmi all

# Remove dangling images and build cache
docker system prune -a

# Check reclaimed space
docker system df
```

## 🧪 System Operations Demo

The demo showcases generic DevOps/SRE operations through mock tools:

### Available System Operations

1. **`system_health`**
   - Returns status of all services (api-gateway, auth-service, database, cache-service)
   - Includes CPU, memory, and uptime metrics
   - Simulates real-world conditions: 30% chance api-gateway is degraded; recovers 120s after a `service_restart`

2. **`service_logs`**
   - Retrieves recent log entries from any service
   - Realistic log format with timestamps and levels
   - Configurable line count (default: 50)

3. **`service_restart`**
   - Simulates restarting a degraded or failed service
   - Returns new process ID and confirmation
   - Instant mock operation (no simulated delay)

4. **`database_status`**
   - Connection pool metrics and query performance
   - Includes slow query detection and cache hit rates
   - Simulated PostgreSQL database

5. **`service_config_update`**
   - Update service configuration values
   - Indicates when restart is required

6. **`service_diagnostics`**
   - Multi-point health checks (endpoint, database, cache, dependencies)
   - Resource usage monitoring
   - Occasionally returns degraded status (10% of checks)

All operations return realistic JSON data and create distributed traces visible in New Relic.

## 🔍 Model Comparison Feature

### How A/B Testing Works

1. **Dual Model Setup**: Two Ollama instances running different models
2. **Traffic Split**: Locust sends 50% traffic to each model
3. **Metrics Collection**:
   - Response latency
   - Success rates
   - Tool usage patterns
4. **Comparison UI**: Side-by-side visualization

### What to Compare

- **Speed**: Model A (~2s) is significantly faster than Model B (~70s) due to smaller size and lower quantization overhead
- **Accuracy**: Model B (ministral-3:8b q4_K_M) uses 4-bit mixed quantization for reliable tool calling; Model A (mistral:7b-instruct) is lighter and faster
- **Size**: Model A (~4GB) vs Model B (~5GB) - Model B uses q4_K_M quantization for reliable structured outputs
- **Use Case Fit**: Model A for fast, efficient responses; Model B for reliable, accurate results

## 📊 New Relic Instrumentation

### Current Implementation

All three Python services are instrumented with **New Relic Python Agent 11.2.0+**:

**Instrumented Services**:
- **ai-agent** (aim-demo_ai-agent)
- **mcp-server** (aim-demo_mcp-server)
- **flask-ui** (aim-demo_flask-ui)

**Configuration Method**: `.ini` files with environment variables for `NEW_RELIC_LICENSE_KEY` and `NEW_RELIC_APP_NAME`

**Features Enabled**:
- ✅ **Distributed Tracing** (W3C trace context propagation across all services)
- ✅ **AI Monitoring** (LLM call tracking, token counting, model performance)
- ✅ **Browser Monitoring** (Real User Monitoring for Flask UI)
- ✅ **Transaction Tracing** (detailed performance breakdown)
- ✅ **Error Collection** (exception tracking and analysis)

**Trace Flow**:
```
Browser (RUM)
  ↓
flask-ui (Python agent + requests)
  ↓
ai-agent (Python agent + httpx)
  ↓
mcp-server (Python agent + Docker API)
```

**View in New Relic**:
1. Navigate to **APM → aim-demo_flask-ui → Distributed Tracing**
2. Trigger a repair workflow from the UI
3. See full end-to-end trace across all four tiers (Browser → Flask → AI Agent → MCP Server)

**AI Monitoring Data Captured**:

- LLM model performance comparison (mistral:7b-instruct-v0.3 vs ministral-3:8b-instruct-2512-q4_K_M)
- Tool call success rates (system_health, service_restart, database_status, etc.)
- Response latency by model
- Token usage and costs
- Hallucination detection patterns
- A/B testing metrics

**Environment Variables** (.env file):
```bash
NEW_RELIC_LICENSE_KEY=your_license_key
NEW_RELIC_APP_NAME_AI_AGENT=aim-demo_ai-agent
NEW_RELIC_APP_NAME_MCP_SERVER=aim-demo_mcp-server
NEW_RELIC_APP_NAME_FLASK_UI=aim-demo_flask-ui
```

## 🛠️ Development

### Project Structure
```
ai-monitoring/
├── docker-compose.yml          # Orchestration
├── Dockerfile.ollama-model-a   # Pre-built Ollama image for Model A
├── Dockerfile.ollama-model-b   # Pre-built Ollama image for Model B
├── .env.example                # Configuration template
├── README.md                   # This file
├── flask-ui/                   # Web interface
├── ai-agent/                   # LangChain agent
├── mcp-server/                 # Generic system operation tools
└── locust-tests/               # Load generation
```

### Making Changes

**Rebuild After Code Changes**:
```bash
docker-compose build <service-name>
docker-compose up -d <service-name>
```

**Rebuild Ollama Images** (if models change):
```bash
docker-compose build ollama-model-a ollama-model-b
docker-compose up -d ollama-model-a ollama-model-b
```

**View Logs**:
```bash
docker-compose logs -f <service-name>
```

**Access Container Shell**:
```bash
docker exec -it aim-<service-name> /bin/bash
```

### Useful Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart ai-agent

# View logs
docker-compose logs -f

# Check status
docker-compose ps

# Clean up
docker-compose down -v
```

For detailed cleanup and disk space management strategies, see the [Cleanup & Disk Space Management](#cleanup--disk-space-management) section below.

## 🎓 Learning Resources

### Related Documentation
- [Ollama Documentation](https://ollama.ai/docs)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [Flask Documentation](https://flask.palletsprojects.com/en/stable/)

### New Relic Resources
- [New Relic AI Monitoring](https://docs.newrelic.com/docs/ai-monitoring/)
- [Model Comparison](https://docs.newrelic.com/docs/ai-monitoring/model-comparison/)
- [Python Agent](https://docs.newrelic.com/docs/apm/agents/python-agent/)

## 🐛 Known Issues

1. **First Build Takes Time**: Initial image build takes 20-30 minutes to build all services (one-time only)
2. **Memory Usage**: Requires 4-6GB Docker memory allocation minimum (8GB+ recommended)
3. **Docker Socket**: Requires privileged access on some systems
4. **Port Conflicts**: Ensure ports 8000, 8001, 8002, 8089, 8501, 11434, 11435 are available
5. **Model "signal: killed"**: If you see this error, your Docker memory is too low - see [Troubleshooting](#-troubleshooting)

## 📚 Next Steps

**After deployment:**
- **Explore service internals**: See individual service READMEs in [Service Discovery Map](#service-discovery-map)
- **Customize agent behavior**: [ai-agent/README.md](ai-agent/README.md)
- **MCP tool operations**: [mcp-server/README.md](mcp-server/README.md)
- **Load generation configuration**: [locust-tests/README.md](locust-tests/README.md)
---

## 📝 Implementation Details: Passive Load & Observability Updates

### Key Architecture: Backend Workflow Control

**MCP Tool Prompts** (15% of load) use **prompt-guided workflow control**:

```
Locust/User → /repair?model=a&workflow=minimal_single_tool
              ↓
          Prompt instructs: "Call system_health ONCE, then Final Answer. STOP."
              ↓
          Returns result (typically 1 tool call)
```

```
Locust/User → /repair?model=b&workflow=forced_full_repair
              ↓
          Prompt instructs:
              1. system_health
              2. service_restart (api-gateway, regardless of status)
              3. system_health (verify)
              ↓
          Returns result (typically 3 tool calls, in order)
```

**Benefits**:

- ✅ Strongly guided tool usage (explicit prompt instructions)
- ✅ Consistent telemetry (low variability in token counts)
- ✅ Minimal LLM reasoning variability (prompt-guided, not free-form)
- ✅ Good for A/B model comparison

**Chat Prompts** (85% of load) use **LLM-decided tool usage**:

```
Locust/User → /chat {"message": "What tools do you have?", "model": "a"}
              ↓
          LLM decides: No tools needed (conversational)
              ↓
          Returns chat response
```

**Benefits**:
- ✅ Natural conversation flow
- ✅ Tests LLM reasoning capabilities
- ✅ Flexible responses
- ✅ Varied tool usage patterns

### New Relic Feedback Events

Each AI request automatically generates feedback based on response quality:

**Smart Heuristics**:
- Failures → `thumbs_down` (100%)
- Very slow (>60s) → `thumbs_down` (80%)
- Very fast (<5s) → `thumbs_up` (90%)
- Multiple tools used (2+) → `thumbs_up` (85%)
- Single tool call → `thumbs_up` (75%)
- No tools (conversational) → `thumbs_up` (70%)

**Feedback Event Structure**:
```python
newrelic.agent.record_llm_feedback_event(
    trace_id=newrelic.agent.current_trace_id(),  # Links to chat completion
    rating="thumbs_up" or "thumbs_down",         # Binary rating
    category="fast" | "slow_response" | "helpful" | ...,
    message="Quick and helpful response (2.3s)",
    metadata={
        'model_variant': 'a',
        'model_name': 'mistral:7b-instruct-v0.3',
        'tool_count': 2,
        'latency_seconds': 2.34,
        'prompt_length': 45
    }
)
```

### Prompt Pool Distribution

| Category | Count | Endpoint | Workflow | LLM Control | Weight |
|----------|-------|----------|----------|-------------|--------|
| MCP Healthy | 1 | `/repair` | `minimal_single_tool` | Prompt-guided | 10% |
| MCP Degraded | 1 | `/repair` | `forced_full_repair` | Prompt-guided | 5% |
| Simple Chat | 5 | `/chat` | N/A | ✅ LLM | 35% |
| Complex Chat | 5 | `/chat` | N/A | ✅ LLM | 30% |
| Error Scenarios | 3 | `/chat` | N/A | ✅ LLM | 10% |
| Boundary Testing | 3 | `/chat` | N/A | ✅ LLM | 8% |
| Abusive Language | 1 | `/chat` | N/A | ✅ LLM | 2% |

### Passive Load Timeline

- **t=0s**: `docker-compose up` starts containers
- **t=~15s**: AI agent healthy, Locust spawns user
- **t=~20s**: `on_start()` fires → **FIRST REQUEST** (immediate)
- **t=~740s** (12 min): Second request via scheduled task
- **t=~1460s** (24 min): Third request
- **Continues every 720s (12 minutes)...**

Result: ~10 requests/hour (5 per model) with immediate startup feedback.

### Technology Stack Update

- LangChain 0.3.11
- langchain-openai 0.2.14 (using Ollama's OpenAI-compatible API)
- langchain-community 0.3.12
- tiktoken 0.8.0 (for client-side token counting)
- Native MCP integration
- Built-in observability hooks
- LLM feedback events with smart heuristics
- tiktoken-based token counting callback for accurate token metrics

---

**Built with**: Docker 🐳 | LangChain 🦜 | Ollama 🦙 | Flask ⚡ | New Relic 📊
