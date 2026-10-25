# Finops report NNNN: <slug>

Status: Draft | Reviewed
Date: <YYYY-MM-DD>
Costs: <ADR or TRD path, or plan path>
Plan SHA-256: <hash of plan.json, or "n/a (no plan yet)">
Currency: <USD unless stated otherwise>
Environments: <dev, prod; separate tables below>

## Scope

<What is being costed, and what is out of scope.>

## Inputs read

<Files read, with paths. For a plan: the plan hash above.>

## Pricing sources

| Service | Source (URL or file) | Retrieved | Age in days | Older than 90 days? |
| --- | --- | --- | --- | --- |
| <service> | <docs/finops/pricing/... or URL> | <YYYY-MM-DD> | <n> | <yes/no> |

No snapshot for a service means its price is `TODO: price unknown`.

## Assumptions

Region: <region or TODO>. Hours per month: <n>. Traffic: <...>. Storage: <...>.
Data transfer: <...>. Environments: <...>. Budget in `CONTEXT.md`: <amount per env, or none>.

## Estimate (monthly)

One table per environment.

| Resource group | Resources | Low | Expected | High | Formula and price source |
| --- | --- | --- | --- | --- | --- |
| <group> | <addresses> | <n or TODO> | <n or TODO> | <n or TODO> | <qty x unit price (source, date)> |
| Total (priced only) | | | | | |

What drives the spread: <...>

## Not priced

<Every resource or charge left out, with the reason.>

## Guardrail gaps

<Missing budget or budget alert, missing tags, unbounded scaling or storage, dev not stopped or
torn down, data-transfer exposure. "None found" only if each was checked.>

## Cheaper alternatives

<Options that still satisfy the standards. Do not choose for the human.>

## Verdict for the human

Expected monthly cost: <n, currency, priced resources only>. Biggest driver: <...>.
Could not price: <...>. Compared with budget: <within / above (human note needed) / no budget set>.
