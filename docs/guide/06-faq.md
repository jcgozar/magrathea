# 6. FAQ

## Concepts

**What is Magrathea, in one sentence?**
A generator that creates a project repository with AI agent personas, infrastructure standards
enforced by policy-as-code, CI and a starter app, and keeps those standards up to date by
reference.

**Is it an app or a framework?**
Neither. It is the generator plus the base content other projects refer to. Your project is the
app.

**Why does a project not contain the base?**
So a standard added later reaches every project. Copied bases drift (this was the original design
and was replaced: [ADR 0006](../adr/0006-base-by-reference.md)). The project pins an exact commit
and a hash, so it is still reproducible and tamper-evident.

**What are "standards as code"?**
A written rule with an ID, a policy that enforces it, and tests. A rule without an enforcement
mechanism is documentation, and is marked `planned`. See [ADR 0001](../adr/0001-standards-as-code-over-orchestrator.md).

**Do I need Claude Code?**
To use the personas, yes today: the generated agents and slash commands are for Claude Code. The
personas themselves are tool-neutral Markdown ([ADR 0004](../adr/0004-tool-neutral-personas.md)),
and the generator, lock, policies and CI do not need it. Supporting another tool means a new
generator in `sync_agents.py`; nobody has written one.

**Do the agents do everything on their own?**
No. A human approves each handoff (spec, TRD/ADR, finops report, applying infrastructure). The one
exception is that the reviewer may merge a pull request classified low risk when every gate passes;
set `"auto_merge": "off"` to remove it.

## Setup and usage

**Where do I run `magrathea`?**
Anywhere. It is one Python file; `init` records where Magrathea lives. See
[Getting started](01-getting-started.md).

**Can I use a private Magrathea or distribution repo?**
The CLI and bootstrap use your own git credentials, so locally it should work. In CI the project
must be able to read the repo (a token); this has **not** been tried. Treat it as unverified.

**A teammate cloned my project and agent edits are blocked.**
They need `make setup`. The base lives in the git-ignored `.magrathea/`, and the path guards call
scripts from it; they fail closed on purpose.

**How do I get new standards into an existing project?**
`make upgrade` (or `magrathea upgrade <dir>`), then review the diff to `magrathea.lock.json`.

**Why did `make upgrade` not update my README or Makefile?**
Those are files the project owns. The changelog says when a template changed; copy it in by hand.

**Can I edit something in `.magrathea/`?**
No. It is a cache and `make verify`/CI fail if it differs from the lock. Add behavior under
`local/`, or ask the owner of the base (`/request-standard`).

**What if two standards disagree?**
Rules are cumulative and each carries an ID; reviewers cite IDs. A project cannot reuse or
override a base ID, and the base does not define exceptions. If two rules truly conflict, that is a
change to the base: raise a request.

**What stops an agent from loosening a rule to pass CI?**
Standards and policy sit behind CODEOWNERS, so changing them needs a human owner. That only works
with branch protection that requires code-owner review, which Magrathea cannot set up for you.
"Do not change a standard in the same PR as the code it judges" is a working agreement in the
personas' instructions, not something CI enforces. What CI does enforce: the base cache matches the
lock, and local standards and policy cannot reuse a base ID or define `exception` rules.

**Do agents get cloud credentials?**
They should not. Developer agents have no cloud access, the platform engineer only *plans*, and a
human applies. The path guard covers file-editing tools only; a persona with a shell could still
run commands, so do not run agents with credentials that can change cloud resources.

## Customizing

**How do I make this my company's Magrathea?**
Create a distribution: a folder with `distro.json` plus only your differences. See
[Customizing](03-customizing.md) and the [Acme example](04-sample-projects.md#c-a-company-distribution-acme-platform).

**Should I fork Magrathea instead?**
You can, and it is the simplest if you only ever want your own copy. A distribution is better when
you want to keep receiving upstream improvements: your changes stay in your folder and upstream
changes arrive as a ref bump you review, rather than as merge conflicts.

**How do I change one rule in a Magrathea standard?**
Replace the whole standards file at the same path in your distribution. Overriding a single rule
by ID is not supported. Better: add your own rule in a new file and avoid reusing the ID. A new
file that reuses a rule ID which an upstream file defines is rejected.

**Can my distribution build on another distribution?**
No. The upstream must be Magrathea itself (no chaining).

**What happens when Magrathea releases a new version?**
Nothing, to your projects, until you bump `upstream.ref` in your distribution, review, tag and let
projects `make upgrade`.

**What is the difference between `templates/` and `base/` in a distribution?**
`templates/` is read by the generator when a project is created and copied once; the project then
owns the files. `base/` is fetched by reference and reaches existing projects on upgrade.

**Can I keep the Magrathea workflow personas (`/add-standard` etc.) at an older version?**
That is decided but not built yet: per-persona pin/local options, `workflow status`, and a
compatibility table of engine versus persona versions ([status](03-customizing.md#status)). For now
the workflow is whatever Magrathea checkout you run; pin it with a git tag.

**Do `/add-standard` and `/add-stack` work on my distribution?**
Not yet. They edit Magrathea's own tree. Use them to draft, then copy the result into your
distribution and run its tests.

## Troubleshooting

**`rule X is defined in standards/a.md of the distribution and in standards/b.md of the upstream`**
Your file defines an ID the upstream still defines elsewhere. Rename your rule, or replace the
upstream file at the same path.

**`remove path 'x' matches nothing in the upstream base`**
The upstream renamed or dropped it. Delete the entry from `remove`.

**`the upstream ... is itself a distribution; chaining is not supported`**
`upstream.source` points at another distribution. Point it at Magrathea.

**`the base fetched ... does not match magrathea.lock.json`**
A tag moved, or the source changed. If that is intended, `python3 scripts/magrathea_sync.py --update`.
If not, find out why before you do.

**A project created before distributions fails to follow one.**
The project owns its `scripts/magrathea_sync.py`, and an old copy does not understand
`distro.json`. Copy the new script from `templates/project/scripts/` into the project.

**The version in my project says `0.5.1`, but my distribution is `2.0`.**
You did not ship a `base/VERSION` in the distribution, so the project records the upstream's.

## Project and licence

**What is the license?**
None chosen yet. Choose one before publishing. (`templates/project/README.md` also links to a
repository URL, now set to the GitHub repo.)

**What is not tested?**
See [the overview](README.md#what-is-and-is-not-proven): stack builds, Kyverno, CI workflows,
private-repo fetching, real `tofu` plans, and live Claude Code sessions.

**Where do I report a problem or propose a change?**
Open an issue at https://github.com/jcgozar/magrathea/issues (the repository is private for now). Inside a project, `/request-standard` writes the request for
whoever maintains the base.
