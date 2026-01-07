"""
AI Monitoring Demo - Flask UI

Main Flask application factory that provides navigation between different modes:
- Repair Mode: Autonomous system repair
- Chat Mode: Free-form conversation for hallucination detection
- Model Comparison: Performance metrics and A/B testing
"""

from flask import Flask, session
from flask_session import Session
from config import Config


def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask-Session
    Session(app)

    # Register blueprints
    from routes.main import bp as main_bp
    from routes.repair import bp as repair_bp
    from routes.chat import bp as chat_bp
    from routes.comparison import bp as comparison_bp
    from routes.api import bp as api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(repair_bp, url_prefix='/repair')
    app.register_blueprint(chat_bp, url_prefix='/chat')
    app.register_blueprint(comparison_bp, url_prefix='/comparison')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Context processor for global template variables
    @app.context_processor
    def inject_globals():
        return {
            'current_mode': session.get('current_mode', 'repair'),
            'config': app.config
        }

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=8501)
