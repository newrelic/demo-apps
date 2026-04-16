FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV NEW_RELIC_CONFIG_FILE=/app/newrelic.ini
ENV FLASK_APP=app.py

EXPOSE 5001

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

CMD ["newrelic-admin", "run-program", "gunicorn", \
     "--bind", "0.0.0.0:5001", \
     "--workers", "2", \
     "--timeout", "60", \
     "--log-level", "info", \
     "wsgi:app"]
