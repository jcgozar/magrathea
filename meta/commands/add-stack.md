---
description: Add a new stack template (for example Python/FastAPI or Go) to Magrathea
version: 1.0.0
argument-hint: <stack description>
---

Use the `magrathea-platform-engineer` agent to add a stack template for: $ARGUMENTS

Create `templates/stacks/<name>/` with `stack.json`, `notes.md` and `files/` (mirror
`templates/stacks/react-java/`), include a Dockerfile that is non-root with pinned tags, a
`service.yaml` per deployable, and CI workflows. Add a test to `tools/test_magrathea.py`
that scaffolds it. Run `make test` and `make sample`. Try to build the generated app and
say plainly if the sandbox could not. Do not change `base/`.
