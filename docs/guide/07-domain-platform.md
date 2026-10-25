# 7. Domain platforms

By default a project owns all its infrastructure (`standalone`). When several projects of one
domain (a team, a product area) should share a cluster, network and add-ons, the shared part
moves to its own repository, a **domain platform**, applied by one platform operator. Projects
attach to it and create only their own resources. The decision is in
[ADR 0009](../adr/0009-shared-domain-platform.md).

**Nothing changes for an existing project.** If `magrathea.json` has no `infra_mode`, the project
is `standalone`, as before; `make upgrade` never adds or changes these fields.

## What exists today

| Piece | State |
| --- | --- |
| `infra_mode`, `domain`, `type` in `magrathea.json`, checked by the lock check (DOMAIN-002) | Built, tested |
| `mode-change` script fails a mode change unless `--approved` (DOMAIN-003) | Script tested on both sides. The CI step that runs it with the `mode-migration` label is untested, and runs on pull requests only |
| Guard: a project in `domain` mode may not create a cluster, VPC and the like (DOMAIN-001) | Built; no CI job runs it, it runs when someone runs `make check` with a plan; Rego tests and one run with `conftest --data` against a synthetic plan; not against a real `tofu show -json` plan |
| `eks-cluster.md` split into provide and consume (Part column), same rule IDs | Built |
| `domain-platform` stack: OpenTofu skeletons for `global`, `network`, `eks`, `addons`, SSM parameters, runbook, issue template | Rendering tested. The OpenTofu has never been run or validated; every TODO is open |
| Persona and command subset for a `domain-platform` | Built, tested |
| `new --domain D`, `new-domain` | Built, tested |
| Tenancy limits, SSM read policy, plan check that the domain platform exists, FinOps treatment, creating a domain platform together with a project in one run | **Planned** (rules DOMAIN-010 to DOMAIN-023 are `planned`) |

## Create a domain platform

    python3 tools/magrathea_cli.py new-domain ../payments-platform --name "Payments"

This makes a separate folder (`git init` it yourself): its own `magrathea.json` with
`"type": "domain-platform"` and `"auto_merge": "off"`, six personas (`platform-engineer`,
`iac-reviewer`, `security`, `architecture-reviewer`, `reviewer`, `finops`) and the commands
`/review`, `/finops`, `/request-standard`. Account, region, CIDRs, the state backend and versions are TODO.
It is not ready to apply. The apply is manual, from a reviewed plan (`docs/runbooks/apply.md`).

## Attach a project

    python3 tools/magrathea_cli.py new ../checkout --name Checkout --stack java-service --domain payments

The project gets `"infra_mode": "domain", "domain": "payments"`. Run `make check PLAN=plan.json`
and DOMAIN-001 fails the plan if it creates shared infrastructure. Capacity requests go to the
operator as an issue in the domain platform repository (`requests/DOMAIN-REQUEST-TEMPLATE.md`),
never as a `magrathea-*` request.

Projects find the domain platform through SSM parameters named
`/<domain>/<region>/platform/<name>` (identifiers only, per region). The full parameter list and
the IAM read policy are TODO.

## Changing the mode later

Editing `infra_mode` moves nothing: it only changes which checks run. It is a migration of state,
identity, networking and data, planned and reviewed like any infrastructure change. CI fails a
pull request that changes `infra_mode`, `domain` or `type` unless it carries the `mode-migration`
label (adding the label re-runs the check), and `iac-reviewer` treats the change as an escalation. The label
only marks a migration that was reviewed; the real approval control is CODEOWNERS on `magrathea.json` plus
branch protection. The CI step runs on pull requests only, so a direct push to the default branch skips it:
branch protection must prevent direct pushes. The step has never run in CI.
DOMAIN-001 is not run by any CI job: it is enforced by whoever runs `make check`, plus the `iac-reviewer`. Magrathea has no tool for the migration.

## Limits

One AWS account (cross-account is out of scope); one domain platform per region (a second region is
deferred); a shared cluster suits similar, medium-sized projects, and one operator is a bottleneck.
