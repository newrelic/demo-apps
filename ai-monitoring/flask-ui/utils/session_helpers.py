"""
Flask session management helpers.
"""

from flask import session
from datetime import datetime


def add_chat_message(role: str, content: str, model: str = None):
    """
    Add a message to the chat history.

    Args:
        role: 'user' or 'assistant'
        content: Message content
        model: Model name (optional, for assistant messages)
    """
    if 'chat_history' not in session:
        session['chat_history'] = []

    message = {
        'role': role,
        'content': content,
        'timestamp': datetime.now().strftime('%H:%M:%S')
    }
    if model:
        message['model'] = model

    session['chat_history'].append(message)
    session.modified = True


def get_chat_history():
    """Get the chat history from session."""
    return session.get('chat_history', [])


def clear_chat_history():
    """Clear the chat history from session."""
    session.pop('chat_history', None)
    session.modified = True


def set_current_mode(mode: str):
    """Set the current UI mode."""
    session['current_mode'] = mode
    session.modified = True


def get_current_mode():
    """Get the current UI mode."""
    return session.get('current_mode', 'repair')
