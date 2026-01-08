"""
API endpoints for AJAX polling.
"""

from flask import Blueprint, jsonify, request, current_app
from services.agent_client import AgentClient
from services.mcp_client import MCPClient

bp = Blueprint('api', __name__)


def get_agent_client():
    """Get AgentClient instance."""
    return AgentClient(current_app.config['AGENT_URL'])


def get_mcp_client():
    """Get MCPClient instance."""
    return MCPClient(current_app.config['MCP_URL'])


@bp.route('/health')
def health_check():
    """Agent health status (polled every 30s)."""
    agent_client = get_agent_client()
    return jsonify(agent_client.health_check())


@bp.route('/metrics')
def get_metrics():
    """Get model metrics (polled for dashboard)."""
    agent_client = get_agent_client()
    return jsonify(agent_client.get_metrics())


@bp.route('/containers')
def get_container_status():
    """Docker container status (polled every 15s)."""
    mcp_client = get_mcp_client()
    return jsonify(mcp_client.docker_ps())


@bp.route('/logs/<container_name>')
def get_container_logs(container_name):
    """Fetch container logs."""
    mcp_client = get_mcp_client()
    lines = request.args.get('lines', 50, type=int)
    return jsonify(mcp_client.get_container_logs(container_name, lines))


@bp.route('/agent/minimal-repair', methods=['POST'])
def agent_minimal_repair():
    """Trigger minimal repair workflow (debugging endpoint)."""
    agent_client = get_agent_client()
    model = request.args.get('model', 'a')

    try:
        response = agent_client.session.post(
            f"{agent_client.base_url}/repair/minimal",
            params={"model": model},
            timeout=150
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/agent/manual-repair', methods=['POST'])
def agent_manual_repair():
    """Trigger manual repair workflow (bypasses PydanticAI)."""
    agent_client = get_agent_client()
    model = request.args.get('model', 'a')

    try:
        response = agent_client.session.post(
            f"{agent_client.base_url}/repair/manual",
            params={"model": model},
            timeout=150
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
