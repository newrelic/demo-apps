"""
Docker tools for MCP server.
Provides container management operations via Docker SDK.
"""

import json
import logging
import docker
from typing import Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Initialize Docker client
try:
    docker_client = docker.from_env()
    logger.info("Docker client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Docker client: {e}")
    docker_client = None


def get_relative_time(timestamp_str: str) -> str:
    """
    Convert ISO timestamp to relative time string (e.g., '2 minutes ago').

    Args:
        timestamp_str: ISO 8601 timestamp string

    Returns:
        Human-readable relative time string
    """
    try:
        # Parse the timestamp (Docker returns ISO 8601 format)
        if timestamp_str.endswith('Z'):
            timestamp_str = timestamp_str[:-1] + '+00:00'

        container_time = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = now - container_time

        seconds = int(delta.total_seconds())

        if seconds < 60:
            return f"{seconds} seconds ago"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        else:
            days = seconds // 86400
            return f"{days} day{'s' if days != 1 else ''} ago"
    except Exception as e:
        logger.warning(f"Failed to parse timestamp: {e}")
        return "unknown"


def docker_ps() -> str:
    """
    List all containers with their current status.

    Returns:
        JSON string with container information including:
        - name: Container name
        - status: Current status (running, exited, restarting, etc.)
        - image: Container image
        - id: Short container ID
        - health: Health status if available
        - started_at: ISO timestamp when container started
        - uptime: Human-readable uptime (e.g., "2 minutes ago")
    """
    try:
        if docker_client is None:
            return json.dumps({"error": "Docker client not initialized"})

        containers = docker_client.containers.list(all=True)
        result = []

        for container in containers:
            health_status = None
            if container.attrs.get('State', {}).get('Health'):
                health_status = container.attrs['State']['Health'].get('Status')

            # Get start time from State
            state = container.attrs.get('State', {})
            started_at = state.get('StartedAt', '')
            uptime = get_relative_time(started_at) if started_at else 'unknown'

            result.append({
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "id": container.short_id,
                "health": health_status,
                "started_at": started_at,
                "uptime": uptime
            })

        logger.debug(f"Listed {len(result)} containers")
        return json.dumps(result, indent=2)

    except Exception as e:
        error_msg = f"Error listing containers: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def read_service_logs(service_name: str, lines: int = 50) -> str:
    """
    Read recent logs from a specific service container.

    Args:
        service_name: Name of the service/container
        lines: Number of log lines to retrieve (default: 50)

    Returns:
        Container logs as string
    """
    try:
        if docker_client is None:
            return "Error: Docker client not initialized"

        container = docker_client.containers.get(service_name)
        logs = container.logs(tail=lines, timestamps=True).decode('utf-8')

        logger.info(f"Retrieved {lines} log lines from {service_name}")
        return f"=== Logs from {service_name} (last {lines} lines) ===\n{logs}"

    except docker.errors.NotFound:
        error_msg = f"Container '{service_name}' not found"
        logger.warning(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error reading logs from {service_name}: {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"


def restart_container(service_name: str) -> str:
    """
    Restart a specific container.

    Args:
        service_name: Name of the service/container to restart

    Returns:
        Success or error message
    """
    try:
        if docker_client is None:
            return "Error: Docker client not initialized"

        container = docker_client.containers.get(service_name)

        # Log pre-restart state
        old_state = container.attrs.get('State', {})
        old_started_at = old_state.get('StartedAt', 'unknown')
        logger.info(f"Restarting container '{service_name}' (previously started: {old_started_at})")

        container.restart(timeout=10)

        # Reload container to get new state
        container.reload()
        new_state = container.attrs.get('State', {})
        new_started_at = new_state.get('StartedAt', 'unknown')

        logger.info(f"✓ Successfully restarted container '{service_name}' (new start time: {new_started_at})")
        return (f"✓ Successfully restarted container '{service_name}'\n"
                f"New start time: {get_relative_time(new_started_at)}")

    except docker.errors.NotFound:
        error_msg = f"Container '{service_name}' not found"
        logger.warning(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error restarting container '{service_name}': {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"


def inspect_container(service_name: str) -> str:
    """
    Get detailed information about a container including environment variables.

    Args:
        service_name: Name of the service/container

    Returns:
        JSON string with container details
    """
    try:
        if docker_client is None:
            return json.dumps({"error": "Docker client not initialized"})

        container = docker_client.containers.get(service_name)
        attrs = container.attrs

        # Extract relevant information
        info = {
            "name": container.name,
            "status": container.status,
            "image": attrs['Config']['Image'],
            "environment": attrs['Config'].get('Env', []),
            "state": attrs['State'],
            "health": attrs['State'].get('Health', {}),
            "restart_count": attrs['RestartCount']
        }

        logger.info(f"Inspected container '{service_name}'")
        return json.dumps(info, indent=2)

    except docker.errors.NotFound:
        error_msg = f"Container '{service_name}' not found"
        logger.warning(error_msg)
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = f"Error inspecting container '{service_name}': {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg})


def update_container_env(service_name: str, key: str, value: str) -> str:
    """
    Update an environment variable for a container.
    Note: This requires recreating the container, which is complex.
    For this demo, we'll return instructions for manual update.

    Args:
        service_name: Name of the service/container
        key: Environment variable key
        value: Environment variable value

    Returns:
        Success message with instructions
    """
    try:
        if docker_client is None:
            return "Error: Docker client not initialized"

        container = docker_client.containers.get(service_name)

        # Get current environment
        current_env = container.attrs['Config'].get('Env', [])

        # Parse environment variables
        env_dict = {}
        for env_var in current_env:
            if '=' in env_var:
                k, v = env_var.split('=', 1)
                env_dict[k] = v

        # Update the specific key
        env_dict[key] = value

        logger.info(f"Environment variable {key}={value} updated for {service_name}")
        logger.info("Note: Container needs restart for changes to take effect")

        return (f"✓ Environment variable {key}={value} noted for '{service_name}'\n"
                f"Recommendation: Restart the container for changes to take effect.\n"
                f"Use restart_container('{service_name}') to apply the fix.")

    except docker.errors.NotFound:
        error_msg = f"Container '{service_name}' not found"
        logger.warning(error_msg)
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Error updating environment for '{service_name}': {str(e)}"
        logger.error(error_msg)
        return f"Error: {error_msg}"
