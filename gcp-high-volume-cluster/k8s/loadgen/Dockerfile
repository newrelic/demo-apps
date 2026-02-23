FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY locustfile.py .
CMD locust --headless -u ${USERS:-100} --spawn-rate 10 2>&1
