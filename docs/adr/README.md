# Architecture decision records

Why Magrathea is built the way it is. Read these before proposing a change to the design.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-standards-as-code-over-orchestrator.md) | Standards are code, not an orchestrator | Accepted |
| 0002 | Not in this repository: it recorded an architecture for a product built with Magrathea, not for Magrathea | Moved out |
| [0003](0003-start-as-one-repo.md) | Start as one repo | Superseded by 0005 |
| [0004](0004-tool-neutral-personas.md) | Tool-neutral personas, with generated Claude Code files | Accepted |
| [0005](0005-scaffold-and-lock.md) | Magrathea scaffolds projects and locks the base | Accepted |
| [0006](0006-base-by-reference.md) | Projects refer to the base instead of holding a copy | Accepted |
| [0007](0007-engine-and-distributions.md) | Engine and distributions | Accepted, in progress |
| [0008](0008-scaling-project-documents.md) | Keeping project documents readable by agents as a project grows | Proposed, pending measurement |
| [0009](0009-shared-domain-platform.md) | Shared domain platform infrastructure | Accepted (2026-10-25), in progress |
| [0010](0010-gitlab-support.md) | GitLab and GitLab CI support | Accepted (2026-10-25), in progress; nothing built |
| [0011](0011-deployed-third-party-services.md) | Deployed third-party services | Accepted (2026-10-25), in progress; nothing built |

Numbers are never reused, so 0002 stays a gap.
