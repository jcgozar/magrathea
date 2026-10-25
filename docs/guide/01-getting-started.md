# 1. Getting started

You will install nothing beyond what you probably have: clone Magrathea, point its CLI at it, and
create a project.

## Requirements

| Needed for | Tool |
| --- | --- |
| Everything | `python3` and `git` |
| The AI personas | [Claude Code](https://claude.com/claude-code) (VS Code extension or CLI), with the project folder opened and **trusted**, because the path guards are hooks and Claude Code runs project hooks only in trusted folders |
| Policy tests (`make test` in Magrathea or a project) | `opa` |
| Checking a real infrastructure plan | `conftest`, and `tofu` to produce the plan |
| Rendering architecture diagrams (`make diagrams`) | `plantuml` (optional) |
| Building the sample apps | Java and Maven, or Node, per the stack's own README |

## 1. Get Magrathea

```sh
git clone <your Magrathea URL> magrathea     # TODO: the public URL is not decided yet
cd magrathea
make test                                    # optional: needs opa
```

## 2. Tell the CLI where Magrathea is

```sh
python3 tools/magrathea_cli.py init --source "$PWD"
```

This saves `~/.config/magrathea/cli.json`. The CLI is a single standard-library file; you can
copy it anywhere and run `init` against a git URL instead of a folder. A Git URL is cloned into
`~/.cache/magrathea/source` and refreshed on each run.

> Shortcut for the rest of this guide:
> `alias magrathea='python3 /path/to/magrathea/tools/magrathea_cli.py'`

## 3. See what stacks exist

```sh
magrathea stacks
# java-service  A single Spring Boot 4 REST microservice on Java 25 (LTS), ...
# react-java    React 18 + TypeScript (Vite) web app and a Spring Boot 3 REST API on Java 21, ...
```

## 4. Create a project

Interactively (prompts for anything you leave out, with an arrow-key stack picker):

```sh
magrathea new
```

Or in one line, with no prompts (good for scripts):

```sh
magrathea --no-input new ../my-app --name "My App" --stack java-service \
  --description "What it does" --owner @your-github-handle --yes
```

The generator then:

1. renders `templates/project/` and the stack into the new folder,
2. fetches the base into `.magrathea/` and writes `magrathea.lock.json` (the exact commit and a
   hash of every file),
3. generates the Claude Code agents into `.claude/`,
4. verifies the result.

The same inputs always give the same repository.

Prefer Claude Code to interview you? Open the Magrathea folder in VS Code, trust it, start Claude
Code and run `/new-project an expense tracker for a small team`. It asks what it
needs, drafts `CONTEXT.md` for your approval, then runs the same generator.

## 5. First steps in the new project

```sh
cd ../my-app
git init && git add . && git commit -m "Scaffold from Magrathea"
make setup        # fetch the pinned base into .magrathea/ (do this after every clone)
```

1. Open the folder in VS Code and **trust it**.
2. Write `CONTEXT.md`: what the project is, who it is for, goals, non-goals, constraints. It is
   the one file a human writes; every agent reads it. Mark guesses as guesses.
3. Replace the placeholder owner in `.github/CODEOWNERS` (together with branch protection that requires
   code-owner review, this is what makes an agent's change to a standard or policy need a human).
4. In Claude Code, `/agents` lists the personas. Start a feature with `/feature <idea>`.

Continue with [2. Using a project](02-using-a-project.md).

## Things that commonly go wrong

| Symptom | Cause and fix |
| --- | --- |
| `error: ... is not a Magrathea source` | `init --source` must be the Magrathea checkout (the folder with `tools/` and `base/`), not a project or a distribution. |
| Agent edits are blocked right after cloning a project | The path guards call scripts in `.magrathea/`, which is not in git. Run `make setup`. The guards fail closed on purpose. |
| `exists and is not empty` | `new` refuses to write into a non-empty folder. |
| `unknown stack 'x'` | `magrathea stacks` lists what is available (and your distribution's, if any). |
| The project's `source` is a local path | Fine for trying things out. CI and teammates need a git URL: pass `--source <url>` to `new`, or edit `magrathea.json` and run `make upgrade`. |
