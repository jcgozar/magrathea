---
description: Estimate the monthly cost of an ADR, TRD or plan with the finops persona
argument-hint: <path to an ADR or TRD, or to a plan.json>
---

Use the `finops` agent to cost this input, following `.magrathea/standards/finops.md`:

$ARGUMENTS

1. If the input is a `plan.json`, record its SHA-256 in the report. The agent has no shell, so
   compute it (`shasum -a 256 <plan.json>`) and pass it in, or ask me.
2. The agent writes `docs/finops/NNNN-<slug>.md` from `.magrathea/docs/FINOPS-TEMPLATE.md`,
   pricing only from snapshots in `docs/finops/pricing/`. If there are none, every price is
   `TODO`; tell me that a human must add a snapshot.
3. Show me the report's verdict, the expected monthly cost, what could not be priced and the
   guardrail gaps. Do not edit the ADR, TRD or infrastructure. If an ADR chooses
   infrastructure, I (or the `architect`) must link the report from it before I accept it.
