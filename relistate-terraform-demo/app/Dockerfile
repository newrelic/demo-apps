FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    NEW_RELIC_CONFIG_FILE=/srv/app/newrelic.ini

RUN useradd --create-home --uid 10001 relistate \
    && mkdir -p /data \
    && chown relistate:relistate /data

WORKDIR /srv/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

USER relistate

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=2).status == 200 else 1)"

CMD ["newrelic-admin", "run-program", "gunicorn", "-w", "2", "-b", "0.0.0.0:8000", "app:app"]
