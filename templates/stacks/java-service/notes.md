- `app/`: one Spring Boot 4.1 service (Java 25 LTS, Maven). Health at `/actuator/health` (liveness and
  readiness probes enabled), example endpoint `GET /api/hello`. Tests with `mvn test` or `mvn verify`.
  The Java package is `com.example.app`; rename it early (`architect` or `developer`).
- `app/Dockerfile`: multi-stage, pinned tags (K8S-006), non-root numeric user 10001 (K8S-005), JRE-only
  runtime, container-aware JVM flags (`MaxRAMPercentage`, `ExitOnOutOfMemoryError`) and a `HEALTHCHECK`
  that runs `app/Healthcheck.java` (compiled in the build stage) (the runtime image has no curl or wget). `app/.dockerignore` keeps the
  build context small.
- `app/service.yaml` is the service contract: what the service is and what infrastructure it needs. The
  developer persona edits only that file to ask for infrastructure. Its `image:` is a TODO until a
  registry is chosen.
- CI: `.github/workflows/service.yml` runs `mvn verify` on changes under `app/`, builds the image on
  pull requests, and on pushes to the default branch pushes `ghcr.io/<owner>/<slug>:<git sha>` (never
  `latest`, K8S-006; `ghcr.io/<OWNER>/*` is in the registry allowlist template of the base). Uses plain
  `docker build` and `docker push`; no third-party actions beyond checkout and setup-java.
- CI: `.github/workflows/local-setup.yml` (SETUP-006) runs the Quick start of `app/README.md`
  (Java 25). Never run in CI; TODO: confirm on the runner.
- Versions chosen (checked manually against Maven Central and Docker Hub on 2026-10-24; Adoptium lists 25 as the
  latest LTS): Spring Boot 4.1.2 (latest GA; 4.2.0-RC1 exists but is not GA), Java 25, image
  `maven:3.9.16-eclipse-temurin-25-noble` for build and `eclipse-temurin:25.0.4.1_1-jre-noble` for runtime.
  TODO: re-check these when you scaffold; patch versions move. Spring Boot 4 moved test classes
  (`@WebMvcTest` is in `org.springframework.boot.webmvc.test.autoconfigure`, from
  `spring-boot-starter-webmvc-test`); examples written for Boot 3 will not compile unchanged.
- TODO: confirm the Spring Boot 4.1 documented Java baseline and that 4.1.2 officially supports Java 25
  (the parent pom only declares a default of 17; the skeleton built and tested on 25 when written).
- TODO: actions are pinned by major tag (`@v4`), not by commit SHA, as in `react-java`; pin by SHA.
  `actions/setup-java@v4` with Java 25 and `cache: maven` is unverified in both the `service` and
  `local-setup` jobs.
- Checks done by hand when the stack was written (Maven `verify` on JDK 25, Docker build, run and
  health check) are manual. `make test` only checks rendering and the shape of the files.
- The workflow token has `contents: read` at workflow level; only the image job has `packages: write`.
