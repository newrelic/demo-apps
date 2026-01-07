"""
Flask application configuration.
"""
import os
from datetime import timedelta


class Config:
    """Flask configuration class."""

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(32).hex())

    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # External services
    AGENT_URL = os.getenv('AGENT_URL', 'http://ai-agent:8001')
    MCP_URL = os.getenv('MCP_URL', 'http://mcp-server:8002')

    # New Relic
    NEW_RELIC_CONFIG_FILE = os.getenv('NEW_RELIC_CONFIG_FILE', '/app/newrelic.ini')
