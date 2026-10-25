# 4. Sample projects

Three walkthroughs. The commands and file trees below come from real runs of the generator. What
each one covers, and what was not run, is stated at the top.

| Sample | Shows | Run by |
| --- | --- | --- |
| [A. A single service](#a-a-single-service-java-service) | The smallest useful project | Generated and verified by `make test`. A Maven verify and Docker build were done by hand once. |
| [B. Web app plus API](#b-web-app-plus-api-react-java) | Two services in one repo | Generated and verified. **The npm and Maven builds have not been run.** |
| [C. A company distribution](#c-a-company-distribution-acme-platform) | Your own stack, standard, persona and template | Built by `make test` and `make sample`. |

All three assume you have done [Getting started](01-getting-started.md) and have
`alias magrathea='python3 /path/to/magrathea/tools/magrathea_cli.py'`.

## A. A single service (`java-service`)

```sh
magrathea --no-input new ../orders-svc --name "Orders Svc" --stack java-service \
  --description "Order API" --owner @you --yes
cd ../orders-svc && git init && git add . && git commit -qm "Scaffold" && make setup
```

What you get (trimmed):

```
orders-svc/
  CONTEXT.md  AGENTS.md  README.md  DESIGN.md  Makefile
  magrathea.json  magrathea.lock.json  scripts/magrathea_sync.py
  app/
    pom.xml  Dockerfile  Healthcheck.java  service.yaml  README.md
    src/main/...  src/test/...
  .github/
    CODEOWNERS
    workflows/ci.yml  service.yml  local-setup.yml
  specs/  docs/{adr,trd,finops,interfaces,runbooks}/  requests/  platform/{infra,gitops}/
  evals/  local/{personas,standards,policy}/
  .magrathea/   (git-ignored cache of the base)
  .claude/      (generated agents and commands)
```

A Spring Boot 4.1 service on Java 25: health at `/actuator/health` with liveness and readiness
probes, an example `GET /api/hello`, a multi-stage non-root Dockerfile with pinned tags, and CI that
runs `mvn verify`, builds the image on pull requests and pushes it to `ghcr.io` on the default
branch. Run it:

```sh
cd app && mvn spring-boot:run
curl http://localhost:8080/api/hello
```

### The service contract

`app/service.yaml` is how the developer says what the service needs, without writing cloud code:

```yaml
name: orders-svc
image: TODO-registry/orders-svc:0.1.0   # pinned tag, never :latest (K8S-006)
port: 8080
health: { path: /actuator/health, liveness: ..., readiness: ... }
resources: { requests: {cpu: 100m, memory: 384Mi}, limits: {memory: 512Mi} }
needs: []                                # e.g. a postgres database; each need must have a standard
```

Add `needs: [postgres]` and the `platform-engineer` writes the database infrastructure from the
Postgres standard (rules `PG-001`...), the `finops` persona estimates its cost, and the
`iac-reviewer` checks it. If a need has **no** standard (say a queue), the platform engineer
writes `requests/magrathea-<slug>.md` instead of improvising: that is the loop that makes your
Magrathea grow.

### A first feature (in Claude Code)

```
/feature add an /api/orders endpoint that returns a list of orders
```

Expected, in order, with you approving each step: a spec in `specs/`, the architect's verdict
(probably "No TRD needed" for a small endpoint), code and tests in `app/` on a branch
`feat/<slug>`, then the reviewers' verdicts and a risk tier. Low risk with a green CI is merged by
the reviewer; anything else waits for you.

> Not tested in a live session. Treat this as the intended behavior, not a guarantee.

## B. Web app plus API (`react-java`)

```sh
magrathea --no-input new ../run-dash --name "Run Dash" --stack react-java \
  --description "Running dashboard" --owner @you --yes
```

```
run-dash/
  app/
    api/   pom.xml  Dockerfile  service.yaml  src/...        # Spring Boot 3, Java 21
    web/   package.json  vite.config.ts  Dockerfile  service.yaml  src/...   # React 18 + Vite
  .github/workflows/  api.yml  web.yml  ci.yml  local-setup.yml
  ... (same project files as sample A)
```

Each service has its own `service.yaml`, Dockerfile and CI workflow, so they build and deploy
independently. `DESIGN.md` is a stub the `ux` persona holds the UI to; fill in your tokens before
asking for UI work, or it will list the missing decisions rather than invent them.

> The Maven and npm builds of this skeleton have **not** been run (no network in the build
> sandbox). Expect to fix versions on first build. The stack's notes list the TODOs.

## C. A company distribution (`acme-platform`)

This is the sample for the platform engineer. It lives in
[examples/acme-platform](../../examples/acme-platform).

```sh
cd /path/to/magrathea
magrathea stacks --distro examples/acme-platform
# java-service ...
# react-java   ...
# static-site  A single HTML page in site/, for projects that need no backend      <- added by Acme

magrathea --no-input new ../acme-site --distro examples/acme-platform \
  --name "Acme Site" --stack static-site --owner @acme-lead --yes
```

What differs in the new project, and why:

| You see | Because the distribution... |
| --- | --- |
| `site/index.html` | added the `static-site` stack (`templates/stacks/static-site/`) |
| `.github/CODEOWNERS` ends with `/platform/ @acme-lead @acme/platform-team` | replaced the CODEOWNERS template (`templates/project/.github/CODEOWNERS`) |
| `.magrathea/standards/acme-naming.md` with `ACME-001`..`ACME-003` | added a standard to its `base/` |
| `.claude/agents/compliance.md` | added a persona to its `base/agents/personas/` |
| Everything else (Postgres and EKS standards, the other ten personas, the workflow) | is Magrathea's default, unchanged |

The lock shows both layers:

```json
{
  "source": "/path/to/magrathea/examples/acme-platform",
  "version": "0.5.1",
  "tree_hash": "...",
  "upstream": { "source": "../..", "ref": null, "commit": null }
}
```

(`commit` is `null` because both layers here are plain folders. With git URLs both are full commit
hashes.) Now change the standard in the distribution and see an existing project pick it up:

```sh
echo '| ACME-004 | MUST | Buckets are private | reviewer judgment | planned |' \
  >> /path/to/magrathea/examples/acme-platform/base/standards/acme-naming.md
cd ../acme-site && make upgrade
# Magrathea base now at 0.5.1 (local path); 1 files changed
#   standards/acme-naming.md
# (or `magrathea upgrade ../acme-site`, which prints "Moved the base from 0.5.1 to 0.5.1; 1 files changed")
```

Undo that line afterwards if you are working in the Magrathea repo. To build your own, follow
[Customizing](03-customizing.md#set-one-up).

## Exercises

1. **Add a rule** to `acme-naming.md` and watch an existing project receive it (above).
2. **Break the rule-ID check.** In the distribution, add a file `base/standards/clash.md` that
   defines `PG-001`. Creating a project fails, naming both files.
3. **Remove a default.** Put `"remove": ["standards/aws-architecture.md"]` in `distro.json`,
   then create a project and check it is gone from `.magrathea/standards/`. Note what is left
   dangling: `architect.md` and `standards/README.md` still mention it. Removing a default does
   not rewrite the files that refer to it; replace those files in your distribution too.
4. **Tamper.** Edit a file in a project's `.magrathea/`, run `make verify` (it fails), then
   `make setup` (it restores).
5. **Add a stack** of your own by copying `templates/stacks/static-site/` and changing it.
