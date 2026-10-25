# Changelog

What a project sees after `make upgrade`.

## 0.6.1

Fixes after an independent review of 0.6.0. Still nothing is enforced on a project without the new fields.

- **Human approval recorded:** the `K8S-010` and `AWSARCH-004` rewordings listed under 0.6.0 were approved
  by the human as written. `K8S-009` and `AWSARCH-006` were accepted via ADR 0009. No rule was weakened.
- `magrathea_lock.py mode-change`: when the previous `magrathea.json` is missing, empty or invalid it still
  exits 0 but now prints a visible `WARNING ... SKIPPED` on stderr.
- `DOMAIN_NAME` is matched with `fullmatch`, so a domain with a trailing newline (`"payments\n"`) now fails
  `verify` (DOMAIN-002). A project that had such a value in `magrathea.json` will see a failure.
- `domain.rego` (DOMAIN-001) shared types now also include `aws_route` and `aws_eks_access_entry`
  (routes in shared route tables, cluster access). A `domain`-mode project that creates them will now fail its plan.
  Not added on purpose: `aws_security_group` (projects legitimately create their own), and `aws_eip` and
  `aws_vpc_endpoint` (a project can legitimately own an Elastic IP or an endpoint for its own use; ask the
  operator via a Magrathea request if your domain wants them shared).
- Wording in `domain-platform.md`: DOMAIN-001 says plainly that no CI job runs the guard (it is enforced by
  running `make check` plus the `iac-reviewer` escalation). DOMAIN-003 says the script is tested on both sides, the
  CI step is untested, CODEOWNERS on `magrathea.json` plus branch protection is the real approval control (the
  label only marks a reviewed migration), and the step is `pull_request`-only so branch protection must stop direct pushes.
  DOMAIN-003 stays `implemented`: the check exists and its pass and fail paths are tested; the CI wiring is not.
- Correction to 0.6.0: it said `eks-cluster.md` defines every rule ID "only there". `COMMON-001` and `COMMON-002` are
  also defined, with the same text, in `postgres.md` (pre-existing, from before ADR 0009).
- **Follow-up for the human:** resolving the `COMMON-001`/`COMMON-002` duplicate between `eks-cluster.md` and
  `postgres.md` is left to you by decision; ADR 0007 (no rule ID defined by two upstream files) is technically
  violated upstream. No row was removed. A test now asserts the two definitions stay identical.

## 0.6.0

Shared domain platform support (ADR 0009, accepted 2026-10-25). **Nothing is enforced on a project
that does not set the new `magrathea.json` fields.** A project with no `infra_mode` is `standalone`,
exactly as before; `make upgrade` never adds or changes `infra_mode`, `domain` or `type`.

- **Changes to existing base rules (a human must look at these):**
  - `K8S-009` (planned): the Enforced-by text now allows "a reminder to the operator who applies by
    hand" besides a scheduled check. The rule and its strength (MUST) are unchanged; it stays `planned`.
  - `K8S-010` (planned): the rule text now says it covers changes to **workloads**, not the OpenTofu
    that creates the cluster and its add-ons. This narrows its scope on paper; it is `planned`, so nothing
    enforced changed.
  - `AWSARCH-004` and `AWSARCH-006` (planned, reviewer judgment): in a project whose `magrathea.json`
    has `infra_mode: "domain"`, an element the domain platform supplies is drawn as external rather than
    dashed `needs a Magrathea request`. `standalone` projects draw as before.
  - No rule ID was removed, no strength lowered, no `implemented` rule made `planned`.
- `eks-cluster.md` gains a **Part** column (`provide`, `consume`, `both`) and a short section on
  providing and consuming a cluster. Every rule ID is kept and defined only there. Status is still the last column.
- New standard `domain-platform` with `DOMAIN-001` to `DOMAIN-003` `implemented` (guard in
  `policy/conftest/domain.rego`; mode field validation and mode-change check in `magrathea_lock.py`) and
  `DOMAIN-010` to `DOMAIN-023` `planned`. The guard fires only on an explicit `infra_mode: "domain"` with a
  `domain`, using a data file CI writes (`magrathea_lock.py mode-data`). Make sure no `local/standards/` file of
  yours defines a `DOMAIN-*` ID (the lock check fails on a clash).
- `magrathea_lock.py verify` now also validates `infra_mode`, `domain` and `type` when present (DOMAIN-002).
  New subcommands `mode-data` and `mode-change`.
- `sync_agents.py` reads `type` from `magrathea.json` and `project-types.json` (new, in the base):
  `domain-platform` repositories do not get the `pm`, `architect`, `developer`, `ux`, `qa-eval` personas or the
  `/feature` command. Projects without a type are unaffected.
- `iac-reviewer` persona: a new check for mode changes and for shared infrastructure in `domain` mode.
- Not done: FinOps treatment of a domain platform (FIN-009, FIN-010 unchanged), SSM read policy, tenancy
  limits, plan check that the domain platform exists, the Kyverno side.

## 0.5.1

- `pm` persona: the "never invent" rule no longer names specific data sources (it named four
  from one example project); it now says third-party services and data sources. Same rule,
  generic wording. Nothing for a project to do; `make upgrade` picks it up.

## 0.5.0

- New standard `aws-architecture` (AWSARCH-001 to AWSARCH-009): how the `architect` draws the
  "Deployment architecture" section of a TRD for projects on AWS (PlantUML text, elements labeled
  with covering rule IDs, uncovered elements dashed and marked `needs a Magrathea request`). All
  rules are `planned` (reviewer judgment); no Rego was added. AWS icon license terms, icon
  library include paths and the minimum PlantUML version are TODO for a human to verify.
