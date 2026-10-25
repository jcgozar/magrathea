# 0007. Engine and distributions

Status: Accepted (2026-10-25), from the planning conversation. Implementation is in progress;
the order of work below shows what exists.

## Context

Magrathea is meant to be open source. A platform engineer at another company should get a
fresh Magrathea, put their own templates, personas, stacks and standards in a folder of their
own, and be left with only the workflow: how to create projects and add standards. Today the
generator reads its content from this repo (`tools/magrathea.py` derives `BASE`,
`templates/project` and `templates/stacks` from its own location), and projects take a single
source (ADR 0006). The content now in `base/` and `templates/` is one opinionated set; it
should become the default, not the only choice.

## Decision

### Three things, versioned separately

| Thing | What it is | Where | Version |
|---|---|---|---|
| Engine | `tools/`: the generator, `check_base_change.py` and the workflow tooling. Runs from the checkout on the platform engineer's machine | this repo | `VERSION` at the repo root, `ENGINE_CHANGELOG.md` |
| Workflow | the `magrathea-*` personas and the commands (`/new-project`, `/add-standard`, `/add-stack`) | this repo, `meta/` | `version` in each file's front matter |
| Content | standards, policies, project personas, templates, stacks, and the scripts that run inside projects (`base/scripts/`: sync, lock, path guard) | defaults here; overrides in a distribution | `base/VERSION` for the defaults, the distribution's own `VERSION` for its result; `CHANGELOG.md` |

The workflow ships with the engine. A distribution does not copy it, and uses the engine's
version unless it chooses otherwise (below).

The scripts under `base/scripts/` run inside projects and reach them through the content
layer, pinned by the project's lock. They are not engine code, and are not versioned with the
engine. Their compatibility with the engine is a content concern, tracked in
`compatibility.json` like the workflow files.

### The checkout is authoritative

The engine is whatever Magrathea checkout the platform engineer runs. Python executes what is on
disk, so a declared version cannot change it. `distro.json` records the engine version the
distribution expects (`workflow.ref`). Tools compare it with the checkout's `VERSION` and, on a
mismatch, stop with an instruction: check out the expected tag, or review the changelog and
bump `ref`. They never silently continue on a different version, and they never fetch and run
another engine version. (Re-executing the declared version, as pre-commit does, may be added
later without changing `distro.json`.)

### A distribution holds only your changes

A distribution is a folder with the same shape as the defaults, containing only what differs,
plus `distro.json`:

```json
{
  "upstream": { "source": "<magrathea url or path>", "ref": "v1.2.0" },
  "remove": [],
  "workflow": {
    "ref": "v1.4.0",
    "pin": { "magrathea-reviewer": "v1.2.0" },
    "local": ["magrathea-platform-engineer"]
  }
}
```

