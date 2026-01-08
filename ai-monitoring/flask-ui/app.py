"""
New Relic AIM Demo - Flask UI

Main Flask application factory that provides:
- Tool Execution: Autonomous workflows with multi-step tool invocations
- Chat Assistant: Free-form conversation with AI agents
- Debug Mode: Raw tool testing capabilities (accessible at /debug)
"""

import logging
import sys
from flask import Flask, session
from flask_session import Session
from config import Config


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configure logging to stdout (for Docker logs)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Set Flask app logger to INFO
    app.logger.setLevel(logging.INFO)

    # Suppress werkzeug access logs (noisy from polling)
    logging.getLogger('werkzeug').setLevel(logging.WARNING)

    # Initialize Flask-Session
    Session(app)

    # Register blueprints
    from routes.main import bp as main_bp
    from routes.tools import bp as tools_bp
    from routes.chat import bp as chat_bp
    from routes.debug import bp as debug_bp
    from routes.api import bp as api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(tools_bp, url_prefix='/tools')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(debug_bp, url_prefix='/debug')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Context processor for global template variables
    @app.context_processor
    def inject_globals():
        return {
            'current_mode': session.get('current_mode', 'tools'),
            'config': app.config
        }

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8501)