- `architect` persona: new step to write that section (or `n/a` off AWS) and a `docs/trd/NNNN-<slug>.puml`
  (already within its writable path `docs/trd/**`). No new persona.
- Project template changes (new projects only; `make upgrade` does not rewrite files you own):
  `docs/trd/TEMPLATE.md` gains a "Deployment architecture" section, the `Makefile` gains
  `make diagrams` (renders `docs/trd/*.puml` to SVG; skips with a message if `plantuml` is not
  installed, `REQUIRE=1` makes that fail), and `.gitignore` ignores `docs/trd/*.svg` and `*.png`.
  To adopt in an existing project, copy those three pieces by hand.
- What could break: the new rule IDs `AWSARCH-*` must not already exist in your `local/standards/`
  (the lock check fails on a clash; rename yours). The architect will now ask for a diagram in
  new AWS TRDs, and `architecture-reviewer` may flag an existing TRD that lacks one. Unrendered
  PlantUML is untested here.

## 0.4.0

- New standard `finops` (FIN-001 to FIN-010) and a new base persona `finops` (access
  `edit-no-shell`, writes only `docs/finops/**`; no shell, no network). It produces a cost report
  per ADR/TRD that chooses infrastructure and per `plan.json`, from a template
  (`.magrathea/docs/FINOPS-TEMPLATE.md`) and from dated pricing snapshots that a human adds in
  `docs/finops/pricing/`. Magrathea ships no prices; without a snapshot every price is `TODO`.
- New command `/finops <adr, trd or plan.json>`. `/feature` now runs `finops` on infrastructure
  ADRs/TRDs before the approval stop, and on `plan.json` before the `iac-reviewer`. WORKFLOW.md
  has the new handoffs, gates and the `finops` writable path.
- Stricter, not looser: `platform-engineer` no longer writes its own "cost note"; it requests a
  finops report for the exact plan (by SHA-256) and links it. `iac-reviewer` treats a missing
  report, or one for a different plan, as a blocker (it was "estimate is plausible").
  `architect` names the finops report in infrastructure ADRs; `architecture-reviewer` records a
  major finding when an infrastructure ADR links none. Expect these on the next infrastructure change.
- FIN-009 (SHOULD, warn, implemented): a Conftest warning for any `aws_budgets_budget` with no
  notification subscriber. All other FIN rules are `planned` (persona judgment).
- Existing projects: `docs/finops/` is not created by `make upgrade` (it lives in `templates/`).
  The persona creates the folder when it writes a report; copy `docs/finops/README.md` and add a
  `/docs/finops/pricing/` line to CODEOWNERS if you want the new-project layout. Add a monthly
  budget per environment to `CONTEXT.md` for FIN-010.

## 0.3.0

- New standard `local-setup` (SETUP-001 to SETUP-006, all `planned`: enforced by persona judgment,
  not by a policy). The `developer` persona now creates or updates a local-setup README for each
  app it changes (template: `.magrathea/docs/LOCAL-SETUP-TEMPLATE.md`), runs every documented
  command, and separates run from unrun commands in the hand-off. The `reviewer` persona records a
  finding when the README is missing or stale or setup is unverified. A CI job that runs the quick
  start is not included in the base.
- Existing apps without a local-setup README get a reviewer finding (major, not blocker) on their
  next change. README path: `app/README.md`, or `app/<name>/README.md` with several apps.
- SETUP-006: stack templates carry a CI workflow, `.github/workflows/local-setup.yml` (so far the
  `react-java` stack), which runs each app README's Quick start as one bash script. New projects
  with that stack get it automatically; existing projects get
  nothing on `make upgrade` (it lives in `templates/`) and must copy it. It is untested.

## 0.2.0

- **Projects now refer to the base instead of holding a copy.** `.magrathea/` is a git-ignored cache
  fetched from the Magrathea repo at the commit pinned in `magrathea.lock.json`. `make upgrade` brings in
  new standards, infrastructure types and persona changes. Existing 0.1.0 projects need the new
  `magrathea.json`, `magrathea.lock.json` and `scripts/magrathea_sync.py` (re-scaffold or copy them in).
- Persona `platform-sre` is now `platform-engineer`: it writes IaC from the standards and sends
  requests to Magrathea (`requests/magrathea-*.md`) for missing standards, infrastructure types or
  CI/CD patterns.
- New independent reviewers: `architecture-reviewer` (code vs TRD, ADRs, spec) and `iac-reviewer`
  (infrastructure vs standards).
- `architect` reviews the spec and writes a TRD (`docs/trd/`) when the change is complex, there is
  no architecture yet, or new infrastructure is needed.
- `reviewer` classifies pull requests as low, medium or high risk (`review/risk.json`,
  `scripts/review_risk.py`). With `auto_merge: "low"` in `magrathea.json` it approves and merges
  low-risk PRs when CI is green and no independent reviewer has a blocker; otherwise it flags a human.
- `/feature` and `/review` updated for the above. Magrathea itself gets `magrathea-platform-engineer`
  and `magrathea-reviewer` personas and `tools/check_base_change.py`.

## 0.1.0

- First release. Base personas (pm, architect, developer, reviewer, security, platform-sre,
  qa-eval, ux), standards for EKS clusters and Postgres with Rego policies and tests, Kyverno
  policies (untested), workflow, `/feature`, `/review` and `/request-standard` commands, the
  path guard, the lock check. Stack: react-java.
