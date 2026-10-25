# Acme naming standard

Applies to every resource a project at Acme creates. Example content: replace it with your own
rules. Rules here are `planned` because no policy enforces them yet; a rule is `implemented`
only with a passing and a failing test (see `standards/README.md`).

## Rules

| ID | Strength | Rule | Enforced by | Status |
| --- | --- | --- | --- | --- |
| ACME-001 | MUST | Resource names start with `acme-` followed by the app name | reviewer judgment | planned |
| ACME-002 | MUST | Repositories use lowercase letters, digits and hyphens only | reviewer judgment | planned |
| ACME-003 | SHOULD | Environment appears as a suffix: `-dev` or `-prod` | reviewer judgment | planned |
