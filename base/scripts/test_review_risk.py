import subprocess
import tempfile
import unittest
from pathlib import Path

import review_risk as rr

CFG = rr.load_config()


def ch(path, added=5, removed=0):
    return {"path": path, "added": added, "removed": removed}


def tier(changes, text=None):
    return rr.classify(changes, text or {}, CFG)["tier"]


class ClassifyTest(unittest.TestCase):
    def test_small_app_change_with_test_is_low(self):
        self.assertEqual(tier([ch("app/api/src/main/java/A.java"), ch("app/api/src/test/java/ATest.java")]), "low")

    def test_docs_only_is_low(self):
        self.assertEqual(tier([ch("README.md"), ch("specs/feature.md")]), "low")

    def test_empty_diff_is_low(self):
        self.assertEqual(tier([]), "low")

    def test_app_change_without_test_is_medium(self):
        self.assertEqual(tier([ch("app/web/src/App.tsx")]), "medium")

    def test_medium_for_moderate_size(self):
        files = [ch("app/web/src/f%d.test.tsx" % i, 20) for i in range(5)]
        self.assertEqual(tier(files), "medium")  # 100 lines > 80

    def test_high_for_sensitive_paths(self):
        for path in ["platform/infra/main.tf", ".github/workflows/ci.yml", "app/api/pom.xml",
                     "app/api/service.yaml", "app/api/Dockerfile", "docs/adr/0002-x.md",
                     "docs/trd/0001-x.md", "local/policy/a.rego", "magrathea.lock.json",
                     "app/api/src/main/resources/db/migration/V2__x.sql"]:
            with self.subTest(path):
                self.assertEqual(tier([ch(path)]), "high")

    def test_high_when_added_lines_mention_auth_or_secrets(self):
        files = [ch("app/api/src/main/java/A.java"), ch("app/api/src/test/java/ATest.java")]
        self.assertEqual(tier(files, {"app/api/src/main/java/A.java": "String password = x;\n"}), "high")

    def test_high_when_very_large(self):
        files = [ch("app/web/src/f%d.test.tsx" % i, 100) for i in range(6)]
        self.assertEqual(tier(files), "high")

    def test_unknown_location_is_not_low(self):
        self.assertEqual(tier([ch("tools/x.py")]), "medium")

    def test_reasons_are_given(self):
        result = rr.classify([ch("platform/x.tf")], {}, CFG)
        self.assertTrue(any("platform/x.tf" in r for r in result["reasons"]))


class GateTest(unittest.TestCase):
    def test_merges_only_when_everything_agrees(self):
        self.assertTrue(rr.gate("low", "approve", "success", "low")["merge"])

    def test_each_condition_blocks(self):
        cases = [
            ("medium", "approve", "success", "low", 0),
            ("high", "approve", "success", "low", 0),
            ("low", "request-changes", "success", "low", 0),
            ("low", "approve", "failure", "low", 0),
            ("low", "approve", "pending", "low", 0),
            ("low", "approve", "success", "off", 0),
            ("low", "approve", "success", "low", 1),
        ]
        for case in cases:
            with self.subTest(case):
                self.assertFalse(rr.gate(*case)["merge"])

    def test_cli_exit_codes_and_default_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(rr.main(["gate", "--tier", "low", "--verdict", "approve", "--ci", "success", "--project", tmp]), 1)
            Path(tmp, "magrathea.json").write_text('{"auto_merge": "low"}')
            self.assertEqual(rr.main(["gate", "--tier", "low", "--verdict", "approve", "--ci", "success", "--project", tmp]), 0)


class GitTest(unittest.TestCase):
    def test_classify_from_a_real_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            def git(*a):
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=tmp, check=True, capture_output=True)
            git("init", "-q", "-b", "main")
            Path(tmp, "README.md").write_text("hi\n")
            git("add", "."); git("commit", "-qm", "base")
            git("checkout", "-qb", "feat")
            Path(tmp, "app/api/src/test").mkdir(parents=True)
            Path(tmp, "app/api/src/test/ATest.java").write_text("class ATest {}\n")
            Path(tmp, "app/api/A.java").write_text("class A { String token; }\n")
            git("add", "."); git("commit", "-qm", "change")
            changes, text = rr.diff_from_git("main", "HEAD", tmp)
            self.assertEqual(sorted(c["path"] for c in changes), ["app/api/A.java", "app/api/src/test/ATest.java"])
            self.assertEqual(rr.classify(changes, text, CFG)["tier"], "high")  # 'token'


if __name__ == "__main__":
    unittest.main()
