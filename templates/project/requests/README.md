# Requests

How the developer agent asks the platform for something it cannot do itself. Create
`NNN-<slug>.md` from `TEMPLATE.md`. The `platform-engineer` agent answers in the same file.
Files named `magrathea-<slug>.md` are requests to the Magrathea repo (a missing standard,
infrastructure type or CI/CD pattern) from `STANDARD-REQUEST-TEMPLATE.md`; they are answered there,
not here. Capacity or changes for the shared infrastructure of a **domain platform** (`infra_mode:
"domain"`) go to its operator as an issue in the domain platform repository; draft it from
`DOMAIN-REQUEST-TEMPLATE.md`. Do not send those through `magrathea-*` files. Nothing here yet.
