"""
Chat Mode routes - Interactive chat assistant.
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from services.agent_client import AgentClient
from utils.session_helpers import set_current_mode, get_chat_history, add_chat_message, clear_chat_history
import requests

bp = Blueprint('chat', __name__)


def get_agent_client():
    """Get AgentClient instance."""
    return AgentClient(current_app.config['AGENT_URL'])


@bp.route('/')
def chat_mode():
    """Main chat interface page."""
    set_current_mode('chat')
    return render_template('pages/chat.html', chat_history=get_chat_history())


@bp.route('/send', methods=['POST'])
def send_message():
    """Send chat message and get response."""
    agent_client = get_agent_client()
    data = request.get_json()
    message = data.get('message', '')
    model = data.get('model', 'a')

    # Add user message to history
    add_chat_message('user', message)

    # Get response from agent
    result = agent_client.send_chat(message, model)

    if 'error' not in result:
        # Add assistant response to history
        add_chat_message('assistant', result.get('response', ''), result.get('model_used', model))

    return jsonify(result)


@bp.route('/clear', methods=['POST'])
def clear_history():
    """Clear chat history from session."""
    clear_chat_history()
    return jsonify({'success': True})


@bp.route('/prompts', methods=['GET'])
def get_prompts():
    """
    Get list of available prompts from the AI agent.

    Fetches prompts from the ai-agent service via API call.
    """
    agent_url = current_app.config['AGENT_URL']

    try:
        # Fetch prompts from AI agent API
        response = requests.get(f"{agent_url}/prompts", timeout=5)

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                'success': True,
                'prompts': data.get('prompts', []),
                'total': data.get('total', 0)
            })
        else:
            return jsonify({
                'success': False,
                'error': f'AI agent returned status {response.status_code}',
                'prompts': []
            }), response.status_code

    except requests.exceptions.RequestException as e:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch prompts from AI agent: {str(e)}',
            'prompts': []
        }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Unexpected error: {str(e)}',
            'prompts': []
        }), 500
