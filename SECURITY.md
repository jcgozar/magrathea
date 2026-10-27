# Security Policy

## Reporting a vulnerability

Please do not open a public issue for a security problem.

Report it privately through GitHub: open the **Security** tab of this repository and choose
**Report a vulnerability**. Include what you found, how to reproduce it, and which version
(`VERSION` and `base/VERSION`) you used.

This is a small project maintained by one person, so there is no guaranteed response time. I will
acknowledge a report as soon as I can and keep you updated on the fix.

## What is in scope

- The generator and CLI in `tools/`.
- The scripts that projects fetch from `base/scripts/`, including the path guard and the lock check.
- The policies in `base/policy/` when they let through something they should block.
- Templates in `templates/` that scaffold an insecure default.

## Supported versions

Only the latest release and `main` receive fixes. Projects pick up fixes to `base/` with
`make upgrade`.

## Good to know

Magrathea generates projects and fetches `base/` by reference at a pinned commit. A fix in `base/`
reaches a project only when that project upgrades its pin.
