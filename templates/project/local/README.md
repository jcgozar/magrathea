# local/

What this project adds on top of the Magrathea base in `.magrathea/` (a read-only cache of the Magrathea repo).
You can add here; you cannot change or remove the base.

| Folder | Add | Rules |
| --- | --- | --- |
| `personas/` | `<name>.md` with **no** front matter adds behavior to the base persona of that name. A file with front matter defines a new persona. | A base persona's permissions and rules cannot be changed. Run `make sync` afterwards. |
| `standards/` | New standards (same table format as `.magrathea/standards/README.md`). | Rule IDs must not reuse a base ID. |
| `policy/` | Rego that enforces your standards, with tests. | `package local`; `deny` and `warn` only; no `exception` rules. |

`make verify` checks all of this, and CI runs it.

If the base lacks a whole infrastructure type (say, a message queue), run
`/request-standard` rather than working around it.
