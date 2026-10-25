# 0011. Deployed third-party services

Status: **Accepted** (2026-10-25, accepted by the human, who agreed with the recommendations in
the earlier proposed version of this ADR, after independent review), **in progress**. **Nothing is
built.** The implementation follows the "Order of work" below; the status of each step is recorded
there. Until a step lands, a project that deploys a third-party service does it without a
standard, as today. Each step that lands updates `AGENTS.md` ("Current state"), `docs/guide/` and the example
(`tools/test_examples.py`) in the same change.

## Context

Some projects need software they do not write: an open-source component that they pin, configure
and run on the cluster. An LLM gateway (for example Bifrost or LiteLLM) is the case that raised
this. **These names are examples only.** This ADR makes no claim about how any product is
deployed, configured or licensed; every such fact is TODO, to be verified per service by a human
when a service is actually adopted.

What Magrathea covers today, from `base/standards/`, the personas and the stacks:

- **Stacks** (`java-service`, `react-java`, `domain-platform`) scaffold code that the project
  builds. A deployed service has no application code and no build pipeline.
- **K8S-005 to K8S-007** (requests/limits and non-root, pinned tag from an approved registry,
  namespace quota and default-deny) are `implemented` as Kyverno policies (K8S-007 is
  `implemented (egress planned)` in `eks-cluster.md`; K8S-006's registry list is a placeholder) and apply to any
  workload. K8S-006 accepts a tag **or** a digest (the policy pattern is `*:* | *@sha256:*`) and
  forbids `latest`. It does not require a digest.
- **K8S-003**: IRSA or Pod Identity, no static keys (`implemented`, blocks `aws_iam_access_key`).
- **K8S-010** (workloads reach the cluster only through Argo CD) is `planned`. ADR 0009 scopes it to
  workloads, not to the OpenTofu that creates the cluster and add-ons.
- **PG-001 to PG-009** cover Postgres on RDS (encryption, TLS, no public access, Secrets Manager
  managed master credentials, backups, class limits, ingress only from the cluster). Not all
  are enforced: PG-008 and PG-009 are `planned`, and PG-003 is `implemented, partial` (it catches only
  `0.0.0.0/0` on port 5432). Other datastores have no standard.
- **FIN-001** (ADR links a finops report) and **FIN-002** (report for the exact plan before apply)
  are `planned` and judged by personas. FIN-003 to FIN-008 and FIN-010 shape the report (FIN-009 is a conftest budget check, `implemented`).
- **Not covered**: a general secrets standard (the `security` persona reviews for secrets in code
  and over-broad IAM, but no rule says how a third-party service gets its secrets); ingress, DNS and
  certificates (`aws-architecture.md` marks them "needs a Magrathea request"); and the supply chain
  for third-party code, see below.
- **Supply chain.** The `security` persona's review checks "new or outdated dependencies" in one
  line. No standard requires pinning by digest, image scanning, a recorded licence and source, or
  a reviewed upgrade procedure. The Kyverno registry list is a placeholder to be filled in.
- **ADR 0009** gives a domain platform add-ons owned by the operator, published SSM parameters
  (`/<domain>/<region>/platform/<name>`), and DOMAIN-001, which stops a project in `domain` mode
  creating shared infrastructure.

A third-party service sits between a project's own workload and a domain platform add-on. Without
a decision, each project would invent the delivery, the pinning and the ownership, and a second
project that needs the same service would deploy its own copy or reach into the first.

## Decision

### 1. A `deployed-service` pattern, as a section inside an existing project

The three ways to model it:

| Option | For | Against |
| --- | --- | --- |
| New **stack** `deployed-service` | A stack is the existing extension unit; `/add-stack` and the tests exist | A stack scaffolds a whole repository (README, CI, app dir). A deployed service is something a project (or domain platform) **has**, often several of them, not what the repository is. Adding a second service would mean a second repository or an awkward overlay on a stack |
| New **`type`** value in `magrathea.json` | Selects a persona and command subset like `domain-platform` | `type` describes what the repository is (ADR 0009). A project that runs a gateway is still a `project`. It would also multiply type-and-mode combinations that DOMAIN-002 must validate |
| A **section / template inside an existing project** | One project can hold several; the same shape works in a `project` and in a `domain-platform` repo; no new combination to validate | Needs its own scaffolding path (a command or a documented copy), since `new` creates whole repositories |

**Decided: the third (2026-10-25).** A deployed service is a folder in a repository that already exists,
with a written standard and a skeleton the platform engineer copies, not a new kind of repository.
No new stack and no new `type`.

Proposed layout in a project, by name only (the content is TODO until built):

```
platform/gitops/services/<service>/   Argo CD application, values file, pinned references
platform/infra/services/<service>/    IRSA role, datastore, secrets, anything OpenTofu creates
docs/runbooks/<service>.md            operate, back up, restore, upgrade, roll back
docs/services/<service>.md            source, licence, version, digest, owner, upgrade log
```

Scaffolding is by a command, `magrathea add-service` (name TODO), or a documented copy from
`templates/`. Decided: a documented copy first, an `add-service` command once two services have used it.

### 2. What a deployed service must have

Each item is a proposed requirement of the pattern. Where a rule is needed, it is written as
`planned` with its ID left TODO (section 3).

- **Pinned artifact**: chart or image pinned by version **and** digest, never `latest` (K8S-006
  already forbids `latest`; the digest part is new).
- **Values file** in git, reviewed; no values edited in the cluster.
- **Namespace** of its own, with quota and default-deny (K8S-007).
- **IRSA role** scoped to its namespace and service account (K8S-003; DOMAIN-021 in `domain` mode),
  with the least privilege it needs. Which AWS permissions a given service needs is TODO per service.
- **Its own datastores**, following existing standards: Postgres on RDS follows PG-001 to PG-009.
  A datastore with no standard (a cache, a queue) needs a Magrathea request first; the pattern
  does not invent one.
- **Secrets**: no secret in git, values or state. Mechanism (Secrets Manager, with how it reaches
  the pod) is TODO; there is no general secrets standard to cite, which is a gap (section 3).
- **Ingress**: TODO. `aws-architecture.md` says ingress, DNS and certificates need a Magrathea
  request; a service that is reachable from outside the cluster waits for that, or is cluster-
  internal only.
- **Delivery through Argo CD** (K8S-010, which is `planned`; once enforced it covers this). No build
  pipeline, no `kubectl apply` by hand.
- **Runbook and upgrade procedure**: how to read release notes, test the new version in `dev`,
  apply, roll back, and what is lost on rollback (datastore migrations). Reviewed like any change.
- **Record**: source repository, licence, who owns the service, current version and digest.
  Licence and any obligation it creates: TODO, a human verifies per service.
- **No build pipeline.** CI checks the pins and the values; it does not build an image. If the
  project has to patch or rebuild the service, it is no longer this pattern (it is a fork the
  project builds, which needs its own decision).

### 3. Supply-chain rules: only what is missing, all `planned`

Checked against `base/standards/`, `base/policy/` and the `security` persona. Covered: no `latest`
and approved-registry (K8S-006), non-root and limits (K8S-005), IRSA (K8S-003), namespace
defaults (K8S-007). Missing, proposed as `planned` rules in a new standard file; **IDs are TODO**
and are chosen when the standard is written, with a prefix that no existing standard or known
local prefix uses:

| Proposed rule (ID TODO) | Strength | Enforcement idea | Status |
| --- | --- | --- | --- |
| Third-party images and charts are pinned by digest as well as version | MUST | Kyverno on images; a CI check on chart references | planned |
| Third-party images are scanned and the result is attached to the upgrade change | SHOULD | CI job, scanner TODO (not chosen here) | planned |
| Source, licence and owner are recorded for each deployed service | MUST | Reviewer judgment against `docs/services/<service>.md`; a CI check that the file exists | planned |
| An upgrade is its own change with release notes read, a `dev` test and a rollback plan | MUST | `iac-reviewer` and `security` judgment | planned |
| A third-party service receives secrets only from the secret store, never from values files | MUST | Reviewer judgment; secret scanning TODO | planned |
| A service taken from a registry outside the approved list is refused | MUST | Already K8S-006 once its placeholders are filled in; extend, do not duplicate | covered, placeholders TODO |

A rule becomes `implemented` only with Rego or Kyverno and a passing and a failing test. The
Kyverno digest policy could be tested like the other three; "scanned" and "licence recorded"
cannot be deterministic checks here and stay judgment, as FIN-001 does.

Rules are not weakened: the proposed rules add to K8S-006, they do not relax it.

### 4. Ownership: project-owned first, promotable to the domain platform

Per service, two states:

- **Project-owned.** The service lives in the project's repository (project layer: namespace,
  IRSA, datastore, Argo CD application) and consumes the standards above. The project's team
  upgrades it. This is the default and needs nothing from the operator beyond what a project
  already has under ADR 0009.
