import shutil
import tempfile
import unittest
from pathlib import Path

import sync_agents

GOOD = """---
name: demo
description: A demo persona: with a colon.
access: edit-shell
writable_paths:
  - app/**
  - "**/evals/**"
---

# Demo

Body text.
"""


class SyncAgentsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".magrathea" / "agents" / "personas").mkdir(parents=True)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, name, text):
        (self.root / ".magrathea" / "agents" / "personas" / name).write_text(text, encoding="utf-8")

    def run_sync(self, *args):
        return sync_agents.main(["--root", str(self.root), *args])

    def test_generates_claude_file_with_tools_and_guard(self):
        self.write("demo.md", GOOD)
        self.assertEqual(self.run_sync(), 0)
        out = (self.root / ".claude" / "agents" / "demo.md").read_text()
        self.assertIn("name: demo", out)
        self.assertIn("tools: Read, Edit, Write, Glob, Grep, Bash", out)
        self.assertIn(".magrathea/scripts/check_paths.py", out)
        self.assertIn("--allow 'app/**'", out)
        self.assertIn("--allow '**/evals/**'", out)
        self.assertIn("GENERATED from .magrathea/agents/personas/demo.md", out)
        self.assertIn("Body text.", out)

    def test_description_with_colon_is_quoted(self):
        self.write("demo.md", GOOD)
        self.run_sync()
        out = (self.root / ".claude" / "agents" / "demo.md").read_text()
        self.assertIn('description: "A demo persona: with a colon."', out)

    def test_read_only_persona_has_no_hook_or_edit_tools(self):
        self.write("viewer.md", "---\nname: viewer\ndescription: Reads.\naccess: read\n---\nBody\n")
        self.run_sync()
        out = (self.root / ".claude" / "agents" / "viewer.md").read_text()
        self.assertIn("tools: Read, Grep, Glob\n", out)
        self.assertNotIn("hooks:", out)
        self.assertNotIn("Edit", out.split("---")[1])

    def test_check_passes_when_in_sync_and_fails_when_edited(self):
        self.write("demo.md", GOOD)
        self.run_sync()
        self.assertEqual(self.run_sync("--check"), 0)
        path = self.root / ".claude" / "agents" / "demo.md"
        path.write_text(path.read_text() + "\nhand edit\n")
        self.assertEqual(self.run_sync("--check"), 1)

    def test_check_fails_when_generated_file_missing(self):
        self.write("demo.md", GOOD)
        self.assertEqual(self.run_sync("--check"), 1)

    def test_stale_generated_file_is_removed(self):
        self.write("demo.md", GOOD)
        self.write("other.md", GOOD.replace("name: demo", "name: other"))
        self.run_sync()
        (self.root / ".magrathea" / "agents" / "personas" / "other.md").unlink()
        self.assertEqual(self.run_sync("--check"), 1)
        self.run_sync()
        self.assertFalse((self.root / ".claude" / "agents" / "other.md").exists())

    def test_hand_written_agent_file_is_left_alone(self):
        self.write("demo.md", GOOD)
        mine = self.root / ".claude" / "agents"
        mine.mkdir(parents=True)
        (mine / "mine.md").write_text("---\nname: mine\ndescription: x\n---\nhand written\n")
        self.run_sync()
        self.assertTrue((mine / "mine.md").exists())
        self.assertEqual(self.run_sync("--check"), 0)

    def test_validation_errors(self):
        cases = {
            "name mismatch": GOOD.replace("name: demo", "name: nope"),
            "bad access": GOOD.replace("edit-shell", "root"),
            "editing without paths": "---\nname: demo\ndescription: d\naccess: edit-shell\n---\nB\n",
            "read with paths": GOOD.replace("edit-shell", "read"),
            "no front matter": "# just a body\n",
            "quote in path": GOOD.replace("app/**", "ap'p/**"),
        }
        for label, text in cases.items():
            with self.subTest(label):
                self.write("demo.md", text)
                self.assertEqual(self.run_sync(), 1)

    def local(self, name, text):
        d = self.root / "local" / "personas"
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(text, encoding="utf-8")

    def test_local_addition_is_appended_to_base_persona(self):
        self.write("demo.md", GOOD)
        self.local("demo.md", "Always use British spelling.\n")
        self.assertEqual(self.run_sync(), 0)
        out = (self.root / ".claude" / "agents" / "demo.md").read_text()
        self.assertIn("Body text.", out)
        self.assertIn("## Project-specific behavior", out)
        self.assertIn("Always use British spelling.", out)
        self.assertLess(out.index("Body text."), out.index("British"))
        self.assertIn("--allow 'app/**'", out)  # the base permissions are unchanged

    def test_local_cannot_redefine_a_base_persona(self):
        self.write("demo.md", GOOD)
        self.local("demo.md", GOOD.replace("app/**", "**"))
        self.assertEqual(self.run_sync(), 1)

    def test_local_addition_needs_a_base_persona(self):
        self.write("demo.md", GOOD)
        self.local("ghost.md", "text\n")
        self.assertEqual(self.run_sync(), 1)

    def test_local_can_define_a_new_persona(self):
        self.write("demo.md", GOOD)
        self.local("docs-writer.md", "---\nname: docs-writer\ndescription: d\naccess: edit-no-shell\nwritable_paths:\n  - docs/**\n---\nBody\n")
        self.assertEqual(self.run_sync(), 0)
        self.assertTrue((self.root / ".claude" / "agents" / "docs-writer.md").exists())

    def test_nobody_may_be_given_write_access_to_the_base(self):
        self.write("demo.md", GOOD.replace("app/**", ".magrathea/**"))
        self.assertEqual(self.run_sync(), 1)
        self.write("demo.md", GOOD)
        self.local("evil.md", "---\nname: evil\ndescription: d\naccess: edit-shell\nwritable_paths:\n  - \"**/.magrathea/**\"\n---\nB\n".replace('"', ''))
        self.assertEqual(self.run_sync(), 1)

    def test_commands_are_copied_with_marker(self):
        self.write("demo.md", GOOD)
        cmd = self.root / ".magrathea" / "claude" / "commands"
        cmd.mkdir(parents=True)
        (cmd / "go.md").write_text("---\ndescription: Go\n---\n\nDo it.\n")
        self.assertEqual(self.run_sync(), 0)
        out = (self.root / ".claude" / "commands" / "go.md").read_text()
        self.assertIn("description: Go", out)
        self.assertIn("GENERATED from .magrathea/claude/commands/go.md", out)
        self.assertIn("Do it.", out)
        self.assertEqual(self.run_sync("--check"), 0)

    def test_a_domain_platform_gets_a_subset_and_the_rest_unchanged(self):
        import json
        for name in ("pm", "architect", "reviewer"):
            self.write(name + ".md", "---\nname: %s\ndescription: d\naccess: read\n---\nB\n" % name)
        cmd = self.root / ".magrathea" / "claude" / "commands"
        cmd.mkdir(parents=True)
        for name in ("feature", "review"):
            (cmd / (name + ".md")).write_text("---\ndescription: x\n---\n\nDo.\n")
        (self.root / ".magrathea" / "project-types.json").write_text(json.dumps(
            {"domain-platform": {"exclude_personas": ["pm", "architect"], "exclude_commands": ["feature"]}}))
        agents = self.root / ".claude" / "agents"
        # no type, or "project": everything is generated
        (self.root / "magrathea.json").write_text(json.dumps({"source": "s"}))
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual(sorted(p.stem for p in agents.glob("*.md")), ["architect", "pm", "reviewer"])
        # domain-platform: the subset, and the stale generated files are removed
        (self.root / "magrathea.json").write_text(json.dumps({"source": "s", "type": "domain-platform"}))
        self.assertEqual(self.run_sync("--check"), 1)
        self.assertEqual(self.run_sync(), 0)
        self.assertEqual(sorted(p.stem for p in agents.glob("*.md")), ["reviewer"])
        self.assertEqual(sorted(p.stem for p in (self.root / ".claude" / "commands").glob("*.md")), ["review"])
        self.assertEqual(self.run_sync("--check"), 0)

    def test_an_unknown_type_is_an_error(self):
        import json
        self.write("demo.md", GOOD)
        (self.root / "magrathea.json").write_text(json.dumps({"type": "mystery"}))
        (self.root / ".magrathea" / "project-types.json").write_text("{}")
        self.assertEqual(self.run_sync(), 1)


if __name__ == "__main__":
    unittest.main()
