FROM locustio/locust:2.20.0

# Set working directory
WORKDIR /locust

# Copy locust files with proper permissions
COPY --chmod=644 locustfile.py /locust/locustfile.py
COPY --chmod=755 run-scenarios.sh /locust/run-scenarios.sh

# Default command - execute the script with bash
ENTRYPOINT ["/bin/bash"]
CMD ["/locust/run-scenarios.sh"]
