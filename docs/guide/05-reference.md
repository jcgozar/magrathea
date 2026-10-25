# 5. Reference

## Files in a project

### `magrathea.json`

```json
{ "source": "https://github.com/acme/acme-platform.git", "ref": "v1.0.0", "auto_merge": "low" }
```

A project attached to a domain platform also has `"infra_mode": "domain", "domain": "payments"`;
a domain platform repository has `"type": "domain-platform"` and a `domain` (see
[Domain platforms](07-domain-platform.md)).

| Field | Meaning |
| --- | --- |
| `source` | Where the base comes from: a git URL or a folder. For a project made with a distribution this is the **distribution**. |
| `ref` | Tag, branch or commit to follow. `null` follows the default branch. |
| `auto_merge` | `low` (the reviewer may merge low-risk PRs) or `off`. Nothing else is accepted: a project may be stricter than the base, never looser. |
| `infra_mode` | Optional. `standalone` (default when absent) or `domain`. Never added or changed by `make upgrade`. |
| `domain` | Optional. Names the domain platform; required when `infra_mode` is `domain`. Lowercase letters, digits, hyphens. |
| `type` | Optional. `project` (default when absent) or `domain-platform`. A `domain-platform` has no `infra_mode`. |

### `magrathea.lock.json`

```json
{
  "source": "...", "ref": "v1.0.0", "commit": "<40 hex>", "version": "1.0.0",
  "tree_hash": "<sha256 of the merged base>",
  "upstream": { "source": "https://github.com/jcgozar/magrathea.git", "ref": "v1.0.0", "commit": "<40 hex>" }
}
```

`commit` is the source's exact commit (`null` for a plain folder). `upstream` appears only when
the source is a distribution. `tree_hash` covers every file of the merged base, so an edit to
`.magrathea/` is detected. `source` and `ref` must agree with `magrathea.json`.

### `.magrathea/`

Git-ignored cache of the merged base. Layout:

| Folder | Holds |
| --- | --- |
| `agents/personas/` | Tool-neutral personas |
| `standards/` | Standards with rule IDs |
| `policy/` | Rego (`conftest/`) and Kyverno policies, with tests |
| `scripts/` | Persona generator, path guard, lock check (with `mode-data` and `mode-change`), risk classifier |
| `project-types.json` | Which personas and commands a project `type` does not get |
| `review/risk.json` | Risk-tier rules |
| `claude/commands/` | Slash commands, copied to `.claude/commands/` by `make sync` |
| `docs/` | `WORKFLOW.md`, `FINOPS-TEMPLATE.md` |
| `VERSION` | The base version |

## Files in a distribution

### `distro.json`

| Field | Required | Meaning |
| --- | --- | --- |
| `upstream.source` | yes | Git URL or folder of Magrathea. A relative folder resolves from the distribution. |
| `upstream.ref` | no | Tag or branch. `null` follows the default branch (not recommended). |
| `remove` | no | Paths under `base/` to drop from the upstream. Relative, no `..`. An entry that matches nothing is an error. |

A distribution folder is detected by `distro.json`. Anything else in the folder is
`base/...` (fetched by projects) or `templates/...` (read by the generator at creation).

## CLI

`magrathea_cli.py` (alias `magrathea`). A top-level `--no-input` stops all prompts: a missing value
is then an error.

| Command | Purpose |
| --- | --- |
| `init [--source S] [--ref R] [--distro DIR] [--distro-source S] [--distro-ref R]` | Save where Magrathea (and your distribution) live. Fails now if unreachable. `--distro ""` clears the saved one. A flag given here replaces the whole saved distribution. |
| `stacks [--distro DIR]` | List stacks, including the distribution's. |
| `new [TARGET] [--name] [--stack] [--description] [--owner] [--source] [--ref] [--domain D] [--distro ...] [--yes]` | Create a project. `--domain D` attaches it to the domain platform `D` (`infra_mode: "domain"`); interactively it asks for one (blank: standalone). `--source` / `--ref` choose which Magrathea provides the generator. With a distribution, `--distro-source` / `--distro-ref` say what the project follows. |
| `new-domain [TARGET] [--name] [--domain] [--description] [--owner] [--source] [--ref] [--distro ...] [--yes]` | Create a domain platform repository (the `domain-platform` stack) without a project. Nothing in it is ready to apply. |
| `upgrade TARGET [--ref R]` | Move a project to the newest base (or `--ref`). Prints the files that changed. |

