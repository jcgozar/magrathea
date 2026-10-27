# Contributing to Magrathea

Thanks for helping. Read [AGENTS.md](AGENTS.md) first: it describes the layout and the rules this
repo follows, and they apply to people as well as agents.

## Ways to contribute

- **Report a problem or ask for a standard:** open an issue. Say which project type or stack it
  affects and what you expected.
- **Fix or improve something:** open a pull request. For anything larger than a small fix, open an
  issue first so we can agree on the approach.
- **Add a stack or a standard:** see `/add-stack` and `/add-standard` in `meta/`, and the existing
  entries in `templates/stacks/` and `base/standards/`.

## Before you open a pull request

```sh
make test      # needs opa
make sample    # scaffolds and verifies a throwaway project in .scratch/
```

Run both. If you changed `meta/`, run `make sync` and commit the result; do not edit `.claude/`
by hand.

## Rules for changes

- **`base/` stays generic.** No project names and no product or stack assumptions.
- **Version and changelog.** A change to `base/` bumps `base/VERSION` and adds a `CHANGELOG.md`
  entry. A change to `tools/`, `meta/` or `templates/project/scripts/` bumps `VERSION` and adds an
  `ENGINE_CHANGELOG.md` entry.
- **Do not weaken or remove a base rule** without explicit maintainer approval. Run
  `python3 tools/check_base_change.py --base <branch>` to see which rules your change touches.
- **Tests.** A rule is `implemented` only with a passing and a failing test.
- **Docs.** If behavior described in `docs/guide/` changes, update the guide and the example
  (`tools/test_examples.py`) in the same pull request. Describe what is planned, not built.
- **Facts.** Do not invent facts about cloud services or versions. Mark unknowns `TODO`.
- **Templates** use `@@placeholder@@`; the generator fails on unknown ones.
- **Decisions** that change direction belong in [docs/adr/](docs/adr/).

## Review

Changes are reviewed by someone other than the author. Expect questions about whether a base change
could break projects that run `make upgrade`.

## License

By contributing you agree that your contribution is licensed under the
[Apache License 2.0](LICENSE), the same as the project.