- **Domain-shared.** The service is a domain platform add-on, owned and applied by the platform
  operator (ADR 0009), and projects consume it.

**Promotion trigger (proposed):** when a second project in the domain needs the same service, it is
promoted rather than deployed a second time. A second project must not deploy its own copy and must
not reach into the first project's namespace or datastore. The decision to promote is the
operator's, requested as an issue in the domain platform repository (the path from ADR 0009);
either project may open the issue and the operator decides.
A service that two projects use only to the same purpose, with different configuration needs, may
stay separate; that is the operator's judgment, recorded in the issue.

**Promotion is a migration**, like a mode change (ADR 0009): state, identity (IRSA, namespace),
data and endpoints move; editing a file alone moves nothing. Magrathea provides no tool for it. A
service deployed as project-owned should keep its namespace, values and datastore separable
(own folder, own state area) so that promotion is a move and not a rewrite.

**How consumption works once shared:** the operator publishes the service's outputs as SSM
parameters under the existing form `/<domain>/<region>/platform/<name>` (for example an endpoint
and a namespace; exact names TODO, in `PARAMETERS.md`, identifiers only, never secrets, DOMAIN-010).
A project reads them like the other parameters (DOMAIN-011: read-only, which principal reads is
TODO). Authentication from a project to the service, per-project keys or budgets and how they are
issued, are TODO per service and are not in the SSM parameters.

