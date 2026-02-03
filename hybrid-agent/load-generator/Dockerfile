FROM selenium/standalone-chromium:latest

# Switch to root to install Node.js
USER root

# Install Node.js 18
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/seluser/app

# Copy package files and install as root
COPY load-generator/package*.json ./
RUN npm install

# Copy source files
COPY load-generator/ ./

# Fix ownership for seluser
RUN chown -R seluser:seluser /home/seluser/app

# Set environment variables
ENV STOREFRONT_URL=http://storefront:80
ENV SCENARIO_INTERVAL_MS=30000
ENV SCENARIOS=happy-path,out-of-stock,slow-payment

# Switch back to selenium user
USER seluser

CMD ["node", "index.js"]
