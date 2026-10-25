# 0009. Shared domain platform infrastructure

Status: **Accepted** (2026-10-25, accepted by the human, who agreed with every recommendation in
the earlier proposed version of this ADR, after independent review). The implementation follows
the "Order of work" below; the status of each step is recorded there. Until a step lands, the
thing it describes is not built and projects own all their infrastructure, as today. Each step
that lands updates `AGENTS.md` ("Current state"), `docs/guide/` and the example
(`tools/test_examples.py`) in the same change.

## Context

Today a project owns everything it deploys. The EKS standard (`eks-cluster.md`) is written as if
each project creates its own cluster, and `aws-architecture.md` marks VPC, subnets, load
balancers, ingress, DNS and certificates as "needs a Magrathea request" because no standard
covers them. ADR 0001 names OpenTofu for the foundation (VPC, EKS, IAM baseline, Argo CD) and
per-app resources for the rest, but does not say whose repository the foundation lives in.

Several projects in the same domain (a team, a product area) would otherwise each pay for a
control plane and a node pool, each run their own ingress, cert-manager, external-dns,
observability agents and Kyverno, and each need a platform engineer's attention. The shared
parts change slowly and carry real risk; the per-project parts change often and are the
project's own business. They should not sit in the same repository or share a review path.

## Decision

### Terms

"Platform" is already overloaded: a project has a `platform/` directory (`platform/infra`,
`platform/gitops`) and a `platform-engineer` persona. This ADR uses:

- **domain platform**: the shared infrastructure of a domain and the repository that holds it.
  Always written in full, never "platform" alone.
- **project infrastructure**: what a project's own `platform/` directory holds. That directory
  name and the persona name do not change.
