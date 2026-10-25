import io
import json
import os
import tempfile
import unittest

import check_paths


def run(tool_input, allow, project, tool_name="Edit", extra=None):
    data = {"tool_name": tool_name, "tool_input": tool_input, "cwd": project}
    if extra:
        data.update(extra)
    argv = []
    for g in allow:
        argv += ["--allow", g]
    return check_paths.main(
        argv,
        stdin=io.StringIO(json.dumps(data)),
        env={"CLAUDE_PROJECT_DIR": project},
        cwd=project,
    )


class CheckPathsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.project = os.path.realpath(self._tmp.name)
        os.makedirs(os.path.join(self.project, "app", "svc"))
        os.makedirs(os.path.join(self.project, "platform", "policy"))

    def tearDown(self):
        self._tmp.cleanup()

    def p(self, *parts):
        return os.path.join(self.project, *parts)

    def test_allows_path_under_glob(self):
        self.assertEqual(run({"file_path": self.p("app", "svc", "main.py")}, ["app/**"], self.project), 0)

    def test_blocks_path_outside_glob(self):
        self.assertEqual(run({"file_path": self.p("platform", "policy", "x.rego")}, ["app/**"], self.project), 2)

    def test_relative_path_is_resolved_against_cwd(self):
        self.assertEqual(run({"file_path": "app/svc/main.py"}, ["app/**"], self.project), 0)
        self.assertEqual(run({"file_path": "platform/x"}, ["app/**"], self.project), 2)

    def test_blocks_path_outside_project(self):
        self.assertEqual(run({"file_path": "/etc/passwd"}, ["**"], self.project), 2)
        self.assertEqual(run({"file_path": "../elsewhere.txt"}, ["**"], self.project), 2)

    def test_blocks_dotdot_escape_from_allowed_dir(self):
        path = self.p("app", "..", "platform", "policy", "x.rego")
        self.assertEqual(run({"file_path": path}, ["app/**"], self.project), 2)

    def test_blocks_symlink_escape(self):
        link = self.p("app", "link")
        os.symlink(self.p("platform", "policy"), link)
        self.assertEqual(run({"file_path": os.path.join(link, "x.rego")}, ["app/**"], self.project), 2)

    def test_double_star_prefix_matches_any_depth(self):
        allow = ["**/evals/**"]
        self.assertEqual(run({"file_path": self.p("evals", "a.json")}, allow, self.project), 0)
        self.assertEqual(run({"file_path": self.p("app", "svc", "evals", "a.json")}, allow, self.project), 0)
        self.assertEqual(run({"file_path": self.p("app", "svc", "main.py")}, allow, self.project), 2)

    def test_single_star_does_not_cross_directories(self):
        allow = ["docs/*.md"]
        self.assertEqual(run({"file_path": self.p("docs", "a.md")}, allow, self.project), 0)
        self.assertEqual(run({"file_path": self.p("docs", "adr", "a.md")}, allow, self.project), 2)

    def test_notebook_path_is_checked(self):
        self.assertEqual(run({"notebook_path": self.p("platform", "n.ipynb")}, ["app/**"], self.project, "NotebookEdit"), 2)
        self.assertEqual(run({"notebook_path": self.p("app", "n.ipynb")}, ["app/**"], self.project, "NotebookEdit"), 0)

    def test_non_file_tool_is_allowed(self):
        self.assertEqual(run({"command": "ls"}, ["app/**"], self.project, "Bash"), 0)

    def test_bad_json_is_blocked(self):
        code = check_paths.main(["--allow", "app/**"], stdin=io.StringIO("not json"), env={}, cwd=self.project)
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
