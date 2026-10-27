# Magrathea

Builds projects to order. Tell Magrathea your idea and it scaffolds a repository with AI
agent personas, infrastructure standards enforced as code, CI, and a starter app for your
stack. You write the project context; the agents do the legwork through specs, ADRs and
PRs. (Named for the planet-building company in *The Hitchhiker's Guide to the Galaxy*.)

- **[Guide](docs/guide/README.md)**: getting started, using a project, customizing Magrathea
  for your company, sample projects, reference and FAQ
- [Plan](docs/PLAN.md)
- [Decisions](docs/adr/)
- [Agent context for working on Magrathea](AGENTS.md)

## Create a project

Open this folder in VS Code (trust it), start Claude Code, and run:

```
/new-project an expense tracker for a small team
```

Magrathea asks what it needs, drafts `CONTEXT.md` for your approval, then runs the
generator. Or run the generator yourself:

```sh
python3 tools/magrathea.py stacks
python3 tools/magrathea.py new ../my-app --name "My App" --stack react-java \
  --description "What it does" --owner @your-handle
```

The new repository has the personas, standards, CI and app skeleton; open it in VS Code
and start with `/feature <idea>`. Its own README explains the rest.

## Make it yours

Magrathea is the engine plus a set of defaults. A company keeps its own templates, stacks,
standards and personas in a **distribution**, a separate folder or repo that holds only what
differs from the defaults and names Magrathea as its upstream:

```sh
python3 tools/magrathea_cli.py new ../acme-site --distro examples/acme-platform \
  --name "Acme Site" --stack static-site
```

Projects follow the distribution; a Magrathea release reaches them only when the distribution
bumps its `upstream.ref`. See the [guide](docs/guide/03-customizing.md),
[examples/acme-platform](examples/acme-platform) and
[ADR 0007](docs/adr/0007-engine-and-distributions.md).

## What every project gets

| Where | What | Can you change it? |
| --- | --- | --- |
| `magrathea.json`, `magrathea.lock.json` | Where the base comes from, the pinned commit, `auto_merge` | Yes (`make upgrade` moves the pin) |
| `.magrathea/` | A git-ignored cache of this repo's `base/`: personas, standards, policies, scripts, workflow | **No.** It is not in the project; CI fails if it differs from the lock. |
| `local/` | Your additions: persona behavior, standards, policy | Yes, add only. You cannot reuse a base rule ID or write policy exceptions. |
| `app/` | The starter app for the stack | Yes (the developer persona's area) |
| `CONTEXT.md` | What the project is | Yours to write |

Because projects refer to the base rather than copy it, a standard added here reaches every
project on its next `make upgrade`.

If a project needs infrastructure, a CI/CD pattern or a rule the base lacks, its
`platform-engineer` writes a request (`/request-standard` in the project). Run `/add-standard`
here with that file: the `magrathea-platform-engineer` adds the standard, policy and tests,
bumps the version, and the `magrathea-reviewer` checks it. Then the project runs `make upgrade`.

## Working on Magrathea

```sh
make test     # base script tests, generator tests, Rego tests (needs opa)
make sample   # generate a throwaway project and the Acme example, and verify them
```

The `magrathea-platform-engineer` maintains `base/`, `templates/` and `tools/`; the
`magrathea-reviewer` reviews its changes independently. Their sources are in `meta/` and
`make sync` generates `.claude/`. Commands: `/new-project`, `/add-standard`, `/add-stack`.

## Stacks

| Stack | Contents | Tested |
| --- | --- | --- |
| `react-java` | React 18 + TypeScript (Vite), Spring Boot 3 on Java 21, Dockerfiles, CI | Template rendering only. The Maven and npm builds have **not** been run. |
| `java-service` | One Spring Boot 4.1 service on Java 25 (LTS), multi-stage non-root Dockerfile, CI that tests and pushes to ghcr.io | Rendering by `make test`. Maven verify and Docker build/run were done by hand once (manual). TODO: confirm Boot 4.1 support for Java 25 and re-check pinned tags; CI workflows never run (see the stack's `notes.md`). |

## Limits

- The path guard covers the file-editing tools, not shell commands. CODEOWNERS and CI are
  the real backstop.
- The lock lives in each project, so a changed pin shows up in review rather than being blocked;
  see ADR 0006.
- The Kyverno policies, the CI workflows and the policies against a real `tofu` plan are
  untested.
- None of this has run in a live Claude Code session yet.

## License

Apache License 2.0; see [LICENSE](LICENSE). Projects you generate with Magrathea are yours and are
not bound by this license, apart from any files you keep from `base/` or `templates/`, which stay
under it.
