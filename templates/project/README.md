# @@name@@

@@description@@

Scaffolded by [Magrathea](https://github.com/jcgozar/magrathea) @@magrathea_version@@ with the
@@stack_title@@ stack.

- [CONTEXT.md](CONTEXT.md): what this project is (write this first)
- [AGENTS.md](AGENTS.md): how agents work here
- [Workflow](.magrathea/docs/WORKFLOW.md)
- [Decisions](docs/adr/)

## Getting started

```sh
git init && git add . && git commit -m "Scaffold from Magrathea"
make setup     # fetch the pinned Magrathea base into .magrathea/ (do this after every clone)
```

1. Open the folder in VS Code and trust it (the agents' path guards are hooks, and Claude
   Code runs project hooks only in trusted folders).
2. Fill in `CONTEXT.md`, or ask the `pm` agent: "Use the pm agent to draft CONTEXT.md from
   these notes: ...".
3. `/agents` lists the personas. `/feature <idea>` runs spec, architecture review (a TRD when
   needed), build and independent review, stopping for your approval each time.
4. Replace the placeholder owner in `.github/CODEOWNERS`.

Requirements: `python3`. Optional: `opa` (policy tests), `conftest` (check plans).

## What you can and cannot change

The base (personas, standards, policies, scripts) lives in the Magrathea repo. This project
refers to it through `magrathea.json` and pins an exact commit in `magrathea.lock.json`;
`.magrathea/` is a git-ignored cache. Add behavior and standards under `local/` (see
`local/README.md`). `make verify` and CI enforce that the cache matches the lock.

To get what Magrathea has added since (new standards, infrastructure types, persona
improvements), run `make upgrade` and review the diff to `magrathea.lock.json`.
Missing something? `/request-standard` writes the request for Magrathea.

The reviewer persona classifies each pull request as low, medium or high risk. When
`auto_merge` is `low` in `magrathea.json` (the default), it approves and merges low-risk PRs
whose CI is green and which the independent reviewers have no blockers on; everything else is
flagged for you. Set it to `off` to merge everything yourself.
