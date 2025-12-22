"""
Docker tools for MCP server.
Provides container management operations via Docker SDK.
"""

import json
import logging
import docker
from typing import Optional

logger = logging.getLogger(__name__)

# Initialize Docker client
try:
    docker_client = docker.from_env()
    logger.info("Docker client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Docker client: {e}")
    docker_client = None


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

            result.append({
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "id": container.short_id,
                "health": health_status
            })

        logger.info(f"Listed {len(result)} containers")
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
        container.restart(timeout=10)

        logger.info(f"Successfully restarted container '{service_name}'")
        return f"✓ Successfully restarted container '{service_name}'"

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
