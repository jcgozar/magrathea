This repository is a **domain platform** (ADR 0009): the shared infrastructure of its domain, applied by a platform operator by hand from a reviewed plan. Projects attach to it
with `infra_mode: "domain"` and read what it publishes from SSM parameters. It has no product
code; the `pm`, `architect`, `developer`, `ux` and `qa-eval` personas and the `/feature` command are not generated here.

- `platform/infra/<area>/`: one OpenTofu root and one state per area, applied in this order:
  `global` (only when needed), `network`, `eks`, `addons`. They are skeletons: they declare the
  provider, an empty S3 backend, the required tags and the SSM parameters this domain publishes,
  and nothing else. The VPC, cluster and add-ons are for the `platform-engineer` to write from
  the standards (`.magrathea/standards/eks-cluster.md`, `domain-platform.md`).
- `docs/domain-platform/README.md`: the published SSM parameters (an interface projects depend on).
- `docs/runbooks/apply.md`: the manual apply steps.
- `.github/ISSUE_TEMPLATE/capacity-request.md`: how projects ask the operator for capacity.
- `magrathea.json` has `"type": "domain-platform"` and `"auto_merge": "off"`: no pull request is
  merged without a human.

**Not ready to apply.** Account, region, CIDRs, the state backend, versions and the values behind
every SSM parameter are TODO. The OpenTofu has not been run or validated by Magrathea.