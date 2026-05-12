# Stage 1: Build WAR
FROM eclipse-temurin:17-jdk AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y maven && rm -rf /var/lib/apt/lists/*

COPY pom.xml .
RUN mvn dependency:go-offline -B

COPY src ./src
RUN mvn clean package -DskipTests -B

# Stage 2: Runtime
FROM tomcat:10.1-jdk17

RUN rm -rf /usr/local/tomcat/webapps/*

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY --from=builder /build/target/relipeople.war /usr/local/tomcat/webapps/ROOT.war

RUN curl -L -o /usr/local/tomcat/newrelic.jar \
        https://download.newrelic.com/newrelic/java-agent/newrelic-agent/current/newrelic-agent.jar

COPY newrelic.yml /usr/local/tomcat/newrelic.yml

ENV CATALINA_OPTS="-javaagent:/usr/local/tomcat/newrelic.jar -Xms256m -Xmx512m -XX:+UseG1GC"

EXPOSE 8080

CMD ["catalina.sh", "run"]
