# Evals

Owned by the `qa-eval` agent. Nothing here yet.

Planned layout:

```
evals/
  product-ai/     datasets, graders and thresholds for the insights service
  agents/         did each persona stay within its boundaries?
  infra-agent/    does the infra agent refuse unsafe requests?
  reports/        one report per run: <date>-<slug>.md
```

Rules:

- Expected outputs come from the spec or from human-labelled data, never invented.
- A threshold is lowered only by a human, with a reason recorded in the PR.
- The infra-agent evals reuse the passing and failing fixtures in
  `.magrathea/policy/conftest/`.
