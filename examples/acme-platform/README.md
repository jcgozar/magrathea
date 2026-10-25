# Acme platform (example distribution)

A small, working example of a Magrathea distribution for a made-up company. It holds only
what differs from Magrathea's defaults:

| File | What it shows |
| --- | --- |
| `distro.json` | The upstream this distribution builds on. Here `../..` is the Magrathea checkout this example lives in; yours would be a git URL and a tag. |
| `base/standards/acme-naming.md` | A new company standard. Every project on this distribution receives it. |
| `base/agents/personas/compliance.md` | A new persona. Projects get it as `.claude/agents/compliance.md`. |
| `templates/project/.github/CODEOWNERS` | A replaced template: a default team owns platform paths. Used by `new` only. |
| `templates/stacks/static-site/` | A new stack, available next to the defaults. |

Try it from the Magrathea root:

```sh
python3 tools/magrathea.py stacks --distro examples/acme-platform
python3 tools/magrathea.py new .scratch/acme-site --distro examples/acme-platform \
  --name "Acme Site" --stack static-site --owner @acme-lead
```

`make sample` and `make test` build this example, so it stays working.
