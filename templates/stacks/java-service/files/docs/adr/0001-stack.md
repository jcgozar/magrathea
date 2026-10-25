# 0001. Stack: Java microservice (Spring Boot)

Status: Accepted (chosen when the project was scaffolded by Magrathea @@magrathea_version@@)

## Context

@@name@@ needed a starting stack. The choice came from the person who scaffolded it.

## Decision

- One Spring Boot 4 service on Java 25 (LTS), built with Maven.
- Built as a container: multi-stage Dockerfile, pinned non-root JRE image, described by `app/service.yaml`.
- CI tests the service and pushes the image to ghcr.io tagged with the git sha.

## Consequences

- Unverified when scaffolded (see Magrathea's `templates/stacks/java-service/notes.md`): that Spring Boot
  4.1 officially supports Java 25, that the pinned image tags and versions are still current, and the CI
  workflows (never run).
- Changing the stack later means a new ADR that supersedes this one.
- The Java package `com.example.app` is a placeholder and should be renamed.
- Infrastructure comes only through `service.yaml` needs and the standards in `.magrathea/`.
