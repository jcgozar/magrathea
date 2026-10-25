import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import magrathea_cli as cli

REPO = Path(__file__).resolve().parent.parent
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t"]


def run_git(cwd, *args):
    subprocess.run([*GIT, *args], cwd=str(cwd), check=True, capture_output=True)


def make_source(dest):
    """A throwaway git repo holding a copy of Magrathea, tagged v1."""
    for name in ("base", "templates", "tools"):
        shutil.copytree(REPO / name, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    run_git(dest, "init", "-q", "-b", "main")
    run_git(dest, "add", "-A")
    run_git(dest, "commit", "-q", "-m", "v1")
    run_git(dest, "tag", "v1")


def commit_change(src):
    (src / "base" / "NEW.txt").write_text("x")
    run_git(src, "add", "-A")
    run_git(src, "commit", "-q", "-m", "v2")


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name)
        for p in (
            mock.patch.object(cli, "CONFIG", self.tmp / "cfg" / "cli.json"),
            mock.patch.object(cli, "CACHE", self.tmp / "cache"),
        ):
            p.start()
            self.addCleanup(p.stop)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["--no-input", *argv])
        return code, out.getvalue(), err.getvalue()


class MenuTest(unittest.TestCase):
    OPTIONS = [("a", "Alpha", "first"), ("b", "Beta", "second " * 30), ("c", "Gamma", "third")]

    def pick(self, keys):
        return cli.run_menu(self.OPTIONS, iter(keys), io.StringIO(), width=60)

    def test_enter_picks_first_by_default(self):
        self.assertEqual(self.pick([cli.KEY_ENTER]), "a")

    def test_down_and_up(self):
        self.assertEqual(self.pick([cli.KEY_DOWN, cli.KEY_DOWN, cli.KEY_ENTER]), "c")
        self.assertEqual(self.pick([cli.KEY_DOWN, cli.KEY_UP, cli.KEY_ENTER]), "a")

    def test_wraps_around(self):
        self.assertEqual(self.pick([cli.KEY_UP, cli.KEY_ENTER]), "c")
        self.assertEqual(self.pick([cli.KEY_DOWN] * 3 + [cli.KEY_ENTER]), "a")

    def test_vim_keys_digits_and_unknown_keys(self):
        self.assertEqual(self.pick(["j", "x", cli.KEY_ENTER]), "b")
        self.assertEqual(self.pick(["3", cli.KEY_ENTER]), "c")
        self.assertEqual(self.pick(["9", cli.KEY_ENTER]), "a")

    def test_cancel_and_exhausted_input(self):
        with self.assertRaises(KeyboardInterrupt):
            self.pick([cli.KEY_DOWN, cli.KEY_CANCEL])
        with self.assertRaises(EOFError):
            self.pick([cli.KEY_DOWN])

    def test_long_summaries_are_truncated_to_the_width(self):
        out = io.StringIO()
        cli.run_menu(self.OPTIONS, iter([cli.KEY_ENTER]), out, width=60)
        for line in out.getvalue().split("\n"):
            visible = line
            for code in ("\x1b[2K", "\x1b[36m", "\x1b[0m", "\x1b[2m", "\r"):
                visible = visible.replace(code, "")
            self.assertLessEqual(len(visible), 60)


class ReadKeyTest(unittest.TestCase):
    def key_for(self, data):
        r, w = os.pipe()
        self.addCleanup(os.close, r)
        os.write(w, data)
        os.close(w)
        return cli.read_key(r, timeout=0.05)

    def test_arrows_enter_and_ctrl_c(self):
        self.assertEqual(self.key_for(b"\x1b[A"), cli.KEY_UP)
        self.assertEqual(self.key_for(b"\x1bOB"), cli.KEY_DOWN)
        self.assertEqual(self.key_for(b"\r"), cli.KEY_ENTER)
        self.assertEqual(self.key_for(b"\x03"), cli.KEY_CANCEL)
        self.assertEqual(self.key_for(b"x"), "x")

    def test_lone_escape_cancels_and_unknown_sequences_are_ignored(self):
        self.assertEqual(self.key_for(b"\x1b"), cli.KEY_CANCEL)
        self.assertIsNone(self.key_for(b"\x1b[C"))

    def test_end_of_input_cancels_instead_of_looping(self):
        self.assertEqual(self.key_for(b""), cli.KEY_CANCEL)


