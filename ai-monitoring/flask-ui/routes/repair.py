"""
Repair Mode routes - Autonomous system repair.
"""

from flask import Blueprint, render_template, jsonify, request, session, current_app
from services.agent_client import AgentClient
from utils.session_helpers import set_current_mode

bp = Blueprint('repair', __name__)


def get_agent_client():
    """Get AgentClient instance."""
    return AgentClient(current_app.config['AGENT_URL'])


@bp.route('/')
def repair_mode():
    """Main repair mode page."""
    set_current_mode('repair')
    return render_template('pages/repair.html')


@bp.route('/trigger', methods=['POST'])
def trigger_repair():
    """Trigger repair workflow (synchronous)."""
    agent_client = get_agent_client()
    data = request.get_json() or {}
    model = data.get('model', 'a')
    result = agent_client.trigger_repair(model)
    return jsonify(result)


@bp.route('/compare', methods=['POST'])
def compare_repairs():
    """Trigger comparison repair (synchronous)."""
    agent_client = get_agent_client()
    result = agent_client.compare_repairs()
    return jsonify(result)
