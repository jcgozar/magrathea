import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import magrathea_lock as lock

lock_mod = lock


class LockTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        base = self.root / ".magrathea"
        (base / "standards").mkdir(parents=True)
        (base / "standards" / "pg.md").write_text("| ID | x |\n| --- | --- |\n| PG-001 | MUST |\n| COMMON-001 | MUST |\n")
        (base / "other.txt").write_text("hello\n")
        self.write_config_and_lock()

    def write_config_and_lock(self, **config_overrides):
        config = {"source": "https://example.invalid/magrathea.git", "ref": "v0.1.0", "auto_merge": "low"}
        config.update(config_overrides)
        (self.root / "magrathea.json").write_text(json.dumps(config))
        lock = {"source": "https://example.invalid/magrathea.git", "ref": "v0.1.0", "commit": "abc",
                "version": "0.1.0", "tree_hash": lock_mod.tree_hash(self.root / ".magrathea")}
        (self.root / "magrathea.lock.json").write_text(json.dumps(lock))

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, rel, text):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def test_clean_project_passes(self):
        self.assertEqual(lock.verify(self.root), [])

    def test_edit_add_remove_are_detected(self):
        self.put(".magrathea/other.txt", "changed\n")
        self.assertIn("differs from magrathea.lock.json", "\n".join(lock.verify(self.root)))

    def test_added_and_removed_files_are_detected(self):
        self.put(".magrathea/new.txt", "x\n")
        self.assertTrue(lock.verify(self.root))
        (self.root / ".magrathea" / "new.txt").unlink()
        (self.root / ".magrathea" / "standards" / "pg.md").unlink()
        self.assertTrue(lock.verify(self.root))

    def test_missing_base_or_lock_or_config_fails_with_a_hint(self):
        import shutil
        shutil.rmtree(self.root / ".magrathea")
        self.assertIn("magrathea_sync.py", "\n".join(lock.verify(self.root)))
        (self.root / "magrathea.lock.json").unlink()
        self.assertIn("--update", "\n".join(lock.verify(self.root)))
        (self.root / "magrathea.json").unlink()
        self.assertIn("magrathea.json is missing", "\n".join(lock.verify(self.root)))

    def test_config_and_lock_must_agree(self):
        self.write_config_and_lock()
        cfg = json.loads((self.root / "magrathea.json").read_text())
        cfg["ref"] = "v9.9.9"
        (self.root / "magrathea.json").write_text(json.dumps(cfg))
        self.assertIn("disagree", "\n".join(lock.verify(self.root)))

    def test_auto_merge_can_only_be_off_or_low(self):
        for value, ok in (("off", True), ("low", True), ("medium", False), ("high", False)):
            self.write_config_and_lock(auto_merge=value)
            self.assertEqual(lock.verify(self.root) == [], ok, value)

    def test_crlf_does_not_count_as_an_edit(self):
        (self.root / ".magrathea" / "other.txt").write_bytes(b"hello\r\n")
        self.assertEqual(lock.verify(self.root), [])

    def test_local_standard_cannot_reuse_base_rule_id(self):
        self.put("local/standards/pg.md", "| PG-001 | SHOULD | weaker |\n")
        self.assertIn("redefines base rule PG-001", "\n".join(lock.verify(self.root)))

    def test_local_standard_with_new_id_is_fine(self):
        self.put("local/standards/pg.md", "| PG-101 | MUST | stricter |\n")
        self.assertEqual(lock.verify(self.root), [])

    def test_local_rego_must_use_local_package_and_no_exceptions(self):
        self.put("local/policy/a.rego", "package main\ndeny contains msg if { msg := 'x' }\n")
        self.put("local/policy/b.rego", "package local\nexception contains rules if { rules := ['x'] }\n")
        self.put("local/policy/c.rego", "package local\nimport rego.v1\ndeny contains msg if { msg := 'ok' }\n")
        problems = "\n".join(lock.verify(self.root))
        self.assertIn("a.rego must use `package local`", problems)
        self.assertIn("b.rego defines an `exception`", problems)
        self.assertNotIn("c.rego", problems)