Layers are resolved in order, the later one winning: the upstream (Magrathea's defaults), then
the distribution.

- Plain files (templates, personas, docs): a distribution file replaces the upstream file at
  the same path.
- Standards: the unit of override is the file. To change a rule, replace the upstream standards
  file at the same path. A distribution file may not define a rule ID that another upstream file
  still defines; that is a hard error naming both files. (The upstream itself may repeat an ID,
  for a rule it states in two standards, and is not checked.) Overriding a single rule by ID
  inside a file is not supported.
- Policies: new files are added; a file at the same path replaces the default.
- Removing a default is explicit: paths under `base/` in `remove`, never by omission. A path
  that matches nothing is an error, so a stale entry after an upstream rename is noticed.
- `VERSION` and the changelog belong to the distribution. If the distribution ships no
  `base/VERSION`, the lock records the upstream's.
- An upstream may not itself be a distribution (no chaining).

A distribution has two kinds of content. `templates/` is read by the generator when a project is
created, from the folder passed to `--distro`, and is copied into the project once. `base/` is
fetched by reference like any base (ADR 0006) and reaches existing projects on upgrade.

**Projects follow the distribution only.** `magrathea.json` keeps one `source` and `ref`: the
distribution. The sync bootstrap fetches it, reads its `distro.json`, fetches the upstream named
there (first), removes, lays the distribution's `base/` over it, and writes the one merged
`.magrathea/`. `distro.json` is therefore the single place that says which upstream version a
distribution is on. The lock records the distribution's commit and, as `upstream`, the
upstream's source, ref and commit, plus one hash of the merged tree. Both commits are pinned, so
a fresh clone reproduces the reviewed base even if an upstream tag moves.
`magrathea_lock.py verify` checks the merged result as it does today.

Upgrading upstream is the distribution's act: bump `upstream.ref`, review, release. Projects
receive it on their next `make upgrade`.

### Workflow versions are the user's choice

- `workflow.ref`: the engine release whose workflow files the distribution uses.
- `workflow.pin`: hold one persona or command at an older release while the rest move on. The
  file is read from that tag of the engine repo.
- `workflow.local`: copy the file into the distribution, which owns it from then on. Later
  engine changes to it are reported, not applied.
- `magrathea workflow status` lists each file's current version, the latest, and the changelog
  entry. `magrathea workflow update [name]` moves a pin. Nothing updates on its own.

### Compatibility is recorded, not assumed

`meta/compatibility.json` is the single source of truth for which engine versions each
workflow file version works with:

```json
{
  "magrathea-reviewer": {
    "1.2.0": { "engine": ">=1.0,<1.4", "notes": "" },
    "1.3.0": { "engine": ">=1.3,<2.0", "safety": true, "notes": "Checks distribution layering." }
  }
}
```

`docs/COMPATIBILITY.md` is generated from it as a table per persona and per engine release
(`make compat`), so humans read a doc and nothing is maintained twice. Tests fail when:

- a file's front matter `version` has no entry in `compatibility.json`;
- the current engine `VERSION` lies outside the range of a workflow file at its current version;
- a release in the changelog has no row in the doc, or the doc is out of date;
- `workflow status` is asked about a pin whose range excludes the engine in use (it reports
  the conflict and does not proceed).

An entry marked `"safety": true` means the version changes what a gate enforces (for example
the reviewer's checks that rules are not weakened). `workflow status` and CI warn loudly when a
pinned or local file is behind a safety release.

## Consequences

- A company customizes by adding files to its own folder. It never edits the engine or the
  defaults, so engine upgrades are a ref bump with a reviewable diff, not a fork merge.
- Engine code (generator, sync, lock, `check_base_change.py`) cannot be pinned per file. It
  moves as one version, and the compatibility table is how a workflow file says what it needs.
- A pinned or local reviewer can lag the gates it is meant to enforce. The `safety` flag and the
  CI warning reduce this; they do not prevent it. The distribution's owner is responsible.
- Layering adds a failure mode: two layers disagreeing. The merged tree is the thing projects
  verify, and a rule-ID clash between a distribution file and an upstream file is a hard error.
- `scripts/magrathea_sync.py` is a file each project owns, so a project created before this
  change keeps the old single-source bootstrap. It fails the hash check against a merged lock
  rather than misbehaving; the fix is to copy the new script in.
- The defaults must be generic enough to be a starting point for others. A separate audit of
  `base/` and `templates/` for project, stack and cloud assumptions is part of this work.
- A mismatch between the checkout and `workflow.ref` is a manual fix. That is deliberate: the
  lock in ADR 0006 also detects drift and fails rather than correcting it.
- Not decided: signed releases, still planned from 0006.

## Order of work

1. Layered content resolution in the generator. **Done for `templates/project` and
   `templates/stacks`** (`--distro`); a distribution's `base/` is covered by step 2.
2. Fetching a distribution with its upstream, merging, and a lock that pins both. **Done**,
   with tests for overlay, removal, ID clashes, pinning, tampering and upgrades.
3. Front matter versions, `distro.json` `workflow` block, `compatibility.json`, `make compat`,
   `workflow status` and `update`.
4. `init-distro`.
5. An `examples/` distribution and the genericity audit.
