# Domain platform '@@domain@@': published parameters

This repository is the domain platform for `@@domain@@`. Projects find it through SSM
parameters. SSM parameters are account-local and regional, so every name includes the region:

    /@@domain@@/<region>/platform/<name>

A project reads the parameters of the region it deploys into. It does not read this repository's
Terraform state. No secrets go in these parameters, only identifiers (DOMAIN-010).

| Name | Value | Written by |
| --- | --- | --- |
| `vpc-id` | VPC ID | `platform/infra/network` |
| `private-subnet-ids` | comma-separated subnet IDs | `platform/infra/network` |
| `public-subnet-ids` | comma-separated subnet IDs | `platform/infra/network` |
| `cluster-name` | EKS cluster name | `platform/infra/eks` |
| `oidc-provider-arn` | OIDC provider ARN | `platform/infra/eks` |
| `ingress-class` | ingress class name | `platform/infra/addons` |

TODO: the list is not final. Add every output a project needs, and note each change to any
name: it is a published interface, and until a contract version exists every project in the
domain needs to be told.

TODO: which principal reads these (the project's CI role, or a plan-time principal) and the exact
read-only IAM policy for the prefix `/@@domain@@/<region>/platform/`. Only this repository's apply
principal may write it (DOMAIN-011). Magrathea has not verified the IAM details.

TODO: the tenancy limits projects get before the first one attaches (DOMAIN-020 to DOMAIN-023):
permission boundary for project IAM roles, namespace naming and ownership, IRSA trust scoped to
the project's namespace and service account, and how a project pipeline gets cluster credentials.
