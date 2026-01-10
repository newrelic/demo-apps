"""
Generic System Operations Tools - Mock implementations for demo purposes.

These tools simulate common DevOps/SRE operations without being tied to
specific infrastructure (Docker, Kubernetes, etc.). All operations return
realistic mock data with simulated delays.
"""

import time
import random
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def check_system_health() -> str:
    """
    Returns overall system health status.

    Simulates checking multiple services, system resources, and overall health.
    """
    logger.info("Tool called: check_system_health")

    return json.dumps({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": [
            {"name": "api-gateway", "status": "running", "cpu": 45, "memory": 62, "uptime": "3d 14h"},
            {"name": "auth-service", "status": "running", "cpu": 23, "memory": 48, "uptime": "5d 2h"},
            {"name": "database", "status": "running", "cpu": 67, "memory": 81, "uptime": "12d 8h"},
            {"name": "cache-service", "status": "running", "cpu": 12, "memory": 34, "uptime": "8d 16h"}
        ],
        "system_metrics": {
            "cpu_usage": 52,
            "memory_usage": 68,
            "disk_usage": 42,
            "network_throughput_mbps": 145.7
        }
    }, indent=2)


def get_service_logs(service_name: str, lines: int = 50) -> str:
    """
    Returns recent logs from a specified service.

    Args:
        service_name: Name of the service to get logs from
        lines: Number of log lines to return (default: 50)
    """
    logger.info(f"Tool called: get_service_logs({service_name}, lines={lines})")

    log_levels = ["INFO", "DEBUG", "WARN"]
    log_entries = []

    for i in range(min(lines, 100)):  # Cap at 100 lines
        timestamp = datetime.now().isoformat()
        level = random.choice(log_levels)
        messages = [
            f"Processing request ID: req-{random.randint(1000, 9999)}",
            f"Database query completed in {random.randint(5, 50)}ms",
            f"Cache hit ratio: {random.uniform(0.85, 0.99):.2f}",
            f"Handling API endpoint /api/v1/users",
            f"Authentication successful for user-{random.randint(100, 999)}",
            f"Background task completed: cleanup-{random.randint(1, 10)}"
        ]
        message = random.choice(messages)

        log_entries.append(f"{timestamp} | {level:5} | {service_name:20} | {message}")

    header = f"=== Logs from {service_name} (last {lines} lines) ===\n"
    return header + "\n".join(log_entries)


def restart_service(service_name: str) -> str:
    """
    Restarts a specified service.

    Args:
        service_name: Name of the service to restart

    Simulates a service restart with appropriate delay.
    """
    logger.info(f"Tool called: restart_service({service_name})")

    return json.dumps({
        "status": "success",
        "service": service_name,
        "message": f"Service {service_name} restarted successfully",
        "restart_time_seconds": 0.0,  # Instant restart (mock delays removed)
        "new_pid": random.randint(10000, 99999),
        "timestamp": datetime.now().isoformat()
    }, indent=2)


def check_database_status() -> str:
    """
    Returns database health and performance metrics.

    Simulates checking database connection pool, query performance,
    and overall database health.
    """
    logger.info("Tool called: check_database_status")

    return json.dumps({
        "status": "connected",
        "database_type": "PostgreSQL 15.3",
        "connection_pool": {
            "active_connections": random.randint(35, 55),
            "idle_connections": random.randint(10, 20),
            "max_connections": 100,
            "pool_utilization": round(random.uniform(0.45, 0.65), 2)
        },
        "performance": {
            "slow_queries": random.randint(0, 5),
            "avg_query_time_ms": round(random.uniform(8.5, 15.5), 2),
            "max_query_time_ms": round(random.uniform(80, 150), 2),
            "queries_per_second": round(random.uniform(150, 250), 1)
        },
        "cache": {
            "cache_hit_rate": round(random.uniform(0.90, 0.97), 3),
            "buffer_pool_usage_percent": random.randint(75, 92)
        },
        "replication": {
            "status": "healthy",
            "lag_ms": random.randint(5, 25)
        },
        "timestamp": datetime.now().isoformat()
    }, indent=2)


def update_configuration(service_name: str, key: str, value: str) -> str:
    """
    Updates a configuration value for a service.

    Args:
        service_name: Name of the service
        key: Configuration key to update
        value: New value for the configuration

    Note: Simulates config update; service restart typically required.
    """
    logger.info(f"Tool called: update_configuration({service_name}, {key}, ***)")

    return json.dumps({
        "status": "updated",
        "service": service_name,
        "config_key": key,
        "previous_value": f"<previous-{key}>",
        "new_value": value,
        "message": f"Configuration {key} updated successfully. Service restart recommended for changes to take effect.",
        "restart_required": True,
        "timestamp": datetime.now().isoformat()
    }, indent=2)


def run_diagnostics(service_name: str) -> str:
    """
    Runs comprehensive health checks and diagnostics on a service.

    Args:
        service_name: Name of the service to diagnose

    Returns detailed health check results across multiple dimensions.
    """
    logger.info(f"Tool called: run_diagnostics({service_name})")

    # Occasionally simulate a degraded state for demo purposes
    is_healthy = random.random() > 0.1  # 90% healthy, 10% degraded

    health_status = "healthy" if is_healthy else "degraded"
    endpoint_status = "healthy" if is_healthy else "timeout"

    return json.dumps({
        "service": service_name,
        "overall_status": health_status,
        "health_checks": {
            "http_endpoint": {
                "status": endpoint_status,
                "response_time_ms": random.randint(15, 50) if is_healthy else random.randint(5000, 8000),
                "status_code": 200 if is_healthy else 504
            },
            "database_connection": {
                "status": "healthy",
                "latency_ms": random.randint(3, 12)
            },
            "cache_connection": {
                "status": "healthy",
                "latency_ms": random.randint(1, 5)
            },
            "external_dependencies": {
                "status": "healthy",
                "services_reachable": 4,
                "services_total": 4
            }
        },
        "resource_usage": {
            "cpu_percent": random.randint(25, 75),
            "memory_percent": random.randint(40, 80),
            "disk_io_mbps": round(random.uniform(10, 50), 1),
            "network_io_mbps": round(random.uniform(20, 100), 1)
        },
        "recent_errors": {
            "last_24h": random.randint(0, 3),
            "last_error": None if is_healthy else "Connection timeout to external service"
        },
        "recommendations": [] if is_healthy else [
            f"Investigate {service_name} endpoint timeouts",
            "Check external service dependencies",
            "Review recent deployment changes"
        ],
        "timestamp": datetime.now().isoformat()
    }, indent=2)
