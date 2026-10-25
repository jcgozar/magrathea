# infra

Infrastructure modules and per-app instances, written by the `platform-engineer` agent under
the standards in `../standards/`. Nothing here yet.

Planned: OpenTofu for the foundation (VPC, EKS, IAM baseline, Crossplane, Argo CD) and
vetted modules with narrow inputs for resources requested more than once (postgres,
bucket, queue). See `../../docs/adr/0001-standards-as-code-over-orchestrator.md`.
