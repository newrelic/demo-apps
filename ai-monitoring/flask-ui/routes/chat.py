"""
Chat Mode routes - Interactive chat assistant.
"""

from flask import Blueprint, render_template, jsonify, request, current_app
from services.agent_client import AgentClient
from utils.session_helpers import set_current_mode, get_chat_history, add_chat_message, clear_chat_history

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


@bp.route('/compare', methods=['POST'])
def compare_chat():
    """Send to both models for comparison."""
    agent_client = get_agent_client()
    data = request.get_json()
    message = data.get('message', '')

    # Add user message to history
    add_chat_message('user', message)

    # Get comparison result
    result = agent_client.compare_chat(message)

    if 'error' not in result:
        # Add both responses to history
        model_a_response = result.get('model_a', {}).get('response', '')
        model_b_response = result.get('model_b', {}).get('response', '')

        add_chat_message('assistant', f"[Model A] {model_a_response}", 'Model A')
        add_chat_message('assistant', f"[Model B] {model_b_response}", 'Model B')

    return jsonify(result)


@bp.route('/clear', methods=['POST'])
def clear_history():
    """Clear chat history from session."""
    clear_chat_history()
    return jsonify({'success': True})
