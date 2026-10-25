# 0001. Standards as code instead of a custom orchestrator

Status: Accepted (2026-10-21), from the planning conversation. Revisit after the first golden-path service.

## Context

The goal was a Humanitec-style platform where an app does not need to know about cloud
infrastructure. The first design had apps declare needs in a Score workload spec and a
custom orchestrator resolve each resource type into environment-specific manifests and
infrastructure.

Because the project is AI-native, a second option emerged: write down standards for
each kind of infrastructure and let AI agents write the Terraform/OpenTofu, with
policy-as-code deciding whether it is acceptable.

Concerns with free-form agent-written infrastructure: output varies between runs,
mistakes are expensive (open access, unencrypted data, oversized resources), and
without a written standard there is nothing to test against.

## Decision

- Write a short standard per resource type with stable rule IDs, each enforced by a named mechanism (OPA/Conftest on the plan JSON, Kyverno in the cluster).
- Agents write infrastructure code through PRs. Policy checks, a sandbox `tofu plan`, a cost estimate and a human approval gate every change.
- Keep a small service YAML as the contract between an app and the platform. Score (`score-k8s`) is optional and replaceable.
- Use vetted modules with narrow inputs for resources requested more than once, so output is near-repeatable. (Planned; not written yet.)
- OpenTofu for the foundation (VPC, EKS, IAM baseline, Crossplane, Argo CD); Crossplane claims for per-app resources.
- Standards and policies sit behind CODEOWNERS. Agents propose changes; humans approve.

## Consequences

- No custom orchestrator to build or maintain.
- More verifiable, not fully deterministic. Policy coverage is partial, so unwritten settings are still free until the rules grow. An allowlist approach and a repeatability eval are planned.
- The first modules need careful human review.
- Open: Crossplane versus OpenTofu only for per-app resources; Score versus a small in-house service YAML.
