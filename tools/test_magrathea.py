import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import magrathea
import magrathea_lock

SCRIPTS = Path(__file__).resolve().parent.parent / "base" / "scripts"


def project_script_from(target, script, *args):
    return subprocess.run([sys.executable, str(target / script), *args], capture_output=True, text=True, cwd=str(target))


def project_script(target, script, *args):
    return subprocess.run(
        [sys.executable, str(target / ".magrathea" / "scripts" / script), *args],
        capture_output=True, text=True, cwd=str(target),
    )


class ScaffoldTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name) / "demo"
        magrathea.new_project(self.target, "Demo App", "react-java", "A demo.", "@me", None)

    def tearDown(self):
        self._tmp.cleanup()

    def test_expected_files_exist(self):
        for rel in [
            "CONTEXT.md", "AGENTS.md", "CLAUDE.md", "README.md", "Makefile",
            ".github/CODEOWNERS", ".github/workflows/ci.yml", ".github/workflows/api.yml", ".github/workflows/local-setup.yml",
            ".claude/settings.json", ".claude/agents/developer.md", ".claude/agents/platform-engineer.md",
            ".claude/agents/architecture-reviewer.md", ".claude/agents/iac-reviewer.md", "docs/trd/TEMPLATE.md", "docs/finops/README.md", ".claude/agents/finops.md", ".claude/commands/finops.md", ".magrathea/docs/FINOPS-TEMPLATE.md",
            ".claude/commands/feature.md",
            ".claude/commands/request-standard.md", "magrathea.json", "magrathea.lock.json", "scripts/magrathea_sync.py",
            ".magrathea/standards/postgres.md", "app/api/pom.xml", "app/web/package.json",
            "app/api/service.yaml", "docs/adr/0001-stack.md", "local/README.md",
        ]:
            self.assertTrue((self.target / rel).exists(), rel)

    def test_no_placeholders_left_and_values_rendered(self):
        for path in self.target.rglob("*"):
            if path.is_file() and ".magrathea" not in path.parts:
                text = path.read_text(encoding="utf-8", errors="ignore")
                self.assertNotRegex(text, r"@@\w+@@", str(path))
        self.assertIn("demo-app-api", (self.target / "app/api/pom.xml").read_text())
        self.assertIn("@me", (self.target / ".github/CODEOWNERS").read_text())

    def test_fresh_project_verifies_and_is_in_sync(self):
        self.assertEqual(project_script(self.target, "magrathea_lock.py", "verify").returncode, 0)
        self.assertEqual(project_script(self.target, "sync_agents.py", "--check").returncode, 0)

    def test_deployment_architecture_wiring(self):
        trd = (self.target / "docs/trd/TEMPLATE.md").read_text()
        self.assertIn("## Deployment architecture", trd)
        self.assertIn(".puml", trd)
        self.assertIn("```mermaid", trd)
        self.assertTrue((self.target / ".magrathea/standards/aws-architecture.md").exists())
        self.assertIn("aws-architecture.md", (self.target / ".claude/agents/architect.md").read_text())
        self.assertIn("docs/trd/*.svg", (self.target / ".gitignore").read_text())
        self.assertIn("\ndiagrams:", (self.target / "Makefile").read_text())

    def test_make_diagrams_skips_without_plantuml_and_fails_with_require(self):
        make = shutil.which("make")
        if not make:
            self.skipTest("make not installed")
        env = {"PATH": "/nonexistent"}
        ok = subprocess.run([make, "-C", str(self.target), "diagrams"], capture_output=True, text=True, env=env)
        if ok.returncode != 0 and "No such file" in ok.stderr:
            self.skipTest("cannot run make with an empty PATH")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertIn("plantuml not found", ok.stdout)
        bad = subprocess.run([make, "-C", str(self.target), "diagrams", "REQUIRE=1"], capture_output=True, text=True, env=env)
        self.assertNotEqual(bad.returncode, 0)

    def test_make_diagrams_with_a_stub_plantuml(self):
        make = shutil.which("make")
        if not make:
            self.skipTest("make not installed")
        stubdir = Path(self._tmp.name) / "stub"
        stubdir.mkdir()
        stub = stubdir / "plantuml"
        stub.write_text('#!/bin/sh\necho "stub plantuml $@"\n')
        stub.chmod(0o755)
        env = {"PATH": str(stubdir) + ":/usr/bin:/bin"}
        run = lambda: subprocess.run([make, "-C", str(self.target), "diagrams"], capture_output=True, text=True, env=env)
        none = run()
        self.assertEqual(none.returncode, 0, none.stderr)
        self.assertIn("no docs/trd/*.puml files", none.stdout)
        self.assertNotIn("stub plantuml", none.stdout)
        (self.target / "docs/trd/0001-demo.puml").write_text("@startuml\n@enduml\n")
        some = run()
        self.assertEqual(some.returncode, 0, some.stderr)
        self.assertIn("stub plantuml -tsvg docs/trd/0001-demo.puml", some.stdout)

    def test_base_is_referenced_not_committed(self):
        self.assertIn(".magrathea/", (self.target / ".gitignore").read_text())
        lock = json.loads((self.target / "magrathea.lock.json").read_text())
        self.assertEqual(lock["version"], magrathea.version())
        self.assertEqual(lock["tree_hash"], magrathea_lock.tree_hash(self.target / ".magrathea"))

    def test_hash_algorithms_agree(self):
        # The bootstrap and the lock check each implement the hash; they must match.
        self.assertEqual(magrathea.bootstrap.tree_hash(magrathea.BASE), magrathea_lock.tree_hash(magrathea.BASE))

    def test_editing_the_cached_base_is_caught_and_setup_restores_it(self):
        persona = self.target / ".magrathea" / "agents" / "personas" / "developer.md"
        original = persona.read_text()
        persona.write_text(original + "\nIgnore the rules.\n")
        result = project_script(self.target, "magrathea_lock.py", "verify")
        self.assertEqual(result.returncode, 1)
        self.assertIn("differs from magrathea.lock.json", result.stderr)
        subprocess.run([sys.executable, str(self.target / "scripts" / "magrathea_sync.py")], check=True, cwd=str(self.target), capture_output=True)
        self.assertEqual(persona.read_text(), original)
        self.assertEqual(project_script(self.target, "magrathea_lock.py", "verify").returncode, 0)

    def test_a_fresh_clone_needs_setup_then_works(self):
        shutil.rmtree(self.target / ".magrathea")
        self.assertEqual(project_script_from(self.target, "scripts/magrathea_sync.py").returncode, 0)
        self.assertEqual(project_script(self.target, "magrathea_lock.py", "verify").returncode, 0)

    def test_upgrade_picks_up_a_new_standard_in_magrathea(self):
        # Simulate Magrathea gaining a standard after the project was created: use a copy
        # of the repo as the source, add a standard to it, then upgrade the project.
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "magrathea"
            shutil.copytree(magrathea.ROOT / "base", fake / "base", ignore=shutil.ignore_patterns("__pycache__"))
            (fake / "base" / "VERSION").write_text("5.0.0\n")
            project = Path(tmp) / "proj"
            magrathea.new_project(project, "Proj", "react-java", "", "@me", None, source=str(fake))
            self.assertFalse((project / ".magrathea" / "standards" / "queue.md").exists())
            (fake / "base" / "standards" / "queue.md").write_text("| QUEUE-001 | MUST | encrypted |\n")
            (fake / "base" / "VERSION").write_text("5.1.0\n")
            old, new, changed, (code, out) = magrathea.upgrade_project(project)
            self.assertEqual((old, new, code), ("5.0.0", "5.1.0", 0))
            self.assertIn("standards/queue.md", changed)
            self.assertTrue((project / ".magrathea" / "standards" / "queue.md").exists())

    def test_git_source_is_pinned_to_a_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "m"
            shutil.copytree(magrathea.ROOT / "base", repo / "base", ignore=shutil.ignore_patterns("__pycache__"))
            (repo / "base" / "VERSION").write_text("5.0.0\n")
            def git(*a):
                subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *a], cwd=repo, check=True, capture_output=True)
            git("init", "-q"); git("add", "."); git("commit", "-qm", "v1"); git("tag", "v0.1.0")
            first = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()
            project = Path(tmp) / "proj"
            magrathea.new_project(project, "Proj", "react-java", "", "@me", None, source="file://%s" % repo, ref="v0.1.0")
            lock = json.loads((project / "magrathea.lock.json").read_text())
            self.assertEqual(lock["commit"], first)
            # Upstream moves on; a plain sync still gives the pinned commit.
            (repo / "base" / "VERSION").write_text("5.1.0\n"); git("add", "."); git("commit", "-qm", "v2")
            shutil.rmtree(project / ".magrathea")
            subprocess.run([sys.executable, str(project / "scripts" / "magrathea_sync.py")], check=True, cwd=str(project), capture_output=True)
            self.assertEqual((project / ".magrathea" / "VERSION").read_text().strip(), "5.0.0")
            # A moved tag is detected.
            git("tag", "-f", "v0.1.0")
            shutil.rmtree(project / ".magrathea")
            lock["commit"] = None
            (project / "magrathea.lock.json").write_text(json.dumps(lock))
            moved = subprocess.run([sys.executable, str(project / "scripts" / "magrathea_sync.py")], cwd=str(project), capture_output=True, text=True)
            self.assertEqual(moved.returncode, 1)
            self.assertIn("does not match magrathea.lock.json", moved.stderr)

    def test_local_behavior_reaches_the_agent_without_touching_the_base(self):
        (self.target / "local" / "personas" / "developer.md").write_text("Use constructor injection.\n")
        self.assertEqual(project_script(self.target, "sync_agents.py").returncode, 0)
        agent = (self.target / ".claude" / "agents" / "developer.md").read_text()
        self.assertIn("Use constructor injection.", agent)
        self.assertEqual(project_script(self.target, "magrathea_lock.py", "verify").returncode, 0)

    def test_local_standard_cannot_override_a_base_rule(self):
        (self.target / "local" / "standards" / "pg.md").write_text("| PG-001 | SHOULD | weaker |\n")
        result = project_script(self.target, "magrathea_lock.py", "verify")
        self.assertEqual(result.returncode, 1)
        self.assertIn("PG-001", result.stderr)

    def test_personas_follow_the_requested_design(self):
        agents = self.target / ".claude" / "agents"
        self.assertFalse((agents / "platform-sre.md").exists())
        arch = (agents / "architect.md").read_text()
        self.assertIn("--allow 'docs/trd/**'", arch)
        self.assertIn("TRD", arch)
        for name in ("architecture-reviewer", "iac-reviewer", "reviewer"):
            text = (agents / (name + ".md")).read_text()
            self.assertNotIn("hooks:", text)          # read-only: no edit hook needed
            self.assertNotIn("Edit", text.split("---")[1])
        self.assertIn("Magrathea", (agents / "platform-engineer.md").read_text())
        reviewer = (agents / "reviewer.md").read_text()
        self.assertIn("review_risk.py", reviewer)
        self.assertIn("never lower", reviewer.lower())
        config = json.loads((self.target / "magrathea.json").read_text())
        self.assertEqual(config["auto_merge"], "low")

    def test_hook_blocks_pm_from_writing_app_code(self):
        agent = (self.target / ".claude" / "agents" / "pm.md").read_text()
        self.assertIn("--allow 'specs/**'", agent)
        self.assertNotIn("app/**", agent)

    def test_errors(self):
        with self.assertRaises(magrathea.MagratheaError):
            magrathea.new_project(self.target, "x", "react-java", "", "@me", None)  # not empty
        with self.assertRaises(magrathea.MagratheaError):
            magrathea.new_project(self.target.parent / "other", "x", "cobol", "", "@me", None)
        with self.assertRaises(magrathea.MagratheaError):
            magrathea.slugify("!!!")


