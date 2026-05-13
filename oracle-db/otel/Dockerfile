FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL -o /tmp/nrdot.deb \
      https://download.newrelic.com/database-monitoring/nrdot-collector/nrdot-collector-host-linux-arm64-latest.deb \
    && dpkg -i /tmp/nrdot.deb \
    && rm /tmp/nrdot.deb

EXPOSE 4317 4318

ENTRYPOINT ["/usr/bin/nrdot-collector-host"]
CMD ["--config=/etc/nrdot-collector-host/config.yaml", \
     "--config=/etc/nrdot-collector-host/internal-telemetry.yaml"]
