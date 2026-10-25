#!/usr/bin/env python3
"""Flag changes to base/ that projects could be surprised by.

    python3 tools/check_base_change.py --base origin/main

Compares the working tree with the merge base of --base and reports:
  - a rule ID removed from base/standards/
  - a rule whose strength went from MUST to SHOULD
  - a rule whose status went from implemented to planned
  - changes under base/ with no base/VERSION bump or no CHANGELOG.md change

Exit 1 if anything is reported. A removal or a weakening needs a human decision; this tool
only makes sure it is seen.
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROW = re.compile(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|\s*([A-Z]+)\s*\|(.*)\|\s*(implemented[^|]*|planned[^|]*)\|\s*$", re.MULTILINE)


def git(repo, *args, check=True):
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)
    if check and result.returncode:
        raise SystemExit("git %s failed: %s" % (args[0], result.stderr.strip()))
    return result.stdout


def rules(text):
    out = {}
    for rule_id, strength, _, status in ROW.findall(text):
        out[rule_id] = (strength, status.strip().split()[0].rstrip(",").lower())
    return out


def standards_at(repo, ref):
    out = {}
    names = git(repo, "ls-tree", "-r", "--name-only", ref, "base/standards", check=False).split()
    for name in names:
        if name.endswith(".md"):
            out.update(rules(git(repo, "show", "%s:%s" % (ref, name))))
    return out


def standards_now(repo):
    out = {}
    for path in sorted(Path(repo, "base", "standards").glob("*.md")):
        out.update(rules(path.read_text(encoding="utf-8")))
    return out


def check(repo, base):
    merge_base = git(repo, "merge-base", base, "HEAD").strip()
    before, after = standards_at(repo, merge_base), standards_now(repo)
    findings = []
    for rule_id, (strength, status) in sorted(before.items()):
        if rule_id not in after:
            findings.append("rule %s was removed" % rule_id)
            continue
        new_strength, new_status = after[rule_id]
        if strength == "MUST" and new_strength != "MUST":
            findings.append("rule %s was weakened from MUST to %s" % (rule_id, new_strength))
        if status == "implemented" and new_status != "implemented":
            findings.append("rule %s went from implemented to %s" % (rule_id, new_status))
    changed = set(git(repo, "diff", "--name-only", merge_base).split())
    changed |= set(git(repo, "ls-files", "--others", "--exclude-standard").split())
    if any(p.startswith("base/") for p in changed):
        if "base/VERSION" not in changed:
            findings.append("base/ changed but base/VERSION was not bumped")
        if "CHANGELOG.md" not in changed:
            findings.append("base/ changed but CHANGELOG.md has no entry")
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", required=True)
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parent.parent))
    args = parser.parse_args(argv)
    findings = check(args.repo, args.base)
    for f in findings:
        print("REVIEW: %s" % f, file=sys.stderr)
    if not findings:
        print("no removed or weakened rules; version and changelog updated")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