- **platform operator**: the human who owns and applies a domain platform (the "single human
  platform engineer" below). The `platform-engineer` persona is a tool that operator drives.

Consequence: the CLI option is `--domain <name>`, not `--platform` (decided).

### Scope: one account, region-aware, no cross-account

The domain platform and its projects share one AWS account. **Cross-account is out of scope for
now** and nothing here is designed for it. The design is prepared for multi-region: a domain
platform instance is **per region**, and a project reads the parameters of the region it deploys
into. Decided: **one domain platform per region**, with the pieces that are global (IAM, registry
replication, DNS) in a **small separate state of the same repository** (an area `global`, applied
first and rarely). When a second region is actually needed is **deferred**; nothing is built for
it beyond the region in the SSM path and the `global` area.

### Where shared infrastructure lives

Shared infrastructure for a domain lives in its own git repository, one per domain. It covers:
VPC and subnets, the EKS cluster and node pools, cluster add-ons (ingress, cert-manager,
external-dns, observability agents, Kyverno), the OIDC provider, the registry, shared KMS keys,
and logging and monitoring backends.

The repository has its own remote state backend, with separate states per area: `global`
(only when needed), `network`, `eks` and `addons`, applied in that order. A change to add-ons cannot plan against, or damage, the
network state. Reads between these states **inside the domain platform repository** (for example
`eks` reading `network` outputs) are fine. The rejection of remote-state reads (below) applies to
projects.

It does not live in a project repository, and it does not live in the Magrathea repository.
Magrathea supplies the standards and the scaffold; the domain owns the result.

### Who operates it

A single platform operator owns and applies the domain platform for the whole team in that
domain. There is no automated pipeline at first: apply is manual, from a reviewed plan. Policy
checks and the FinOps report (FIN-002) still apply to that plan.

- **Capacity** (node pools, add-ons, version upgrades) is requested from the operator. This
  needs a **new request path**, see "Requests to the domain platform" (decided there).
- **Tenancy** is self-service in the project repository: namespace, quotas, network policies,
  RBAC, IRSA roles, and the project's own data stores. The security limits on that self-service
  are set in "Tenancy security" under Decisions on the Open items.

### Requests to the domain platform

The existing flows do not cover this. In `base/docs/WORKFLOW.md` and the `request-standard`
command, `requests/magrathea-<slug>.md` goes from a project to **Magrathea** (a missing
standard, infrastructure type or CI/CD pattern), and `requests/NNN-<slug>.md` is **inside** one
project (developer to platform-engineer). There is no project-to-domain-operator path today.
Decided: a request to the domain platform operator is an **issue in the domain platform
repository** from an issue template the domain-platform stack provides
(`.github/ISSUE_TEMPLATE/capacity-request.md`). Projects get a matching template
(`requests/DOMAIN-REQUEST-TEMPLATE.md`) to draft it. There is no command for it. Capacity
requests must not be sent through `magrathea-*` requests.

### Infra mode and project type

`magrathea.json` today holds only `source`, `ref` and `auto_merge` (written by
`tools/magrathea.py`). Two optional fields are added:

| Field | Values | Meaning |
| --- | --- | --- |
| `infra_mode` | `standalone` (default), `domain` | `standalone`: the project owns all its infrastructure. `domain`: it attaches to a domain platform and creates only project infrastructure. |
| `domain` | a domain name | Required when `infra_mode` is `domain`; names the domain platform. |
| `type` | `project` (default), `domain-platform` | What the repository is. Separate from `infra_mode` (decided). A `domain-platform` repo has no `infra_mode` of its own; it may carry `domain` to name itself. |

`standalone` does not imply EKS. Whether a standalone project runs on Kubernetes, containers,
functions or something else is a separate architecture decision in the project's TRD or ADR.

**Existing projects.** An absent field means `standalone` / `project`. `make upgrade` never adds
or changes `infra_mode`, `domain` or `type`. The guard enforces only on an explicit
`infra_mode: "domain"` with a `domain`. Nothing silently starts enforcing on existing projects.
Changing the mode later is a migration (state, identity, networking, data), planned and reviewed
like any infrastructure change; editing the field alone changes which checks run and moves
nothing. Magrathea provides no tool for it.

**How the guard learns the mode.** The policies live in the locked `.magrathea/` base (ADR
0006); `magrathea.json` is project-owned. Decided: the project's CI reads
`magrathea.json` and writes a small data file that it passes to conftest with `--data`; the
domain guard rules read it and do nothing when it says `standalone` or is absent. The policy set
stays in the base; the base never reads project files itself. Implementation detail: the file is
`{"magrathea": {"infra_mode": ..., "domain": ..., "type": ...}}` (nested under a `magrathea` key
so it cannot collide with other data at the root of conftest's data document), written by
`magrathea_lock.py mode-data`.

**Protecting the mode.** `magrathea.json` is already under CODEOWNERS in the project template
and in `high_paths` in `base/review/risk.json`, so any edit to it is high risk and is never
auto-merged. Decided: CI flags a change of `infra_mode`,
`domain` or `type` against the merge base (`magrathea_lock.py mode-change`) and fails unless the
change is marked as an approved migration (the pull request label `mode-migration`);
`iac-reviewer` treats a mode change as an explicit escalation, a named item in its checklist. `make upgrade` cannot
switch modes. Whether the edit-path guard (`check_paths.py`, an allow-list per persona) already
keeps every persona away from `magrathea.json` must be checked persona by persona when this is
built; CODEOWNERS and CI are the real control, as the guard's own docstring says.

### What a domain-platform repo contains

The domain platform repository is itself a Magrathea project: it has its own `magrathea.json`
(`"type": "domain-platform"`), carries the base lock (`magrathea.lock.json`, `.magrathea/`; ADR
0006), and generates its agent files from tool-neutral personas (ADR 0004). It has no product
code and no UI.

Accepted as proposed. Personas available in `base/agents/personas/` today: `architect`,
`architecture-reviewer`, `developer`, `finops`, `iac-reviewer`, `pm`, `platform-engineer`,
`qa-eval`, `reviewer`, `security`, `ux`.

| Persona | In a domain-platform repo | Exists today |
| --- | --- | --- |
| `platform-engineer` | yes: writes the IaC from the standards; the platform operator drives it | yes |
| `iac-reviewer` | yes: reviews every plan | yes |
| `security` | yes | yes |
| `architecture-reviewer` | yes | yes |
| `reviewer` | yes | yes |
| `finops` | yes: FIN-002 report for each plan | yes |
| `architect` | no (decisions are ADRs by the operator; confirmed excluded) | yes (excluded) |
| `pm`, `developer`, `ux`, `qa-eval` | no: no product features or UI to build | yes (excluded) |

Commands in `base/claude/commands/` today: `feature`, `finops`, `request-standard`, `review`.
Accepted: `review`, `finops` and `request-standard` apply (the last one still goes to Magrathea
for standards). `feature` is a product-feature flow (spec, TRD, build, review) and does not
apply as written; platform changes go through ADR, plan and review instead. Nothing needs to be
added for the persona list or existing commands to exist, but **what needs to be added** is:
(a) a way for the `domain-platform` type to select this persona and command subset (built in
`sync_agents.py`, driven by `project-types.json` in the base), (b) a domain-platform request
template (no command).

Extra review rules for this repository:

- Every change is high risk. `auto_merge` is `off` in its `magrathea.json` (built). Treating all
  paths as `high_paths` needs a platform-specific `risk.json`; the mechanism is still Open.
- Apply is manual, from a reviewed plan; FIN-002 applies (a finops report for the exact
  `plan.json` before `tofu apply`) and IaC review applies, as for any project.
- The operator is the sole owner at first; who approves when the author is the only owner is
  still Open.

### Creating projects and platforms

`magrathea new` offers three choices:

1. **Standalone**: a project that owns its infrastructure.
2. **Attach to an existing domain platform**: `--domain <name>`; the project is created with
   `infra_mode: "domain"`.
3. **Create a new domain platform together with the project**: the domain platform is
   scaffolded first, as a separate directory and a separate git repository, then the project.

A generated domain platform lists unknowns (account IDs, regions, CIDRs) as TODO and never
presents itself as ready to apply. A standalone command, `new-domain` (decided over `--type domain-platform`), creates one without
a project. Generation is never silent: the tool
says what it will create and where, and asks before creating a second repository.

### How projects find the domain platform

The domain platform publishes a small, documented list of outputs as SSM parameters. SSM
parameters are **account-local and regional**, so the path includes the region:

`/<domain>/<region>/platform/<name>` (decided).

The list is expected to include the cluster name, OIDC provider ARN, VPC ID, subnet IDs and
ingress class; the full list stays TODO and is part of the domain platform's documentation (the
generated repository starts it in `docs/domain-platform/PARAMETERS.md`). A
project reads the parameters of the region it deploys into. Projects do not read the domain
platform's remote state, so that state stays private to the operator. Reading remote state
outputs was considered and rejected for projects.

- The path convention is a **published interface**: renaming or removing a parameter breaks
  projects.
- **No secrets** go in these parameters; they hold identifiers only.
- Only the domain platform's apply principal can write `/<domain>/<region>/platform/*`, so a
  project cannot spoof them. Projects get read-only access to that prefix and nothing else of
  the domain platform's. Which principal reads (the project's CI role, or the plan-time
  principal) and the exact IAM policy: TODO.

