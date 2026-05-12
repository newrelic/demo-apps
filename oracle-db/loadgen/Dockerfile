FROM python:3.11-slim

WORKDIR /app

# Install Chromium and ChromeDriver directly from apt (works on amd64 + arm64)
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x load_gen.py

CMD ["python", "-u", "load_gen.py"]
