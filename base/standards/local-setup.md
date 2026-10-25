# Local setup standard

Applies to every app a feature changes, in any stack. Its purpose: a human can install the
right tools and run the app and its tests from the README alone, and every command the README
shows has been run.

The mechanism for SETUP-001 to SETUP-005 is the `developer` and `reviewer` personas reading the
change and the hand-off. That is a judgment, not a deterministic check, and it can be skipped or
get things wrong. Those rules are therefore `planned`, not `implemented`: no policy or test
exists. SETUP-006 is the stronger mechanism and needs CI work.

## Rules

| ID | Strength | Rule | Enforced by | Status |
| --- | --- | --- | --- | --- |
| SETUP-001 | MUST | Every app a feature changes has a local-setup README at `app/README.md` (single-app project) or `app/<name>/README.md` (several apps; one per app) with a prerequisites section (a tool and version table). It also covers how to run tests, how to try the feature by hand, and troubleshooting | `reviewer` persona check | planned |
| SETUP-002 | MUST | Quick-start commands are one per line with no trailing comments (a trailing `#` is a glob in zsh) | `reviewer` persona check | planned |
| SETUP-003 | MUST | The developer runs every documented command, or lists the ones it did not run as "unverified" in both the hand-off and the README | `reviewer` persona check | planned |
| SETUP-004 | MUST | The reviewer records a finding (severity major, not blocker) when setup is unverified, or the README is missing or stale for the change | `reviewer` persona instructions | planned |
| SETUP-005 | SHOULD | Versions in the prerequisites table come from repo files (build file, package manifest, Dockerfile, compose file); unknown versions are marked TODO | `reviewer` persona check | planned |
| SETUP-006 | SHOULD | A CI job executes the documented quick start | Per-stack CI workflow template, owned by the Magrathea platform engineer | planned (templates untested) |

## Notes

- A README template is in `.magrathea/docs/LOCAL-SETUP-TEMPLATE.md`.
- Prerequisites to consider: language runtime, build tool (and its wrapper, if the docs name
  one, it must exist), container runtime, database, ports, environment variables (and how they
  are loaded into the shell), and test-time dependencies such as Testcontainers.
- Apps with no database, containers or proxy still need the README; its sections are short.

## Severity and re-running

- The SETUP-004 finding is **major, not blocker**. `review_risk.py gate` counts only blocking
  findings from independent reviewers, so this finding does not by itself stop auto-merge of a
  low-risk change; the reviewer's own verdict still decides whether to request changes. Existing
  apps without a README get this finding on their next change.
- The reviewer may re-run cheap commands from the README to check them.

## SETUP-006: CI template per stack

The Magrathea platform engineer owns one CI workflow template per stack, in
`templates/stacks/<stack>/files/.github/workflows/local-setup.yml`. It runs the commands in the
README's `## Quick start` code blocks. Other stacks add their own through `/add-stack`.

- A stack's template has never been run (no network or container runtime where it was written),
  so the rule stays `planned`. Stacks without a template have no CI check yet.
- The template joins the README's Quick start code blocks into one bash script with
  `set -euo pipefail`, run in order from the app directory. Limits: no foreground servers (a block
  that never exits runs to the job timeout and fails; background it or leave it out), and commands
  that need secrets, a local `.env` or a container runtime may fail in CI. TODO: confirm runner
  behaviour per stack.
- New projects scaffolded with that stack receive it automatically.
- Existing projects do **not** receive it on `make upgrade`, because it lives in `templates/`, not
  `base/`. They must copy it from the Magrathea repo.