class ConfigTest(CliTestCase):
    def test_missing_config_is_empty(self):
        self.assertEqual(cli.load_config(), {})

    def test_invalid_json_and_wrong_shape_are_errors(self):
        cli.CONFIG.parent.mkdir(parents=True)
        cli.CONFIG.write_text("{nope", encoding="utf-8")
        with self.assertRaisesRegex(cli.CliError, "not valid JSON"):
            cli.load_config()
        cli.CONFIG.write_text("[1]", encoding="utf-8")
        with self.assertRaisesRegex(cli.CliError, "malformed"):
            cli.load_config()

    def test_non_string_ref_is_malformed(self):
        cli.CONFIG.parent.mkdir(parents=True)
        cli.CONFIG.write_text('{"source": "x", "ref": 1}', encoding="utf-8")
        with self.assertRaisesRegex(cli.CliError, "malformed"):
            cli.load_config()

    def test_dash_prefixed_source_and_ref_are_refused(self):
        for source, ref in (("--upload-pack=x ://y", None), ("-x", None), ("file:///x", "--output=y")):
            with self.assertRaisesRegex(cli.CliError, "must not start with '-'"):
                cli.fetch_source(source, ref)

    def test_unexpected_errors_become_messages_not_tracebacks(self):
        with mock.patch.object(cli, "cmd_stacks", side_effect=TypeError("boom")), mock.patch.dict(cli.COMMANDS, {"stacks": cli.cmd_stacks}):
            code, _, err = self.run_cli("stacks")
        self.assertEqual(code, 1)
        self.assertIn("TypeError: boom", err)

    def test_init_with_folder_saves_config_and_lists_stacks(self):
        code, out, _ = self.run_cli("init", "--source", str(REPO))
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(cli.CONFIG.read_text())["source"], str(REPO))
        self.assertIn("react-java", out)

    def test_init_rejects_a_bad_source_and_saves_nothing(self):
        code, _, err = self.run_cli("init", "--source", str(self.tmp / "nope"))
        self.assertEqual(code, 1)
        self.assertIn("not found", err)
        self.assertFalse(cli.CONFIG.exists())

    def test_init_rejects_a_folder_that_is_not_magrathea(self):
        (self.tmp / "other").mkdir()
        code, _, err = self.run_cli("init", "--source", str(self.tmp / "other"))
        self.assertEqual(code, 1)
        self.assertIn("not a Magrathea source", err)
        self.assertFalse(cli.CONFIG.exists())


class NewTest(CliTestCase):
    def setUp(self):
        super().setUp()
        self.run_cli("init", "--source", str(REPO))

    def test_flags_only_creates_a_verified_project(self):
        target = self.tmp / "app"
        code, out, err = self.run_cli("new", str(target), "--name", "Flag App", "--stack", "react-java")
        self.assertEqual(code, 0, err)
        self.assertIn("Created", out)
        self.assertTrue((target / "magrathea.lock.json").is_file())
        self.assertEqual(json.loads((target / "magrathea.json").read_text())["source"], str(REPO))

    def test_missing_name_without_a_terminal_is_an_error(self):
        code, _, err = self.run_cli("new", str(self.tmp / "x"), "--stack", "react-java")
        self.assertEqual(code, 1)
        self.assertIn("--name", err)

    def test_missing_stack_with_several_stacks_is_an_error(self):
        code, _, err = self.run_cli("new", str(self.tmp / "x"), "--name", "X")
        self.assertEqual(code, 1)
        self.assertIn("--stack", err)

    def test_unknown_stack_lists_available_ones(self):
        code, _, err = self.run_cli("new", str(self.tmp / "x"), "--name", "X", "--stack", "cobol")
        self.assertEqual(code, 1)
        self.assertIn("react-java", err)
        self.assertFalse((self.tmp / "x").exists())

    def test_bad_name_and_non_empty_target_are_errors(self):
        code, _, err = self.run_cli("new", str(self.tmp / "x"), "--name", "!!!", "--stack", "react-java")
        self.assertEqual(code, 1)
        self.assertIn("letters or digits", err)
        (self.tmp / "full").mkdir()
        (self.tmp / "full" / "f").write_text("x")
        code, _, err = self.run_cli("new", str(self.tmp / "full"), "--name", "X", "--stack", "react-java")
        self.assertEqual(code, 1)
        self.assertIn("not empty", err)

    def test_default_target_is_the_slug_in_the_current_folder(self):
        old = os.getcwd()
        os.chdir(self.tmp)
        self.addCleanup(os.chdir, old)
        code, _, err = self.run_cli("new", "--name", "My Cool App", "--stack", "react-java")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.tmp / "my-cool-app" / "magrathea.json").is_file())


