---
description: Independently review the current branch or pull request, classify its risk, and merge it only if it is low risk and every gate passes
argument-hint: [pull request number or notes]
---

Review the current branch (or the pull request given) against the default branch.

Pull request or notes, if given: $ARGUMENTS

1. Run `python3 .magrathea/scripts/review_risk.py classify --base <default branch>` and note the
   tier and reasons. This is the floor.
2. Use the `architecture-reviewer` agent on the diff, against the spec, TRD and ADRs.
3. If the diff touches `platform/` or other infrastructure, use the `iac-reviewer` agent.
   If it touches authentication, secrets, dependencies, IAM or network exposure, use the
   `security` agent. If it changes the UI, use the `ux` agent.
4. Use the `reviewer` agent with those results. It decides the final tier (never lower than
   the script's), asks the gate in `review_risk.py`, and either approves and merges (low risk,
   everything agrees) or comments and flags a human (anything else).
5. Report the tier, each reviewer's verdict, and whether the change was merged. If it was not,
   say exactly what a human has to decide.

Do not merge anything yourself. Only the `reviewer` agent merges, and only when the gate allows
it. Do not edit code to fix findings; hand them back to the `developer`.
