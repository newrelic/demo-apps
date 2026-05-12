# syntax=docker/dockerfile:1

# Stage 1: Build
FROM eclipse-temurin:17-jdk AS builder

# Install Maven
RUN apt-get update && \
    apt-get install -y --no-install-recommends maven && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy pom.xml first to leverage Docker layer caching for dependencies
COPY pom.xml .
RUN mvn dependency:go-offline -B

# Copy source and build
COPY src ./src
RUN mvn clean package -DskipTests -B

# Stage 2: Runtime
FROM eclipse-temurin:17-jre

# Install curl for healthchecks
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --system --gid 1001 relipeople && \
    useradd --system --uid 1001 --gid relipeople --create-home --home-dir /home/relipeople relipeople

WORKDIR /app

COPY --from=builder /build/target/relipeople-backend.jar /app/app.jar

RUN curl -L -o /app/newrelic.jar \
        https://download.newrelic.com/newrelic/java-agent/newrelic-agent/current/newrelic-agent.jar

COPY newrelic.yml /app/newrelic.yml

RUN chown -R relipeople:relipeople /app

USER relipeople

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8080/actuator/health || exit 1

CMD ["java", "-Xms256m", "-Xmx512m", "-XX:+UseG1GC", "-javaagent:/app/newrelic.jar", "-jar", "/app/app.jar"]
