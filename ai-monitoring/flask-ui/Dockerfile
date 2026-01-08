FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set New Relic configuration
ENV NEW_RELIC_CONFIG_FILE=/app/newrelic.ini

# Expose Flask port
EXPOSE 8501

# Run with gunicorn and New Relic instrumentation
CMD ["newrelic-admin", "run-program", "gunicorn", \
     "--bind", "0.0.0.0:8501", \
     "--workers", "4", \
     "--timeout", "120", \
     "--log-level", "info", \
     "--error-logfile", "-", \
     "--capture-output", \
     "wsgi:app"]
