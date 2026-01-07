# Troubleshooting Guide

This document covers common issues, solutions, and maintenance tasks for the AI Monitoring Demo Application.

## 📋 Table of Contents

- [Common Issues](#common-issues)
  - [Models Not Loading](#models-not-loading)
  - [Container Crashes](#container-crashes)
  - [Permission Errors](#permission-errors)
  - [Ollama Model Memory Errors](#ollama-model-memory-errors-most-common)
  - [Out of Memory (General)](#out-of-memory-general)
  - [Agent Not Responding](#agent-not-responding)
  - [Chaos Engine Too Aggressive](#chaos-engine-too-aggressive)
  - [Build Failures](#build-failures)
- [Cleanup & Disk Space Management](#cleanup--disk-space-management)

## Common Issues

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
docker logs aim-target-app

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

### Ollama Model Memory Errors (Most Common)

**Symptom**: In the Streamlit UI, you see errors like:
```
Error: status_code: 500, model_name: qwen2.5:0.5b, body: {'message': 'llama runner process has terminated: signal: killed'}
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

**Current Configuration** (Optimized for Limited Memory):
- **Model A**: llama3.2:1b (~1.5-2GB memory)
- **Model B**: qwen2.5:0.5b (~500MB-1GB memory) - Ultra lightweight
- **Total Required**: 4-6GB Docker memory minimum (8GB+ recommended)

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

# Use only Model A in the UI (3GB model works on minimal Docker settings)
```

**Memory Requirements Summary**:

| Docker Memory | Model A (1b) | Model B (0.5b) | Result |
|---------------|--------------|----------------|--------|
| **< 4GB** | ⚠️ Tight | ⚠️ Tight | May work but not recommended |
| **4-6GB** | ✅ Works | ✅ Works | Minimum for comfortable operation |
| **8GB+** | ✅ Works | ✅ Works | Recommended |
| **12GB+** | ✅ Works | ✅ Works | Ideal for development |

**Check Your Current Docker Memory**:
```bash
# View Docker memory allocation
docker info | grep Memory

# Check current container memory usage
docker stats --no-stream

# Check if containers are being OOM killed
docker inspect aim-ollama-model-b | grep -i oom
```

### Out of Memory (General)

**Symptom**: Random services getting killed, not just Ollama

**Solution**:
```bash
# Check which containers are being OOM killed
docker inspect aim-target-app | grep -i oom
docker inspect aim-ai-agent | grep -i oom

# If multiple services affected, increase Docker memory allocation
# See "Ollama Model Memory Errors" section above for instructions
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

### Chaos Engine Too Aggressive

**Symptom**: System keeps failing before repairs complete

**Solution**:
```bash
# Edit .env file
CHAOS_INTERVAL=300  # Increase to 5 minutes

# Or disable temporarily
CHAOS_ENABLED=false

# Restart chaos engine
docker-compose restart chaos-engine
```

### Build Failures

**Symptom**: `docker-compose build` fails during image building

**Do I need to run `docker-compose down` before retrying?**

**No!** `docker-compose down` is for stopping/removing running containers. Build failures don't create running containers, so you don't need to clean up.

**Solutions**:

>FIRST - ensure your are using Cloudflare `Gateway with DoH`. `Gateway with WARP` has SSL issues downloading Ollama.

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

## Cleanup & Disk Space Management

### Check Current Disk Usage

```bash
# See all Docker disk usage (images, containers, volumes, build cache)
docker system df

# See detailed image sizes
docker images | grep aim

# Check specific volume sizes
docker volume ls | grep aim
docker system df -v | grep aim
```

### Disk Space Breakdown

| Component | Size | Can Remove? | Impact |
|-----------|------|-------------|--------|
| Ollama Model A image | ~2GB | Yes | Next start requires 3-min rebuild |
| Ollama Model B image | ~1.5GB | Yes | Next start requires 2-min rebuild |
| App service images | ~2GB | Yes | Next start requires 2-min rebuild |
| Docker volumes | ~500MB | Yes | Loses failure state, model cache |
| Container logs | ~200-500MB | Yes | Loses log history |
| Build cache | ~1GB | Yes | Slower future rebuilds |

### Cleanup Strategies

#### Partial Cleanup (Stop services, keep images for fast restart)

```bash
# Stop containers but keep images and volumes
docker-compose down

# Disk reclaimed: ~200-500MB (running containers and recent logs)
# Restart time: <30 seconds with: docker-compose up -d
```

💡 **Recommended if running demo again soon** - keeps model images cached!

#### Remove Volumes (Clean slate for testing)

```bash
# Stop and remove containers + volumes (keeps images)
docker-compose down -v

# Disk reclaimed: ~1GB (includes volume data and logs)
# Images remain cached for fast restart
# Restart time: ~30 seconds (recreates volumes)
```

#### Remove Application Images (Keep Ollama models)

```bash
# Remove just the application service images
docker-compose down
docker rmi $(docker images | grep 'aim-\(target-app\|ai-agent\|mcp-server\|chaos-engine\|locust\|streamlit\)' | awk '{print $3}')

# Disk reclaimed: ~2GB
# Ollama models remain cached (most important part)
# Next start: ~2 minute rebuild for app services
```

#### Remove Ollama Images (Reclaim model storage)

```bash
# Remove the pre-built Ollama images
docker rmi aim-ollama-model-a
docker rmi aim-ollama-model-b

# Disk reclaimed: ~3.5GB (the two model images)
# ⚠️  Next startup requires: docker-compose build ollama-model-a ollama-model-b
# ⚠️  Rebuild time: 3-5 minutes to re-download and bake models
```

⚠️  **Only do this if you won't run the demo for a while!**

#### Full Cleanup (Remove everything)

```bash
# Stop services and remove all containers, volumes, and images
docker-compose down -v --rmi all

# Disk reclaimed: ~7-8GB (everything)
# Next start: Requires full rebuild (5-8 minutes)
```

#### Aggressive Cleanup (Remove all unused Docker resources)

```bash
# Remove all stopped containers, unused networks, dangling images
docker system prune

# Remove everything not currently in use (including unused images)
docker system prune -a

# Remove build cache (reclaim 1-2GB but slower future builds)
docker builder prune

# ⚠️  WARNING: This affects ALL Docker projects on your system, not just this demo
```

### Recommended Cleanup Strategy

**After a demo (running again within days)**:
```bash
# Keep images cached for fast restart
docker-compose down -v

# Disk used: ~6GB (images cached)
# Next start: <1 minute
```

💡 **Why keep images cached?**
- **Ollama models are relatively small** (~3.5GB total) but still take time to download
- **Model pulling takes 3-5 minutes** over network
- **Disk space is temporary**, rebuild time is permanent
- **Perfect for repeated demos** - start time goes from 5+ minutes to <1 minute
- **Worth keeping if demoing within 1-2 weeks**

**After a demo (won't run for weeks/months)**:
```bash
# Reclaim all disk space
docker-compose down -v --rmi all

# Disk reclaimed: ~7-8GB
# Trade-off: 5-8 minute rebuild next time
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