class DomainCliTest(CliTestCase):
    def setUp(self):
        super().setUp()
        self.run_cli("init", "--source", str(REPO))

    def test_new_domain_creates_a_domain_platform(self):
        target = self.tmp / "pay"
        code, out, err = self.run_cli("new-domain", str(target), "--name", "Payments")
        self.assertEqual(code, 0, err)
        self.assertIn("Nothing in it is ready to apply", out)
        config = json.loads((target / "magrathea.json").read_text())
        self.assertEqual((config["type"], config["domain"], config["auto_merge"]), ("domain-platform", "payments", "off"))
        self.assertNotIn("infra_mode", config)

    def test_new_domain_honors_an_explicit_domain_and_refuses_a_bad_one(self):
        code, _, err = self.run_cli("new-domain", str(self.tmp / "a"), "--name", "Payments", "--domain", "pay-eu")
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads((self.tmp / "a/magrathea.json").read_text())["domain"], "pay-eu")
        code, _, err = self.run_cli("new-domain", str(self.tmp / "b"), "--name", "Payments", "--domain", "Pay EU")
        self.assertEqual(code, 1)
        self.assertIn("domain", err)

    def test_new_with_domain_attaches_the_project(self):
        target = self.tmp / "app"
        code, out, err = self.run_cli("new", str(target), "--name", "App", "--stack", "java-service", "--domain", "payments")
        self.assertEqual(code, 0, err)
        config = json.loads((target / "magrathea.json").read_text())
        self.assertEqual((config["infra_mode"], config["domain"]), ("domain", "payments"))
        self.assertNotIn("type", config)
        self.assertIn("payments", out)

    def test_new_without_domain_writes_no_mode_fields(self):
        target = self.tmp / "app"
        self.assertEqual(self.run_cli("new", str(target), "--name", "App", "--stack", "java-service")[0], 0)
        self.assertEqual(sorted(json.loads((target / "magrathea.json").read_text())), ["auto_merge", "ref", "source"])


class GitSourceTest(CliTestCase):
    def setUp(self):
        super().setUp()
        self.src = self.tmp / "src"
        self.src.mkdir()
        make_source(self.src)
        self.url = "file://" + str(self.src)

    def test_clones_pins_a_tag_and_picks_up_new_commits(self):
        code, _, err = self.run_cli("init", "--source", self.url, "--ref", "v1")
        self.assertEqual(code, 0, err)
        self.assertTrue((cli.fetch_source(self.url, "v1") / "tools" / "magrathea.py").is_file())

        commit_change(self.src)
        self.assertFalse((cli.fetch_source(self.url, "v1") / "base" / "NEW.txt").exists())  # a tag stays put
        self.assertTrue((cli.fetch_source(self.url, "main") / "base" / "NEW.txt").exists())  # a branch moves
        self.assertTrue((cli.fetch_source(self.url) / "base" / "NEW.txt").exists())  # the default branch

    def test_unknown_ref_is_an_error(self):
        with self.assertRaisesRegex(cli.CliError, "not found"):
            cli.fetch_source(self.url, "v9")

    def test_unreachable_url_is_an_error_without_a_cache(self):
        with self.assertRaisesRegex(cli.CliError, "could not fetch"):
            cli.fetch_source("file://" + str(self.tmp / "missing"))

    def test_falls_back_to_the_cache_when_the_remote_disappears(self):
        cli.fetch_source(self.url)
        shutil.rmtree(self.src)
        err = io.StringIO()
        with redirect_stderr(err):
            clone = cli.fetch_source(self.url)
        self.assertTrue((clone / "tools" / "magrathea.py").is_file())
        self.assertIn("using the cached copy", err.getvalue())

    def test_new_from_a_git_source_records_it_in_the_project(self):
        self.run_cli("init", "--source", self.url, "--ref", "v1")
        target = self.tmp / "app"
        code, _, err = self.run_cli("new", str(target), "--name", "Git App", "--stack", "react-java")
        self.assertEqual(code, 0, err)
        config = json.loads((target / "magrathea.json").read_text())
        self.assertEqual((config["source"], config["ref"]), (self.url, "v1"))

    def test_follows_the_remotes_default_branch_when_it_changes(self):
        cli.fetch_source(self.url)
        run_git(self.src, "checkout", "-q", "-b", "trunk")
        (self.src / "base" / "TRUNK.txt").write_text("x")
        run_git(self.src, "add", "-A")
        run_git(self.src, "commit", "-q", "-m", "trunk")
        run_git(self.src, "branch", "-q", "-D", "main")  # HEAD now points at trunk
        self.assertTrue((cli.fetch_source(self.url) / "base" / "TRUNK.txt").exists())

    def test_upgrade_uses_the_projects_source_not_the_configured_one(self):
        self.run_cli("init", "--source", self.url)
        target = self.tmp / "app"
        self.assertEqual(self.run_cli("new", str(target), "--name", "Up App", "--stack", "react-java")[0], 0)
        commit_change(self.src)
        self.run_cli("init", "--source", str(REPO))  # the CLI now points somewhere else entirely
        code, out, err = self.run_cli("upgrade", str(target))
        self.assertEqual(code, 0, err)
        self.assertIn("NEW.txt", out)

    def test_upgrade_without_a_project_config_is_an_error(self):
        (self.tmp / "empty").mkdir()
        code, _, err = self.run_cli("upgrade", str(self.tmp / "empty"))
        self.assertEqual(code, 1)
        self.assertIn("magrathea.json", err)

    def test_upgrade_runs_through_the_cli(self):
        self.run_cli("init", "--source", self.url)
        target = self.tmp / "app"
        self.assertEqual(self.run_cli("new", str(target), "--name", "Up App", "--stack", "react-java")[0], 0)
        commit_change(self.src)
        code, out, err = self.run_cli("upgrade", str(target))
        self.assertEqual(code, 0, err)
        self.assertIn("NEW.txt", out)


