"""A project that follows a distribution gets the upstream base with the distribution's base laid over it."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import magrathea

UPSTREAM = magrathea.ROOT


def write(root, files):
    for rel, text in files.items():
        path = Path(root) / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def make_distro(root, files=None, remove=None, upstream=None):
    cfg = {"upstream": {"source": str(upstream or UPSTREAM), "ref": None}}
    if remove:
        cfg["remove"] = remove
    write(root, {"distro.json": json.dumps(cfg), **(files or {})})
    return Path(root)


def sh(*cmd, cwd):
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


class DistroBaseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.out = self.tmp / "proj"

    def tearDown(self):
        self._tmp.cleanup()

    def new(self, distro, **kw):
        return magrathea.new_project(self.out, "Acme Svc", "java-service", "", "@me", None, distro=distro, **kw)[0]

    def cache(self, rel):
        return (self.out / ".magrathea" / rel)

    def test_a_distro_file_replaces_the_upstream_file_and_the_rest_is_kept(self):
        distro = make_distro(self.tmp / "d", {"base/docs/WORKFLOW.md": "Acme workflow\n"})
        self.new(distro)
        self.assertEqual(self.cache("docs/WORKFLOW.md").read_text(), "Acme workflow\n")
        self.assertTrue(self.cache("standards").is_dir())
        self.assertTrue(self.cache("agents/personas/developer.md").is_file())

    def test_a_distro_can_add_a_standard_and_it_is_in_the_project(self):
        distro = make_distro(self.tmp / "d", {"base/standards/acme-db.md": "| ACMEDB-001 | Use the Acme cluster | planned |\n"})
        self.new(distro)
        self.assertTrue(self.cache("standards/acme-db.md").is_file())
        verify = sh(sys.executable, ".magrathea/scripts/magrathea_lock.py", "verify", cwd=self.out)
        self.assertEqual(verify.returncode, 0, verify.stderr)

    def test_a_rule_id_in_two_files_is_an_error(self):
        import re
        rule_id = next(m for md in sorted((UPSTREAM / "base/standards").glob("*.md"))
                       for m in re.findall(r"^\|\s*([A-Z][A-Z0-9]*-\d+)\s*\|", md.read_text(), re.M))
        distro = make_distro(self.tmp / "d", {"base/standards/clash.md": "| %s | redefined | planned |\n" % rule_id})
        with self.assertRaises(magrathea.MagratheaError) as ctx:
            self.new(distro)
        self.assertIn(rule_id, str(ctx.exception))

    def test_replacing_the_whole_file_changes_a_rule_without_a_clash(self):
        existing = next(iter(sorted((UPSTREAM / "base/standards").glob("*.md"))))
        distro = make_distro(self.tmp / "d", {"base/standards/" + existing.name: existing.read_text() + "\nAcme addendum\n"})
        self.new(distro)
        self.assertIn("Acme addendum", self.cache("standards/" + existing.name).read_text())

    def test_remove_drops_an_upstream_file(self):
        victim = next(iter(sorted((UPSTREAM / "base/standards").glob("*.md")))).name
        distro = make_distro(self.tmp / "d", remove=["standards/" + victim])
        self.new(distro)
        self.assertFalse(self.cache("standards/" + victim).exists())

    def test_remove_that_matches_nothing_is_an_error(self):
        distro = make_distro(self.tmp / "d", remove=["standards/nope.md"])
        with self.assertRaises(magrathea.MagratheaError) as ctx:
            self.new(distro)
        self.assertIn("nope.md", str(ctx.exception))

    def test_remove_cannot_escape_base(self):
        distro = make_distro(self.tmp / "d", remove=["../README.md"])
        with self.assertRaises(magrathea.MagratheaError):
            self.new(distro)

    def test_a_removed_file_can_be_replaced_by_the_distro(self):
        victim = next(iter(sorted((UPSTREAM / "base/standards").glob("*.md")))).name
        distro = make_distro(self.tmp / "d", {"base/standards/" + victim: "| MINE-001 | mine | planned |\n"},
                             remove=["standards/" + victim])
        self.new(distro)
        self.assertIn("MINE-001", self.cache("standards/" + victim).read_text())

    def test_the_distro_version_wins_when_it_ships_one(self):
        distro = make_distro(self.tmp / "d", {"base/VERSION": "acme-3.1.4\n"})
        self.new(distro)
        self.assertEqual(json.loads((self.out / "magrathea.lock.json").read_text())["version"], "acme-3.1.4")

    def test_the_lock_records_the_distribution_and_its_upstream(self):
        distro = make_distro(self.tmp / "d")
        self.new(distro)
        lock = json.loads((self.out / "magrathea.lock.json").read_text())
        config = json.loads((self.out / "magrathea.json").read_text())
        self.assertEqual(config["source"], str(distro.resolve()))
        self.assertEqual(lock["source"], str(distro.resolve()))
        self.assertEqual(lock["upstream"]["source"], str(UPSTREAM))

    def test_local_standards_still_cannot_redefine_a_distro_rule(self):
        distro = make_distro(self.tmp / "d", {"base/standards/acme-db.md": "| ACMEDB-001 | rule | planned |\n"})
        self.new(distro)
        write(self.out, {"local/standards/mine.md": "| ACMEDB-001 | weaker | planned |\n"})
        verify = sh(sys.executable, ".magrathea/scripts/magrathea_lock.py", "verify", cwd=self.out)
        self.assertNotEqual(verify.returncode, 0)
        self.assertIn("ACMEDB-001", verify.stderr)

    def test_an_edit_to_the_merged_cache_is_caught_and_setup_restores_it(self):
        distro = make_distro(self.tmp / "d", {"base/docs/WORKFLOW.md": "Acme workflow\n"})
        self.new(distro)
        self.cache("docs/WORKFLOW.md").write_text("tampered\n")
        self.assertNotEqual(sh(sys.executable, ".magrathea/scripts/magrathea_lock.py", "verify", cwd=self.out).returncode, 0)
        self.assertEqual(sh(sys.executable, "scripts/magrathea_sync.py", cwd=self.out).returncode, 0)
        self.assertEqual(self.cache("docs/WORKFLOW.md").read_text(), "Acme workflow\n")

    def test_a_chained_upstream_is_rejected(self):
        middle = make_distro(self.tmp / "mid")
        distro = make_distro(self.tmp / "d", upstream=middle)
        with self.assertRaises(magrathea.MagratheaError) as ctx:
            self.new(distro)
        self.assertIn("chaining", str(ctx.exception))

    def test_a_distro_without_base_still_follows_the_upstream_base(self):
        distro = make_distro(self.tmp / "d", {"templates/project/README.md": "x\n"})
        self.new(distro)
        self.assertEqual(
            self.cache("standards").exists(), True)


class DistroGitTest(unittest.TestCase):
    """The distribution and the upstream as git repos: pinning and upgrading."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.up = self.tmp / "up"
        shutil.copytree(UPSTREAM / "base", self.up / "base", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        write(self.up, {"base/VERSION": "1.0.0\n", "base/docs/WORKFLOW.md": "upstream v1\n"})
        self.git_init(self.up, "u1")
        sh("git", "tag", "v1", cwd=self.up)
        self.dist = self.tmp / "dist"
        write(self.dist, {"base/standards/acme.md": "| ACME-001 | acme | planned |\n"})
        make_distro(self.dist, upstream="file://" + str(self.up))
        cfg = json.loads((self.dist / "distro.json").read_text())
        cfg["upstream"]["ref"] = "v1"
        (self.dist / "distro.json").write_text(json.dumps(cfg))
        self.git_init(self.dist, "d1")
        self.out = self.tmp / "proj"
        magrathea.new_project(self.out, "Acme Svc", "java-service", "", "@me", None, distro=self.dist,
                              source="file://" + str(self.dist))

    def tearDown(self):
        self._tmp.cleanup()

    def git_init(self, folder, message):
        sh("git", "init", "-q", "-b", "main", cwd=folder)
        sh("git", "config", "user.email", "t@example.com", cwd=folder)
        sh("git", "config", "user.name", "t", cwd=folder)
        self.commit(folder, message)

    def commit(self, folder, message):
        sh("git", "add", "-A", cwd=folder)
        sh("git", "commit", "-q", "-m", message, cwd=folder)

    def lock(self):
        return json.loads((self.out / "magrathea.lock.json").read_text())

    def test_both_commits_are_pinned(self):
        lock = self.lock()
        self.assertEqual(len(lock["commit"]), 40)
        self.assertEqual(len(lock["upstream"]["commit"]), 40)
        self.assertEqual(lock["upstream"]["ref"], "v1")

    def test_an_upstream_change_does_not_reach_a_project_until_the_distro_bumps_its_ref(self):
        write(self.up, {"base/docs/WORKFLOW.md": "upstream v2\n", "base/VERSION": "2.0.0\n"})
        self.commit(self.up, "u2")
        sh("git", "tag", "v2", cwd=self.up)
        # a fresh clone is reproduced exactly
        sh("rm", "-rf", str(self.out / ".magrathea"), cwd=self.tmp)
        self.assertEqual(sh(sys.executable, "scripts/magrathea_sync.py", cwd=self.out).returncode, 0)
        self.assertEqual((self.out / ".magrathea/docs/WORKFLOW.md").read_text(), "upstream v1\n")
        # an upgrade follows the distribution, which still says v1
        magrathea.upgrade_project(self.out)
        self.assertEqual((self.out / ".magrathea/docs/WORKFLOW.md").read_text(), "upstream v1\n")
        # the distribution bumps the upstream ref: that is the explicit upgrade
        cfg = json.loads((self.dist / "distro.json").read_text())
        cfg["upstream"]["ref"] = "v2"
        (self.dist / "distro.json").write_text(json.dumps(cfg))
        self.commit(self.dist, "bump upstream")
        old, new, changed, _ = magrathea.upgrade_project(self.out)
        self.assertEqual((self.out / ".magrathea/docs/WORKFLOW.md").read_text(), "upstream v2\n")
        self.assertEqual((old, new), ("1.0.0", "2.0.0"))
        self.assertIn("docs/WORKFLOW.md", changed)
        self.assertEqual(self.lock()["upstream"]["ref"], "v2")

    def test_a_moved_upstream_tag_is_detected(self):
        write(self.up, {"base/docs/WORKFLOW.md": "sneaky\n"})
        self.commit(self.up, "sneaky")
        sh("git", "tag", "-f", "v1", cwd=self.up)
        # the lock pins the commit, so the project still gets what it reviewed
        sh("rm", "-rf", str(self.out / ".magrathea"), cwd=self.tmp)
        self.assertEqual(sh(sys.executable, "scripts/magrathea_sync.py", cwd=self.out).returncode, 0)
        self.assertEqual((self.out / ".magrathea/docs/WORKFLOW.md").read_text(), "upstream v1\n")


if __name__ == "__main__":
    unittest.main()
