# Technical requirements documents (TRDs)

A TRD is the agreed technical design for a spec. The `architect` writes one when a change is
complex, when there is no architecture yet for the area, or when it needs new infrastructure.
Small changes that fit an existing design do not get one.

- Number them `NNNN-<slug>.md` from `TEMPLATE.md`. Status starts as `Draft`.
- Only a human sets `Approved`.
- The `developer` builds to the approved TRD, the `platform-engineer` provides its
  infrastructure section, and the independent `architecture-reviewer` checks code against it.
- If the design must change during the build, update the TRD (and say so); do not let code and
  design drift apart.
- Deployment architecture: for projects on AWS the TRD has a PlantUML diagram,
  `docs/trd/NNNN-<slug>.puml`, committed as text. `make diagrams` renders SVG next to it
  (needs `plantuml`; skips with a message if absent; the SVG is git-ignored). Mermaid stays for
  sequence diagrams.
