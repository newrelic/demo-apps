FROM eclipse-temurin:17-jdk
WORKDIR /app
COPY HelloWorld.java ./
RUN javac HelloWorld.java
EXPOSE 8080
ENTRYPOINT ["java", "HelloWorld"]
