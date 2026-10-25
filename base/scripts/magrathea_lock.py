"""Check that a project still honors the Magrathea base it is pinned to.

    python3 .magrathea/scripts/magrathea_lock.py verify        # run in CI

Checks:
  1. magrathea.json is valid and agrees with magrathea.lock.json.
  2. .magrathea/ is present and identical to what the lock recorded (hash of every file).
     The base is fetched from the Magrathea repo, not committed here, so an edit to the
     local copy is detected and `python3 scripts/magrathea_sync.py` restores it.
  3. local/standards/ does not reuse or restate a base rule ID, so base rules cannot be
     replaced or removed by redefining them.
  4. local/policy/*.rego use `package local` and define no `exception` rules, so local
     policies can only add checks to the base, never switch base checks off.
  5. The optional mode fields (`infra_mode`, `domain`, `type`) are valid (DOMAIN-002). Absent
     fields mean `standalone` / `project`; nothing is enforced on a project that has none.

Other commands (ADR 0009):
  mode-data --out FILE     write the effective mode as {"magrathea": {...}} for `conftest --data`
  mode-change --previous F fail if infra_mode, domain or type differ from the previous
                           magrathea.json, unless --approved (DOMAIN-003). If the previous file is
                           missing, empty or invalid it exits 0 with a warning on stderr

Limit: the lock is in this repo, so someone can edit .magrathea/ and the lock together.
CODEOWNERS on magrathea.json and magrathea.lock.json is the control for that, and a changed
lock shows up in review. Nobody can alter the base for other projects from here.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

BASE_DIR = ".magrathea"
CONFIG = "magrathea.json"
LOCK = "magrathea.lock.json"
AUTO_MERGE_VALUES = ("off", "low")
IGNORED_DIRS = {".git", "__pycache__"}
INFRA_MODES = ("standalone", "domain")
PROJECT_TYPES = ("project", "domain-platform")
DOMAIN_NAME = re.compile(r"[a-z][a-z0-9-]{0,30}[a-z0-9]|[a-z]")  # use fullmatch
RULE_ROW = re.compile(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|", re.MULTILINE)
PACKAGE = re.compile(r"^\s*package\s+([\w.]+)", re.MULTILINE)
EXCEPTION = re.compile(r"^\s*(?:default\s+)?exception\b", re.MULTILINE)


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def hash_tree(base):
    base = Path(base)
    out = {}
    for path in sorted(base.rglob("*")):
        if path.is_file() and not (set(path.relative_to(base).parts) & IGNORED_DIRS):
            out[path.relative_to(base).as_posix()] = file_hash(path)
    return out


def tree_hash(base):
    return hashlib.sha256(json.dumps(hash_tree(base), sort_keys=True).encode()).hexdigest()


def base_rule_ids(base):
    ids = set()
    for md in Path(base, "standards").glob("*.md"):
        ids.update(RULE_ROW.findall(md.read_text(encoding="utf-8")))
    return ids


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), None
    except FileNotFoundError:
        return None, "%s is missing" % Path(path).name
    except ValueError:
        return None, "%s is not valid JSON" % Path(path).name


def effective_mode(config):
    """The mode with defaults applied; an absent field means standalone / project."""
    return {
        "infra_mode": config.get("infra_mode") or "standalone",
        "domain": config.get("domain") or None,
        "type": config.get("type") or "project",
    }


def mode_problems(config):
    """DOMAIN-002: the optional mode fields are valid. Absent fields are always fine."""
    problems = []
    mode = config.get("infra_mode")
    kind = config.get("type")
    domain = config.get("domain")
    if "infra_mode" in config and mode not in INFRA_MODES:
        problems.append("magrathea.json: infra_mode must be one of %s" % ", ".join(INFRA_MODES))
    if "type" in config and kind not in PROJECT_TYPES:
        problems.append("magrathea.json: type must be one of %s" % ", ".join(PROJECT_TYPES))
    if "domain" in config and (not isinstance(domain, str) or not DOMAIN_NAME.fullmatch(domain)):
        problems.append("magrathea.json: domain must be a lowercase name of letters, digits and hyphens")
    if mode == "domain" and not domain:
        problems.append("magrathea.json: infra_mode \"domain\" requires a domain name")
    if kind == "domain-platform" and "infra_mode" in config:
        problems.append("magrathea.json: a domain-platform has no infra_mode of its own")
    return problems


def mode_changes(previous, current):
    """DOMAIN-003: the mode fields that differ (by effective value) between two configs."""
    before, after = effective_mode(previous), effective_mode(current)
    return ["%s: %s -> %s" % (k, before[k], after[k]) for k in before if before[k] != after[k]]


def verify(root):
    root = Path(root)
    base = root / BASE_DIR
    problems = []

    config, err = load(root / CONFIG)
    if err:
        return [err]
    lock, err = load(root / LOCK)
    if err:
        return [err + "; run `python3 scripts/magrathea_sync.py --update`"]
    if config.get("auto_merge", "off") not in AUTO_MERGE_VALUES:
        problems.append(
            "magrathea.json: auto_merge must be one of %s (a project may be stricter than the base, never looser)"
            % ", ".join(AUTO_MERGE_VALUES)
        )
    problems += mode_problems(config)
    if config.get("source") != lock.get("source") or config.get("ref") != lock.get("ref"):
        problems.append("magrathea.json (source/ref) and magrathea.lock.json disagree; run `python3 scripts/magrathea_sync.py --update`")

    if not base.is_dir():
        problems.append("%s/ is missing; run `python3 scripts/magrathea_sync.py` (or `make setup`)" % BASE_DIR)
        return problems
    if tree_hash(base) != lock.get("tree_hash"):
        problems.append("%s/ differs from magrathea.lock.json (edited or stale); run `python3 scripts/magrathea_sync.py` to restore it" % BASE_DIR)

    reserved = base_rule_ids(base)
    for md in sorted((root / "local" / "standards").glob("*.md")) if (root / "local" / "standards").is_dir() else []:
        for rule_id in RULE_ROW.findall(md.read_text(encoding="utf-8")):
            if rule_id in reserved:
                problems.append(
                    "%s redefines base rule %s; base rules cannot be replaced or removed"
                    % (md.relative_to(root).as_posix(), rule_id)
                )

    policy_dir = root / "local" / "policy"
    for rego in sorted(policy_dir.rglob("*.rego")) if policy_dir.is_dir() else []:
        text = rego.read_text(encoding="utf-8")
        rel = rego.relative_to(root).as_posix()
        pkg = PACKAGE.search(text)
        name = pkg.group(1) if pkg else ""
        if not (name == "local" or name.startswith(("local.", "local_test"))):
            problems.append("%s must use `package local` (found %s)" % (rel, pkg.group(1) if pkg else "none"))
        if EXCEPTION.search(text):
            problems.append("%s defines an `exception` rule; local policy may only add checks" % rel)
    return problems


def command_mode_data(root, out):
    config, err = load(Path(root) / CONFIG)
    if err:
        print("FAIL: %s" % err, file=sys.stderr)
        return 1
    bad = mode_problems(config)
    if bad:
        for p in bad:
            print("FAIL: %s" % p, file=sys.stderr)
        return 1
    Path(out).write_text(json.dumps({"magrathea": effective_mode(config)}, indent=2) + "\n", encoding="utf-8")
    return 0


def command_mode_change(root, previous, approved):
    config, err = load(Path(root) / CONFIG)
    if err:
        print("FAIL: %s" % err, file=sys.stderr)
        return 1
    old, _ = load(previous) if previous and Path(previous).is_file() and Path(previous).stat().st_size else (None, None)
    if old is None:  # no earlier magrathea.json (new repository, or unreadable): nothing to compare
        print("WARNING: the previous magrathea.json is missing, empty or invalid; the mode check (DOMAIN-003) "
              "was SKIPPED and compared nothing", file=sys.stderr)
        return 0
    changed = mode_changes(old, config)
    if not changed:
        print("infra_mode, domain and type are unchanged")
        return 0
    for c in changed:
        print("MODE CHANGE: %s" % c, file=sys.stderr)
    if approved:
        print("approved as a migration; state, identity, networking and data must be planned and reviewed", file=sys.stderr)
        return 0
    print("Changing the mode is a migration, not a setting. Label the pull request `mode-migration` once the "
          "migration is planned and approved.", file=sys.stderr)
    return 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=["verify", "mode-data", "mode-change"])
    parser.add_argument("--root", default=str(Path(__file__).resolve().parent.parent.parent))
    parser.add_argument("--out", help="mode-data: file to write")
    parser.add_argument("--previous", help="mode-change: the previous magrathea.json")
    parser.add_argument("--approved", action="store_true", help="mode-change: the change is an approved migration")
    args = parser.parse_args(argv)
    if args.command == "mode-data":
        if not args.out:
            parser.error("mode-data needs --out")
        return command_mode_data(args.root, args.out)
    if args.command == "mode-change":
        return command_mode_change(args.root, args.previous, args.approved)
    problems = verify(args.root)
    if problems:
        for p in problems:
            print("FAIL: %s" % p, file=sys.stderr)
        print("The Magrathea base is read-only here. Add to it under local/, or ask Magrathea (/request-standard).", file=sys.stderr)
        return 1
    print("magrathea base intact; local additions are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
