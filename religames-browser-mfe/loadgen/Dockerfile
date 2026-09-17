FROM selenium/standalone-chromium:latest

# Switch to root to install Node.js
USER root

# Install Node.js 20
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /home/seluser/app

# Copy package files and install as root
COPY package*.json ./
RUN npm install --omit=dev

# Copy source files
COPY . ./

# Fix ownership for seluser
RUN chown -R seluser:seluser /home/seluser/app

# Switch back to selenium user
USER seluser

CMD ["node", "index.js"]