### 5. Standalone and domain `infra_mode`

- **`standalone`**: the project owns the cluster, the service and everything it needs. The pattern
  applies as in sections 1 to 3. There is no promotion.
- **`domain`**: the project's own service stays in project infrastructure (namespace, IRSA role,
  datastore, Argo CD application), under DOMAIN-020 to DOMAIN-023 once those exist (permission
  boundary, namespace-scoped IRSA, no ClusterRole, namespace naming). A chart that installs
  cluster-wide objects (CRDs, ClusterRoles, admission webhooks) cannot be a project-owned service in
  `domain` mode; it is a request to the operator. Whether a given chart does this is TODO per
  service. A shared service is consumed through SSM parameters.

### 6. The guard (DOMAIN-001)

DOMAIN-001 stops a project in `domain` mode creating a listed set of shared infrastructure types
(cluster, node groups, VPC, subnets, EKS add-ons, access entries, OIDC provider and so on). Proposed:

- **Should not treat as shared**: a project-owned service's namespace, IRSA role, security group,
  database, secret, or Argo CD application. These are project infrastructure; adding them to the
  list would break ADR 0009's self-service tenancy.
- **Should treat as shared, if it ever appears in a project plan**: resources that install
  cluster-scoped objects through OpenTofu (for example a `helm_release` or Kubernetes manifest that
  creates CRDs or ClusterRoles) or an `aws_eks_addon`. `aws_eks_addon` is already in the list. The
  Rego cannot tell what a chart contains from the plan, so cluster-scoped objects are better
  caught by DOMAIN-022 (Kyverno, `planned`) and by Argo CD project scoping. **No change to
  DOMAIN-001 is proposed**; the list is extended only by a Magrathea request, as its comment says.
