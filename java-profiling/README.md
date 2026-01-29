# New Relic Java Flight Recorder (JFR) Demo

A comprehensive Java 17 Spring Boot application demonstrating New Relic's Java Flight Recorder (JFR) and Thread Profiler capabilities.

## Overview

This demo showcases:
- **Real-time JFR Monitoring**: CPU hotspots, memory allocation, and GC activity
- **Thread Profiler**: Flame graphs, lock contention, and I/O wait visualization
- **Automated Load Generation**: Locust-driven scenarios for consistent telemetry
- **Java 17 + Spring Boot 3.2**: Modern Java stack with containerized deployment

## Architecture

```
┌─────────────────┐
│  Locust         │  Automated Load Generator
│  Load Generator │  (Headless Mode)
└────────┬────────┘
         │ HTTP Scenarios
         v
┌─────────────────┐
│  Java App       │  Port 8081 (host) / 8080 (container)
│  Spring Boot    │  - GET /health
│  + New Relic    │  - GET /api/cpu-burn
│  Agent v7.0+    │  - GET /api/memory-pressure
│  + JFR Enabled  │  - GET /api/io-wait
└─────────────────┘  - GET /api/lock-contention
         │
         v
┌─────────────────┐
│  New Relic      │
│  - APM          │
│  - JFR Dashboard│
│  - Thread Profiler│
└─────────────────┘
```

## Prerequisites

