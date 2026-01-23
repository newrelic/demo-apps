# ==========================================
# Stage 1: Build Stage - Maven + JDK 17
# ==========================================
FROM eclipse-temurin:17-jdk AS builder

# Install Maven
RUN apt-get update && \
    apt-get install -y maven && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy pom.xml first (for dependency caching)
COPY pom.xml .

# Download dependencies (cached layer if pom.xml unchanged)
RUN mvn dependency:go-offline -B

# Copy source code
COPY src ./src

# Build the application (skip tests for faster build)
RUN mvn clean package -DskipTests -B

# ==========================================
# Stage 2: Agent Download Stage
# ==========================================
FROM debian:bookworm-slim AS agent-downloader

# Install curl and unzip
RUN apt-get update && \
    apt-get install -y curl unzip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Download New Relic Java Agent
WORKDIR /agent
RUN curl -O https://download.newrelic.com/newrelic/java-agent/newrelic-agent/current/newrelic-java.zip && \
    unzip newrelic-java.zip && \
    rm newrelic-java.zip

# ==========================================
# Stage 3: Runtime Stage - JRE 17
# ==========================================
FROM eclipse-temurin:17-jre

# Install wget for health checks
RUN apt-get update && \
    apt-get install -y wget && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy JAR from builder stage
COPY --from=builder /build/target/java-profiling.jar /app/java-profiling.jar

# Copy New Relic agent from agent-downloader stage
COPY --from=agent-downloader /agent/newrelic /opt/newrelic/

# Create non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser && \
    chown -R appuser:appgroup /app /opt/newrelic

USER appuser

# Expose application port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run with New Relic agent
CMD ["java", \
     "-javaagent:/opt/newrelic/newrelic.jar", \
     "-Xms512m", \
     "-Xmx1g", \
     "-XX:+UseG1GC", \
     "-jar", \
     "/app/java-profiling.jar"]
