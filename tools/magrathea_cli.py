#!/usr/bin/env python3
"""Magrathea CLI: an interactive front end to the generator.

    magrathea_cli.py init     [--source GIT_URL_OR_PATH] [--ref REF] [--distro FOLDER]
                              [--distro-source GIT_URL_OR_PATH] [--distro-ref REF]
    magrathea_cli.py new      [TARGET] [--name N] [--stack S] [--description D] [--owner O] [--yes]
                              [--domain D] [--distro FOLDER] [--distro-source ...] [--distro-ref ...]
    magrathea_cli.py new-domain [TARGET] [--name N] [--domain D] [--description D] [--owner O] [--yes]
    magrathea_cli.py stacks   [--distro FOLDER]
    magrathea_cli.py upgrade  TARGET [--ref REF]

`new --domain D` attaches the project to the domain platform D (infra_mode "domain"); `new-domain`
scaffolds a domain platform repository on its own (ADR 0009).

`init` saves where Magrathea lives (a git URL or a folder), and optionally your distribution: a
local folder of your own templates, stacks and base additions (ADR 0007). With a distribution,
new projects follow it (--distro-source says where projects fetch it from; default: the folder's
git origin, or the folder) and it names its own upstream. The other commands fetch it (git URLs
are cloned into a cache and refreshed on each run), then call the generator in tools/magrathea.py
from that copy, so this file adds prompts and fetching but no rendering logic. This file is
standalone: copy it anywhere, run `init`, and it works without a Magrathea checkout.

Anything not given as a flag is asked for. Without a terminal, or with --no-input, nothing is
asked and a missing value is an error. The CLI stores no model or GitHub tokens; private git
sources use the user's own git credentials.

Environment: MAGRATHEA_CLI_CONFIG (config file), MAGRATHEA_CLI_CACHE (clone cache).
Standard library only.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import select
import shutil
import subprocess
import sys
from pathlib import Path

CONFIG = Path(os.environ.get("MAGRATHEA_CLI_CONFIG") or Path.home() / ".config" / "magrathea" / "cli.json")
CACHE = Path(os.environ.get("MAGRATHEA_CLI_CACHE") or Path.home() / ".cache" / "magrathea" / "source")
DEFAULT_OWNER = "@your-github-handle"
KEY_UP, KEY_DOWN, KEY_ENTER, KEY_CANCEL = "up", "down", "enter", "cancel"


class CliError(Exception):
    pass


# ---- config and source -------------------------------------------------------------------

def own_checkout():
    """The Magrathea checkout this file sits in (tools/ inside it), if any."""
    root = Path(__file__).resolve().parent.parent
    return root if (root / "templates").is_dir() and (root / "base").is_dir() else None


def default_source():
    root = own_checkout()
    if not root:
        return None
    remote = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"], capture_output=True, text=True)
    return remote.stdout.strip() if remote.returncode == 0 and remote.stdout.strip() else str(root)


def load_config():
    try:
        text = CONFIG.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as err:
        raise CliError("cannot read %s: %s" % (CONFIG, err))
    try:
        config = json.loads(text)
    except ValueError:
        raise CliError("%s is not valid JSON; fix it or run `init` again" % CONFIG)
    keys = ("source", "ref", "distro", "distro_source", "distro_ref")
    if not isinstance(config, dict) or not all(isinstance(config.get(k) or "", str) for k in keys):
        raise CliError("%s is malformed; run `init` again" % CONFIG)
    return config


def save_config(source, ref, distro=None, distro_source=None, distro_ref=None):
    data = {"source": source}
    if ref:
        data["ref"] = ref
    for key, value in (("distro", distro), ("distro_source", distro_source), ("distro_ref", distro_ref)):
        if value:
            data[key] = value
    try:
        CONFIG.parent.mkdir(parents=True, exist_ok=True)
        CONFIG.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    except OSError as err:
        raise CliError("cannot write %s: %s" % (CONFIG, err))


def check_not_option(value, what):
    """A source or ref starting with '-' would be read by git as an option."""
    if value and value.startswith("-"):
        raise CliError("%s must not start with '-': %s" % (what, value))


def is_local(source):
    return "://" not in source and not source.startswith("git@")


def git(*args, cwd=None, interactive_auth=False):
    env = dict(os.environ)
    if not interactive_auth:
        env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=env)
    except FileNotFoundError:
        raise CliError("git is not installed or not on PATH")
    if result.returncode:
        raise CliError("git %s failed: %s" % (" ".join(args[:2]), (result.stderr or result.stdout).strip()))
    return result.stdout.strip()


def fetch_source(source, ref=None, allow_prompt=False):
    """Return a folder holding Magrathea. Folders are used as they are; git URLs are cloned/refreshed."""
    check_not_option(source, "source")
    check_not_option(ref, "ref")
    if is_local(source):
        path = Path(source).expanduser()
        if not path.is_dir():
            raise CliError("Magrathea source folder not found: %s" % source)
        return path.resolve()
    clone = CACHE / hashlib.sha256(source.encode()).hexdigest()[:16]
    try:
        if (clone / ".git").is_dir():
            git("fetch", "--quiet", "--tags", "--force", "--prune", "origin", cwd=str(clone), interactive_auth=allow_prompt)
        else:
            clone.parent.mkdir(parents=True, exist_ok=True)
            if clone.exists():
                shutil.rmtree(clone)
            git("clone", "--quiet", "--", source, str(clone), interactive_auth=allow_prompt)
    except CliError as err:
        if not (clone / ".git").is_dir():
            raise CliError("could not fetch Magrathea from %s: %s" % (source, err))
        print("warning: could not refresh %s (%s); using the cached copy" % (source, err), file=sys.stderr)
    if not ref:
        try:  # follow the remote's current default branch, not the one it had at clone time
            git("remote", "set-head", "origin", "--auto", cwd=str(clone), interactive_auth=allow_prompt)
        except CliError:
            pass  # offline or no HEAD: origin/HEAD from the clone is still usable
    candidates = ["origin/" + ref, "refs/tags/" + ref, ref] if ref else ["origin/HEAD"]
    for candidate in candidates:
        try:
            rev = git("rev-parse", "--verify", "--quiet", "--end-of-options", candidate + "^{commit}", cwd=str(clone))
        except CliError:
            continue
        git("checkout", "--quiet", "--detach", rev, cwd=str(clone))
        return clone
    raise CliError("ref '%s' not found in %s" % (ref, source) if ref else "%s has no default branch to follow" % source)


def load_generator(root):
    path = root / "tools" / "magrathea.py"
    if not path.is_file():
        raise CliError("%s is not a Magrathea source (no tools/magrathea.py)" % root)
    spec = importlib.util.spec_from_file_location("magrathea_generator", path)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as err:  # a broken source should read as a CLI error, not a traceback
        raise CliError("could not load the generator from %s: %s" % (path, err))
    return module


def open_source(args, allow_prompt=False):
    config = load_config()
    source = getattr(args, "source", None) or config.get("source") or default_source()
    ref = getattr(args, "ref", None) if getattr(args, "ref", None) is not None else config.get("ref")
    if not source:
        raise CliError("no Magrathea source configured; run `init --source <git URL or folder>`")
    return load_generator(fetch_source(source, ref or None, allow_prompt)), source, ref or None


def require_distro_support(generator, distro):
    if distro and "distro" not in generator.new_project.__code__.co_varnames:
        raise CliError("this Magrathea source is older than engine 0.6.0 and cannot use a distribution; update it")


def distro_settings(args, config):
    """(folder or None, source or None, ref or None) for the distribution, flags over saved config."""
    def pick(flag, key):
        value = getattr(args, flag, None)
        return value if value is not None else config.get(key) or None

    folder = pick("distro", "distro")
    source, ref = pick("distro_source", "distro_source"), pick("distro_ref", "distro_ref")
    check_not_option(source, "distro source")
    check_not_option(ref, "distro ref")
    if folder:
        folder = str(Path(folder).expanduser())
        if not Path(folder).is_dir():
            raise CliError("distribution folder not found: %s" % folder)
        folder = str(Path(folder).resolve())
    elif source or ref:
        raise CliError("--distro-source and --distro-ref need a --distro folder")
    return folder, source, ref


# ---- prompts -----------------------------------------------------------------------------

class Terminal:
    def __init__(self, enabled):
        self.enabled = enabled and sys.stdin.isatty() and sys.stdout.isatty()

    def need(self, value, flag):
        if value is not None:
            return value
        raise CliError("missing %s (no terminal to ask on)" % flag)

    def ask(self, label, default="", required=False, check=None):
        suffix = " [%s]" % default if default else ""
        while True:
            value = input("? %s%s: " % (label, suffix)).strip() or default
            if required and not value:
                print("  a value is required")
                continue
            if check and value:
                problem = check(value)
                if problem:
                    print("  " + problem)
                    continue
            return value

    def confirm(self, label):
        return input("? %s [Y/n]: " % label).strip().lower() in ("", "y", "yes")


def read_key(fd, timeout=0.05):
    """One key press from a raw/cbreak terminal as KEY_*, a character, or None for ignored input."""
    data = os.read(fd, 1)
    if not data:
        return KEY_CANCEL  # end of input or hangup
    ch = data.decode(errors="ignore")
    if ch in ("\r", "\n"):
        return KEY_ENTER
    if ch == "\x03":
        return KEY_CANCEL
    if ch == "\x1b":
        if not select.select([fd], [], [], timeout)[0]:
            return KEY_CANCEL  # a lone Esc
        rest = os.read(fd, 8).decode(errors="ignore")
        if not rest:
            return KEY_CANCEL
        return {"[A": KEY_UP, "OA": KEY_UP, "[B": KEY_DOWN, "OB": KEY_DOWN}.get(rest)
    return ch


def run_menu(options, keys, out, width=80):
    """Drive a menu: options is [(key, title, summary)]; keys yields KEY_* values. Returns the chosen key."""
    index = 0
    title_width = max(len(title) for _, title, _ in options)
    room = max(10, width - title_width - 6)
    drawn = False

    def draw():
        nonlocal drawn
        if drawn:
            out.write("\x1b[%dA" % len(options))
        for i, (_, title, summary) in enumerate(options):
            marker = "\x1b[36m>\x1b[0m" if i == index else " "
            text = summary if len(summary) <= room else summary[: room - 1] + "…"
            out.write("\r\x1b[2K%s %-*s  \x1b[2m%s\x1b[0m\n" % (marker, title_width, title, text))
        out.flush()
        drawn = True

    draw()
    for key in keys:
        key = {"k": KEY_UP, "j": KEY_DOWN}.get(key, key)
        if key == KEY_ENTER:
            return options[index][0]
        if key == KEY_CANCEL:
            raise KeyboardInterrupt
        if key == KEY_UP:
            index = (index - 1) % len(options)
        elif key == KEY_DOWN:
            index = (index + 1) % len(options)
        elif isinstance(key, str) and key.isdigit() and 1 <= int(key) <= len(options):
            index = int(key) - 1
        draw()
    raise EOFError


def choose(label, options):
    """Arrow-key menu on a real terminal; numbered prompt where raw terminal mode is unavailable."""
    try:
        import termios
        import tty
    except ImportError:  # Windows
        for number, (_, title, summary) in enumerate(options, 1):
            print("  %d) %s  %s" % (number, title, summary))
        while True:
            answer = input("? %s [1-%d]: " % (label, len(options))).strip()
            if answer.isdigit() and 1 <= int(answer) <= len(options):
                return options[int(answer) - 1][0]
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    print("? %s  (up/down, enter, esc to cancel)" % label)
    sys.stdout.write("\x1b[?25l")
    try:
        tty.setcbreak(fd)

        def keys():
            while True:
                key = read_key(fd)
                if key is not None:
                    yield key

        return run_menu(options, keys(), sys.stdout, shutil.get_terminal_size().columns)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        sys.stdout.write("\x1b[?25h")
        sys.stdout.flush()


# ---- commands ----------------------------------------------------------------------------

def cmd_init(args, term):
    config = load_config()
    source = args.source or (term.ask("Magrathea source (git URL or folder)", config.get("source") or default_source() or "", required=True)
                             if term.enabled else config.get("source") or default_source())
    if not source:
        raise CliError("missing --source (no terminal to ask on)")
    ref = args.ref if args.ref is not None else (term.ask("Ref (tag or branch, blank for the default branch)", config.get("ref", ""))
                                                 if term.enabled else config.get("ref", ""))
    generator = load_generator(fetch_source(source, ref or None, allow_prompt=term.enabled))  # fail now if unreachable
    distro, distro_source, distro_ref = distro_settings(args, {} if any(
        getattr(args, k) is not None for k in ("distro", "distro_source", "distro_ref")) else config)
    require_distro_support(generator, distro)
    try:
        stacks = generator.list_stacks(distro)
    except generator.MagratheaError as err:
        raise CliError(str(err))
    save_config(source, ref, distro, distro_source, distro_ref)
    print("Saved %s" % CONFIG)
    if distro:
        print("Distribution: %s" % distro)
    print("Magrathea %s, %d stack(s): %s" % (generator.version(), len(stacks), ", ".join(stacks) or "none"))


def cmd_stacks(args, term):
    generator, _, _ = open_source(args)
    distro, _, _ = distro_settings(args, load_config())
    require_distro_support(generator, distro)
    try:
        found = generator.list_stacks(distro)
    except generator.MagratheaError as err:
        raise CliError(str(err))
    for key, meta in found.items():
        print("%-14s %s" % (key, meta["summary"]))


def cmd_new(args, term):
    generator, source, ref = open_source(args, allow_prompt=term.enabled)
    distro, distro_source, distro_ref = distro_settings(args, load_config())
    if distro:  # projects follow the distribution; it names its own upstream
        source, ref = distro_source, distro_ref
    require_distro_support(generator, distro)
    try:
        stacks = generator.list_stacks(distro)
    except generator.MagratheaError as err:
        raise CliError(str(err))
    if not stacks:
        raise CliError("this Magrathea source has no stacks")

    def valid_name(value):
        try:
            generator.slugify(value)
        except generator.MagratheaError as err:
            return str(err)

    name = args.name if args.name is not None else (
        term.ask("Project name", required=True, check=valid_name) if term.enabled else term.need(None, "--name"))
    if valid_name(name):
        raise CliError(valid_name(name))

    stack = args.stack
    if stack is None:
        if len(stacks) == 1:
            stack = next(iter(stacks))
            if term.enabled:
                print("Stack: %s (the only one available)" % stacks[stack]["title"])
        elif term.enabled:
            stack = choose("Stack", [(k, m["title"], m["summary"]) for k, m in stacks.items()])
        else:
            term.need(None, "--stack")
    if stack not in stacks:
        raise CliError("unknown stack '%s'. Available: %s" % (stack, ", ".join(stacks)))

    description = args.description if args.description is not None else (
        term.ask("Description (one sentence)") if term.enabled else "")
    domain = getattr(args, "domain", None)
    is_domain_platform = stacks[stack].get("type") == "domain-platform"
    if domain is None and term.enabled and not is_domain_platform and hasattr(generator, "DOMAIN_PLATFORM"):
        domain = term.ask("Domain platform to attach to (blank: this project owns its infrastructure)") or None
    if domain and not hasattr(generator, "DOMAIN_PLATFORM"):
        raise CliError("this Magrathea source is older than engine 0.7.0 and does not know domain platforms; update it")
    owner = args.owner or (term.ask("Owner (GitHub handle)", DEFAULT_OWNER) if term.enabled else DEFAULT_OWNER)
    default_target = str(Path.cwd() / generator.slugify(name))
    target = args.target or (term.ask("Target folder", default_target) if term.enabled else default_target)
    target = Path(target).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise CliError("%s exists and is not empty" % target)

    if term.enabled and not args.yes:
        print("\n  name    %s\n  stack   %s\n  owner   %s\n  folder  %s\n  source  %s%s\n" % (
            name, stacks[stack]["title"], owner, target, source or distro or "this Magrathea", " @ " + ref if ref else ""))
        if not term.confirm("Create it?"):
            raise KeyboardInterrupt
    try:
        if domain:
            path, values = generator.new_project(target, name, stack, description, owner, None, source, ref, distro, domain)
        else:
            path, values = generator.new_project(target, name, stack, description, owner, None, source, ref, distro)
    except generator.MagratheaError as err:
        raise CliError(str(err))
    print("Created %s  (%s, Magrathea %s)" % (path, values["stack_title"], values["magrathea_version"]))
    if domain and not is_domain_platform:
        print("It attaches to the domain platform '%s' (infra_mode \"domain\"). It may not create shared infrastructure; "
              "ask the platform operator for capacity (requests/DOMAIN-REQUEST-TEMPLATE.md)." % domain)
    print("Next: open it in Claude Code and run /new-project to draft CONTEXT.md, or edit CONTEXT.md by hand.")


def cmd_new_domain(args, term):
    """Create a domain platform repository without a project (ADR 0009). Says what it creates; creates one repo."""
    generator, source, ref = open_source(args, allow_prompt=term.enabled)
    distro, distro_source, distro_ref = distro_settings(args, load_config())
    if distro:
        source, ref = distro_source, distro_ref
    require_distro_support(generator, distro)
    if not hasattr(generator, "DOMAIN_PLATFORM"):
        raise CliError("this Magrathea source is older than engine 0.7.0 and cannot create a domain platform; update it")
    try:
        stacks = generator.list_stacks(distro)
    except generator.MagratheaError as err:
        raise CliError(str(err))
    if generator.DOMAIN_PLATFORM not in stacks:
        raise CliError("this Magrathea source has no 'domain-platform' stack")
    name = args.name if args.name is not None else (
        term.ask("Domain platform name", required=True) if term.enabled else term.need(None, "--name"))
    domain = args.domain or generator.slugify(name)
    description = args.description if args.description is not None else ""
    owner = args.owner or (term.ask("Owner (GitHub handle)", DEFAULT_OWNER) if term.enabled else DEFAULT_OWNER)
    default_target = str(Path.cwd() / (generator.slugify(name) + "-platform"))
    target = args.target or (term.ask("Target folder", default_target) if term.enabled else default_target)
    target = Path(target).expanduser().resolve()
    if target.exists() and any(target.iterdir()):
        raise CliError("%s exists and is not empty" % target)
    if term.enabled and not args.yes:
        print("\n  This creates a new git-ready folder for the shared infrastructure of the domain '%s':\n"
              "  folder  %s\n  owner   %s\n  It is a separate repository from any project, and nothing in it is ready to apply.\n"
              % (domain, target, owner))
        if not term.confirm("Create it?"):
            raise KeyboardInterrupt
    try:
        path, values = generator.new_project(target, name, generator.DOMAIN_PLATFORM, description, owner, None,
                                             source, ref, distro, domain)
    except generator.MagratheaError as err:
        raise CliError(str(err))
    print("Created the domain platform '%s' in %s  (Magrathea %s)" % (domain, path, values["magrathea_version"]))
    print("Nothing in it is ready to apply. Next: fill in every TODO (account, region, CIDRs, state backend), then read docs/runbooks/apply.md.")


def cmd_upgrade(args, term):
    try:  # load the generator from the project's own source, as `make upgrade` would
        project = json.loads((Path(args.target) / "magrathea.json").read_text(encoding="utf-8"))
        source, ref = project["source"], project.get("ref")
        if not isinstance(source, str) or not isinstance(ref or "", str):
            raise ValueError
    except (OSError, ValueError, KeyError):
        raise CliError("%s has no readable magrathea.json with a source" % args.target)
    followed = fetch_source(source, args.ref or ref or None, allow_prompt=term.enabled)
    if (followed / "tools" / "magrathea.py").is_file():
        generator = load_generator(followed)
    else:  # the project follows a distribution, which holds no tools: use the configured Magrathea
        generator = open_source(argparse.Namespace(), allow_prompt=term.enabled)[0]
    try:
        old, new, changed, (code, out) = generator.upgrade_project(args.target, args.ref)
    except generator.MagratheaError as err:
        raise CliError(str(err))
    print("Moved the base from %s to %s; %d files changed" % (old, new, len(changed)))
    for path in changed:
        print("  %s" % path)
    if code:
        raise CliError("the project's local additions no longer pass the new base:\n%s" % out)


def add_distro_flags(p):
    p.add_argument("--distro", help="a distribution folder layered over Magrathea's defaults (ADR 0007)")
    p.add_argument("--distro-source", help="git URL or path projects fetch the distribution from")
    p.add_argument("--distro-ref", help="tag or branch of the distribution projects follow")


def build_parser():
    parser = argparse.ArgumentParser(prog="magrathea", description=__doc__.splitlines()[0])
    parser.add_argument("--no-input", action="store_true", help="never prompt; missing values are errors")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="save where Magrathea lives")
    p.add_argument("--source", help="git URL or folder")
    p.add_argument("--ref", help="tag or branch to follow")
    add_distro_flags(p)
    p = sub.add_parser("stacks", help="list available stacks")
    p.add_argument("--distro", help="a distribution folder layered over Magrathea's defaults")
    p = sub.add_parser("new", help="scaffold a new project")
    p.add_argument("target", nargs="?", help="folder to create (default: ./<project-slug>)")
    p.add_argument("--name")
    p.add_argument("--stack")
    p.add_argument("--description")
    p.add_argument("--owner")
    p.add_argument("--source", help="override the configured source for this project")
    p.add_argument("--ref", help="override the configured ref for this project")
    p.add_argument("--domain", help="attach the project to this domain platform (infra_mode \"domain\")")
    add_distro_flags(p)
    p.add_argument("--yes", "-y", action="store_true", help="skip the confirmation")
    p = sub.add_parser("new-domain", help="scaffold a domain platform (shared infrastructure) repository")
    p.add_argument("target", nargs="?", help="folder to create (default: ./<name>-platform)")
    p.add_argument("--name")
    p.add_argument("--domain", help="domain name used in SSM paths (default: the slug of --name)")
    p.add_argument("--description")
    p.add_argument("--owner")
    p.add_argument("--source", help="override the configured source")
    p.add_argument("--ref", help="override the configured ref")
    add_distro_flags(p)
    p.add_argument("--yes", "-y", action="store_true", help="skip the confirmation")
    p = sub.add_parser("upgrade", help="move a project to the newest base (or to --ref)")
    p.add_argument("target")
    p.add_argument("--ref")
    return parser


COMMANDS = {"init": cmd_init, "stacks": cmd_stacks, "new": cmd_new, "new-domain": cmd_new_domain, "upgrade": cmd_upgrade}


def main(argv=None):
    args = build_parser().parse_args(argv)
    term = Terminal(enabled=not args.no_input)
    try:
        COMMANDS[args.command](args, term)
    except CliError as err:
        print("error: %s" % err, file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\ncancelled", file=sys.stderr)
        return 130
    except Exception as err:  # keep tracebacks for bugs out of users' faces; the message still names the problem
        print("error: %s: %s" % (type(err).__name__, err), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