- A shared third-party service is created in the **domain platform repository**, where DOMAIN-001
  does not fire (the mode is `domain-platform`/absent there).

### 7. FinOps

- A deployed service is infrastructure: the ADR that adopts it links a finops report (FIN-001) and
  the plan that creates it has a report for the exact plan (FIN-002). The report must price what the
  service **runs on** (compute for replicas, its datastore, storage, load balancers, data
  transfer) and say what is not priced (FIN-004).
- Costs that do not appear in a plan, such as a per-request cost of an upstream paid API behind a
  gateway, are unknown to the plan and are reported as assumptions or TODO (FIN-003: never a guess).
- Who pays when shared (decided 2026-10-25): a domain-shared service's cost is a **shared cost**,
  the domain platform's cost, and is not charged to the first project that used the service. This
  does **not** decide ADR 0009's allocation method, budget ownership, or how FIN-009/FIN-010 apply
  to a domain platform; those stay open there.
- On promotion, the report is redone, since the cost moves from the project's budget to the
  domain platform's budget.

### 8. The `security` persona

- Reviews each adoption and each upgrade: source and licence record, digest pin, exposed ports and
  ingress, IRSA permissions, secret handling, whether the chart installs cluster-scoped objects.
- Maintains the proposed supply-chain rules as `local/` rules when a project needs them first; the
  base version comes through a Magrathea request (`/request-standard`), like any missing standard.
- Is an independent reviewer: it does not review a service it adopted.
- The `iac-reviewer` checks the plan and the finops report; the `reviewer` merges only when the
  tier allows. A deployed-service change touches `platform/**`, so it is high risk under
  `base/review/risk.json` and is never auto-merged. On a provider without enforced
  required code-owner approval (see ADR 0010, GitLab Community is unverified), this rule is
  judged by the persona, not enforced by the provider.

## Alternatives considered

1. **A new stack `deployed-service`.** Rejected, see section 1: wrong grain.
2. **A new `type`.** Rejected, see section 1.
3. **Always shared (every third-party service is a domain add-on).** Rejected: it makes the
   operator a bottleneck for every experiment, and ADR 0009 keeps tenancy self-service.
4. **Always project-owned.** Rejected: a second project would run a second copy, or couple to the
   first.
5. **Do nothing; treat the service as any workload.** The existing K8S rules already apply, so this
   is the fallback if the human wants no new pattern. It leaves the supply-chain gap, the upgrade
   procedure and the promotion path undecided.
6. **Fork and build it in the project.** Out of scope: this is a different pattern with a build
   pipeline and its own supply-chain concerns.

## Consequences

- A project that adopts a third-party service has a repeatable shape, and a path to share it.
- The supply-chain gap is named and tracked as `planned` rules, not silently assumed covered.
- More documents per service (runbook, record), which the reviewers must keep up to date. An
  out-of-date version record is a risk; a CI check for the file's existence does not prove it is
  current.
- Promotion is a migration with real cost; the "keep it separable" guidance reduces it but is not
  enforced.
- A shared service is a single point of failure for the projects that depend on it, and the
  operator becomes responsible for its upgrades. How that load is bounded is not decided.
- Magrathea takes on no knowledge of any specific product; per-service facts live in the project
  (or the domain platform), marked TODO until verified.

## Backward compatibility

- No `magrathea.json` field is added (recommended path), so no existing project changes.
- No existing rule is changed or removed. New rule IDs use a new prefix chosen when built (TODO),
  checked against base and known local prefixes. `K8S-006` is not edited; a digest rule is added
  beside it.
- A project's `platform/gitops` and `platform/infra` directories keep their role; the `services/`
  subfolders are additive. Existing projects get the new standard on `make upgrade` as a document
  and policy; a `planned` rule does not fail anything. An `implemented` Kyverno digest policy would
  change admission for existing clusters that use tag-only images, so if it is built it ships in
  warn/audit mode first (decided).
