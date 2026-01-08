"""
Debug Mode routes - Diagnostic tools for PydanticAI issues.
"""

import logging
from flask import Blueprint, render_template, jsonify, request, current_app
from services.agent_client import AgentClient
from utils.session_helpers import set_current_mode

bp = Blueprint('debug', __name__)
logger = logging.getLogger(__name__)


def get_agent_client():
    """Get AgentClient instance."""
    return AgentClient(current_app.config['AGENT_URL'])


@bp.route('/')
def debug_mode():
    """Main debug mode page."""
    set_current_mode('debug')
    return render_template('pages/debug.html')


@bp.route('/test', methods=['POST'])
def test_minimal_agent():
    """Test minimal agent (no tools) to diagnose hanging."""
    data = request.get_json() or {}
    model = data.get('model', 'a')
    message = data.get('message', 'Hello, can you respond?')

    logger.info(f"[DEBUG] Testing minimal agent - model={model}, message='{message[:50]}...'")

    try:
        agent_client = get_agent_client()

        # Call the debug test endpoint
        response = agent_client.session.post(
            f"{agent_client.base_url}/debug/test",
            params={"model": model, "message": message},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()

        logger.info(f"[DEBUG] Test completed - success={result.get('success')}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"[DEBUG] Test failed - error={str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route('/direct-llm', methods=['POST'])
def test_direct_llm():
    """Test direct LLM call bypassing PydanticAI."""
    data = request.get_json() or {}
    model = data.get('model', 'a')

    logger.info(f"[DEBUG] Testing direct LLM call - model={model}")

    try:
        agent_client = get_agent_client()

        # Call the direct LLM test endpoint
        response = agent_client.session.post(
            f"{agent_client.base_url}/debug/direct-llm",
            params={"model": model},
            timeout=60
        )
        response.raise_for_status()
        result = response.json()

        logger.info(f"[DEBUG] Direct LLM test completed - success={result.get('success')}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"[DEBUG] Direct LLM test failed - error={str(e)}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
