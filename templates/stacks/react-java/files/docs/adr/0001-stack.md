# 0001. Stack: React + Java (Spring Boot)

Status: Accepted (chosen when the project was scaffolded by Magrathea @@magrathea_version@@)

## Context

@@name@@ needed a starting stack. The choice came from the person who scaffolded it.

## Decision

- Web: React 18 + TypeScript, built with Vite, served by unprivileged nginx.
- API: Spring Boot 3 on Java 21, built with Maven.
- Both are containers with pinned, non-root images, described by a `service.yaml` each.

## Consequences

- Changing the stack later means a new ADR that supersedes this one.
- The Java package `com.example.app` is a placeholder and should be renamed.
- Infrastructure comes only through `service.yaml` needs and the standards in `.magrathea/`.
