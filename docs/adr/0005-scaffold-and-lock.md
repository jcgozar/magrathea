# 0005. Magrathea scaffolds projects and locks the base

Status: Accepted (2026-10-22), from the planning conversation. Supersedes the earlier
single-product layout decisions (a modular monolith, then one repo; 0003 here) as far as
Magrathea is concerned. The "vendored base with a checksum manifest" mechanism was
replaced by 0006 (projects refer to the base); the rest stands.

## Context

Magrathea began as a repo containing both a platform and one product. The aim is
different: Magrathea is the platform engineer's tool. A person with an idea asks Magrathea
for a new project and gets a repository with the agent personas, the infrastructure
standards, CI and a stack-appropriate app skeleton. Only the project's context is the
person's to write. Projects can add to the base but not change or remove it, and new
infrastructure types are added to the base by Magrathea, not by one-off workarounds.

## Decision

- Magrathea is the generator plus the base. `base/` holds personas, standards, policies,
  scripts, workflow and commands. `templates/project/` holds files a project owns.
  `templates/stacks/<name>/` holds an app skeleton, its CI and its Dockerfiles.
- `tools/magrathea.py new` renders a project deterministically: same inputs, same
  repository. An agent command (`/new-project`) interviews the person, drafts `CONTEXT.md`
  and calls the generator, so the agent decides inputs and the script produces the output.
- The base is **vendored** into each project as `.magrathea/`, with `manifest.json`
  (sha256 per file). CI runs `magrathea_lock.py verify` and fails on any difference.
  CODEOWNERS covers `/.magrathea/`. `magrathea upgrade` refreshes it.
- Projects extend through `local/`:
  - `local/personas/<name>.md` without front matter appends behavior to a base persona;
    with front matter it defines a new persona. A base persona's tools and writable paths
    cannot change, and no persona may write to `.magrathea/`.
  - `local/standards/` adds rules. A rule ID that exists in the base is an error.
  - `local/policy/` adds Rego in `package local`. `exception` rules are an error, so local
    policy can add checks but cannot switch base checks off.
- A missing infrastructure type is requested with `/request-standard` in the project. The
  request goes to Magrathea, where `/add-standard` has the platform agent add the standard,
  its policy and tests to the base, bump the version and write a changelog entry.

## Consequences

- Fixing a base rule or adding a type reaches projects through `magrathea upgrade`, not
  through copy and paste.
- The lock is a check, not a barrier. The manifest sits next to the files it describes, so a
  person who edits both passes `verify`. CODEOWNERS and review are the control for that.
  A stronger design would compare against a published, signed release of the base; it
  would need Magrathea to publish releases first.
- A new base rule ID can collide with an ID a project already added locally. `upgrade`
  reports that and the project renames its own rule.
- The personas assume stack-independent paths (`app/`, `platform/`, `local/`). A stack that
  needs a different layout would require a base change.
- The product Magrathea was first planned inside is now an ordinary project built with
  Magrathea, not part of it. Its architecture decision (ADR 0002) was moved out of this
  repository, and 0003 (one repo) no longer applies here.
