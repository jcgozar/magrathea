#!/usr/bin/env python3
"""Generate .claude/agents and .claude/commands from the Magrathea base plus local additions.

    python3 .magrathea/scripts/sync_agents.py          # write the generated files
    python3 .magrathea/scripts/sync_agents.py --check  # exit 1 if out of date (for CI)

Inputs:
  .magrathea/agents/personas/*.md   base personas (read-only cache of the Magrathea base)
  local/personas/<name>.md          project additions. Without front matter, the text is
                                    appended to the base persona of that name. With front
                                    matter, it defines a new persona (it cannot reuse a base name).
  .magrathea/claude/commands/*.md   base slash commands

The Magrathea repo uses the same script for its own agents:
  python3 base/scripts/sync_agents.py --root . --personas-dir meta/personas \\
      --commands-dir meta/commands --local-dir "" --scripts-dir base/scripts

A project whose magrathea.json says `"type": "domain-platform"` gets a subset: the personas and
commands that `.magrathea/project-types.json` excludes for that type are not generated (ADR 0009).
Without a type, or with `"project"`, everything is generated, as before.

A persona file has simple front matter (name, description, access, writable_paths,
optional model) followed by the prompt body. Only this script knows Claude Code's
file format, so supporting another tool means adding one more generator here.
"""

import argparse
import json
import sys
from pathlib import Path

MARKER = "GENERATED from "
BASE_DIR = ".magrathea"
LOCAL_HEADING = "## Project-specific behavior"

# Tool-neutral access levels, mapped to Claude Code tool names.
ACCESS_TOOLS = {
    "read": ["Read", "Grep", "Glob"],
    "read-shell": ["Read", "Grep", "Glob", "Bash"],
    "edit-no-shell": ["Read", "Edit", "Write", "Glob", "Grep"],
    "edit-shell": ["Read", "Edit", "Write", "Glob", "Grep", "Bash"],
}

# File-editing tools covered by the path guard.
GUARDED_TOOLS = "Edit|Write|NotebookEdit"


class PersonaError(Exception):
    pass


