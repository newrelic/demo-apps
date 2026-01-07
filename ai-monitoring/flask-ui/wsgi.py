"""
WSGI entry point for gunicorn.
This ensures proper New Relic instrumentation with WSGI.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
