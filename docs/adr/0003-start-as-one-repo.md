# 0003. Start as one repo with two top-level folders

Status: Superseded by 0005. Magrathea is now a separate repo that generates projects.

## Context

The platform should be open-sourceable, so it must behave like something the app
consumes from outside. Two repos force that discipline but add friction (versioning the
platform, cross-repo PRs), which matters at about 8 hours a week.

## Decision

Start with one repo containing `platform/` and `app/` as top-level folders. Split
`platform/` out when it is ready to open source (for example with `git filter-repo`).
The rule that makes this safe: `app/` never imports from `platform/` internals.

## Consequences

- One PR can touch both sides when needed, and agents share one `AGENTS.md`.
- The boundary is enforced by convention and review until the split, so it needs a CI check once there is code on both sides.
- If the friction of one repo becomes a problem, or the platform needs its own release cadence, split earlier.
