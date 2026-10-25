# Project context for agents working on Magrathea

Read this first. This repo is the generator and the base for other projects, not an app.

## What this is

Magrathea scaffolds new projects. `tools/magrathea.py new` renders a project from
`templates/project/` and a stack in `templates/stacks/`, and writes `magrathea.json` pointing
the project at this repo's `base/`. Projects **refer** to the base (a pinned commit, fetched into
a git-ignored `.magrathea/`); they never hold a copy. Decisions: [docs/adr/](docs/adr/),
especially 0001 (standards as code), 0004 (tool-neutral personas), 0005 (scaffold), 0006
(base by reference) and 0009 (shared domain platform; accepted). Plan: [docs/PLAN.md](docs/PLAN.md).

## Layout

```
base/       what every project fetches by reference (must stay generic)
  agents/personas/  tool-neutral personas      standards/  rules with IDs
  policy/           Rego and Kyverno + tests   scripts/    sync, path guard, lock check, risk
  claude/commands/  slash commands             docs/       WORKFLOW.md
  review/risk.json  risk-tier rules            VERSION     bump on every change
  project-types.json  personas/commands a project `type` does not get (domain-platform)
examples/            a working example distribution (acme-platform), built by make test and make sample
templates/project/   files a new project owns (README, AGENTS, CONTEXT, CI, local/, bootstrap ...)
templates/stacks/    one folder per stack: stack.json, notes.md, files/
tools/               the generator, magrathea_cli.py (interactive front end), check_base_change.py and their tests
docs/guide/          the human guide: getting started, usage, customizing, samples, reference, FAQ
VERSION              the engine version (tools/ and the magrathea-* workflow); see ENGINE_CHANGELOG.md
meta/                Magrathea's own personas and commands (source for .claude/)
.claude/             generated from meta/ with `make sync`; do not edit
```

## Personas

Projects get `pm`, `architect`, `developer`, `reviewer`, `architecture-reviewer`, `iac-reviewer`,
`security`, `platform-engineer`, `qa-eval`, `ux` from `base/`. Here, in `meta/personas/`:

- `magrathea-platform-engineer` maintains `base/`, `templates/` and `tools/`. It answers requests
  from projects' platform engineers (`requests/magrathea-*.md`) for missing standards,
  infrastructure types and CI/CD patterns. A project's `platform-engineer` writes IaC from the
  standards; this one writes the standards.
- `magrathea-reviewer` independently reviews its changes. The author never reviews its own work.

Commands: `/new-project`, `/add-standard`, `/add-stack`.

## Rules

- Keep `base/` generic: no project names, no product or stack assumptions.
- Every change to `base/` bumps `base/VERSION` and adds a `CHANGELOG.md` entry. Every project
  receives it on its next `make upgrade`, so check what it could break.
- Changes to `tools/`, `meta/` or `templates/project/scripts/` bump `VERSION` and add an
  `ENGINE_CHANGELOG.md` entry; a workflow persona or command also bumps its own `version:`.
- Keep `docs/guide/` true: if behavior it describes changes, change the guide and the example
  (`tools/test_examples.py`) in the same change. Say what is planned, not built.
- Distributions (ADR 0007): a distribution file replaces the upstream file at the same path, and
  may not define a rule ID another upstream file defines. Keep `new_project(..., distro=None)` and
  `list_stacks(distro=None)` backward compatible: `tools/magrathea_cli.py` calls them positionally.
- Never weaken or remove a base rule without explicit human approval
  (`python3 tools/check_base_change.py --base <branch>` reports them).
- A rule is `implemented` only with a passing and a failing test.
- Templates use `@@placeholder@@`; the generator fails on unknown ones.
- Do not invent facts about cloud services or versions. Mark unknowns TODO.

## Commands

```sh
make test      # needs opa
make sample    # scaffold and verify a throwaway project in .scratch/
make sync      # regenerate .claude/ from meta/
python3 tools/magrathea_cli.py init   # then `new` (prompts: name, stack menu, ...), `stacks`, `upgrade`
```

## Current state

- Tested: the CLI (menu selection logic, config, git clone/ref/refresh/offline fallback, flags-only `new`, upgrade;
  raw key reading and the terminal menu were exercised once through a pseudo-terminal, not in CI), persona generator, path guard, risk classifier and merge gate, lock check, bootstrap
  (local path and git sources, pinning, moved tags), scaffolding, upgrade picking up a new
  standard, base-change checker, 46 Rego tests in total (`opa test`, includes the 8 DOMAIN-001 tests) against synthetic plans.
- `java-service` stack: rendering tested; its Maven `verify` (JDK 25) and Docker build, run and
  healthcheck were done once by hand (manual), not by `make test`.
- Not tested: the `react-java` Maven and npm builds (no network in the build sandbox), the
  Kyverno policies, real PlantUML rendering (`make diagrams` is tested only with the tool absent
  and with a stub `plantuml`), the AWS icon library, the CI workflows, fetching from a private
  GitHub repo, `gh pr merge` and `gh pr checks` as the reviewer persona uses them, policies against a real `tofu show -json`
  plan, and everything inside a live Claude Code session. Whether the personas follow their
  instructions has not been evaluated.
- Domain platform (ADR 0009, accepted 2026-10-25; base 0.6.1, engine 0.7.1). Tested: the mode fields and
  their validation (DOMAIN-002), the mode-change check script (DOMAIN-003), the persona and command subset
  for `type: "domain-platform"`, `new --domain` and `new-domain` (generator and CLI), upgrade adding no mode
  fields, 8 Rego tests for the DOMAIN-001 guard (counted within the 46 above), and a run of real `conftest --data` against a synthetic plan
  (in `make test` only if `conftest` is installed). Not tested: the CI mode-change step and the `mode-migration`
  label (the step runs on pull requests only; no CI job runs the DOMAIN-001 guard, only `make check`), the `domain-platform` OpenTofu (never run, validated or planned; `tofu` is not installed here), the
  guard against a real `tofu show -json` plan, SSM parameters in a real account. Planned: DOMAIN-010 to
  DOMAIN-023 (SSM interface, IAM read policy, plan check that the domain platform exists, tenancy limits),
  the FinOps treatment of a domain platform, creating a domain platform together with a project in one run,
  a platform-specific `risk.json`.
