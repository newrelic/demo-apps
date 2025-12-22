"""Configuration for MCP Server."""

import os

# Docker configuration
DOCKER_HOST = os.getenv("DOCKER_HOST", "unix:///var/run/docker.sock")

# Locust configuration
LOCUST_URL = os.getenv("LOCUST_URL", "http://locust:8089")

# MCP Server configuration
MCP_PORT = int(os.getenv("MCP_PORT", "8002"))

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
