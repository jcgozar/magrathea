# AWS deployment architecture standard

Applies to the "Deployment architecture" section of a TRD when the project's infrastructure is on
AWS (stated in `CONTEXT.md` or implied by the standards the TRD cites). It says how the
`architect` draws that infrastructure and how each drawn element ties back to a standard. If the
project is not on a cloud with an architecture standard, the section says `n/a`.

This standard is about documentation. It adds no Rego: no plan policy checks a diagram. Every
rule below is `planned` (checked by the `architecture-reviewer` and the human, not by a tool).
The rules that other standards own (K8S, PG, FIN) are enforced where those standards say.

## Rules

| ID | Strength | Rule | Enforced by | Status |
| --- | --- | --- | --- | --- |
| AWSARCH-001 | MUST | A TRD for a project on AWS has a "Deployment architecture" section; for any other project the section says `n/a` | `architecture-reviewer` judgment | planned |
| AWSARCH-002 | MUST | The diagram is PlantUML text committed as `docs/trd/NNNN-<slug>.puml` (same number and slug as the TRD) and referenced from the TRD. Rendered SVG/PNG is a build artifact and is not committed | `architecture-reviewer` judgment. The template `.gitignore` ignores `docs/trd/*.svg` and `*.png` only in newly scaffolded projects; existing projects must add those entries themselves | planned |
| AWSARCH-003 | MUST | Every drawn element carries a label with the rule ID or range of the standard that covers it (for example `K8S-001..K8S-004`) | `architecture-reviewer` judgment | planned |
| AWSARCH-004 | MUST | An element with no covering standard is drawn dashed and labeled `needs a Magrathea request`, and appears with the same status in the TRD's Infrastructure needs table. Exception: in a project in `domain` mode, an element the domain platform supplies is drawn as external (see Conventions), not dashed | `architecture-reviewer` judgment | planned |
| AWSARCH-005 | MUST | The diagram never shows what the standards forbid (for example a public database, or ingress from `0.0.0.0/0` to the database port) | `architecture-reviewer` judgment; PG-002, PG-003 and K8S-001 catch it later in the plan | planned |
| AWSARCH-006 | MUST | The diagram and the Infrastructure needs table list the same elements (elements supplied by a domain platform are marked external in both) | `architecture-reviewer` judgment | planned |
| AWSARCH-007 | MUST | The `.puml` holds no secrets, credentials, account IDs or real hostnames | `architecture-reviewer` and `security` judgment | planned |
| AWSARCH-008 | SHOULD | Elements are grouped by the nesting in the table below (cloud, region, VPC, subnet tier) and labels use the AWS service category names for service types (this is about names in labels, not about using images or icons; icon terms are TODO) | `architecture-reviewer` judgment | planned |
| AWSARCH-009 | SHOULD | The diagram source renders with `make diagrams` when PlantUML is installed | `architecture-reviewer` judgment. `make diagrams` is a convenience target in the project template, not an enforcement mechanism; real rendering is not exercised by Magrathea's tests | planned |

## Mapping from standards to diagram elements

Draw an element only for what the TRD needs. Label it with the IDs in the second column.

| Diagram element | Covering rules | Notes |
| --- | --- | --- |
| EKS cluster and control plane | K8S-001 to K8S-004, K8S-009, K8S-010 | Show the API endpoint as private or CIDR-limited (K8S-001) |
| KMS key for cluster secrets | K8S-002 | |
| Workload identity (IRSA or Pod Identity) | K8S-003 | Draw the role binding, never an access key |
| Node group and launch template | K8S-004 | |
| In-cluster workloads and namespaces | K8S-005 to K8S-008 | Namespace boundary carries the quota and default-deny label (K8S-007) |
| Postgres on RDS | PG-001 to PG-007, PG-009 | Private subnets only (PG-002); ingress arrow only from the cluster (PG-009, planned) |
| Master credentials in Secrets Manager | PG-004 | |
| AWS Budget for the stack | FIN-009 | Optional element |
| Tags `app`, `env`, `owner` | COMMON-001, COMMON-002 | Note once per diagram, not per element |
| Elements a domain platform supplies (cluster, VPC and subnets, ingress, DNS, certificates), in a project whose `magrathea.json` has `infra_mode: "domain"` | The rules of the standard that covers the element on the providing side (for example K8S-001 to K8S-004 for the cluster), labeled with the domain platform's name | Drawn as external, outside the project boundary. Not dashed: a domain platform supplies them, no request to Magrathea is needed. A `standalone` project, or an element the domain platform does not supply, follows the next row |
| VPC, subnets, route tables, NAT, load balancers, ingress, DNS, certificates, object storage, queues, caches, CDN, anything else | none at the time of writing | Dashed, `needs a Magrathea request` (AWSARCH-004). Check `.magrathea/standards/` first: a newer base may cover it |

## Conventions

- **Nesting:** AWS Cloud, then Region, then VPC, then subnet tier (public or private), then
  services. Availability Zones only when the design depends on them (for example Multi-AZ, PG-005).
- **External elements (domain mode):** a `domain` project draws what its domain platform supplies
  inside a separate boundary labeled with the domain platform's name, outside the project's own
  boundary, with the element's covering rule IDs. The project's arrows into it (for example the
  workload identity binding) stay solid. A `standalone` project draws as before.
- **Lines:** solid for an element a standard covers, dashed (`..` or `[dashed]`) for one that needs a
  request. Label every arrow with the protocol or purpose.
- **Labels:** `<name>\n<RULE-IDs>` or `<name>\nneeds a Magrathea request`.
- **Icon groupings:** use the AWS Architecture Icons categories for the service type (for example
  Compute, Containers, Database, Security/Identity, Networking, Management/Governance). Exact
  category names, versions and file names: TODO (take them from the current AWS Architecture Icons
  download; Magrathea has not verified them).
- **Sequence and flow diagrams** stay in Mermaid in the TRD's Flows section. PlantUML is for
  deployment architecture only.

## PlantUML and the AWS icon library

- The `.puml` must be valid PlantUML without any icon library, so it renders and reads with plain
  shapes. Icons are an optional improvement.
- A community PlantUML library of AWS icons exists. Its include path, version and whether the
  standard PlantUML distribution bundles it: TODO (not verified by Magrathea; do not copy an
  include line from here, check the library's own documentation).
- **AWS icon license and usage terms: TODO, a human must verify** before icons are used in
  published or customer-facing material. This standard makes no claim about them. Do not commit
  icon files to the repository.
- Minimum PlantUML version: TODO.

## Notes

- Rendering is a project concern (`make diagrams`), not a Magrathea test. If PlantUML is not
  installed the target prints a message and skips; set `REQUIRE=1` to make that a failure.
- The `architect` has no shell, so it writes only the `.puml` source. A human or CI renders it.
- When a request is answered and a standard now covers an element, update the diagram labels in
  the same change as the TRD revision (and tell the human, as for any change to an approved TRD).
