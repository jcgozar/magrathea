# Standards

A standard says what an acceptable resource looks like. Agents write infrastructure
code; these files, and the policies that enforce them, decide whether it is accepted.

## Rule format

Every rule has:

| Field | Meaning |
| --- | --- |
| ID | Stable, never reused: `K8S-001`, `PG-004`, `COMMON-001`. Policies and test names carry the same ID. |
| Strength | **MUST** blocks the PR. **SHOULD** warns. |
| Rule | One sentence, testable. |
| Enforced by | The mechanism that checks it. A rule with no mechanism is not a rule. |
| Status | `implemented` (a policy and a test exist) or `planned` (documented only). |

## Enforcement layers

| Layer | Tool | When it runs | Where |
| --- | --- | --- | --- |
| Plan policy | OPA/Rego via Conftest on `tofu show -json` output | On every PR, after `tofu plan` | `policy/conftest/` |
| Cluster admission | Kyverno | At apply time, and as a background scan | `policy/kyverno/` |
| Scheduled checks | CI job | Nightly | planned |

## Changing a standard

- Standards and policies sit behind CODEOWNERS (`../.github/CODEOWNERS` at the repo root). Agents may
  propose changes, but only a human owner can approve them.
- A PR that changes a standard must not also change the infrastructure it is
  judged against.
- Every rule needs a passing and a failing test before it is marked `implemented`.

## Exceptions (planned)

Waivers will live in `policy/waivers.yaml`, one entry per waiver, each with a rule
ID, the resource address, a reason and an expiry date. Expired waivers fail CI.
No waiver mechanism is wired into the policies yet.

```yaml
# policy/waivers.yaml (format only, not enforced yet)
waivers:
  - rule: PG-006
    resource: aws_db_instance.app
    reason: one-off load test
    expires: 2026-12-01
```

## Standards

- [EKS cluster](eks-cluster.md)
- [Postgres](postgres.md)
- [Local setup](local-setup.md)
- [FinOps](finops.md)
- [Domain platform](domain-platform.md) (shared infrastructure for several projects; project modes)
- [AWS deployment architecture](aws-architecture.md) (documentation conventions, no policy)
