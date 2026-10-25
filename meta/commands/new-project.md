---
description: Scaffold a new project from Magrathea. Interviews you, drafts CONTEXT.md, then runs the generator
version: 1.0.0
argument-hint: <your project idea>
---

Scaffold a new project with Magrathea.

The idea: $ARGUMENTS

1. **Interview.** Run `python3 tools/magrathea.py stacks` to see the available stacks. Ask me
   (one short message, not a form) for anything the idea does not already tell you: the
   project name, who it is for, the stack (default to the closest available), where to create
   it (default `../<slug>`), and any architectural decisions I have already made. If no stack
   fits, say so and offer to add one with the `magrathea-platform-engineer` agent rather than picking a wrong one.
2. **Draft CONTEXT.md.** Write it to `.scratch/CONTEXT.md` using the sections in
   `templates/project/CONTEXT.md`. Fill in what I told you. Mark everything I did not say as
   TODO; do not invent users, goals or constraints. Show it to me and **wait for approval**.
3. **Scaffold.** Run `python3 tools/magrathea.py new <target> --name "<name>" --stack <stack>
   --description "<one sentence>" --context .scratch/CONTEXT.md`. If I gave a GitHub handle,
   pass `--owner`. Pass `--source` with the Magrathea git URL and `--ref` with a tag if I
   have published Magrathea; otherwise the project will refer to this local checkout, which works
   on this machine but not in CI. Say so.
4. **Record decisions.** For each architectural decision I already made, write
   `docs/adr/NNNN-<slug>.md` in the new project from `docs/adr/template.md` there, status
   `Accepted`. Number from 0002; `0001` is the stack. Do not invent decisions.
5. **Report.** Show the folder tree at depth 2, say what was verified by the generator, say
   what was not (see the notes in `AGENTS.md` about untested parts), and tell me the next
   steps: open the new folder in VS Code, trust it, fill in the TODOs in `CONTEXT.md`, set the
   CODEOWNERS owner, `git init`.

Do not run anything inside the new project beyond what the generator did, and do not push.
