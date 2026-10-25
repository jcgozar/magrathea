#!/usr/bin/env python3
"""Classify a change as low, medium or high risk, and decide whether it may auto-merge.

    python3 .magrathea/scripts/review_risk.py classify --base origin/main [--head HEAD]
    python3 .magrathea/scripts/review_risk.py gate --tier low --verdict approve --ci success

The tier is the *floor*: the reviewer persona may raise it on judgment but never lower it.
Anything not clearly low is left to a human. The rules are in .magrathea/review/risk.json.

Tiers
  high    touches infrastructure, CI, dependencies, containers, migrations, decisions (ADR/TRD),
          project config, or adds code that mentions auth, secrets, crypto and similar; or is
          very large.
  medium  moderately large, touches evals, interfaces or project context, or changes app code
          without changing any test.
  low     small (<= max_lines_low lines, <= max_files_low files), docs or specs, or app changes
          that come with tests.

`gate` allows an automatic merge only when magrathea.json has "auto_merge": "low" AND the
tier is low AND the reviewer approved AND CI passed AND no independent reviewer found a
blocker. Otherwise a human decides.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from check_paths import glob_to_regex

BASE = Path(__file__).resolve().parent.parent
ORDER = {"low": 0, "medium": 1, "high": 2}


def load_config(path=None):
    return json.loads(Path(path or BASE / "review" / "risk.json").read_text(encoding="utf-8"))


def matches(path, patterns):
    return any(re.fullmatch(glob_to_regex(p), path) for p in patterns)


def classify(changes, added_text, cfg):
    """changes: list of {"path", "added", "removed"}; added_text: {path: text of added lines}."""
    tier = "low"
    reasons = []

    def raise_to(level, reason):
        nonlocal tier
        if ORDER[level] > ORDER[tier]:
            tier = level
        reasons.append("%s: %s" % (level, reason))

    if not changes:
        return {"tier": "low", "reasons": ["no changes"], "files": 0, "lines": 0}

    files = len(changes)
    lines = sum(c["added"] + c["removed"] for c in changes)
    paths = [c["path"] for c in changes]

    for path in paths:
        if matches(path, cfg["high_paths"]):
            raise_to("high", "%s is a sensitive path" % path)
        elif matches(path, cfg["medium_paths"]):
            raise_to("medium", "%s needs a closer look" % path)

    words = [w.lower() for w in cfg["sensitive_words"]]
    for path in paths:
        haystack = (path + "\n" + added_text.get(path, "")).lower()
        hit = next((w for w in words if w in haystack), None)
        if hit:
            raise_to("high", "%s mentions '%s'" % (path, hit))

    if files > cfg["max_files_medium"] or lines > cfg["max_lines_medium"]:
        raise_to("high", "very large change (%d files, %d lines)" % (files, lines))
    elif files > cfg["max_files_low"] or lines > cfg["max_lines_low"]:
        raise_to("medium", "larger than a small change (%d files, %d lines)" % (files, lines))

    is_test = lambda p: matches(p, cfg["test_paths"])
    is_doc = lambda p: matches(p, cfg["low_paths"])
    source = [p for p in paths if p.startswith("app/") and not is_test(p) and not is_doc(p)]
    if source and not any(is_test(p) for p in paths):
        raise_to("medium", "app code changed without any test change")

    unknown = [p for p in paths if not (p.startswith("app/") or is_doc(p) or is_test(p)
                                         or matches(p, cfg["high_paths"]) or matches(p, cfg["medium_paths"]))]
    if unknown:
        raise_to("medium", "files outside app/ and docs: %s" % ", ".join(unknown[:3]))

    return {"tier": tier, "reasons": reasons or ["small change in app code with tests, or docs only"], "files": files, "lines": lines}


def gate(tier, verdict, ci, setting, blockers=0):
    reasons = []
    if setting != "low":
        reasons.append("auto_merge is '%s' in magrathea.json; a human merges" % setting)
    if tier != "low":
        reasons.append("risk is %s; a human must review" % tier)
    if verdict != "approve":
        reasons.append("reviewer verdict is '%s'" % verdict)
    if ci != "success":
        reasons.append("CI is '%s', not success" % ci)
    if blockers:
        reasons.append("%d blocking finding(s) from an independent reviewer" % blockers)
    return {"merge": not reasons, "reasons": reasons or ["low risk, approved, CI green, no blockers"]}


def git(*args, repo="."):
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if result.returncode:
        raise SystemExit("git %s failed: %s" % (args[0], result.stderr.strip()))
    return result.stdout


def diff_from_git(base, head, repo="."):
    merge_base = git("merge-base", base, head, repo=repo).strip()
    changes = []
    for line in git("diff", "--numstat", "-M", "%s...%s" % (merge_base, head), repo=repo).splitlines():
        added, removed, path = line.split("\t", 2)
        if "=>" in path:  # rename: keep the new path
            path = re.sub(r"\{.* => (.*)\}", r"\1", path).replace("//", "/") if "{" in path else path.split(" => ")[-1]
        binary = added == "-"
        changes.append({"path": path, "added": 100 if binary else int(added), "removed": 0 if binary else int(removed)})
    added_text, current = {}, None
    for line in git("diff", "-U0", "-M", "%s...%s" % (merge_base, head), repo=repo).splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
        elif line.startswith("+") and not line.startswith("+++") and current:
            added_text[current] = added_text.get(current, "") + line[1:] + "\n"
    return changes, added_text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("classify")
    c.add_argument("--base", required=True)
    c.add_argument("--head", default="HEAD")
    c.add_argument("--repo", default=".")
    c.add_argument("--config")
    g = sub.add_parser("gate")
    g.add_argument("--tier", required=True, choices=list(ORDER))
    g.add_argument("--verdict", required=True, choices=["approve", "request-changes"])
    g.add_argument("--ci", required=True)
    g.add_argument("--blockers", type=int, default=0)
    g.add_argument("--setting", help="default: auto_merge from magrathea.json")
    g.add_argument("--project", default=".")
    args = parser.parse_args(argv)

    if args.command == "classify":
        changes, added_text = diff_from_git(args.base, args.head, args.repo)
        print(json.dumps(classify(changes, added_text, load_config(args.config)), indent=2))
        return 0
    setting = args.setting
    if setting is None:
        try:
            setting = json.loads((Path(args.project) / "magrathea.json").read_text(encoding="utf-8")).get("auto_merge", "off")
        except (OSError, ValueError):
            setting = "off"
    result = gate(args.tier, args.verdict, args.ci, setting, args.blockers)
    print(json.dumps(result, indent=2))
    return 0 if result["merge"] else 1


if __name__ == "__main__":
    sys.exit(main())
