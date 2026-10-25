- `app/api/`: Spring Boot 3 (Java 21, Maven). Health at `/actuator/health`, example endpoint
  `GET /api/hello`. Tests with `./mvnw test` or `mvn test`.
- `app/web/`: React 18 + TypeScript on Vite. `npm install`, `npm run dev` (proxies `/api` to
  `localhost:8080`), `npm run build`.
- Each has a `Dockerfile` (non-root, pinned base images). `app/api/service.yaml` is the service
  contract: what the service is and what infrastructure it needs. The developer persona edits
  only that file to ask for infrastructure.
- The Java package is `com.example.app`. Rename it early (`architect` or `developer`).
- CI: `.github/workflows/api.yml` and `web.yml` build and test on changes to each.
- CI: `.github/workflows/local-setup.yml` (SETUP-006) runs the Quick start of `app/api/README.md`
  and `app/web/README.md` as one bash script per app (Java 21, Node 22). Apps without a README are
  skipped. No foreground servers in Quick start. Never run; TODO: confirm Docker/Testcontainers on
  the runner.
