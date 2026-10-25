# Applying the domain platform (manual)

There is no pipeline. One operator applies, from a plan that has been reviewed. Steps, per area, in
the order `global`, `network`, `eks`, `addons`:

1. `tofu plan -out tfplan` and `tofu show -json tfplan > plan.json` in the area's folder, with
   short-lived credentials for the account (TODO: how the operator gets them).
2. `make check PLAN=plan.json` from the repository root (policies from the base, with the mode data
   file; this repository has no `infra_mode`, so the project-side guard stays quiet).
3. The `finops` persona writes a report for exactly this `plan.json` (FIN-002); the `iac-reviewer`
   reviews the change and the plan.
4. A human reads the plan and the review, then runs `tofu apply tfplan`.
5. Check the SSM parameters under `/@@domain@@/<region>/platform/` and tell the projects if any
   name changed.

K8S-009 (cluster version currency) is a reminder to the operator here, not an automated job.
Nothing in this runbook has been run.
