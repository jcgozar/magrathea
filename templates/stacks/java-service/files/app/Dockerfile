# Pinned tags, non-root runtime (standards K8S-005 and K8S-006). Build context is this folder.
FROM maven:3.9.16-eclipse-temurin-25-noble AS build
WORKDIR /src
COPY pom.xml .
RUN mvn -q -B dependency:go-offline
COPY src ./src
RUN mvn -q -B -DskipTests package
COPY Healthcheck.java .
RUN javac -d /src/healthcheck Healthcheck.java

# JRE only. The image has no curl or wget, so the health check is a small Java program compiled in the build stage
# (a JRE cannot run source files).
FROM eclipse-temurin:25.0.4.1_1-jre-noble
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER 10001
WORKDIR /app
COPY --from=build --chown=10001:10001 /src/target/app.jar app.jar
COPY --from=build --chown=10001:10001 /src/healthcheck /app/healthcheck
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD ["java", "-Xshare:auto", "-XX:TieredStopAtLevel=1", "-cp", "/app/healthcheck", "Healthcheck"]
# Container-aware heap (a share of the container memory limit); exit on OOM so the orchestrator restarts it.
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-XX:+ExitOnOutOfMemoryError", "-jar", "/app/app.jar"]