A formal contract version for the parameter list is deferred until more than one team shares a
domain.

### Ordering and failure

The domain platform is applied before any project. In `domain` mode a project's plan fails with
a clear message when the domain platform or its parameters are missing; it does not fall back
to creating them.

### The EKS standard is split

`eks-cluster.md` gains two parts, **Providing a cluster** (domain platform only) and **Consuming
a cluster** (projects). Decided: keep it in **one file** with a column saying which part a rule
is in, so every rule ID is defined once. Two files would each need a disjoint set of IDs; the
ADR 0007 rule (a distribution may not define an ID another upstream file still defines) makes
duplicates a hazard, and `magrathea_lock.py` reserves base IDs for projects. Existing IDs are
kept; none is removed or weakened.

**Rule mapping (accepted).** `provide` = applies to the domain platform repo;
`consume` = applies to projects in `domain` mode; `both` = applies to either. In `standalone`
mode a project is subject to both parts.

| Rule | Subject (summary) | Part | Note |
| --- | --- | --- | --- |
| COMMON-001 | tags `app`, `env`, `owner` | both | Applies to any resource. Stays defined once; not repeated in a second file. Tags do not see inside a node pool (cost, below). |
| COMMON-002 | `env` is `dev` or `prod` | both | Same. Open: whether a domain platform, being shared, needs an `env` value of its own. |
| K8S-001 | private or CIDR-limited API endpoint | provide | |
| K8S-002 | KMS secrets encryption, all five log types | provide | |
| K8S-003 | IRSA or Pod Identity; no `aws_iam_access_key` | consume | Straddler. The Rego blocks static keys in any plan, so it applies to both repos' plans. The domain platform's part (the OIDC provider exists and is published) is not a new rule ID here; it is a documented SSM output. |
| K8S-004 | IMDSv2 on node launch templates | provide | Straddler. Nodes belong to the domain platform. In `standalone` mode the project is the provider. A project in `domain` mode cannot create node templates (guard), so the rule is moot for it. |
| K8S-005 | requests, memory limit, non-root | consume | The domain platform installs the Kyverno policy that enforces it. |
| K8S-006 | pinned tags, approved registry | consume | The registry itself is provided; its placeholders are filled by the domain. |
| K8S-007 | per-namespace quota and default-deny ingress | consume | Straddler. The project creates the namespace and its objects (consume); the domain platform installs the Kyverno policy (provide, no new ID proposed). Egress remains planned. |
| K8S-008 | PodDisruptionBudget (planned) | consume | |
| K8S-009 | cluster version currency (planned) | provide | Reworded for manual apply: a reminder to the operator (see Consequences). |
| K8S-010 | changes only through Argo CD (planned) | consume | Reworded: applies to workloads, not to the OpenTofu that creates the cluster and add-ons. |

