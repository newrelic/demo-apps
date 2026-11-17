FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --uid 10001 loadgen

WORKDIR /srv/loadgen

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY generate_traffic.py ./

USER loadgen

CMD ["python", "-u", "generate_traffic.py"]
