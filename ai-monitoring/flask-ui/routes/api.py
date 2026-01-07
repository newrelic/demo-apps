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


@bp.route('/load-test/status')
def load_test_status():
    """Current load test statistics (polled every 5s)."""
    mcp_client = get_mcp_client()
    return jsonify(mcp_client.get_load_test_stats())


@bp.route('/load-test/start', methods=['POST'])
def start_load_test():
    """Start load test."""
    mcp_client = get_mcp_client()
    data = request.get_json()
    users = data.get('users', 10)
    spawn_rate = data.get('spawn_rate', 2)
    duration = data.get('duration', 1800)
    return jsonify(mcp_client.start_load_test(users, spawn_rate, duration))


@bp.route('/load-test/stop', methods=['POST'])
def stop_load_test():
    """Stop load test."""
    mcp_client = get_mcp_client()
    return jsonify(mcp_client.stop_load_test())
