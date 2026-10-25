import json
import tempfile
import unittest
from pathlib import Path

import magrathea


def make_distro(root, files=None):
    root.mkdir(parents=True, exist_ok=True)
    (root / "distro.json").write_text(json.dumps({"upstream": {"source": str(magrathea.ROOT), "ref": None}}))
    for rel, text in (files or {}).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


class DistroLayeringTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def new(self, distro, stack="java-service", name="Acme Svc"):
        target = self.tmp / "out"
        magrathea.new_project(target, name, stack, "", "@me", None, distro=distro)
        return target

    def test_no_distro_is_the_defaults(self):
        self.assertEqual(magrathea.list_stacks(), magrathea.list_stacks(None))
        self.assertIn("react-java", magrathea.list_stacks())

    def test_a_distro_file_replaces_the_default_at_the_same_path(self):
        distro = make_distro(self.tmp / "d", {"templates/project/README.md": "# @@name@@ by Acme\n"})
        self.assertEqual((self.new(distro) / "README.md").read_text(), "# Acme Svc by Acme\n")

    def test_files_the_distro_does_not_mention_stay_default(self):
        distro = make_distro(self.tmp / "d", {"templates/project/README.md": "x\n"})
        target = self.new(distro)
        self.assertTrue((target / "CONTEXT.md").is_file())
        self.assertTrue((target / "magrathea.lock.json").is_file())

    def test_a_distro_can_add_a_stack(self):
        distro = make_distro(self.tmp / "d", {
            "templates/stacks/go-api/stack.json": json.dumps({"name": "go-api", "title": "Go API", "summary": "s"}),
            "templates/stacks/go-api/notes.md": "Go notes\n",
            "templates/stacks/go-api/files/main.go": "// @@slug@@\n",
        })
        self.assertIn("go-api", magrathea.list_stacks(distro))
        target = self.new(distro, stack="go-api")
        self.assertEqual((target / "main.go").read_text(), "// acme-svc\n")

    def test_a_distro_can_override_one_file_of_a_default_stack(self):
        distro = make_distro(self.tmp / "d", {"templates/stacks/java-service/notes.md": "Acme notes\n"})
        self.assertEqual(magrathea.list_stacks(distro)["java-service"], magrathea.list_stacks()["java-service"])
        target = self.new(distro)
        text = "".join(p.read_text(errors="ignore") for p in target.glob("*.md"))
        self.assertIn("Acme notes", text)

    def test_the_default_checkout_is_not_changed(self):
        before = (magrathea.ROOT / "templates/project/README.md").read_text()
        distro = make_distro(self.tmp / "d", {"templates/project/README.md": "replaced\n"})
        self.new(distro)
        self.assertEqual((magrathea.ROOT / "templates/project/README.md").read_text(), before)

    def test_a_distro_file_that_collides_with_a_stack_file_is_an_error(self):
        stack_files = [p.relative_to(magrathea.ROOT / "templates/stacks/java-service/files")
                       for p in (magrathea.ROOT / "templates/stacks/java-service/files").rglob("*") if p.is_file()]
        rel = stack_files[0].as_posix()
        distro = make_distro(self.tmp / "d", {"templates/project/" + rel: "x\n"})
        with self.assertRaises(magrathea.MagratheaError):
            self.new(distro)

    def test_unknown_placeholder_in_a_distro_file_fails(self):
        distro = make_distro(self.tmp / "d", {"templates/project/README.md": "@@nope@@\n"})
        with self.assertRaises(magrathea.MagratheaError):
            self.new(distro)

    def test_a_folder_without_distro_json_is_rejected(self):
        (self.tmp / "d").mkdir()
        with self.assertRaises(magrathea.MagratheaError):
            magrathea.list_stacks(self.tmp / "d")


if __name__ == "__main__":
    unittest.main()
