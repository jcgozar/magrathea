# FinOps standard

Applies to every change that chooses, changes or applies cloud infrastructure, in any stack.
Its purpose: a human sees a sourced, reproducible cost estimate before approving an ADR that
picks infrastructure and before approving an apply.

The mechanism for most rules is the `finops` persona and the reviewers reading its report. That
is a judgment, not a deterministic check, so those rules are `planned`. Only FIN-009 has a
policy and tests. Magrathea ships no prices: pricing snapshots are supplied and refreshed by a
human in the project.

## Rules

| ID | Strength | Rule | Enforced by | Status |
| --- | --- | --- | --- | --- |
| FIN-001 | MUST | Every ADR that chooses or changes infrastructure links a finops report before a human accepts it | `finops` persona; `architecture-reviewer` checks the link | planned |
| FIN-002 | MUST | A finops report exists for the exact `plan.json` (the report names the plan's SHA-256) before any `tofu apply`; the human attaches it to the approval | `iac-reviewer` checks the hash by hand (`shasum -a 256 plan.json`); a CI check is not part of the base | planned |
| FIN-003 | MUST | Every price carries a source (URL or file) and a retrieval date; an unknown price is `TODO`, never a guess | Report template; `finops` persona; `iac-reviewer` check | planned |
| FIN-004 | MUST | A report states assumptions: region, hours per month, traffic, storage, data transfer, environments, and which resources are not priced | Report template | planned |
| FIN-005 | MUST | A report gives low, expected and high monthly cost per resource group and in total, with the currency and the formula | Report template | planned |
| FIN-006 | MUST | The `finops` persona never edits infrastructure, standards, policy, specs or pricing snapshots; it writes only its reports | Persona `writable_paths` (`docs/finops/**`), CODEOWNERS on `docs/finops/pricing/` | planned |
| FIN-007 | SHOULD | A report flags guardrail gaps: no budget in `CONTEXT.md`, no budget resource, resources without `app`/`env`/`owner` tags, unbounded autoscaling or storage, no dev stop or teardown plan | Report template section | planned |
| FIN-008 | SHOULD | Prices come from a dated snapshot under `docs/finops/pricing/` that a human refreshes; the report says when the snapshot is older than 90 days (TODO: owner confirms the limit) | Report template; `finops` persona | planned |
| FIN-009 | SHOULD | Every `aws_budgets_budget` in a plan has at least one notification with a subscriber (email addresses or SNS topic) | `policy/conftest/finops.rego`, warn | implemented |
| FIN-010 | SHOULD | When `CONTEXT.md` states a budget per environment, the report compares expected and high cost with it, and an expected cost above budget carries a human note | `finops` persona; `iac-reviewer` check | planned |

## Notes

- FIN-009 checks only budgets that are in the plan. A plan cannot show that a budget is missing,
  so "every account and environment has a budget" is reported under FIN-007, not enforced.
  The attribute names it reads (`notification`, `subscriber_email_addresses`,
  `subscriber_sns_topic_arns`) are those of the AWS provider's `aws_budgets_budget`; TODO:
  verify against the provider version a project pins.
- Reports live in `docs/finops/NNNN-<slug>.md`, numbered like ADRs, status `Draft` or `Reviewed`.
  The template is `.magrathea/docs/FINOPS-TEMPLATE.md`. Snapshots live in
  `docs/finops/pricing/<service>-<region>-<YYYY-MM-DD>.md`: source URL, retrieval date, unit
  prices used.
- Currency defaults to USD; the report states the currency it used. TODO: owner confirms.
- Reports cover `dev` and `prod` separately (COMMON-002). The budget limit per environment is
  set by the project owner in `CONTEXT.md`; the base does not set one.
- The `finops` persona has no network and no shell. It cannot fetch current prices; with no
  snapshot every price is `TODO`.
