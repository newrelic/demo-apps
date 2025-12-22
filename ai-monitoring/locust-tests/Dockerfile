FROM locustio/locust:2.20.0

# Copy locustfile
COPY locustfile.py /locust/locustfile.py

WORKDIR /locust

# Expose Locust web UI and worker ports
EXPOSE 8089 5557

# Default command (can be overridden in docker-compose)
CMD ["locust"]
