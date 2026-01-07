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

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit with New Relic instrumentation
CMD ["newrelic-admin", "run-program", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
