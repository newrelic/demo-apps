"""
Model Comparison routes - Performance metrics dashboard.
"""

from flask import Blueprint, render_template, jsonify, current_app
from services.agent_client import AgentClient
from utils.session_helpers import set_current_mode

bp = Blueprint('comparison', __name__)


def get_agent_client():
    """Get AgentClient instance."""
    return AgentClient(current_app.config['AGENT_URL'])


@bp.route('/')
def comparison_dashboard():
    """Model comparison dashboard page."""
    set_current_mode('comparison')
    return render_template('pages/comparison.html')


@bp.route('/export')
def export_metrics():
    """Export metrics as JSON file."""
    agent_client = get_agent_client()
    metrics = agent_client.get_metrics()
    return jsonify(metrics)
