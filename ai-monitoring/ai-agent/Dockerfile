FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set New Relic configuration file location
ENV NEW_RELIC_CONFIG_FILE=/app/newrelic.ini

# Expose agent API port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the agent service with New Relic instrumentation
CMD ["newrelic-admin", "run-program", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
