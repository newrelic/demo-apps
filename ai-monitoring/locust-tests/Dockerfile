FROM locustio/locust:2.20.0

# Copy prompt pool from ai-agent (for comprehensive testing)
# Use --chown to set proper ownership for locust user
COPY --chown=locust:locust ai-agent/prompt_pool.py /locust/prompt_pool.py

# Copy locustfile
COPY --chown=locust:locust locust-tests/locustfile.py /locust/locustfile.py

WORKDIR /locust

# Expose Locust web UI and worker ports
EXPOSE 8089 5557

# Default command (can be overridden in docker-compose)
CMD ["locust"]
