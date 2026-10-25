# Project context for agents

Read this first, then `CONTEXT.md`. Every agent persona works from them.

## What this is

@@name@@: @@description@@

What the project is, who it is for and its constraints are in [CONTEXT.md](CONTEXT.md).
Humans set direction; AI agents with distinct personas do most of the legwork through git
artifacts: specs, ADRs and PRs. The flow is in [.magrathea/docs/WORKFLOW.md](.magrathea/docs/WORKFLOW.md).

## Stack: @@stack_title@@

@@stack_notes@@

## Repo layout

```
.magrathea/  READ-ONLY cache of the Magrathea base (git-ignored; `make setup` fetches it).
local/       what this project adds to the base (personas, standards, policy)
app/         the application code (see the stack section above)
platform/    infrastructure code and GitOps config for this project (platform-engineer)
specs/       one spec per feature (pm)
requests/    asks to the platform (developer, platform-engineer) and to Magrathea (/request-standard)
evals/       evals and reports (qa-eval)
docs/        ADRs, interfaces, runbooks, finops reports
.claude/     generated Claude Code agents and commands. Edit the sources, then `make sync`.
```

## The base comes from Magrathea

- `.magrathea/` is a read-only, git-ignored cache of the Magrathea base, fetched at the commit
  pinned in `magrathea.lock.json` (source and ref are in `magrathea.json`). It is not in this
  repo, and it changes only by `python3 scripts/magrathea_sync.py --update` (`make upgrade`),
  which brings in everything Magrathea has added since, including new standards. CI fails if the
  cache differs from the lock. Do not work around this.
- You may **add** behavior to a persona in `local/personas/`, standards in
  `local/standards/` and policy in `local/policy/`. You may not change or remove what the
  base defines, reuse a base rule ID, or write policy `exception` rules.
- If a kind of infrastructure, a CI/CD pattern or a rule has no standard in the base, do not
  invent a one-off. Write a request to Magrathea with `/request-standard`.

## Working agreements

- **Git is the handoff.** PM writes specs, architect writes ADRs, developers open PRs.
- **Humans approve every handoff for now,** except that the reviewer may merge a pull request
  classified low risk when every gate passes (see `.magrathea/docs/WORKFLOW.md`). Set
  `auto_merge` to `off` in `magrathea.json` to turn that off.
- **Do not edit `local/standards/` or `local/policy/`** in a PR that also changes the
  thing they judge. Propose standard changes separately; a human approves.
- **Developer agents have no cloud access.** Ask for infrastructure through the service
  YAML or a request. Never loosen a rule or add a waiver to make a PR pass.
- **Do not invent facts.** If a value, name or API detail is unknown, leave a clearly
  marked TODO and say what is missing.
- **Cite rule IDs** from `.magrathea/standards/` and `local/standards/` in PRs and reviews.

## Commands

```sh
make test      # Rego tests, base and local (needs opa)
make check PLAN=plan.json   # check a real tofu plan (needs conftest)
make verify    # base intact, local additions valid
make sync      # regenerate .claude/ after editing local/personas/
make setup     # fetch the pinned Magrathea base (after cloning)
make upgrade   # move to the newest base for the configured ref
```

Slash commands: `/feature <idea>`, `/review`, `/request-standard`, `/finops`.

Personas: pm, architect (writes TRDs), developer, reviewer (risk-tiered, may merge low-risk
PRs when `auto_merge` is `low`), architecture-reviewer, iac-reviewer, security, platform-engineer,
finops (costs infrastructure from dated pricing snapshots), qa-eval, ux. The persona that wrote something never reviews it.

## Current state

Scaffolded by Magrathea @@magrathea_version@@. Nothing here has been run yet except what
Magrathea tested when it generated the project; see the generator's notes.