New rule IDs for the guard use the prefix `DOMAIN-`, defined in one new file,
`base/standards/domain-platform.md`; add-on installation rules stay TODO. They must not collide with existing IDs, with local-only prefixes projects may use, or with an
upstream ID a distribution replaces (ADR 0007).

The guard forbids a project in `domain` mode from creating shared resources (`aws_eks_cluster`,
VPC and the like; exact list TODO). It does not run in `standalone` mode. It is `implemented`
only once it has a passing and a failing test (AGENTS.md); see the order of work.

### Other standards affected

- **`aws-architecture.md`.** AWSARCH-004 (an element with no covering standard is dashed and
  labeled `needs a Magrathea request`) must say what a domain project does with elements the
  domain platform supplies: the mapping table gains rows for them. Diagram convention
  (proposed): `standalone` projects draw as today; `domain` projects draw the domain platform's
  elements (cluster, VPC, ingress, DNS) as **external**, labeled with the domain platform's
  name, not dashed as "needs a request", and outside the project's boundary. AWSARCH-006
  (diagram and Infrastructure needs table list the same elements) is kept, with those elements
  marked external in both.
- **`finops.md`.** FIN-009 (every budget has a subscriber) and FIN-010 (compare the report with a
  budget stated in `CONTEXT.md`) assume a project has its own budget. Whether the domain
  platform has its own budget, and whether a project's budget includes a share of it, is Open.
  FIN-001, FIN-002 and FIN-007 apply to the domain platform repo unchanged.

## Consequences

- **Shared blast radius.** A bad domain-platform change or upgrade affects every project in the
  domain. Mitigations: strict review of its repo, staged upgrades (a non-production cluster or
  node pool first; TODO: decide how), and isolation between projects inside the cluster by
  quotas, network policies and Pod Security (K8S-005 to K8S-007). These reduce the risk; they do
  not remove it.
- **Isolation level.** A shared cluster with namespaces suits medium projects with similar
  needs. Regulated workloads, or workloads very different from their neighbours, should use
  `standalone` or their own domain platform.
- **Single operator.** One person is a bottleneck and a single point of failure for capacity
  changes and for incident response. Accepted at the start; a pipeline and a second operator
  are not decided here.
- **Cost.** One control plane and node pool serve many projects, which lowers fixed cost. It
  also hides who spends what, so per-namespace cost allocation through tags and labels is
  needed (COMMON-001 tags are per resource and do not see inside a node pool). The FinOps
  reports (FIN-001, FIN-002) must say whether a project's estimate includes a share of the
  domain platform. Exact allocation method: TODO.
- **Discovery by SSM is a published interface.** Until a contract version exists, a change to a
  parameter needs a note to every project in the domain.
- **Manual apply is a gap against existing intent.** K8S-009 and K8S-010 are `planned` and
  assume automation; see the mapping for their rewording.
- **More repositories to scaffold, secure and back up.** The domain platform repo needs its own
  CODEOWNERS, state bucket and locking, and base lock (ADR 0006). The generator must produce
  these.
