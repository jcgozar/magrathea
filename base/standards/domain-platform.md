# Domain platform standard

A **domain platform** is the shared infrastructure of a domain (a team or product area): VPC,
EKS cluster and node pools, add-ons, OIDC provider, registry, shared KMS keys, logging and
monitoring. It lives in its own repository (`type: "domain-platform"` in `magrathea.json`) and
is applied by hand by a platform operator. Projects in the same account attach to it
(`infra_mode: "domain"`) and create only project infrastructure. See ADR 0009 for the decision.

A project with no `infra_mode` in `magrathea.json` is `standalone`: it owns everything and none
of the rules marked "domain mode" below apply. Nothing here changes for existing projects until
someone edits `magrathea.json` on purpose, and that edit is a high-risk change (DOMAIN-003).

Same account only; cross-account is out of scope. A domain platform is per region.

## Rules

| ID | Strength | Rule | Enforced by | Status |
| --- | --- | --- | --- | --- |
| DOMAIN-001 | MUST | A project in `domain` mode creates no shared infrastructure (cluster, node groups, launch templates, VPC, subnets, gateways, route tables and routes, EKS add-ons and cluster access entries, OIDC provider). The mode is read from a data file CI writes from `magrathea.json` (`magrathea_lock.py mode-data`) and passes to conftest with `--data`; without it, or in `standalone` mode, the rule does nothing | `policy/conftest/domain.rego`. No CI job runs this guard; it is enforced only when the operator or developer runs `make check` (with the plan), plus the `iac-reviewer` escalation on shared infrastructure in `domain` mode | implemented |
| DOMAIN-002 | MUST | In `magrathea.json`, `infra_mode` is `standalone` or `domain`, `type` is `project` or `domain-platform`, `domain` is a lowercase name (letters, digits, hyphens) and is required when `infra_mode` is `domain`, and a `domain-platform` has no `infra_mode`. An absent field means `standalone` / `project` | `scripts/magrathea_lock.py verify` | implemented |
| DOMAIN-003 | MUST | A change to `infra_mode`, `domain` or `type` against the merge base fails CI unless the pull request is an approved migration (label `mode-migration`, which marks a migration that was reviewed; it is not itself the approval). Changing the mode moves no state, identity, networking or data; it is a planned migration | `scripts/magrathea_lock.py mode-change`. The script is tested on both sides (change fails, approved change passes); the CI step that runs it is untested. The real approval control is CODEOWNERS on `magrathea.json` plus branch protection; the label only marks a reviewed migration. The step runs on `pull_request` only, so a direct push to the default branch skips it and branch protection must prevent that | implemented |
| DOMAIN-010 | MUST | The domain platform publishes its outputs as SSM parameters named `/<domain>/<region>/platform/<name>`, holding identifiers only (never secrets). Renaming or removing one breaks projects | Reviewer judgment; `iac-reviewer` | planned |
| DOMAIN-011 | MUST | Only the domain platform's apply principal writes `/<domain>/<region>/platform/*`; projects have read-only access to that prefix and nothing else of the domain platform's. Which principal reads, and the exact IAM policy: TODO, to be verified by a human | Policy on the IAM plan | planned |
| DOMAIN-012 | MUST | In `domain` mode a plan fails with a clear message when the domain platform or its parameters are missing; it never falls back to creating them | Plan check, TODO | planned |
| DOMAIN-013 | MUST | The domain platform keeps separate states per area (`network`, `eks`, `addons`, and `global` if used), applied in that order; projects do not read these states | Reviewer judgment | planned |
| DOMAIN-020 | MUST | IAM roles a project creates carry a permission boundary set by the domain platform. Required before the first project attaches | Rego on the plan, TODO | planned |
| DOMAIN-021 | MUST | IRSA trust of a project's role is scoped to the project's own namespace and service account. Required before the first project attaches | Rego on the plan, TODO | planned |
| DOMAIN-022 | MUST | A project does not create `ClusterRole` or `ClusterRoleBinding` objects. Required before the first project attaches | Kyverno, TODO | planned |
| DOMAIN-023 | MUST | A project's namespace follows the naming and ownership rules of its domain platform. Required before the first project attaches | Kyverno, TODO | planned |

DOMAIN-001 to DOMAIN-003 are the only `implemented` rules: each has a passing and a failing test
(`opa test` for 001; `base/scripts/test_magrathea_lock.py` for 002 and 003). For 003 the tests cover the script only, not the CI step; that is the same meaning of `implemented` as for the other rules (the check exists and its pass and fail paths are tested), but the CI wiring is untested and a push straight to the default branch is not checked. The rest are
documented intent. The Part column of [eks-cluster.md](eks-cluster.md) says which Kubernetes
rules are for the provider and which for the consumer; those IDs are defined there only.

## The mode data file

`magrathea_lock.py mode-data --out .mode.json` writes
`{"magrathea": {"infra_mode": "standalone", "domain": null, "type": "project"}}` (the effective
values, with defaults applied). Pass it with `conftest test ... --data .mode.json`. The project
template's `make check` does this.

## Notes

- The shared type list in `domain.rego` is a starting list; add more with a Magrathea request.
  It does not include the container registry, which a project may need to write to (TODO).
- The guard sees only what a plan shows. It is a check, not access control: nothing stops a
  principal with enough IAM rights from creating these resources outside a plan.
- Reading the parameters at plan time is not built (DOMAIN-012); a project in `domain` mode
  gets its inputs from the domain platform's documented parameters by hand until it is.