- `new_project(...)` and `list_stacks(distro=None)` keep their signatures (AGENTS.md); an
  `add-service` command, if built, is a new subcommand, not a change to `new`.
- ADR 0007 distributions: a distribution may replace the skeleton files and may not define a rule
  ID the upstream standard defines.
- The domain-platform stack gains, at most, an optional `addons`-area skeleton for shared services;
  existing domain platform repositories are not changed by `make upgrade`.

## Order of work

None of this is done.

1. Decided items recorded (this ADR); no Open items remain.
2. Write the standard file (name TODO) with the requirements in section 2 and the supply-chain rules
   in section 3 as `planned`, IDs chosen then. Base bump and changelog.
3. Skeletons under `templates/` for `platform/gitops/services/<service>/`, the infra folder, the
   runbook and the record, with TODO placeholders. Rendering test. If an `add-service` command is
   chosen, it comes here (engine bump).
4. Implement the digest rule as Kyverno (audit mode first) with a passing and a failing test;
   mark it `implemented` only then.
5. Extend the `security` and `iac-reviewer` checklists (base persona change).
6. Domain-platform side: promotion procedure, the issue template field "service to promote",
   service outputs in `PARAMETERS.md`. Depends on ADR 0009 steps still open.
7. Adopt one real service with a human, and verify its deployment, config and licence facts. Until
   then nothing in this ADR is validated against a real chart.

## Tested and untested (planned)

- Planned to test: template rendering, skeleton placeholders, any `add-service` command, the
  Kyverno digest policy with a passing and a failing resource, and that the new standard's rule IDs
  are unique across base and the example.
- Cannot be tested here: a real Helm chart or image, Argo CD delivery (K8S-010 is itself
  `planned`), IRSA against real IAM, Kyverno policies on a real cluster (the existing three have
  never run on one, per `AGENTS.md`), SSM consumption across a real domain platform, image
  scanning, and any claim about a specific product.

## What changes when built

- `docs/guide/`: `02-using-a-project.md` (adding a service), `03-customizing.md` (local rules),
  `05-reference.md` (the standard, any command), `06-faq.md`, `07-domain-platform.md` (promotion,
  consuming a shared service).
- `AGENTS.md`: "Current state" (what is tested and not) and the layout/personas lines if a command
  or template folder is added.
- `tools/test_examples.py`: the example project gets a service skeleton and checks it renders; if
  it uses `make test` to count Rego tests, the count in `AGENTS.md` changes with it.
- `base/` standards, personas (`security`, `iac-reviewer`, `platform-engineer`), policy and tests;
  `base/VERSION`, `CHANGELOG.md`; `VERSION` and `ENGINE_CHANGELOG.md` for `tools/` or `templates/`.

## Decided (2026-10-25, accepted by the human)

1. **Shape**: a section inside an existing project; no new stack, no new `type`.
2. **Promotion trigger**: a second project needs the service. Either project may open the issue;
   the operator decides.
3. **Digest enforcement**: a separate `planned` Kyverno rule that tightens K8S-006 for third-party
   images, `implemented` in audit mode first.
4. **Scaffolding**: a documented copy first; an `add-service` command later.
5. **Standard file**: a new standard file, not an edit of `eks-cluster.md`.
6. **Secrets standard**: a separate Magrathea request and ADR; this pattern marks the secrets item
   TODO until then.
7. **Licence policy**: record the licence (proposed rule); the allow-list is left to the human.
8. **Scanner choice** for the image-scan rule: TODO, not chosen.
9. **Cost of a shared service**: a shared cost, the domain platform's cost, not charged to the
   first project. ADR 0009's allocation method, budget ownership and FIN-009/FIN-010 treatment
   remain open there and are not decided here.
10. **Domain platform `addons` skeleton**: left alone until a first promotion exists.

## Open

Still needs a human: the scanner (item 8), the licence allow-list (item 7), the secrets standard
(item 6, a separate request and ADR), and the ADR 0009 cost questions in item 9. None blocks
steps 2 to 5.
