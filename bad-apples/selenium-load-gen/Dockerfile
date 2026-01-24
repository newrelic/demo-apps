FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Detect architecture and install Chrome/Chromium accordingly
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        # Install Google Chrome for x86_64
        wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg && \
        echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
        apt-get update && \
        apt-get install -y google-chrome-stable && \
        rm -rf /var/lib/apt/lists/*; \
    else \
        # Install Chromium for ARM64/Apple Silicon
        apt-get update && \
        apt-get install -y chromium chromium-driver && \
        rm -rf /var/lib/apt/lists/* && \
        ln -s /usr/bin/chromium /usr/bin/google-chrome; \
    fi

# Install ChromeDriver (for amd64 only, arm64 uses chromium-driver from apt)
RUN ARCH=$(dpkg --print-architecture) && \
    if [ "$ARCH" = "amd64" ]; then \
        CHROMEDRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
        wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
        unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
        rm /tmp/chromedriver.zip && \
        chmod +x /usr/local/bin/chromedriver; \
    fi

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make script executable
RUN chmod +x load_gen.py

# Run load generation continuously
CMD ["python", "-u", "load_gen.py"]