Environment: `MAGRATHEA_CLI_CONFIG` (config file, default `~/.config/magrathea/cli.json`),
`MAGRATHEA_CLI_CACHE` (clone cache, default `~/.cache/magrathea/source`). The CLI stores no
tokens; private git sources use your own git credentials.

The generator can be called directly: `python3 tools/magrathea.py {stacks|new|new-domain|upgrade}` with the
same options (plus `--distro`). It does no prompting.

## Make targets (Magrathea repo)

| Target | What it does |
| --- | --- |
| `make test` | Base script tests, generator and CLI tests, Rego tests (needs `opa`) |
| `make sample` | Scaffold and verify a throwaway project and the Acme example in `.scratch/` |
| `make sync` | Regenerate `.claude/` from `meta/` (do not edit `.claude/`) |

For a project's make targets see [Using a project](02-using-a-project.md#make-targets).

## Versions

| Version | File | Bumped when |
| --- | --- | --- |
| Engine | `VERSION`, `ENGINE_CHANGELOG.md` | The generator, CLI, or workflow persona/command behavior changes |
| Base (defaults) | `base/VERSION`, `CHANGELOG.md` | **Every** change under `base/`: every project receives it |
| Workflow personas and commands | `version:` in front matter of `meta/personas/*.md`, `meta/commands/*.md` | The file changes (all start at 1.0.0) |
| Your distribution | its own `base/VERSION` and `CHANGELOG.md` | Every change to its `base/` |

The compatibility record between engine versions and workflow file versions is planned
([status](03-customizing.md#status)); today the version fields exist but nothing reads them.

## Persona file format

```markdown
---
name: <file name without .md>
description: <when to use it>
access: read | read-shell | edit-no-shell | edit-shell
writable_paths:          # edit-* only; never under .magrathea/
  - specs/
model: <optional>
---
<Markdown prompt body>
```

| `access` | Tools |
| --- | --- |
| `read` | Read, Grep, Glob |
| `read-shell` | Read, Grep, Glob, Bash |
| `edit-no-shell` | Read, Edit, Write, Glob, Grep |
| `edit-shell` | Read, Edit, Write, Glob, Grep, Bash |

A local persona **without** front matter appends text to the base persona of that name.

## Standards: rule table

| ID | Strength | Rule | Enforced by | Status |
| --- | --- | --- | --- | --- |

`eks-cluster.md` has an extra **Part** column (`provide`, `consume`, `both`) after Strength. Status is
always the last column. `MUST` blocks the PR, `SHOULD` warns. `implemented` means a policy plus a passing and a failing
test exist; `planned` is documentation only. IDs match `[A-Z][A-Z0-9]*-\d+` at the start of a table
row and are never reused.

## Template placeholders

`@@name@@`, `@@slug@@`, `@@description@@`, `@@stack@@`, `@@stack_title@@`, `@@stack_notes@@`,
`@@magrathea_version@@` (the base version), `@@owner@@`, `@@source@@`, `@@ref@@`, `@@domain@@`
(the domain platform name; empty for a project that is not attached to or creating one). An unknown
placeholder fails the build.

## Where to read more

| Topic | Document |
| --- | --- |
| Why standards are code | [ADR 0001](../adr/0001-standards-as-code-over-orchestrator.md) |
| Tool-neutral personas | [ADR 0004](../adr/0004-tool-neutral-personas.md) |
| Scaffold and lock | [ADR 0005](../adr/0005-scaffold-and-lock.md) |
| Base by reference | [ADR 0006](../adr/0006-base-by-reference.md) |
| Engine and distributions | [ADR 0007](../adr/0007-engine-and-distributions.md) |
| Shared domain platform | [ADR 0009](../adr/0009-shared-domain-platform.md) |
| Plan and roadmap | [PLAN.md](../PLAN.md) |
