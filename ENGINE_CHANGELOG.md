# Engine changelog

What changes for the person running Magrathea's tools (`tools/`) and the `magrathea-*`
workflow personas and commands. Changes to the content projects receive are in
[CHANGELOG.md](CHANGELOG.md). Which workflow file versions work with which engine versions is
in [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) once that exists (ADR 0007).

## 0.7.1

Fixes after an independent review of 0.7.0.

- Project template `ci.yml`: the `pull_request` trigger now has `types: [opened, synchronize, reopened, labeled, unlabeled]`
  so adding the `mode-migration` label re-runs the mode check. Comments say that CODEOWNERS on `magrathea.json` plus
  branch protection is the real approval control, and that the step is `pull_request`-only (a direct push skips it).
  Still never run in CI. New projects only.
- `tools/magrathea.py` validates `--domain` with `fullmatch` (a trailing newline is rejected).
- `tools/test_magrathea.py`: the ID-uniqueness test now asserts that the allowed `COMMON-001`/`COMMON-002` duplicate in
  `postgres.md` has the same text as the one in `eks-cluster.md`.
- `docs/guide/07-domain-platform.md` and `AGENTS.md` state what is and is not tested or enforced in CI.

## 0.7.0

Shared domain platform support (ADR 0009). Existing projects and commands behave as before.

- `tools/magrathea.py`: `new --domain D` attaches a project to a domain platform (`infra_mode: "domain"`);
  `new-domain` creates a domain platform repository (stack `domain-platform`, `type: "domain-platform"`,
  `auto_merge: "off"`). `new_project(..., distro=None, domain=None)` gains a trailing optional argument;
  `list_stacks(distro=None)` is unchanged. A stack may declare `"type"` in `stack.json`. New placeholder
  `@@domain@@`. Without `domain`, `magrathea.json` is written exactly as before.
- `tools/magrathea_cli.py`: `new --domain`, an interactive prompt for it, and `new-domain`. It asks before creating the
  second repository and says nothing in it is ready to apply. Creating a domain platform together with a project
  in one run is not built.
- New stack `domain-platform`: OpenTofu skeletons per area (`global`, `network`, `eks`, `addons`) with SSM parameters
  at `/<domain>/<region>/platform/<name>`, a runbook for the manual apply and a capacity-request issue template.
  The OpenTofu has never been run or validated.
- Project template (new projects only): `make check` writes `.mode.json` and passes it to conftest; CI gains a
  mode-change step for pull requests; `requests/DOMAIN-REQUEST-TEMPLATE.md`; `.mode.json` is git-ignored. To adopt in an
  existing project, copy those by hand. The CI step has never run.

## 0.6.0

- The engine has its own version (this file and `VERSION`), separate from `base/VERSION`.
- `tools/magrathea.py` accepts `--distro DIR` for `new` and `stacks`: a distribution's
  `templates/project` and `templates/stacks` are layered over the defaults (ADR 0007, step 1).
  - A project can follow a distribution (ADR 0007, step 2). `new --distro DIR` writes the
  distribution as the project's `source`. `templates/project/scripts/magrathea_sync.py` now
  reads the source's `distro.json`, fetches its `upstream` first, applies `remove`, lays the
  distribution's `base/` over it, and rejects a rule ID the distribution shares with a different
  upstream file. The lock gains an `upstream` entry (source, ref, commit), so both commits are
  pinned. Plain sources behave as before. Projects created earlier keep their copy of the
  bootstrap (a file they own); copy the new `scripts/magrathea_sync.py` in to follow a
  distribution.
- `tools/magrathea_cli.py` accepts `--distro`, `--distro-source` and `--distro-ref` on `init` (saved
  in the CLI config), `new` and `stacks`. `upgrade` of a project that follows a distribution loads
  the generator from the configured Magrathea, since a distribution holds no tools.
- New: `examples/acme-platform` (a working distribution: a stack, a standard, a persona and a
  replaced template), `tools/test_examples.py`, and `make sample` builds it.
- New: `docs/guide/` (getting started, using a project, customizing, sample projects,
  reference, FAQ).
- Workflow personas and commands carry a `version` in their front matter, all starting at 1.0.0.