def unquote(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_persona(text, source):
    """Parse front matter (key: value, and key: followed by '- item' lines) and body."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise PersonaError("%s: missing front matter" % source)
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
    except StopIteration:
        raise PersonaError("%s: front matter is not closed" % source)

    meta = {}
    key = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw.lstrip().startswith("- "):
            if key is None or not isinstance(meta.get(key), list):
                raise PersonaError("%s: list item with no key: %r" % (source, raw))
            meta[key].append(unquote(raw.lstrip()[2:]))
            continue
        if ":" not in raw:
            raise PersonaError("%s: cannot parse front matter line %r" % (source, raw))
        name, _, value = raw.partition(":")
        key = name.strip()
        meta[key] = [] if value.strip() == "" else unquote(value)

    body = "\n".join(lines[end + 1 :]).strip("\n") + "\n"
    return meta, body


def validate(meta, stem, source):
    for field in ("name", "description", "access"):
        if not meta.get(field) or isinstance(meta[field], list):
            raise PersonaError("%s: '%s' is required" % (source, field))
    if meta["name"] != stem:
        raise PersonaError("%s: name '%s' must match the file name" % (source, meta["name"]))
    if meta["access"] not in ACCESS_TOOLS:
        raise PersonaError(
            "%s: access must be one of %s" % (source, ", ".join(sorted(ACCESS_TOOLS)))
        )
    paths = meta.get("writable_paths", [])
    if meta["access"].startswith("edit") and not paths:
        raise PersonaError("%s: an editing persona needs writable_paths" % source)
    if meta["access"].startswith("read") and paths:
        raise PersonaError("%s: a read-only persona cannot have writable_paths" % source)
    for p in paths:
        if "'" in p or '"' in p:
            raise PersonaError("%s: quotes are not allowed in writable_paths" % source)
        if BASE_DIR in p:
            raise PersonaError("%s: a persona may not write to %s (read-only)" % (source, BASE_DIR))


def render_claude(meta, body, stem, origin, scripts_dir=BASE_DIR + "/scripts"):
    lines = [
        "---",
        "name: %s" % meta["name"],
        "description: %s" % json.dumps(meta["description"]),
        "tools: %s" % ", ".join(ACCESS_TOOLS[meta["access"]]),
    ]
    if meta.get("model"):
        lines.append("model: %s" % meta["model"])
    paths = meta.get("writable_paths", [])
    if paths:
        allow = " ".join("--allow '%s'" % p for p in paths)
        command = 'python3 "$CLAUDE_PROJECT_DIR/%s/check_paths.py" %s' % (scripts_dir, allow)
        lines += [
            "hooks:",
            "  PreToolUse:",
            "    - matcher: %s" % json.dumps(GUARDED_TOOLS),
            "      hooks:",
            "        - type: command",
            "          command: %s" % json.dumps(command),
        ]
    lines += [
        "---",
        "<!-- %s%s by sync_agents.py. Do not edit; edit the source. -->" % (MARKER, origin),
        "",
        "",
    ]
    return "\n".join(lines) + body


def split_front_matter(text):
    return text.lstrip().startswith("---")


def type_exclusions(root):
    """(excluded personas, excluded commands) for the project type in magrathea.json; ((), ()) if none."""
    try:
        config = json.loads((root / "magrathea.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return (), ()
    kind = config.get("type") if isinstance(config, dict) else None
    if not kind or kind == "project":
        return (), ()
    try:
        types = json.loads((root / BASE_DIR / "project-types.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise PersonaError("magrathea.json has type '%s' but %s/project-types.json is missing or invalid" % (kind, BASE_DIR))
    if kind not in types:
        raise PersonaError("magrathea.json type '%s' is not defined in %s/project-types.json" % (kind, BASE_DIR))
    return tuple(types[kind].get("exclude_personas", [])), tuple(types[kind].get("exclude_commands", []))


def build(root, personas_dir=BASE_DIR + "/agents/personas", commands_dir=BASE_DIR + "/claude/commands",
          local_dir="local/personas", scripts_dir=BASE_DIR + "/scripts", exclude_personas=(), exclude_commands=()):
    """Return {relative output path: content} for every persona and command."""
    base_dir = root / personas_dir
    local_dir = root / local_dir if local_dir else None
    outputs = {}
    sources = sorted(base_dir.glob("*.md"))
    if not sources:
        raise PersonaError("no personas found in %s" % base_dir)

    base = {}
    for src in sources:
        source = src.relative_to(root).as_posix()
        meta, body = parse_persona(src.read_text(encoding="utf-8"), source)
        validate(meta, src.stem, source)
        base[src.stem] = (meta, body, source)

    additions = {}
    new_personas = {}
    for src in sorted(local_dir.glob("*.md")) if local_dir and local_dir.is_dir() else []:
        if src.name.lower() == "readme.md":
            continue
        source = src.relative_to(root).as_posix()
        text = src.read_text(encoding="utf-8")
        if split_front_matter(text):
            if src.stem in base:
                raise PersonaError(
                    "%s: cannot redefine the base persona '%s'. Remove the front matter to add "
                    "behavior to it, or pick another name." % (source, src.stem)
                )
            meta, body = parse_persona(text, source)
            validate(meta, src.stem, source)
            new_personas[src.stem] = (meta, body, source)
        else:
            if src.stem not in base:
                raise PersonaError(
                    "%s: no base persona named '%s' to add behavior to" % (source, src.stem)
                )
            additions[src.stem] = (text.strip("\n") + "\n", source)

    for stem, (meta, body, source) in base.items():
        if stem in exclude_personas:
            continue
        origin = source
        if stem in additions:
            extra, extra_source = additions[stem]
            body = body.rstrip("\n") + "\n\n%s\n\nAdded by this project (`%s`). These add to the rules above and never replace them.\n\n%s" % (
                LOCAL_HEADING, extra_source, extra)
            origin = "%s + %s" % (source, extra_source)
        outputs[".claude/agents/%s.md" % stem] = render_claude(meta, body, stem, origin, scripts_dir)
    for stem, (meta, body, source) in new_personas.items():
        if stem in exclude_personas:
            continue
        outputs[".claude/agents/%s.md" % stem] = render_claude(meta, body, stem, source, scripts_dir)

    command_dir = root / commands_dir
    for src in sorted(command_dir.glob("*.md")) if command_dir.is_dir() else []:
        if src.stem in exclude_commands:
            continue
        text = src.read_text(encoding="utf-8")
        source = src.relative_to(root).as_posix()
        lines = text.splitlines()
        if not lines or lines[0].strip() != "---":
            raise PersonaError("%s: command needs front matter" % source)
        end_fm = next(i for i in range(1, len(lines)) if lines[i].strip() == "---")
        marker = "<!-- %s%s by sync_agents.py. Do not edit. -->" % (MARKER, source)
        outputs[".claude/commands/%s.md" % src.stem] = "\n".join(lines[: end_fm + 1] + [marker, ""] + lines[end_fm + 1 :]) + "\n"
    return outputs


def stale_files(root, outputs):
    """Generated agent files that no longer have a source persona."""
    stale = []
    for sub in ("agents", "commands"):
        folder = root / ".claude" / sub
        if folder.is_dir():
            for path in sorted(folder.glob("*.md")):
                rel = path.relative_to(root).as_posix()
                if rel not in outputs and MARKER in path.read_text(encoding="utf-8"):
                    stale.append(rel)
    return stale


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if files are out of date")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent.parent))
    parser.add_argument("--personas-dir", default=BASE_DIR + "/agents/personas")
    parser.add_argument("--commands-dir", default=BASE_DIR + "/claude/commands")
    parser.add_argument("--local-dir", default="local/personas", help='"" for none')
    parser.add_argument("--scripts-dir", default=BASE_DIR + "/scripts", help="where check_paths.py lives")
    args = parser.parse_args(argv)
    root = Path(args.root)

    try:
        exclude_personas, exclude_commands = type_exclusions(root)
        outputs = build(root, args.personas_dir, args.commands_dir, args.local_dir, args.scripts_dir,
                        exclude_personas, exclude_commands)
    except PersonaError as err:
        print("error: %s" % err, file=sys.stderr)
        return 1

    stale = stale_files(root, outputs)
    problems = []
    for rel, content in outputs.items():
        path = root / rel
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            problems.append("out of date: %s" % rel)
    problems += ["stale: %s (no source persona)" % rel for rel in stale]

    if args.check:
        if problems:
            for p in problems:
                print(p, file=sys.stderr)
            print("run the sync again without --check", file=sys.stderr)
            return 1
        print("agents and commands in sync (%d files)" % len(outputs))
        return 0

    for rel, content in outputs.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    for rel in stale:
        (root / rel).unlink()
    print("wrote %d files%s" % (len(outputs), ", removed %d stale" % len(stale) if stale else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
