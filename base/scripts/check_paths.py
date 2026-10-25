#!/usr/bin/env python3
"""PreToolUse hook: allow file edits only under the given glob patterns.

Used by the generated Claude Code agent files. Claude Code passes the tool call as JSON
on stdin. Exit 0 allows the call; exit 2 blocks it and sends stderr back to the agent.

    check_paths.py --allow 'app/**' --allow 'requests/**'

Limits: this guards the file-editing tools only (Edit, Write, NotebookEdit). An agent
that also has a shell can still change files through it, so CODEOWNERS, branch
protection and CI remain the real backstop.
"""

import argparse
import json
import os
import re
import sys


def glob_to_regex(glob):
    """Translate a path glob to a regex. `**` crosses directories, `*` and `?` do not."""
    out = []
    i = 0
    while i < len(glob):
        c = glob[i]
        if c == "*":
            if glob[i : i + 2] == "**":
                if glob[i : i + 3] == "**/":
                    out.append("(?:.*/)?")
                    i += 3
                    continue
                out.append(".*")
                i += 2
                continue
            out.append("[^/]*")
        elif c == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(c))
        i += 1
    return re.compile("^" + "".join(out) + "$")


def target_path(tool_input):
    return tool_input.get("file_path") or tool_input.get("notebook_path")


def check(data, allow, env, cwd):
    """Return None if the call is allowed, otherwise the reason it is blocked."""
    tool_input = data.get("tool_input") or {}
    path = target_path(tool_input)
    if not path:
        return None  # not a file-editing call

    project = os.path.realpath(env.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or cwd)
    base = data.get("cwd") or project
    absolute = path if os.path.isabs(path) else os.path.join(base, path)
    absolute = os.path.realpath(absolute)
    rel = os.path.relpath(absolute, project).replace(os.sep, "/")

    if rel == ".." or rel.startswith("../"):
        return "%s is outside the project." % path
    if any(glob_to_regex(g).match(rel) for g in allow):
        return None
    return "%s is not in this agent's writable paths (%s)." % (rel, ", ".join(allow))


def main(argv=None, stdin=None, env=None, cwd=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--allow", action="append", default=[], metavar="GLOB")
    args = parser.parse_args(argv)

    stdin = stdin if stdin is not None else sys.stdin
    env = env if env is not None else os.environ
    cwd = cwd if cwd is not None else os.getcwd()

    try:
        data = json.load(stdin)
    except ValueError:
        print("Blocked: could not read the hook input.", file=sys.stderr)
        return 2

    reason = check(data, args.allow, env, cwd)
    if reason:
        print(
            "Blocked: %s Hand this to the right persona or ask the human." % reason,
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
