FROM python:3.11-slim

WORKDIR /app

# Install curl for health checks
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set New Relic configuration
ENV NEW_RELIC_CONFIG_FILE=/app/newrelic.ini
ENV FLASK_APP=app.py

EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Run with gunicorn and New Relic instrumentation
CMD ["newrelic-admin", "run-program", "gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--log-level", "info", \
     "wsgi:app"]
