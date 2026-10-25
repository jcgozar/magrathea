# 0006. Projects refer to the base instead of holding a copy

Status: Accepted (2026-10-22), from review feedback. Supersedes the "vendored" part of 0005.

## Context

ADR 0005 copied the base into each project as `.magrathea/` and locked it with a checksum
manifest. That does not scale: a standard or infrastructure type added to Magrathea later never
reached projects created earlier, and the manifest could only say "unchanged", not "up to date".

## Decision

- The base lives only in the Magrathea repository (`base/`). A project holds:
  - `magrathea.json`: the source (a git URL or a local path), the ref to follow (a tag, branch
    or commit), and project settings such as `auto_merge`.
  - `magrathea.lock.json`: the exact commit fetched, the base version, and a hash of every
    fetched file.
  - `scripts/magrathea_sync.py`: a small standard-library bootstrap that fetches the pinned
    commit into `.magrathea/`, a **git-ignored cache**, and fails if the files do not match
    the recorded hash.
- Everything that used to read `.magrathea/` still does; only where it comes from changed.
- `python3 scripts/magrathea_sync.py --update` (`make upgrade`) re-resolves the ref, rewrites the
  lock and shows which base files changed. The lock change is an ordinary diff for review.
  Following a branch (`main`) gives new standards at every upgrade; following a tag pins them.
- CI fetches exactly the locked commit, then runs `magrathea_lock.py verify`: the cache matches
  the lock, `magrathea.json` and the lock agree, and `local/` additions do not reuse a base rule
  ID, define policy `exception` rules, or set `auto_merge` looser than the base allows.
- Magrathea's own `tools/check_base_change.py` surfaces removed or weakened rules and a missing
  version or changelog entry on every change to the base, since every project will receive it.

## Consequences

- A new standard in Magrathea reaches existing projects on `make upgrade`. Nothing is copied by
  hand.
- A fresh clone needs `make setup` before the agents' path guards work (they call scripts in the
  cache); until then the hooks fail closed and block edits.
- The base is read-only in a project by construction: it is not in the repository, and edits to
  the cache are detected and overwritten by `make setup`.
- CI needs read access to the Magrathea repo. A private Magrathea repo needs a token in the CI
  job. This has not been tried.
- The lock is still in the project repo, so someone could change the lock to point somewhere
  else. That shows in review of `magrathea.lock.json`, which CODEOWNERS covers. Signed releases
  would remove this and are planned.
- A moved tag is detected (the hash differs) and reported rather than silently followed.
- A base change can break projects that upgrade. The mitigation is the review by
  `magrathea-reviewer`, `check_base_change.py`, versioned tags and the changelog, not a
  technical guarantee.
