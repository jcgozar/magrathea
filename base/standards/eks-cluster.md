# EKS cluster standard

Applies to every Kubernetes cluster the platform creates on AWS. Local clusters
(kind or k3d) follow the in-cluster rules (K8S-005 to K8S-008) but not the AWS ones.

## Providing and consuming a cluster

A cluster is either owned by the project (`standalone`, the default) or supplied by a domain
platform that several projects share ([domain-platform.md](domain-platform.md)). The **Part**
column says which side a rule is about:

- **provide**: whoever creates the cluster. A domain platform repository (`type:
  "domain-platform"` in `magrathea.json`), or a `standalone` project.
- **consume**: whoever deploys onto a cluster. A project in `domain` mode, or a `standalone`
  project.
- **both**: applies to any plan, whatever the repository.

A project with no `infra_mode` in `magrathea.json` is `standalone` and is subject to every
rule, as before. A project in `domain` mode is subject to the **consume** and **both** rules and
may not create the cluster, so the **provide** rules do not apply to it.

## Rules

| ID | Strength | Part | Rule | Enforced by | Status |
| --- | --- | --- | --- | --- | --- |
| COMMON-001 | MUST | both | Carries the tags `app`, `env` and `owner` | `policy/conftest/lib.rego` | implemented |
| COMMON-002 | MUST | both | `env` is `dev` or `prod` | `policy/conftest/lib.rego` | implemented |
| K8S-001 | MUST | provide | The API endpoint is private, or public access is limited to listed CIDRs (never `0.0.0.0/0`) | `policy/conftest/eks.rego` | implemented |
| K8S-002 | MUST | provide | Secrets are encrypted with a KMS key, and all five control-plane log types are enabled | `policy/conftest/eks.rego` | implemented |
| K8S-003 | MUST | consume | Workloads use IRSA or EKS Pod Identity; no static IAM access keys | `policy/conftest/eks.rego` (blocks `aws_iam_access_key`) | implemented |
| K8S-004 | MUST | provide | Node launch templates require IMDSv2 (`http_tokens = "required"`) | `policy/conftest/eks.rego` | implemented |
| K8S-005 | MUST | consume | Containers set CPU and memory requests and a memory limit; pods run as non-root | `policy/kyverno/k8s-005-resources-and-nonroot.yaml` | implemented |
| K8S-006 | MUST | consume | Images use a pinned tag (never `latest`) from an approved registry | `policy/kyverno/k8s-006-images.yaml` (registry placeholders to fill in) | implemented |
| K8S-007 | MUST | consume | Each namespace has a ResourceQuota and a default-deny ingress NetworkPolicy | `policy/kyverno/k8s-007-namespace-defaults.yaml` | implemented (egress planned) |
| K8S-008 | SHOULD | consume | Production workloads with 2 or more replicas have a PodDisruptionBudget | Kyverno, warn mode | planned |
| K8S-009 | MUST | provide | The cluster version stays within one minor release of the latest EKS-supported version | A scheduled check that opens an upgrade issue, or a reminder to the operator who applies by hand | planned |
| K8S-010 | MUST | consume | Changes to workloads reach the cluster only through Argo CD. This is about workloads, not about the OpenTofu that creates the cluster and its add-ons | Argo CD RBAC, plus restricted cluster access for humans and agents | planned |

## Why these rules

- **K8S-001 to K8S-004** close the common ways a cluster gets compromised or becomes unauditable: an open API server, readable secrets, missing audit logs, long-lived keys, and the instance metadata service.
- **K8S-005 and K8S-006** keep workloads predictable and traceable. Requests let the scheduler place pods, a memory limit contains leaks, and pinned tags make a deploy reproducible. CPU limits are deliberately not required.
- **K8S-007** gives each namespace a blast-radius boundary by default.
- **K8S-009 and K8S-010** keep the cluster supportable and make git the only path to change for
  workloads. A domain platform is applied by hand from a reviewed plan, so K8S-009 can be a
  reminder to the operator rather than an automated job; K8S-010 does not cover that apply.

## Notes

- K8S-003 is **consume** because it is about workload identity, but its Rego blocks static IAM
  keys in any plan, so it applies to the plans of both repository types. K8S-004 is **provide**
  (nodes belong to whoever creates the cluster). K8S-007 is **consume** (a project creates its
  namespace and objects); the admission policy that enforces it is installed by the provider.

- Quota values and the registry allowlist are starting values; adjust them for your account.
- The plan policies see only what the plan shows. Settings that are unknown until apply
  (for example a computed default) are treated as the provider default.
