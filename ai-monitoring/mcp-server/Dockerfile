FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set New Relic configuration file location
ENV NEW_RELIC_CONFIG_FILE=/app/newrelic.ini

# Expose MCP server port
EXPOSE 8002

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Run the MCP server with New Relic instrumentation
CMD ["newrelic-admin", "run-program", "python", "server.py"]
