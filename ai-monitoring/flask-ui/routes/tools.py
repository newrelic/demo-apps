"""
Tools Mode routes - Autonomous tool execution workflows.
"""

import logging
import time
from flask import Blueprint, render_template, jsonify, request, session, current_app
from services.agent_client import AgentClient
from utils.session_helpers import set_current_mode

bp = Blueprint('tools', __name__)
logger = logging.getLogger(__name__)


def get_agent_client():
    """Get AgentClient instance."""
    return AgentClient(current_app.config['AGENT_URL'])


@bp.route('/')
def tools_mode():
    """Main tools mode page."""
    set_current_mode('tools')
    return render_template('pages/tools.html')


@bp.route('/trigger', methods=['POST'])
def trigger_tools():
    """Trigger tool execution workflow (synchronous)."""
    start_time = time.time()
    data = request.get_json() or {}
    model = data.get('model', 'a')

    logger.info(f"[TOOLS-TRIGGER] Request received - model={model}, client_ip={request.remote_addr}")

    try:
        agent_client = get_agent_client()
        logger.info(f"[TOOLS-TRIGGER] AgentClient instantiated, calling trigger_repair(model={model})")

        result = agent_client.trigger_repair(model)

        elapsed = time.time() - start_time
        success = "error" not in result
        logger.info(f"[TOOLS-TRIGGER] Response received - success={success}, elapsed={elapsed:.2f}s, model={model}")

        if not success:
            logger.warning(f"[TOOLS-TRIGGER] Tool execution failed - error={result.get('error', 'unknown')}, model={model}")

        return jsonify(result)
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[TOOLS-TRIGGER] Unexpected exception - error={str(e)}, elapsed={elapsed:.2f}s, model={model}", exc_info=True)
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


