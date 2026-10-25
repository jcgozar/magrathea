---
description: Take a feature idea through spec, architecture review (TRD if needed), build and independent review, stopping for approval at each handoff
argument-hint: <feature idea>
---

Take this feature idea through the flow in `.magrathea/docs/WORKFLOW.md`:

$ARGUMENTS

Work through the steps in order. Use the named subagents, and stop where the flow says to.

1. **Spec.** Use the `pm` agent to write `specs/<slug>.md`. Show me the spec and its open
   questions, then **stop and wait for my approval**.
2. **Architecture review.** Use the `architect` agent on the approved spec. It reviews the spec,
   then either writes a TRD in `docs/trd/` (the change is complex, there is no architecture
   yet for the area, or it needs new infrastructure) or says why none is needed, and writes
   ADRs for hard-to-reverse choices. Show me the result and any questions for the PM, then
   **stop and wait for my approval** of the TRD and ADRs. If the TRD's infrastructure table or
   an ADR chooses infrastructure, first use the `finops` agent on it (`/finops`), have the
   report linked from the ADR, and show the report together with the TRD for the approval
   stop. If no infrastructure is involved, skip `finops`.
3. **Infrastructure.** If the TRD's infrastructure table has needs, tell me. Use the
   `platform-engineer` agent only when I ask; it provides what the standards allow and writes a
   request for Magrathea (`/request-standard`) for anything they do not. When it produces
   `plan.json`, use the `finops` agent on that plan (compute the plan's SHA-256 for it) and
   attach the report to the summary. Then use the `iac-reviewer` agent on its change and the
   report.
4. **Build.** Use the `developer` agent to implement the approved spec and TRD on a branch
   `feat/<slug>`. If it files a request in `requests/`, stop and tell me.
5. **Review.** Run the `review` flow (`/review`) on the branch: the `reviewer` classifies
   risk, the `architecture-reviewer` checks the code against the TRD, ADRs and spec, and the
   `security` and `ux` agents join where they apply.
6. **Report.** Summarize what changed, the risk tier, the review findings by severity, the rule
   IDs followed, whether anything was merged, and everything unverified. Do not push or open a
   PR unless I ask.

Rules: do not skip an approval stop, and do not do a persona's work yourself. The persona that
wrote something never reviews it.
