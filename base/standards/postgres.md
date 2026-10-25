# Postgres standard

Applies to every Postgres database the platform creates. On AWS this means
`aws_db_instance` with `engine = "postgres"`. Locally it is a Postgres container.

## Rules

| ID | Strength | Rule | Enforced by | Status |
| --- | --- | --- | --- | --- |
| COMMON-001 | MUST | Carries the tags `app`, `env` and `owner` | `policy/conftest/lib.rego` | implemented |
| COMMON-002 | MUST | `env` is `dev` or `prod` | `policy/conftest/lib.rego` | implemented |
| PG-001 | MUST | Encrypted at rest, and TLS required through a parameter group that sets `rds.force_ssl = 1` | `policy/conftest/rds.rego` | implemented |
| PG-002 | MUST | Never publicly accessible | `policy/conftest/rds.rego` | implemented |
| PG-003 | MUST | No ingress from `0.0.0.0/0` on port 5432 | `policy/conftest/rds.rego` (checks security group rules in the plan) | implemented, partial |
| PG-004 | MUST | Master credentials are managed by AWS Secrets Manager (`manage_master_user_password = true`) | `policy/conftest/rds.rego` | implemented |
| PG-005 | MUST | Backups on, with the minimum retention below. Prod also requires Multi-AZ, deletion protection and a final snapshot | `policy/conftest/rds.rego` | implemented |
| PG-006 | MUST | Instance class and storage ceiling come from the per-environment limits below | `policy/conftest/rds.rego` | implemented |
| PG-007 | SHOULD | Minor-version auto-upgrade is enabled | `policy/conftest/rds.rego` (warn) | implemented |
| PG-008 | MUST | Local databases run the same Postgres major version as AWS | CI check on the local definition | planned |
| PG-009 | MUST | Ingress only from the cluster's security group | Needs a reference to the cluster SG; not expressible from the plan alone | planned |

## Per-environment values (starting values)

| Setting | dev | prod |
| --- | --- | --- |
| Allowed instance classes | `db.t4g.micro`, `db.t4g.small`, `db.t4g.medium` | `db.t4g.medium`, `db.t4g.large`, `db.m6g.large` |
| Storage limit (allocated and autoscaling ceiling) | 50 GB | 500 GB |
| Minimum backup retention | 1 day | 7 days |
| Multi-AZ | optional | required |
| Deletion protection | optional | required |
| Final snapshot on delete | optional | required |

These values live in `policy/conftest/rds.rego` (`pg_limits`). Change them there
and in this table together.

## Notes

- PG-003 only catches rules that open the port to the whole internet. The positive
  rule, PG-009, is planned.
- PG-001's TLS check assumes the parameter group is created in the same plan. If it
  already exists elsewhere, the instance is accepted as long as it names a parameter group.
