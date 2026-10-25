# 0004. Tool-neutral personas, with generated Claude Code files

Status: Accepted (2026-10-22), from the planning conversation.

## Context

The agents are defined as personas (PM, architect, developer, reviewer, security,
platform/SRE, QA/eval, UX). Claude Code reads subagents from `.claude/agents/*.md`, with a
Claude-specific front matter (`tools`, `hooks`, `model`). The project should not be locked
to one AI tool: only a thin layer is tool-specific.

## Decision

- The source of truth is tool-neutral Markdown in `base/agents/personas/` (vendored into projects as `.magrathea/agents/personas/`, extended by `local/personas/`): name, description,
  an access level, writable paths, and the prompt body (role, reads, writes, never, hand-off).
- `base/scripts/sync_agents.py` (in a project: `.magrathea/scripts/`) generates `.claude/agents/*.md` from them. The generated files
  are committed so the agents work immediately; CI fails if they drift.
- Path limits are enforced for the file-editing tools by a small script
  (`check_paths.py`) that the generated files call as a hook. Hooks stay thin and
  call repo scripts, so CI or another tool can run the same logic.
- Orchestration (`.claude/commands/`) is a thin, Claude-specific layer. The flow itself is
  described tool-neutrally in `docs/WORKFLOW.md`.
- Real enforcement stays outside the tool: CODEOWNERS, branch protection and CI.

## Consequences

- Supporting another tool means adding a generator to `sync_agents.py`, not rewriting
  personas.
- The path guard does not cover a persona's shell access. Personas that have a shell can
  write files through it, so CODEOWNERS and CI are the backstop, and agents should not run
  with credentials that can change cloud resources.
- The slash commands and subagent delegation are the least portable part and would need
  rebuilding for another tool.
