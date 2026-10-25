#!/usr/bin/env python3
"""Magrathea: scaffold projects from the base and a stack template, and upgrade them.

    python3 tools/magrathea.py stacks
    python3 tools/magrathea.py new ../my-app --name "My App" --stack react-java \\
        --description "What it does" [--owner @me] [--source GIT_URL] [--ref v0.1.0]
    python3 tools/magrathea.py new ../my-app ... --domain payments   # attach to a domain platform
    python3 tools/magrathea.py new-domain ../payments-platform --name "Payments" [--domain payments]
    python3 tools/magrathea.py upgrade ../my-app [--ref v0.2.0]

`--distro DIR` (on `new` and `stacks`) layers a distribution over the defaults (ADR 0007): files
in DIR/templates/project and DIR/templates/stacks/<stack> replace the default file at the same
path, and new stacks are added. DIR must hold a distro.json. With `new --distro`, the project
follows the distribution (--source and --ref then say where to fetch the distribution from;
default: DIR's git origin, or DIR itself), and the distribution's base/ is laid over its upstream.

`new` renders templates/project and the chosen stack into the target folder and writes
magrathea.json, which says where the base lives (this repo) and which ref to follow. It
then fetches base/ into <target>/.magrathea/ (a git-ignored cache) and records the exact
commit and a hash in magrathea.lock.json, generates the Claude Code agents and verifies
the result. The same inputs always give the same repository. Projects refer to this repo's
base/; they do not hold a copy of it.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "base"
PROJECT_TEMPLATE = ROOT / "templates" / "project"
STACKS = ROOT / "templates" / "stacks"
sys.path.insert(0, str(BASE / "scripts"))
sys.path.insert(0, str(PROJECT_TEMPLATE / "scripts"))

import magrathea_lock as lock  # noqa: E402
import magrathea_sync as bootstrap  # noqa: E402

IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
PLACEHOLDER = re.compile(r"@@(\w+)@@")
DISTRO_CONFIG = "distro.json"


DOMAIN_PLATFORM = "domain-platform"


class MagratheaError(Exception):
    pass


def version():
    return (BASE / "VERSION").read_text(encoding="utf-8").strip()


def slugify(name):
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not slug:
        raise MagratheaError("project name must contain letters or digits")
    return slug


def open_distro(distro):
    """The layers to resolve content from, defaults first. A distribution is a folder with distro.json."""
    if not distro:
        return [ROOT]
    distro = Path(distro).resolve()
    if not (distro / DISTRO_CONFIG).is_file():
        raise MagratheaError("%s is not a distribution: no %s" % (distro, DISTRO_CONFIG))
    return [ROOT, distro]


def stack_layers(layers, stack):
    return [layer / "templates" / "stacks" / stack for layer in layers if (layer / "templates" / "stacks" / stack).is_dir()]


def list_stacks(distro=None):
    """Stack metadata by name. Where a distribution has the same stack, its stack.json wins."""
    layers = open_distro(distro)
    names = sorted({p.name for layer in layers for p in (layer / "templates" / "stacks").glob("*") if p.is_dir()})
    stacks = {}
    for name in names:
        found = [d / "stack.json" for d in stack_layers(layers, name) if (d / "stack.json").is_file()]
        if not found:
            raise MagratheaError("stack '%s' has no stack.json in any layer" % name)
        stacks[name] = json.loads(found[-1].read_text(encoding="utf-8"))
    return stacks


def render(text, values, source):
    def repl(match):
        key = match.group(1)
        if key not in values:
            raise MagratheaError("%s: unknown placeholder @@%s@@" % (source, key))
        return values[key]

    return PLACEHOLDER.sub(repl, text)


def render_layers(src_roots, values):
    """Render the files of several layers into {relative path: bytes}; a later layer replaces an earlier one."""
    files = {}
    for src_root in src_roots:
        for src in sorted(src_root.rglob("*")):
            if not src.is_file() or "__pycache__" in src.parts or src.name == ".DS_Store":
                continue
            data = src.read_bytes()
            try:
                data = render(data.decode("utf-8"), values, src.as_posix()).encode("utf-8")
            except UnicodeDecodeError:
                pass
            files[src.relative_to(src_root).as_posix()] = data
    return files


def default_source(folder=ROOT):
    """The git remote of a checkout, else its path (fine locally, not for CI)."""
    result = subprocess.run(["git", "-C", str(folder), "remote", "get-url", "origin"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else str(folder)


def write_config(target, source, ref, extra=None):
    """magrathea.json. `extra` holds the optional mode fields (type, infra_mode, domain), written only when given."""
    config = {"source": source, "ref": ref, "auto_merge": "low"}
    config.update(extra or {})
    (target / bootstrap.CONFIG).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def run_project_script(target, script, *args):
    cmd = [sys.executable, str(target / ".magrathea" / "scripts" / script), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(target))
    return result.returncode, (result.stdout + result.stderr).strip()


def check_domain_name(domain):
    if not (isinstance(domain, str) and lock.DOMAIN_NAME.fullmatch(domain)):
        raise MagratheaError("domain '%s' must be a lowercase name of letters, digits and hyphens" % domain)


def new_project(target, name, stack, description, owner, context_file, source=None, ref=None, distro=None,
                domain=None):
    """Scaffold a project. `domain` attaches it to a domain platform (infra_mode "domain"); for a stack of
    type "domain-platform" it names the domain platform being created (default: the project's slug)."""
    layers = open_distro(distro)
    stacks = list_stacks(distro)
    if stack not in stacks:
        raise MagratheaError("unknown stack '%s'. Available: %s" % (stack, ", ".join(stacks) or "none"))
    kind = stacks[stack].get("type", "project")
    mode_fields = {}
    if kind == DOMAIN_PLATFORM:
        domain = domain or slugify(name)
        check_domain_name(domain)
        mode_fields = {"type": DOMAIN_PLATFORM, "domain": domain}
    elif domain:
        check_domain_name(domain)
        mode_fields = {"infra_mode": "domain", "domain": domain}
    target = Path(target).resolve()
    if target.exists() and any(target.iterdir()):
        raise MagratheaError("%s exists and is not empty" % target)
    if context_file and not Path(context_file).is_file():
        raise MagratheaError("context file not found: %s" % context_file)

    stack_dirs = stack_layers(layers, stack)
    notes = [d / "notes.md" for d in stack_dirs if (d / "notes.md").is_file()]
    meta = stacks[stack]
    values = {
        "name": name,
        "slug": slugify(name),
        "description": description or "TODO: one sentence on what this project does.",
        "stack": stack,
        "stack_title": meta["title"],
        "stack_notes": notes[-1].read_text(encoding="utf-8").strip() if notes else "",
        "magrathea_version": version(),
        "owner": owner,
        "source": source or (default_source(Path(distro).resolve()) if distro else default_source()),
        "ref": ref or "the default branch",
        "domain": domain or "",
    }
    target.mkdir(parents=True, exist_ok=True)
    project_files = render_layers([layer / "templates" / "project" for layer in layers], values)
    stack_files = render_layers([d / "files" for d in stack_dirs], values)
    for rel in sorted(set(project_files) & set(stack_files)):
        raise MagratheaError("template collision: %s exists already" % rel)
    for rel, data in {**project_files, **stack_files}.items():
        dest = target / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
    # With a distribution the project follows the distribution; its distro.json names the upstream.
    follow = source or (default_source(Path(distro).resolve()) if distro else default_source())
    write_config(target, follow, ref, mode_fields)
    if kind == DOMAIN_PLATFORM:  # every change to a domain platform is a human decision
        config = json.loads((target / bootstrap.CONFIG).read_text(encoding="utf-8"))
        config["auto_merge"] = "off"
        (target / bootstrap.CONFIG).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    try:
        bootstrap.sync(target, update=True)
    except bootstrap.SyncError as err:
        raise MagratheaError("could not fetch the base: %s" % err)
    if context_file:
        shutil.copyfile(context_file, target / "CONTEXT.md")

    code, out = run_project_script(target, "sync_agents.py")
    if code:
        raise MagratheaError("agent generation failed:\n%s" % out)
    code, out = run_project_script(target, "magrathea_lock.py", "verify")
    if code:
        raise MagratheaError("verification failed:\n%s" % out)
    return target, values


def upgrade_project(target, ref=None):
    target = Path(target).resolve()
    if not (target / bootstrap.CONFIG).is_file():
        raise MagratheaError("%s has no %s" % (target, bootstrap.CONFIG))
    try:
        old = json.loads((target / bootstrap.LOCK).read_text(encoding="utf-8")).get("version", "unknown")
        lock_data, previous = bootstrap.sync(target, update=True, ref=ref)
    except (bootstrap.SyncError, OSError) as err:
        raise MagratheaError(str(err))
    now = bootstrap.hash_tree(target / bootstrap.CACHE)
    changed = sorted(p for p in set(previous) | set(now) if previous.get(p) != now.get(p))
    code, out = run_project_script(target, "sync_agents.py")
    if code:
        raise MagratheaError("agent generation failed after upgrade:\n%s" % out)
    code, out = run_project_script(target, "magrathea_lock.py", "verify")
    return old, lock_data["version"], changed, (code, out)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p_stacks = sub.add_parser("stacks", help="list available stacks")
    p_stacks.add_argument("--distro", help="a distribution folder layered over the defaults")
    p_new = sub.add_parser("new", help="scaffold a new project")
    p_new.add_argument("target")
    p_new.add_argument("--name", required=True)
    p_new.add_argument("--stack", required=True)
    p_new.add_argument("--description", default="")
    p_new.add_argument("--owner", default="@your-github-handle")
    p_new.add_argument("--context", help="an existing CONTEXT.md to use instead of the template")
    p_new.add_argument("--source", help="git URL (or path) the project fetches the base from; default: this repo's origin")
    p_new.add_argument("--ref", help="tag, branch or commit to follow; default: the default branch")
    p_new.add_argument("--distro", help="a distribution folder layered over the defaults")
    p_new.add_argument("--domain", help="attach the project to this domain platform (infra_mode \"domain\")")
    p_dom = sub.add_parser("new-domain", help="scaffold a domain platform (shared infrastructure) repository")
    p_dom.add_argument("target")
    p_dom.add_argument("--name", required=True)
    p_dom.add_argument("--domain", help="domain name used in SSM paths (default: the slug of --name)")
    p_dom.add_argument("--description", default="")
    p_dom.add_argument("--owner", default="@your-github-handle")
    p_dom.add_argument("--source")
    p_dom.add_argument("--ref")
    p_dom.add_argument("--distro")
    p_up = sub.add_parser("upgrade", help="move a project to the newest base (or to --ref)")
    p_up.add_argument("target")
    p_up.add_argument("--ref")
    args = parser.parse_args(argv)

    try:
        if args.command == "stacks":
            for key, meta in list_stacks(args.distro).items():
                print("%-12s %s" % (key, meta["summary"]))
            return 0
        if args.command == "new":
            target, values = new_project(
                args.target, args.name, args.stack, args.description, args.owner, args.context,
                args.source, args.ref, args.distro, args.domain,
            )
            print("Created %s (%s, Magrathea %s)" % (target, values["stack_title"], values["magrathea_version"]))
            print("Next: fill in CONTEXT.md, set the owner in .github/CODEOWNERS, open the folder in VS Code.")
            return 0
        if args.command == "new-domain":
            target, values = new_project(
                args.target, args.name, DOMAIN_PLATFORM, args.description, args.owner, None,
                args.source, args.ref, args.distro, args.domain,
            )
            print("Created the domain platform '%s' in %s (Magrathea %s)" % (values["domain"], target, values["magrathea_version"]))
            print("Nothing in it is ready to apply: fill in every TODO (account, region, CIDRs, state backend) first.")
            return 0
        if args.command == "upgrade":
            old, new, changed, (code, out) = upgrade_project(args.target, args.ref)
            print("Moved the base from %s to %s; %d files changed" % (old, new, len(changed)))
            for path in changed:
                print("  %s" % path)
            if code:
                print("\nThe project's local additions no longer pass the new base:\n%s" % out, file=sys.stderr)
                return 1
            return 0
    except MagratheaError as err:
        print("error: %s" % err, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
