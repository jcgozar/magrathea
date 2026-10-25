import subprocess
import tempfile
import unittest
from pathlib import Path

import check_base_change as cbc

STD = "| ID | Strength | Rule | Enforced by | Status |\n| --- | --- | --- | --- | --- |\n| Q-001 | MUST | encrypted | q.rego | implemented |\n| Q-002 | SHOULD | tagged | q.rego | planned |\n"


class CheckBaseChangeTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        self.put("base/standards/q.md", STD)
        self.put("base/VERSION", "0.1.0\n")
        self.put("CHANGELOG.md", "# c\n")
        self.git("add", "."); self.git("commit", "-qm", "base")
        self.git("checkout", "-qb", "feat")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *a):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=self.repo, check=True, capture_output=True)

    def put(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def run_check(self):
        return cbc.check(str(self.repo), "main")

    def test_parser_reads_rows(self):
        self.assertEqual(cbc.rules(STD), {"Q-001": ("MUST", "implemented"), "Q-002": ("SHOULD", "planned")})

    def test_clean_addition_with_version_and_changelog_passes(self):
        self.put("base/standards/q.md", STD + "| Q-003 | MUST | x | q.rego | planned |\n")
        self.put("base/VERSION", "0.2.0\n"); self.put("CHANGELOG.md", "# c\n- q\n")
        self.assertEqual(self.run_check(), [])

    def test_removal_weakening_and_downgrade_are_reported(self):
        weakened = STD.replace("| Q-001 | MUST | encrypted | q.rego | implemented |", "| Q-001 | SHOULD | encrypted | q.rego | planned |")
        weakened = weakened.replace("| Q-002 | SHOULD | tagged | q.rego | planned |\n", "")
        self.put("base/standards/q.md", weakened)
        self.put("base/VERSION", "0.2.0\n"); self.put("CHANGELOG.md", "# c\n- q\n")
        text = "\n".join(self.run_check())
        self.assertIn("Q-001 was weakened from MUST to SHOULD", text)
        self.assertIn("Q-001 went from implemented to planned", text)
        self.assertIn("Q-002 was removed", text)

    def test_missing_version_bump_and_changelog_are_reported(self):
        self.put("base/standards/new.md", "| N-001 | MUST | a | b | planned |\n")
        text = "\n".join(self.run_check())
        self.assertIn("VERSION was not bumped", text)
        self.assertIn("CHANGELOG.md has no entry", text)

    def test_change_outside_base_needs_nothing(self):
        self.put("tools/x.py", "pass\n")
        self.assertEqual(self.run_check(), [])


if __name__ == "__main__":
    unittest.main()
