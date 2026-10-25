---
description: Ask Magrathea to add a standard, an infrastructure type, a CI/CD pattern, or to change a base rule
argument-hint: <what is missing and why>
---

Write a request for the Magrathea platform engineer. It maintains the base, which this
project can only use and extend, not change.

Topic: $ARGUMENTS

1. Check `.magrathea/standards/` and `local/standards/` first. If something already covers
   this, say so and stop.
2. Use the `platform-engineer` agent to write `requests/magrathea-<slug>.md` from
   `requests/STANDARD-REQUEST-TEMPLATE.md`: the type of request (standard, infrastructure
   type, CI/CD pattern or rule change), why this project needs it, the rules you propose
   (MUST or SHOULD, each testable), what would enforce them, and what is blocked meanwhile.
3. Tell me where the file is and that it has to go to Magrathea: open an issue or PR on the
   Magrathea repo, or run `/add-standard` there with this file. Do not copy rules into
   `.magrathea/`; it is read-only here.
4. If I want a stopgap, use the `security` agent to add a narrower version in
   `local/standards/` with a clearly different rule ID prefix. Say it is temporary and must be
   removed after the Magrathea change arrives (`make upgrade`).
