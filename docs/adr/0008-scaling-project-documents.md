# 0008. Keeping project documents readable by agents as a project grows

Status: Proposed (2026-10-25). **Not accepted and not scheduled.** Adopt it only if the
measurement below shows agents getting worse as a project grows. If it does not, mark this
Rejected and say what was measured.

## Context

Every feature produces a spec; some produce a TRD, an ADR or a finops report. The git size of
these is negligible. The concern is what the agents read. As written today:

- `pm` reads all existing specs and ADRs. `architect` reads all TRDs, ADRs and interfaces. There
  is no index, no status filter and no area scoping.
- Specs have no status, so a shipped spec looks like a pending one. ADRs and TRDs have a
  `Superseded` status, but no persona is told to skip superseded documents.
- The `architect` numbers TRDs and ADRs "next in sequence", so two features on parallel branches
  can take the same number.
- The `architect` and `developer` read all of `.magrathea/standards/` and `local/standards/`
  (about 22 KB in six files today). A distribution that adds standards increases this.
- Rules enforced by CI (lock check, path guard, risk classifier, Rego policies) do not depend on
  how much an agent reads. Rules marked `planned`, enforced by "reviewer judgment", do.

This is a hypothesis from reading the persona instructions. Nothing has been measured.

## Measure first

Build a synthetic project with generated documents at several sizes (for example 10, 50, 200
and 500 specs, with proportional TRDs and ADRs), and run the personas on a fixed set of tasks
with the `qa-eval` persona. Record, per size:

1. Which files each persona opens, and the characters or tokens in its "read first" set.
2. Whether it finds the one relevant ADR or TRD that a task depends on (plant a decision that a
   new spec contradicts).
3. Whether the reviewers still catch planted violations: one of a `planned` (judgment) rule and
   one of an `implemented` (policy) rule.
4. Duplicate document numbers when two features are started on parallel branches.

Decide the thresholds for "worse" before running, and write them here. TODO: not set.

## Decision, if the measurement shows a problem

Adopt these together as one base release, because they depend on each other:

- **Generated indexes**: `specs/INDEX.md`, `docs/adr/INDEX.md`, `docs/trd/INDEX.md`, one line per
  document (number, title, status, area, summary), built by a script in `base/scripts/` from the
  documents' front matter. CI checks them with `--check`, like `sync_agents.py`. Personas read the
  index first and open only matching documents.
- **Statuses and a read rule**: specs get Draft, Approved, Shipped, Abandoned. Personas skip
  Superseded, Shipped and Abandoned documents unless another document references them.
- **A current-state summary**: the `architect` keeps a short `docs/ARCHITECTURE.md` of the
  decisions that still hold. Agents read it instead of the history of ADRs. ADRs remain
  immutable records.
- **Collision-proof names**: slug plus date, or numbers assigned by the index script.
- **`make context-size`**: reports each persona's "read first" set in characters; CI warns above
  a threshold (TODO: threshold from the measurement).
- **Fewer judgment-only rules**: when review keeps raising the same `planned` rule, turn it into
  a Rego policy with a failing test.

## If the measurement shows no problem

Mark this Rejected, keep the numbers in this file, and re-run the measurement when personas,
standards or the document types change substantially.

## Consequences if adopted

- A base change: `base/VERSION` bump, changelog, and tests for the index script (a passing and a
  failing case for the sync check). Existing projects need a one-time migration of their
  documents' front matter, which `make upgrade` does not do because the documents are theirs.
- Persona instructions change, so `magrathea-reviewer` must check that no persona still says
  "read everything".
- A distribution that adds document types must teach the index script about them.