def make_distro(dest, upstream=REPO, files=None):
    dest.mkdir(parents=True)
    (dest / "distro.json").write_text(json.dumps({"upstream": {"source": str(upstream), "ref": None}}))
    for rel, text in (files or {}).items():
        (dest / rel).parent.mkdir(parents=True, exist_ok=True)
        (dest / rel).write_text(text)
    return dest


class DistroTest(CliTestCase):
    def setUp(self):
        super().setUp()
        self.distro = make_distro(self.tmp / "acme", files={
            "templates/project/README.md": "# @@name@@ at Acme\n",
            "base/docs/WORKFLOW.md": "Acme workflow\n",
        })

    def test_init_saves_the_distribution_and_new_projects_follow_it(self):
        code, out, err = self.run_cli("init", "--source", str(REPO), "--distro", str(self.distro))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(cli.CONFIG.read_text())["distro"], str(self.distro.resolve()))
        target = self.tmp / "app"
        code, out, err = self.run_cli("new", str(target), "--name", "Acme App", "--stack", "java-service")
        self.assertEqual(code, 0, err)
        self.assertEqual((target / "README.md").read_text(), "# Acme App at Acme\n")
        self.assertEqual((target / ".magrathea/docs/WORKFLOW.md").read_text(), "Acme workflow\n")
        self.assertEqual(json.loads((target / "magrathea.json").read_text())["source"], str(self.distro.resolve()))

    def test_flags_work_without_saved_config(self):
        self.run_cli("init", "--source", str(REPO))
        target = self.tmp / "app"
        code, _, err = self.run_cli("new", str(target), "--name", "A", "--stack", "java-service", "--distro", str(self.distro))
        self.assertEqual(code, 0, err)
        self.assertTrue((target / ".magrathea/docs/WORKFLOW.md").read_text().startswith("Acme"))

    def test_stacks_lists_the_distributions_stacks(self):
        make_distro(self.tmp / "go", files={
            "templates/stacks/go-api/stack.json": json.dumps({"name": "go-api", "title": "Go", "summary": "A Go API"}),
        })
        self.run_cli("init", "--source", str(REPO))
        code, out, _ = self.run_cli("stacks", "--distro", str(self.tmp / "go"))
        self.assertEqual(code, 0)
        self.assertIn("go-api", out)
        self.assertIn("java-service", out)

    def test_bad_folders_and_orphan_flags_are_errors(self):
        self.run_cli("init", "--source", str(REPO))
        code, _, err = self.run_cli("stacks", "--distro", str(self.tmp / "nope"))
        self.assertEqual((code, "not found" in err), (1, True))
        (self.tmp / "plain").mkdir()
        code, _, err = self.run_cli("stacks", "--distro", str(self.tmp / "plain"))
        self.assertEqual((code, "distro.json" in err), (1, True))
        code, _, err = self.run_cli("init", "--source", str(REPO), "--distro-ref", "v1")
        self.assertEqual((code, "--distro" in err), (1, True))

    def test_an_empty_distro_flag_clears_the_saved_one(self):
        self.run_cli("init", "--source", str(REPO), "--distro", str(self.distro))
        self.run_cli("init", "--source", str(REPO), "--distro", "")
        self.assertNotIn("distro", json.loads(cli.CONFIG.read_text()))

    def test_upgrade_works_for_a_project_that_follows_a_distribution(self):
        self.run_cli("init", "--source", str(REPO), "--distro", str(self.distro))
        target = self.tmp / "app"
        self.assertEqual(self.run_cli("new", str(target), "--name", "A", "--stack", "java-service")[0], 0)
        (self.distro / "base/docs/WORKFLOW.md").write_text("Acme workflow v2\n")
        code, out, err = self.run_cli("upgrade", str(target))
        self.assertEqual(code, 0, err)
        self.assertIn("docs/WORKFLOW.md", out)
        self.assertEqual((target / ".magrathea/docs/WORKFLOW.md").read_text(), "Acme workflow v2\n")


if __name__ == "__main__":
    unittest.main()
