"""The example distribution must keep working: the guide points readers at it."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import magrathea

EXAMPLE = magrathea.ROOT / "examples" / "acme-platform"


def run(target, script, *args):
    return subprocess.run([sys.executable, str(target / ".magrathea" / "scripts" / script), *args],
                          capture_output=True, text=True, cwd=str(target))


class AcmeExampleTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name) / "site"
        magrathea.new_project(self.target, "Acme Site", "static-site", "A site.", "@acme-lead", None, distro=EXAMPLE)

    def tearDown(self):
        self._tmp.cleanup()

    def test_it_adds_a_stack_a_standard_and_a_persona(self):
        self.assertIn("static-site", magrathea.list_stacks(EXAMPLE))
        self.assertIn("Acme Site", (self.target / "site/index.html").read_text())
        self.assertIn("ACME-001", (self.target / ".magrathea/standards/acme-naming.md").read_text())
        self.assertTrue((self.target / ".claude/agents/compliance.md").is_file())

    def test_it_replaces_a_template_and_keeps_the_rest(self):
        self.assertIn("@acme/platform-team", (self.target / ".github/CODEOWNERS").read_text())
        self.assertTrue((self.target / "CONTEXT.md").is_file())
        self.assertTrue((self.target / ".magrathea/standards/postgres.md").is_file())

    def test_the_project_verifies_and_is_in_sync(self):
        self.assertEqual(run(self.target, "magrathea_lock.py", "verify").returncode, 0)
        self.assertEqual(run(self.target, "sync_agents.py", "--check").returncode, 0)

    def test_the_default_stacks_still_work_with_it(self):
        other = self.target.parent / "svc"
        magrathea.new_project(other, "Acme Svc", "java-service", "", "@me", None, distro=EXAMPLE)
        self.assertEqual(run(other, "magrathea_lock.py", "verify").returncode, 0)

    def test_domain_platform_works_with_a_distribution(self):
        dp = self.target.parent / "dp"
        magrathea.new_project(dp, "Acme Domain", "domain-platform", "", "@me", None, distro=EXAMPLE)
        self.assertEqual(json.loads((dp / "magrathea.json").read_text())["type"], "domain-platform")
        self.assertEqual(run(dp, "magrathea_lock.py", "verify").returncode, 0)
        self.assertEqual(run(dp, "sync_agents.py", "--check").returncode, 0)
        attached = self.target.parent / "attached"
        magrathea.new_project(attached, "Acme Attached", "static-site", "", "@me", None, distro=EXAMPLE, domain="acme")
        self.assertEqual(json.loads((attached / "magrathea.json").read_text())["infra_mode"], "domain")
        self.assertEqual(run(attached, "magrathea_lock.py", "verify").returncode, 0)

    def test_the_lock_names_the_distribution(self):
        lock = json.loads((self.target / "magrathea.lock.json").read_text())
        self.assertTrue(lock["source"].endswith("examples/acme-platform"))


if __name__ == "__main__":
    unittest.main()
