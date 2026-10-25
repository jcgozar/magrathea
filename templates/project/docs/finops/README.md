# Finops

Cost reports written by the `finops` agent, `NNNN-<slug>.md`, from
`.magrathea/docs/FINOPS-TEMPLATE.md`. Rules: `.magrathea/standards/finops.md`.

## Pricing snapshots

`pricing/<service>-<region>-<YYYY-MM-DD>.md`, added and refreshed by a human (the agent has no
network and does not edit this folder). Each holds the source URL, the retrieval date and the
unit prices used. Without a snapshot every price in a report is `TODO`. Snapshots older than 90
days are flagged in reports (TODO: owner confirms the limit).

## Budget

Set the monthly budget per environment, and the currency, in `CONTEXT.md` (Constraints).
Reports compare their estimate with it.
