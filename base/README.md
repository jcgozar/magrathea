# .magrathea/ (read-only)

This folder is the Magrathea base, fetched from the Magrathea repository by
`python3 scripts/magrathea_sync.py` at the commit pinned in `magrathea.lock.json`. It is a
git-ignored cache: **do not edit it.** CI fails if it differs from the lock. Change it by asking
Magrathea (`/request-standard`), then `make upgrade` to receive the change.

- `agents/personas/`: base personas (tool-neutral). Add behavior in `local/personas/`.
- `standards/`: written infrastructure standards with rule IDs.
- `policy/`: the Rego and Kyverno policies that enforce them, with tests.
- `review/risk.json`: the rules the reviewer uses to classify a pull request's risk.
- `claude/commands/`: slash commands, copied to `.claude/commands/` by `make sync`.
- `docs/WORKFLOW.md`: how work moves between personas.
- `scripts/`: the persona generator, the path guard, the lock check and the risk classifier.