class ModeTest(unittest.TestCase):
    """DOMAIN-002 and DOMAIN-003 (ADR 0009)."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".magrathea").mkdir()
        (self.root / ".magrathea" / "x.txt").write_text("x\n")

    def tearDown(self):
        self._tmp.cleanup()

    def config(self, **extra):
        cfg = {"source": "s", "ref": "r", "auto_merge": "low", **extra}
        (self.root / "magrathea.json").write_text(json.dumps(cfg))
        (self.root / "magrathea.lock.json").write_text(json.dumps(
            {"source": "s", "ref": "r", "commit": "c", "version": "1", "tree_hash": lock.tree_hash(self.root / ".magrathea")}))
        return cfg

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = lock.main(["--root", str(self.root), *argv])
            except SystemExit as e:
                code = e.code
        return code, out.getvalue() + err.getvalue()

    def test_absent_fields_are_valid_and_mean_standalone(self):
        self.config()
        self.assertEqual(lock.verify(self.root), [])
        self.assertEqual(lock.effective_mode({}), {"infra_mode": "standalone", "domain": None, "type": "project"})

    def test_valid_domain_mode_and_domain_platform_pass(self):
        self.config(infra_mode="domain", domain="payments")
        self.assertEqual(lock.verify(self.root), [])
        self.config(type="domain-platform", domain="payments")
        self.assertEqual(lock.verify(self.root), [])

    def test_invalid_values_fail(self):
        for extra in ({"infra_mode": "shared"}, {"type": "platform"}, {"infra_mode": "domain"},
                      {"infra_mode": "domain", "domain": "Not Valid"}, {"domain": 3},
                      {"infra_mode": "domain", "domain": "payments\n"}, {"infra_mode": "domain", "domain": "a\n"},
                      {"type": "domain-platform", "infra_mode": "standalone"}):
            self.config(**extra)
            self.assertTrue(lock.verify(self.root), extra)

    def test_mode_data_writes_the_effective_mode(self):
        self.config(infra_mode="domain", domain="payments")
        out = self.root / "mode.json"
        self.assertEqual(self.run_main("mode-data", "--out", str(out))[0], 0)
        self.assertEqual(json.loads(out.read_text()), {"magrathea": {"infra_mode": "domain", "domain": "payments", "type": "project"}})
        self.config()
        self.run_main("mode-data", "--out", str(out))
        self.assertEqual(json.loads(out.read_text())["magrathea"]["infra_mode"], "standalone")

    def test_mode_data_refuses_an_invalid_config(self):
        self.config(infra_mode="domain")
        code, _ = self.run_main("mode-data", "--out", str(self.root / "mode.json"))
        self.assertEqual(code, 1)
        self.assertFalse((self.root / "mode.json").exists())

    def previous(self, **extra):
        p = self.root / "previous.json"
        p.write_text(json.dumps({"source": "s", "ref": "r", **extra}))
        return str(p)

    def test_a_mode_change_fails_unless_approved(self):
        self.config(infra_mode="domain", domain="payments")
        prev = self.previous()
        code, out = self.run_main("mode-change", "--previous", prev)
        self.assertEqual(code, 1)
        self.assertIn("infra_mode: standalone -> domain", out)
        self.assertEqual(self.run_main("mode-change", "--previous", prev, "--approved")[0], 0)

    def test_no_change_and_explicit_defaults_pass(self):
        self.config()
        self.assertEqual(self.run_main("mode-change", "--previous", self.previous())[0], 0)
        self.config(infra_mode="standalone", type="project")  # spelling out the default is not a change
        self.assertEqual(self.run_main("mode-change", "--previous", self.previous())[0], 0)

    def test_leaving_domain_mode_and_changing_the_domain_also_fail(self):
        self.config()
        self.assertEqual(self.run_main("mode-change", "--previous", self.previous(infra_mode="domain", domain="a"))[0], 1)
        self.config(infra_mode="domain", domain="b")
        self.assertEqual(self.run_main("mode-change", "--previous", self.previous(infra_mode="domain", domain="a"))[0], 1)

    def test_a_missing_or_empty_previous_file_skips_the_check(self):
        self.config(infra_mode="domain", domain="payments")
        self.assertEqual(self.run_main("mode-change", "--previous", str(self.root / "nope.json"))[0], 0)
        empty = self.root / "empty.json"
        empty.write_text("")
        self.assertEqual(self.run_main("mode-change", "--previous", str(empty))[0], 0)

    def test_a_skipped_check_prints_a_visible_warning_on_stderr(self):
        self.config(infra_mode="domain", domain="payments")
        bad = self.root / "bad.json"
        bad.write_text("{not json")
        for prev in (self.root / "nope.json", self.root / "empty2.json", bad):
            if prev.name == "empty2.json":
                prev.write_text("")
            err = io.StringIO()
            with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
                code = lock.main(["mode-change", "--root", str(self.root), "--previous", str(prev)])
            self.assertEqual(code, 0)
            self.assertIn("WARNING", err.getvalue())
            self.assertIn("SKIPPED", err.getvalue())



if __name__ == "__main__":
    unittest.main()