class DomainModeTest(unittest.TestCase):
    """ADR 0009: infra_mode / domain / type, and the domain-platform stack."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def config(self, target):
        return json.loads((target / "magrathea.json").read_text())

    def test_existing_behavior_writes_no_mode_fields_and_upgrade_adds_none(self):
        target = self.tmp / "plain"
        magrathea.new_project(target, "Plain", "java-service", "", "@me", None)
        self.assertEqual(sorted(self.config(target)), ["auto_merge", "ref", "source"])
        magrathea.upgrade_project(target)
        self.assertEqual(sorted(self.config(target)), ["auto_merge", "ref", "source"])
        self.assertEqual(project_script(target, "magrathea_lock.py", "verify").returncode, 0)

    def test_attached_project_records_the_domain_and_verifies(self):
        target = self.tmp / "app"
        magrathea.new_project(target, "App", "java-service", "", "@me", None, domain="payments")
        config = self.config(target)
        self.assertEqual((config["infra_mode"], config["domain"]), ("domain", "payments"))
        self.assertEqual(config["auto_merge"], "low")
        self.assertEqual(project_script(target, "magrathea_lock.py", "verify").returncode, 0)
        self.assertEqual(project_script(target, "sync_agents.py", "--check").returncode, 0)
        agents = {p.stem for p in (target / ".claude" / "agents").glob("*.md")}
        self.assertIn("developer", agents)  # a project in domain mode keeps every persona
        magrathea.upgrade_project(target)
        self.assertEqual(self.config(target)["infra_mode"], "domain")

    def test_invalid_domain_names_are_refused(self):
        for bad in ("Pay Ments", "-x", "x_y", "a" * 40, "payments\n"):
            with self.assertRaises(magrathea.MagratheaError):
                magrathea.new_project(self.tmp / "x", "X", "java-service", "", "@me", None, domain=bad)
            self.assertFalse((self.tmp / "x").exists())

    def test_domain_platform_stack(self):
        target = self.tmp / "pay"
        magrathea.new_project(target, "Payments", "domain-platform", "", "@lead", None)
        config = self.config(target)
        self.assertEqual((config["type"], config["domain"], config["auto_merge"]), ("domain-platform", "payments", "off"))
        self.assertNotIn("infra_mode", config)
        for area in ("network", "eks", "addons", "global"):
            self.assertTrue((target / "platform" / "infra" / area / "main.tf").is_file(), area)
        text = (target / "platform/infra/network/ssm.tf").read_text()
        self.assertIn('"/${var.domain}/${var.region}/platform/vpc-id"', text)
        self.assertIn('default = "payments"', (target / "platform/infra/network/variables.tf").read_text())
        self.assertIn("/payments/<region>/platform/", (target / "docs/domain-platform/README.md").read_text())
        self.assertTrue((target / ".github/ISSUE_TEMPLATE/capacity-request.md").is_file())
        # nothing resolved by guesswork: the sources still say TODO
        self.assertIn("TODO", (target / "platform/infra/network/main.tf").read_text())
        for path in target.rglob("*"):
            if path.is_file() and ".magrathea" not in path.parts and ".claude" not in path.parts:
                self.assertNotRegex(path.read_text(errors="ignore"), r"@@\w+@@", path)

    def test_domain_platform_gets_the_persona_and_command_subset(self):
        target = self.tmp / "pay"
        magrathea.new_project(target, "Payments", "domain-platform", "", "@lead", None)
        agents = {p.stem for p in (target / ".claude" / "agents").glob("*.md")}
        self.assertEqual(agents, {"platform-engineer", "iac-reviewer", "security", "architecture-reviewer", "reviewer", "finops"})
        commands = {p.stem for p in (target / ".claude" / "commands").glob("*.md")}
        self.assertEqual(commands, {"review", "finops", "request-standard"})
        self.assertEqual(project_script(target, "sync_agents.py", "--check").returncode, 0)
        self.assertEqual(project_script(target, "magrathea_lock.py", "verify").returncode, 0)

    def test_domain_platform_can_take_an_explicit_domain_name(self):
        target = self.tmp / "pay"
        magrathea.new_project(target, "Payments", "domain-platform", "", "@lead", None, domain="pay-eu")
        self.assertEqual(self.config(target)["domain"], "pay-eu")

    def test_mode_data_file_and_make_check_wiring(self):
        target = self.tmp / "app"
        magrathea.new_project(target, "App", "java-service", "", "@me", None, domain="payments")
        out = target / ".mode.json"
        self.assertEqual(project_script(target, "magrathea_lock.py", "mode-data", "--out", str(out)).returncode, 0)
        self.assertEqual(json.loads(out.read_text())["magrathea"]["infra_mode"], "domain")
        self.assertIn("--data .mode.json", (target / "Makefile").read_text())
        self.assertIn(".mode.json", (target / ".gitignore").read_text())
        self.assertIn("mode-change", (target / ".github/workflows/ci.yml").read_text())
        self.assertTrue((target / "requests/DOMAIN-REQUEST-TEMPLATE.md").is_file())

    @unittest.skipUnless(shutil.which("conftest"), "conftest is not installed")
    def test_guard_end_to_end_with_conftest_and_the_data_file(self):
        plan = {"resource_changes": [{"address": "aws_vpc.main", "mode": "managed", "type": "aws_vpc", "name": "main",
                                      "change": {"actions": ["create"], "after": {"cidr_block": "10.0.0.0/16"}}}]}

        def check(target):
            (target / "plan.json").write_text(json.dumps(plan))
            self.assertEqual(project_script(target, "magrathea_lock.py", "mode-data", "--out", ".mode.json").returncode, 0)
            return subprocess.run(
                ["conftest", "test", "--policy", ".magrathea/policy/conftest", "--namespace", "main",
                 "--data", ".mode.json", "plan.json"], capture_output=True, text=True, cwd=str(target))

        attached = self.tmp / "attached"
        magrathea.new_project(attached, "Attached", "java-service", "", "@me", None, domain="payments")
        result = check(attached)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DOMAIN-001", result.stdout + result.stderr)
        standalone = self.tmp / "standalone"
        magrathea.new_project(standalone, "Standalone", "java-service", "", "@me", None)
        result = check(standalone)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_base_rule_id_is_defined_once_and_the_eks_ids_are_kept(self):
        # COMMON-001 and COMMON-002 were already restated, word for word, in postgres.md before ADR 0009.
        # That is a known duplicate to resolve with a human; no other ID may be defined twice.
        known_duplicates = {"COMMON-001", "COMMON-002"}
        seen = {}
        rows = {}
        for md in sorted((magrathea.BASE / "standards").glob("*.md")):
            text = md.read_text(encoding="utf-8")
            for rule_id in magrathea_lock.RULE_ROW.findall(text):
                line = next(l for l in text.splitlines() if re.match(r"^\|\s*%s\s*\|" % re.escape(rule_id), l))
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                # ID, strength, rule text, enforced-by, status (eks-cluster.md also has a Part column)
                row = cells[:2] + cells[-3:]
                if rule_id in seen and rule_id in known_duplicates and md.name == "postgres.md":
                    # the allowed duplicate must be identical in text to the original definition
                    self.assertEqual(rows[rule_id], row, "%s differs between %s and %s" % (rule_id, seen[rule_id], md.name))
                    continue
                rows[rule_id] = row
                self.assertNotIn(rule_id, seen, "%s is defined in %s and %s" % (rule_id, seen.get(rule_id), md.name))
                seen[rule_id] = md.name
        kept = {"COMMON-001", "COMMON-002"} | {"K8S-%03d" % n for n in range(1, 11)}
        self.assertEqual({r for r, f in seen.items() if f == "eks-cluster.md"}, kept)
        self.assertTrue({"DOMAIN-001", "DOMAIN-002", "DOMAIN-003"} <= set(seen))

    def test_editing_the_mode_by_hand_is_caught_by_the_lock_check_when_invalid(self):
        target = self.tmp / "app"
        magrathea.new_project(target, "App", "java-service", "", "@me", None)
        config = self.config(target)
        config["infra_mode"] = "domain"  # no domain name
        (target / "magrathea.json").write_text(json.dumps(config))
        self.assertNotEqual(project_script(target, "magrathea_lock.py", "verify").returncode, 0)


class JavaServiceStackTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name) / "svc"
        magrathea.new_project(self.target, "Orders Svc", "java-service", "A service.", "@me", None)

    def tearDown(self):
        self._tmp.cleanup()

    def read(self, rel):
        return (self.target / rel).read_text()

    def test_files_and_rendering(self):
        for rel in [
            "app/pom.xml", "app/Dockerfile", "app/.dockerignore", "app/Healthcheck.java", "app/service.yaml",
            "app/README.md", "app/src/main/resources/application.properties",
            "app/src/main/java/com/example/app/Application.java",
            "app/src/main/java/com/example/app/HelloController.java",
            "app/src/test/java/com/example/app/HelloControllerTest.java",
            ".github/workflows/service.yml", ".github/workflows/local-setup.yml", "docs/adr/0001-stack.md",
        ]:
            self.assertTrue((self.target / rel).exists(), rel)
        for path in self.target.rglob("*"):
            if path.is_file() and ".magrathea" not in path.parts:
                self.assertNotRegex(path.read_text(encoding="utf-8", errors="ignore"), r"@@\w+@@", str(path))
        self.assertIn("<artifactId>orders-svc</artifactId>", self.read("app/pom.xml"))
        self.assertIn("name: orders-svc", self.read("app/service.yaml"))

    # Checks as functions on text, so each can be shown to fail on a mutated input.
    @staticmethod
    def dockerfile_problems(text):
        problems = []
        froms = [l.split()[1] for l in text.splitlines() if l.startswith("FROM ")]
        if len(froms) < 2:
            problems.append("not multi-stage")
        for image in froms:
            if ":" not in image or image.endswith(":latest"):
                problems.append("unpinned image " + image)
        user = [l.split()[1] for l in text.splitlines() if l.startswith("USER ")]
        if not user or user[-1] in ("root", "0"):
            problems.append("no non-root USER")
        for needle in ("HEALTHCHECK", "MaxRAMPercentage"):
            if needle not in text:
                problems.append("missing " + needle)
        if not froms or "jre" not in froms[-1]:
            problems.append("runtime is not a JRE image")
        return problems

    @staticmethod
    def service_yaml_problems(text):
        problems = []
        image = [l for l in text.splitlines() if l.startswith("image:")]
        value = image[0].split("#")[0].split(":", 1)[1].strip() if image else ""
        if ":" not in value or value.endswith(":latest"):
            problems.append("image not pinned")
        if not re.search(r"limits:\s*\n\s+memory:", text):
            problems.append("no memory limit")
        return problems

    @staticmethod
    def workflow_problems(text):
        problems = []
        top = text.split("\njobs:")[0]
        if not re.search(r"^permissions:\n  contents: read$", top, re.M):
            problems.append("no workflow-level read-only permissions")
        if text.count("packages: write") != 1 or "packages: write" in top:
            problems.append("packages: write must be only on the image job")
        if ":latest" in text or "GITHUB_SHA" not in text:
            problems.append("tag is not the sha")
        if "tr '[:upper:]' '[:lower:]'" not in text:
            problems.append("owner not lowercased")
        if "github.event.repository.default_branch" not in text or "github.event_name == 'push'" not in text:
            problems.append("push not limited to the default branch")
        if "${{ secrets" in text.split("run: |")[-1] or "${{ github.actor" in text.split("run: |")[-1]:
            problems.append("secret or actor inline in a run script")
        return problems

    def test_dockerfile_follows_container_standards(self):
        text = self.read("app/Dockerfile")
        self.assertEqual(self.dockerfile_problems(text), [])
        for bad in [
            text.replace("eclipse-temurin:25.0.4.1_1-jre-noble", "eclipse-temurin:latest"),
            text.replace("USER 10001", "USER root"),
            text.replace("USER 10001\n", ""),
            text.replace("HEALTHCHECK", "#"),
        ]:
            self.assertNotEqual(self.dockerfile_problems(bad), [])

    def test_service_contract_meets_k8s_005_006(self):
        text = self.read("app/service.yaml")
        self.assertEqual(self.service_yaml_problems(text), [])
        self.assertNotEqual(self.service_yaml_problems(text.replace("image: TODO-registry/orders-svc:0.1.0", "image: x/orders-svc:latest")), [])
        self.assertNotEqual(self.service_yaml_problems(text.replace("    memory: 512Mi", "    cpu: 1")), [])
        self.assertIn("readOnlyRootFilesystem", text)

    def test_ci_workflow(self):
        text = self.read(".github/workflows/service.yml")
        self.assertEqual(self.workflow_problems(text), [])
        self.assertIn("ghcr.io", text)
        self.assertNotEqual(self.workflow_problems(text.replace("permissions:\n  contents: read\n\n", "", 1)), [])
        self.assertNotEqual(self.workflow_problems(text.replace("tr '[:upper:]' '[:lower:]'", "cat")), [])
        self.assertNotEqual(self.workflow_problems(text.replace("github.event.repository.default_branch", "x")), [])
        self.assertNotEqual(self.workflow_problems(text.replace('"$REGISTRY_TOKEN"', '"${{ secrets.GITHUB_TOKEN }}"')), [])

    def test_unsafe_name_does_not_reach_xml_or_java(self):
        import xml.etree.ElementTree as ET
        target = Path(self._tmp.name) / "odd"
        magrathea.new_project(target, 'A&B <x> "q"', "java-service", "", "@me", None)
        ET.parse(str(target / "app/pom.xml"))  # raises if not well-formed
        for rel in ["app/src/main/java/com/example/app/HelloController.java",
                    "app/src/test/java/com/example/app/HelloControllerTest.java"]:
            self.assertNotRegex((target / rel).read_text(), r'[&<]x|"q"')
            self.assertIn("Hello from a-b-x-q", (target / rel).read_text())

    def test_fresh_project_verifies_and_is_in_sync(self):
        self.assertEqual(project_script(self.target, "magrathea_lock.py", "verify").returncode, 0)
        self.assertEqual(project_script(self.target, "sync_agents.py", "--check").returncode, 0)


if __name__ == "__main__":
    unittest.main()
