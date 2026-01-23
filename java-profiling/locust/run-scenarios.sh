#!/bin/bash
# run-scenarios.sh - Sequential scenario orchestration

set -e

TARGET_HOST=${LOCUST_TARGET_HOST:-"http://java-app:8080"}
AUTOSTART=${LOCUST_AUTOSTART:-"false"}

echo "==================================================================="
echo "Java Profiling Demo - Automated Load Scenario Runner"
echo "==================================================================="
echo "Target: $TARGET_HOST"
echo "Auto-start: $AUTOSTART"
echo ""

# Wait for Java app to be healthy
echo "[$(date)] Waiting for Java application to be healthy..."
until python3 -c "import urllib.request; urllib.request.urlopen('$TARGET_HOST/health')" 2>/dev/null; do
    echo "[$(date)] App not ready, waiting 5 seconds..."
    sleep 5
done
echo "[$(date)] Java application is healthy!"
echo ""

if [ "$AUTOSTART" != "true" ]; then
    echo "AUTOSTART is not enabled. Launch Locust web UI manually at http://localhost:8089"
    exec locust -f /locust/locustfile.py --host "$TARGET_HOST" --web-port 8089
    exit 0
fi

# Automated scenario execution
echo "==================================================================="
echo "SCENARIO 1: Normal Baseline Traffic (60 seconds)"
echo "==================================================================="
echo "Pattern: 1 user, 1 req/sec to /health"
echo ""
locust -f /locust/locustfile.py \
    --host "$TARGET_HOST" \
    --users 1 \
    --spawn-rate 1 \
    --run-time 60s \
    --headless \
    --only-summary \
    NormalTrafficUser

echo ""
echo "==================================================================="
echo "SCENARIO 2: CPU Spike (30 seconds)"
echo "==================================================================="
echo "Pattern: 10 concurrent users hammering /api/cpu-burn"
echo ""
locust -f /locust/locustfile.py \
    --host "$TARGET_HOST" \
    --users 10 \
    --spawn-rate 5 \
    --run-time 30s \
    --headless \
    --only-summary \
    CpuSpikeUser

echo ""
echo "==================================================================="
echo "SCENARIO 3: Memory Pressure (60 seconds)"
echo "==================================================================="
echo "Pattern: 5 users, steady requests to /api/memory-pressure"
echo ""
locust -f /locust/locustfile.py \
    --host "$TARGET_HOST" \
    --users 5 \
    --spawn-rate 2 \
    --run-time 60s \
    --headless \
    --only-summary \
    MemoryPressureUser

echo ""
echo "==================================================================="
echo "SCENARIO 4: Lock Contention (30 seconds)"
echo "==================================================================="
echo "Pattern: 3 users triggering /api/lock-contention"
echo ""
locust -f /locust/locustfile.py \
    --host "$TARGET_HOST" \
    --users 3 \
    --spawn-rate 1 \
    --run-time 30s \
    --headless \
    --only-summary \
    LockContentionUser

echo ""
echo "==================================================================="
echo "SCENARIO 5: IO Wait (45 seconds)"
echo "==================================================================="
echo "Pattern: 5 users with /api/io-wait requests"
echo ""
locust -f /locust/locustfile.py \
    --host "$TARGET_HOST" \
    --users 5 \
    --spawn-rate 2 \
    --run-time 45s \
    --headless \
    --only-summary \
    IoWaitUser

echo ""
echo "==================================================================="
echo "ALL SCENARIOS COMPLETE!"
echo "==================================================================="
echo "Total runtime: ~3.5 minutes (225 seconds)"
echo "Check New Relic for JFR data:"
echo "  - APM: Transaction traces and throughput"
echo "  - JFR Dashboard: CPU, Memory, GC, Thread states"
echo "  - Thread Profiler: Flame graphs and hot methods"
echo ""
echo "Looping scenarios... (press Ctrl+C to stop)"
echo ""

# Loop scenarios continuously for ongoing demo
while true; do
    sleep 60
    echo "[$(date)] Restarting scenario loop..."
done
