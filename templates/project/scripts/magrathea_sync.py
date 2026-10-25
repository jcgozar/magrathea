#!/usr/bin/env python3
"""Fetch the Magrathea base into .magrathea/ at the version this project is pinned to.

    python3 scripts/magrathea_sync.py                 # fetch exactly what magrathea.lock.json says
    python3 scripts/magrathea_sync.py --update        # move to the newest commit of the configured ref
    python3 scripts/magrathea_sync.py --update --ref v0.3.0   # move to another ref

The base (personas, standards, policies, scripts) lives in the Magrathea repository, not in
this one. `.magrathea/` is a git-ignored cache of it. `magrathea.json` says where to fetch
from and which ref to track; `magrathea.lock.json` records the exact commit and a hash of
the fetched files, so everyone, and CI, gets the same base until someone runs --update.

If the source is a distribution (it has a distro.json), its upstream is fetched first and the
distribution's own base/ is laid over it: a file at the same path replaces the upstream file,
paths listed in distro.json "remove" are dropped, and a rule ID defined in two different files
is an error. The result is the one .magrathea/ the lock hashes.

Standard library only, so it works on a fresh clone before anything else exists.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = "magrathea.json"
LOCK = "magrathea.lock.json"
CACHE = ".magrathea"
IGNORED_DIRS = {".git", "__pycache__"}
DISTRO = "distro.json"
RULE_ROW = re.compile(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|", re.MULTILINE)


class SyncError(Exception):
    pass


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def hash_tree(base):
    """Map relative path -> sha256 for every file under base."""
    base = Path(base)
    out = {}
    for path in sorted(base.rglob("*")):
        if path.is_file() and not (set(path.relative_to(base).parts) & IGNORED_DIRS):
            out[path.relative_to(base).as_posix()] = file_hash(path)
    return out


def tree_hash(base):
    return hashlib.sha256(json.dumps(hash_tree(base), sort_keys=True).encode()).hexdigest()


def read_json(path, what):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SyncError("%s is missing" % what)
    except ValueError as err:
        raise SyncError("%s is not valid JSON: %s" % (what, err))


def git(*args, cwd=None):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env)
    if result.returncode:
        raise SyncError("git %s failed: %s" % (" ".join(args[:2]), result.stderr.strip()))
    return result.stdout.strip()


def is_hex_commit(rev):
    return bool(rev) and len(rev) == 40 and all(c in "0123456789abcdef" for c in rev)


def checkout(source, rev, dest, relative_to):
    """Make `source` at `rev` readable. Returns (folder, commit); commit is None for a plain folder."""
    local = Path(source) if os.path.isabs(source) else Path(relative_to) / source
    if "://" not in source and not source.startswith("git@") and local.is_dir():
        return local, None
    if is_hex_commit(rev):
        git("clone", "--quiet", source, str(dest))
        git("checkout", "--quiet", rev, cwd=str(dest))
    else:
        args = ["clone", "--quiet", "--depth", "1"]
        if rev:
            args += ["--branch", rev]
        git(*args, source, str(dest))
    return Path(dest), git("rev-parse", "HEAD", cwd=str(dest))


def copy_base(src, dest):
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*IGNORED_DIRS, "*.pyc"))


def read_distro(folder):
    """The settings of a distribution folder, or None if it is a plain base."""
    path = Path(folder) / DISTRO
    if not path.is_file():
        return None
    cfg = read_json(path, "%s of the source" % DISTRO)
    upstream = cfg.get("upstream")
    if not isinstance(upstream, dict) or not upstream.get("source"):
        raise SyncError("%s needs upstream.source (and usually upstream.ref)" % DISTRO)
    remove = cfg.get("remove", [])
    if not isinstance(remove, list) or not all(isinstance(r, str) for r in remove):
        raise SyncError("%s: remove must be a list of paths under base/" % DISTRO)
    for r in remove:
        if not r or os.path.isabs(r) or ".." in Path(r).parts:
            raise SyncError("%s: remove path %r must be relative and inside base/" % (DISTRO, r))
    return {"upstream": upstream, "remove": remove}


def overlay(src, dest):
    for path in sorted(Path(src).rglob("*")):
        rel = path.relative_to(src)
        if set(rel.parts) & IGNORED_DIRS or path.suffix == ".pyc":
            continue
        target = Path(dest) / rel
        if path.is_dir():
            if target.exists() and not target.is_dir():
                raise SyncError("the distribution has a folder where the upstream has a file: %s" % rel.as_posix())
            target.mkdir(parents=True, exist_ok=True)
        else:
            if target.is_dir():
                raise SyncError("the distribution has a file where the upstream has a folder: %s" % rel.as_posix())
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)


def rule_ids(md):
    return set(RULE_ROW.findall(md.read_text(encoding="utf-8")))


def check_rule_ids(merged, distro_base):
    """A distribution file may not define a rule ID that another (upstream) file still defines.

    To change a rule, replace the upstream file at the same path (or list it in "remove" and
    replace it). Upstream may repeat an ID across its own files; only the distribution is checked.
    """
    own = {md.name: rule_ids(md) for md in Path(distro_base, "standards").glob("*.md")}
    for md in sorted(Path(merged, "standards").glob("*.md")):
        if md.name in own:
            continue
        for rule_id in sorted(rule_ids(md)):
            clash = next((name for name, ids in sorted(own.items()) if rule_id in ids), None)
            if clash:
                raise SyncError(
                    "rule %s is defined in standards/%s of the distribution and in standards/%s of the "
                    "upstream. Replace the whole upstream file at the same path to change a rule."
                    % (rule_id, clash, md.name)
                )


def fetch(source, rev, workdir, root, upstream_rev=None):
    """Build workdir/base from `source` at `rev`.

    A plain source contributes its base/. A distribution (distro.json) contributes its upstream's
    base/ (at `upstream_rev`, else the ref in distro.json) with its own base/ laid over it.
    Returns (commit of source, upstream record or None).
    """
    src, commit = checkout(source, rev, workdir / "source", root)
    distro = read_distro(src)
    if distro is None:
        if not (src / "base").is_dir():
            raise SyncError("%s at %s has no base/ folder" % (source, rev or "default branch"))
        copy_base(src / "base", workdir / "base")
        return commit, None
    up = distro["upstream"]
    up_ref = up.get("ref")
    up_src, up_commit = checkout(up["source"], upstream_rev or up_ref, workdir / "upstream", src)
    if read_distro(up_src) is not None:
        raise SyncError("the upstream %s is itself a distribution; chaining is not supported" % up["source"])
    if not (up_src / "base").is_dir():
        raise SyncError("the upstream %s has no base/ folder" % up["source"])
    merged = workdir / "base"
    copy_base(up_src / "base", merged)
    for rel in distro["remove"]:
        victim = merged / rel
        if not victim.exists():
            raise SyncError("%s: remove path %r matches nothing in the upstream base; delete it from the list" % (DISTRO, rel))
        shutil.rmtree(victim) if victim.is_dir() else victim.unlink()
    if (src / "base").is_dir():
        overlay(src / "base", merged)
        check_rule_ids(merged, src / "base")
    return commit, {"source": up["source"], "ref": up_ref, "commit": up_commit}


def install(root, source, rev, expected_hash=None, upstream_rev=None):
    """Fetch into .magrathea/. Returns (commit, tree_hash, version, previous file hashes, upstream)."""
    cache = root / CACHE
    previous = hash_tree(cache) if cache.is_dir() else {}
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        commit, upstream = fetch(source, rev, work, root, upstream_rev)
        new_hash = tree_hash(work / "base")
        if expected_hash and new_hash != expected_hash:
            raise SyncError(
                "the base fetched from %s does not match magrathea.lock.json (a tag moved, or the "
                "source changed). Run `python3 scripts/magrathea_sync.py --update` if that is intended."
                % source
            )
        if cache.exists():
            shutil.rmtree(cache)
        shutil.copytree(work / "base", cache)
    version_file = cache / "VERSION"
    version = version_file.read_text(encoding="utf-8").strip() if version_file.is_file() else "unknown"
    return commit, new_hash, version, previous, upstream


def sync(root=ROOT, update=False, ref=None, source=None):
    root = Path(root)
    config = read_json(root / CONFIG, CONFIG)
    if update:
        if ref:
            config["ref"] = ref
        if source:
            config["source"] = source
        commit, digest, version, previous, upstream = install(root, config["source"], config.get("ref"))
        (root / CONFIG).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        lock = {"source": config["source"], "ref": config.get("ref"), "commit": commit,
                "version": version, "tree_hash": digest}
        if upstream:
            lock["upstream"] = upstream
        (root / LOCK).write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
        return lock, previous
    lock = read_json(root / LOCK, LOCK + " (run with --update once to create it)")
    cache = root / CACHE
    if cache.is_dir() and tree_hash(cache) == lock["tree_hash"]:
        return lock, hash_tree(cache)
    pinned = lock.get("upstream") or {}
    install(root, lock["source"], lock.get("commit") or lock.get("ref"), lock["tree_hash"],
            pinned.get("commit") or pinned.get("ref"))
    return lock, {}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--update", action="store_true", help="re-resolve the ref and rewrite the lock")
    parser.add_argument("--ref", help="with --update: track this tag, branch or commit from now on")
    parser.add_argument("--source", help="with --update: fetch from this git URL or path from now on")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args(argv)
    if (args.ref or args.source) and not args.update:
        parser.error("--ref and --source need --update")
    try:
        lock, previous = sync(args.root, args.update, args.ref, args.source)
    except SyncError as err:
        print("error: %s" % err, file=sys.stderr)
        return 1
    if args.update:
        now = hash_tree(Path(args.root) / CACHE)
        changed = sorted(p for p in set(previous) | set(now) if previous.get(p) != now.get(p))
        print("Magrathea base now at %s (%s); %d files changed" % (lock["version"], (lock["commit"] or "local path")[:12], len(changed)))
        for path in changed:
            print("  %s" % path)
        print("Next: python3 .magrathea/scripts/sync_agents.py && python3 .magrathea/scripts/magrathea_lock.py verify")
    else:
        print("Magrathea base %s ready in %s/" % (lock["version"], CACHE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