- **Migration cost.** Because mode changes are migrations, choosing `standalone` for a project
  that later grows has a real price.

## Order of work

Status as of 2026-10-25. Base 0.6.0 and engine 0.7.0 carry all of it. Details of what is tested are
in `AGENTS.md` "Current state".

1. **Done.** `eks-cluster.md` has a Part column (provide / consume / both) and a short section; every
   rule ID kept; K8S-009 and K8S-010 reworded as in the mapping (both `planned`).
2. **Partly done.** `aws-architecture.md` (AWSARCH-004, AWSARCH-006, mapping row, external-element
   convention) is updated. The `finops.md` treatment of FIN-009/FIN-010 for a domain platform is **not**
   decided (still open).
3. **Done.** `type` / `infra_mode` / `domain` fields, validation in the lock check (DOMAIN-002), the
   CI data file (`mode-data`), the mode-change check (DOMAIN-003; the script is tested, the CI step has
   never run), the `iac-reviewer` escalation.
4. **Partly done.** The `domain-platform` stack (`global`, `network`, `eks`, `addons` skeletons,
   region-aware SSM parameters, persona and command subset, TODO placeholders) renders and verifies.
   The OpenTofu has never been run or validated; the add-ons and the cluster itself are not written.
5. **Done.** Request path: an issue template in the domain platform repository and a project-side template.
   No command.
6. **Partly done.** `--domain`, the interactive prompt and `new-domain` are built. Creating a domain platform
   together with a project in one run (choice 3) and the "domain platform not found" plan check (DOMAIN-012)
   are **planned**.
7. **Done for DOMAIN-001.** The Rego guard has passing and failing tests and is `implemented`; it was also run
   once with `conftest --data` against a synthetic plan. Not run against a real `tofu show -json` plan.

Each step that touches `base/` bumps `base/VERSION` and adds a `CHANGELOG.md` entry; steps in
`tools/`, `meta/` or `templates/project/scripts/` bump `VERSION` and add an
`ENGINE_CHANGELOG.md` entry.

## Decisions on the Open items

Each item below was open in the proposed version; the human accepted the recommendation.

- **Rule mapping**: as in the table; one file. Done.
- **Persona and command subset**: as in the table; `architect` is **excluded**.
- **`type` field** is separate from `infra_mode`; field names as in the table.
- **Guard learns the mode** from a data file CI writes for `conftest --data`.
- **Request path**: an issue in the domain platform repository from a template.
- **CLI naming**: `--domain`; `new-domain`.
- **SSM**: path form `/<domain>/<region>/platform/<name>`. Still TODO (not invented here): the
  full parameter list, which principal reads (the project's CI role or a plan-time principal) and
  the exact least-privilege IAM policy. These need AWS/IAM facts to be verified by a human.
- **Multi-region**: one domain platform per region, global pieces in a small separate state of the
  same repository. **Deferred:** when a second region is actually needed.
- **Cross-account**: out of scope. **Deferred;** revisit if the account model changes.
- **Tenancy security** for self-service: permission boundaries on IAM roles projects create,
  namespace-scoped IRSA trust, no ClusterRole creation by projects, and namespace naming and
  ownership rules are **MUST rules that must exist before the first project attaches**. They are
  written as `planned` rules in `domain-platform.md` (DOMAIN-020 to DOMAIN-023); how a project
  pipeline gets cluster credentials is TODO.
- **State and credentials**: operator-only access to the domain platform's state bucket; manual
  apply with short-lived credentials.

## Still open

The proposed version gave no recommendation for these, so they were not decided by the
acceptance. Nothing is built for them.

- **FinOps**: does the domain platform have its own budget, does a project's budget include a
  share (FIN-009/FIN-010), and the per-namespace cost allocation method. `finops.md` is
  unchanged.
- **Review path** for the domain platform repo: CODEOWNERS when the operator is the only owner,
  the staged upgrade method, and a platform-specific `risk.json` mechanism (only `auto_merge:
  "off"` is built).
- Whether the domain platform needs an `env` value of its own (COMMON-002 allows `dev` and `prod`).
- Compute choice for `standalone` projects (separate decisions).
- Creating a domain platform together with a project in one `magrathea new` run (choice 3 above).