- **Docker Desktop** or Docker Engine 20.10+
- **Docker Compose** V2
- **New Relic account** with license key ([Get one free](https://newrelic.com/signup))
- **8GB RAM minimum** (for Java app + agent + load generation)

## Quick Start

### 1. Clone and Navigate

```bash
cd java-profiling
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your New Relic license key
# REQUIRED: NEW_RELIC_LICENSE_KEY=your_key_here
```

### 3. Start the Demo

```bash
docker compose up -d --build
```

Services will start in this order:
1. **Java app** builds (2-3 minutes first time, downloads agent at build time)
2. **Java app** starts and becomes healthy (~30 seconds)
3. **Locust** starts and begins automated scenarios

### 4. Monitor Services

- **Application Health**: http://localhost:8081/health
- **Locust Logs**: `docker compose logs -f locust`

## Load Scenarios

The demo runs 5 automated scenarios in sequence:

### Scenario 1: Normal Baseline (60 seconds)
- **Pattern**: 1 req/sec to `/health`
- **Purpose**: Establish baseline transaction metrics
- **Observe**: Normal transaction traces, low resource usage

### Scenario 2: CPU Spike (30 seconds)
- **Pattern**: 10 concurrent users to `/api/cpu-burn`
- **Purpose**: Trigger CPU-intensive computation
- **What it does**: Fibonacci(43), regex matching, prime factorization
- **Observe in New Relic**:
  - Thread Profiler: Flame graph shows `calculateFibonacci`, `isPrime` hot methods
  - CPU usage spikes to 90-100%
  - Transaction duration 2-3 seconds

### Scenario 3: Memory Pressure (60 seconds)
- **Pattern**: 5 users to `/api/memory-pressure`
- **Purpose**: Create memory churn and GC activity
- **What it does**: Allocates 100MB+ short-lived objects, string concatenation
- **Observe in New Relic**:
  - JFR Dashboard: Increased GC frequency and duration
  - Heap allocation rate spikes
  - Young Generation GC events

### Scenario 4: Lock Contention (30 seconds)
- **Pattern**: 3 users to `/api/lock-contention`
- **Purpose**: Demonstrate thread blocking
- **What it does**: 5 threads compete for same synchronized lock
- **Observe in New Relic**:
  - Thread Profiler: Threads in BLOCKED state
  - Monitor contention events
  - Lock wait time visible

### Scenario 5: I/O Wait (45 seconds)
- **Pattern**: 5 users to `/api/io-wait`
- **Purpose**: Show I/O wait time in profiler
- **What it does**: External HTTP call + Thread.sleep()
- **Observe in New Relic**:
  - Thread Profiler: Threads in WAITING state
  - Low CPU, high duration transactions
  - External call segments in traces

**Total cycle time**: ~3.5 minutes, then loops continuously

## What to Observe in New Relic

**Note:** It can take 5-10 minutes after startup before JFR profiling data appears in the New Relic UI. Transaction data will appear within 1-2 minutes, but thread profiler and flame graphs may take longer to populate.

### 1. APM View
- Navigate to **APM → [java-profiling-demo]**
- See transaction throughput and response times
- Each scenario creates distinct transaction patterns

### 2. JFR Dashboard
- Navigate to **APM → [java-profiling-demo] → JFR**
- **CPU Usage**: Spikes during Scenario 2
- **Heap Usage**: Allocation pressure during Scenario 3
- **GC Activity**: Young Gen collections during memory pressure
- **Thread States**: BLOCKED threads during Scenario 4

### 3. Thread Profiler
- Navigate to **APM → [java-profiling-demo] → Thread Profiler**
- **Flame Graphs**: Shows hot methods (CPU burn scenario)
- **Thread States**: Visualize RUNNABLE/BLOCKED/WAITING
- **Lock Contention**: See synchronized block waits

### 4. Transaction Traces
- Click on slow transactions
- See method-level breakdown
- External call segments for I/O scenario

## Manual Testing

To manually trigger individual endpoints:

```bash
curl http://localhost:8081/api/cpu-burn
curl http://localhost:8081/api/memory-pressure
curl http://localhost:8081/api/io-wait
curl http://localhost:8081/api/lock-contention
```

## Troubleshooting

### No Data in New Relic

#### Step 1: Check License Key Validity

**View agent logs for connection errors:**
```bash
docker compose exec java-app cat /opt/newrelic/logs/newrelic_agent.log | grep -i "error\|connected"
```

**Common errors:**
- `ERROR: Invalid license key` → License key is wrong or expired
- `ERROR: Remote preconnect call failed` → Network or license key issue

**Fix:** Update `.env` with a valid Ingest License Key from https://one.newrelic.com/launcher/api-keys-ui.api-keys-launcher

#### Step 2: Verify Agent Startup

**Check agent logs:**
```bash
docker compose logs java-app | grep -i "new relic"
```

Look for:
- `"New Relic Agent: JFR service started"` (JFR enabled)
- `"Connected to collector.newrelic.com:443"` (agent connected successfully)

**Verify environment:**
```bash
# Check license key is set
docker compose exec java-app env | grep NEW_RELIC
```

#### Step 3: Restart After Fixing

```bash
# After updating .env with valid license key
docker compose up -d java-app

# Wait 30 seconds, then verify connection
sleep 30
docker compose logs java-app | tail -20
```

### Agent Not Attached

**Symptom**: Application runs but no New Relic data

**Check:**
```bash
# Verify agent jar exists in container
docker compose exec java-app ls -lh /opt/newrelic/newrelic.jar

# Should show ~2MB file
```

### JFR Data Missing

**Verify JFR is enabled:**
```bash
curl http://localhost:8081/health
# Should show: "jfr_enabled": "true"
```

**Check agent version:**
```bash
docker compose exec java-app cat /opt/newrelic/newrelic.jar | grep -a "Implementation-Version"
```

Must be v7.0.0 or higher for JFR support.

### High Memory Usage

**Symptom**: Container using too much RAM

**Solution**: Adjust JVM heap in `app/Dockerfile`:
```dockerfile
CMD ["java", \
     "-javaagent:/opt/newrelic/newrelic.jar", \
     "-Xms256m", \
     "-Xmx512m", \  # Reduce from 1g
     "-jar", \
     "/app/java-profiling.jar"]
```

### Locust Scenarios Not Running

**Check Locust logs:**
```bash
docker compose logs locust
```

Look for messages indicating scenario execution. Each scenario will show:
- Scenario name and duration
- Number of users and spawn rate
- Request statistics when complete

## Cleanup

```bash
# Stop all services
docker compose down

# Remove volumes (if any)
docker compose down -v

# Remove images to free disk space
docker compose down --rmi all
```

## Architecture Details

### Service Communication
- Locust → Java App: HTTP REST calls
- Java App → New Relic: Agent data export (HTTPS)
- Services communicate via Docker network

### New Relic Agent Integration
- Agent JAR: Downloaded at Docker build time (not committed to repo)
- Configuration: 100% via environment variables
- Instrumentation: Automatic via `-javaagent` flag

### Load Generation
- Locust runs scenarios sequentially
- Each scenario targets specific endpoint
- Scenarios loop continuously after completion

## Additional Resources

- [New Relic JFR Documentation](https://docs.newrelic.com/docs/apm/agents/java-agent/features/real-time-java-profiling-using-jfr-metrics/)
- [Java Agent Configuration](https://docs.newrelic.com/docs/apm/agents/java-agent/configuration/java-agent-configuration-config-file/)
- [Spring Boot Reference](https://spring.io/projects/spring-boot)
- [Locust Documentation](https://docs.locust.io/)

---

**Built with**: Java 17 | Spring Boot 3.2 | New Relic Java Agent 7.0+ | Docker | Locust
