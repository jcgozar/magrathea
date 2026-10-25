# 0010. GitLab and GitLab CI support

Status: **Accepted** (2026-10-25, accepted by the human, who agreed with the recommendations in
the earlier proposed version of this ADR, after independent review), **in progress**. **Nothing is
built.** The implementation follows the "Order of work" below; the status of each step is recorded
there. Until a step lands, every generated project targets GitHub, as today. Each step that lands
updates `AGENTS.md` ("Current state"), `docs/guide/` and the example (`tools/test_examples.py`) in
the same change. One decision is still open and blocks no step: whether Magrathea later ships a
supported fallback for GitLab tiers below Premium (Open item 1).

## Context

Teams that will use Magrathea run GitLab and GitLab CI. Magrathea was written for GitHub. The
workflow text, the CI files and several scripts assume it. The inventory below comes from a grep
of `base/`, `templates/`, `tools/` and `meta/` for `gh`, GitHub, `.github`, CODEOWNERS, pull
request and `mode-migration`. Where the table says "GitLab: TODO", the GitLab behaviour has not
been checked and must be verified by a human before anything is built on it. Line numbers were
re-checked against the repository on 2026-10-25 and drift as files change.

### What is GitHub-specific today

| # | Where | What it assumes | Kind |
| --- | --- | --- | --- |
| 1 | `templates/project/.github/workflows/ci.yml` | GitHub Actions: `actions/checkout`, `setup-opa`, `github.event_name`, `github.base_ref`, `github.event.pull_request.labels`, `$RUNNER_TEMP`, `pull_request` event types `labeled`/`unlabeled` | CI file |
| 2 | `templates/stacks/*/files/.github/workflows/` (`service.yml`, `api.yml`, `web.yml`, `local-setup.yml`) | GitHub Actions; `service.yml` pushes to `ghcr.io/<owner>/...` with `GITHUB_TOKEN`, `GITHUB_REPOSITORY_OWNER`, `GITHUB_SHA` | Stack CI files, registry |
| 2a | `templates/stacks/java-service/`: `stack.json` (summary, "pushed to ghcr.io by CI"), `notes.md` (lines 12-13), `files/app/service.yaml` (lines 4, 5, 8), `files/docs/adr/0001-stack.md` (line 13) | The image registry is `ghcr.io/<owner>/<slug>:<git sha>` in text the project owns | Stack text, registry |
| 3 | `base/agents/personas/reviewer.md` (Decide, steps 2, 4, 5) | `gh pr checks`, `gh pr review --approve`, `gh pr merge --squash --delete-branch`, `gh pr comment`, the `needs-human-review` label | Persona text |
| 4 | `base/claude/commands/review.md`, `feature.md`, `request-standard.md` | "pull request" wording; `request-standard` says "open an issue or PR on the Magrathea repo" | Command text |
| 5 | `base/agents/personas/iac-reviewer.md` (line 36: a mode change is a blocker unless the pull request carries the `mode-migration` label), `base/scripts/magrathea_lock.py` (line 196, the message "Label the pull request `mode-migration`..."), `base/standards/domain-platform.md` (DOMAIN-003) | the pull request label `mode-migration` marks an approved mode migration | Mode-change control (ADR 0009) |
| 6 | `templates/project/.github/CODEOWNERS`, `base/standards/README.md` (`../.github/CODEOWNERS`), `base/review/risk.json` (`.github/**` in `high_paths`), `base/agents/personas/security.md`, `AGENTS.md` and `base/docs/WORKFLOW.md` ("CODEOWNERS, branch protection and CI are the real enforcement", line 105), `base/agents/personas/security.md` (line 49: "CODEOWNERS requires a human to approve them"), `templates/project/.github/workflows/ci.yml` (line 22 comment), `base/scripts/magrathea_lock.py` (line 24 docstring), `base/scripts/check_paths.py` (line 10 docstring), `base/standards/README.md` (line 28) | GitHub's CODEOWNERS location and syntax, GitHub branch protection | Ownership and enforcement |
| 7 | `base/docs/WORKFLOW.md`, `base/README.md`, `templates/project/AGENTS.md`, `README.md`, `evals/README.md`, `base/standards/README.md` ("blocks the PR") | "pull request" / "PR" wording | Wording only |
| 8 | `templates/project/.github/workflows/ci.yml` header, `scripts/magrathea_sync.py`, ADR 0006 | The base is fetched with `git clone` from the `source` in `magrathea.json`; a private repo needs a token in CI | Base fetch |
| 9 | `templates/stacks/domain-platform/files/.github/ISSUE_TEMPLATE/capacity-request.md` and its notes (ADR 0009) | GitHub issue templates | Request path |
| 10 | `tools/magrathea.py`, `tools/magrathea_cli.py`, `meta/commands/new-project.md` | `--owner` default `@your-github-handle`; prompt "Owner (GitHub handle)"; the next-step message names `.github/CODEOWNERS`; `tools/magrathea_cli.py` line 24 ("The CLI stores no model or GitHub tokens") | Generator |
| 11 | `base/policy/kyverno/k8s-006-images.yaml` | Approved registries include a `ghcr.io/<OWNER>/*` placeholder | Policy placeholder |
| 12 | `base/standards/local-setup.md` (SETUP-006) | The per-stack CI template is `.github/workflows/local-setup.yml` | Standard text |
| 13 | `tools/test_magrathea.py` (lines 39, 55, 270, 300, 377, 454), `tools/test_examples.py` (line 36) | Tests assert `.github/CODEOWNERS`, `.github/workflows/*.yml` and `.github/ISSUE_TEMPLATE/` paths. They stay valid for `github`; GitLab needs its own cases | Tests |
| 14 | `base/agents/personas/architecture-reviewer.md` (line 3: "every pull request"), `templates/stacks/domain-platform/notes.md` (line 13: "no pull request is...") | "pull request" wording | Wording only |

Already provider-neutral, and to be kept so: `Makefile` targets (`setup`, `upgrade`, `test`,
`check`, `verify`, `sync`), `base/scripts/` (sync, lock, `review_risk.py`, `check_paths.py`,
`sync_agents.py`), the Rego and Kyverno policies, `magrathea_lock.py mode-change` and `mode-data`.
The scripts take their inputs as arguments, not from a CI provider's environment.

## Decision

The human accepted the direction on 2026-10-25. The sections below are decided unless marked
Open. Where a section depends on a GitLab capability that is unverified, it says so and the
dependent step in "Order of work" carries it as a precondition.

**GitLab tier is the user's choice (decided 2026-10-25).** Magrathea is used by many teams, so
this ADR makes no assumption about any one team's GitLab edition. GitLab support targets users on
GitLab Premium or higher, where the CODEOWNERS-based controls exist (see the note below). A user on
a lower tier chooses their own substitute control and accepts what it does not enforce; Magrathea
does not claim the CODEOWNERS control there. Whether Magrathea later ships a supported fallback for
lower tiers is Open item 1.

**Note (2026-10-25): code ownership on GitLab is a Premium-tier feature.** GitLab's documentation
labels Code Owners, the protected-branch setting "Require approval from code owners", and merge
request approval rules as Tier: Premium, Ultimate (docs.gitlab.com, pages for Code Owners,
protected branches and approval rules; read 2026-10-25, tier labels only, not tested on an
instance). Protected branches with role-based push and merge restrictions are labelled Free,
Premium, Ultimate. So the CODEOWNERS control that ADRs 0004, 0005, 0006 and 0009 rely on is
available on GitLab only at Premium or higher. Whether the open-source Community build differs
from the Free tier was not checked. Re-check the labels against current docs before building.

### 1. The CI provider is a choice, with GitHub as the default

- A new option `ci` on `magrathea new` (and `new-domain`, and an interactive prompt in
  `magrathea_cli.py`), with values `github` (default) and `gitlab`.
- `magrathea.json` gets an **optional** field `ci`. Absent means `github`. Same compatibility rule
  as `infra_mode` in ADR 0009: `make upgrade` never adds or changes it, so existing projects are
  unchanged and nothing silently starts targeting GitLab.
- Changing `ci` later is a migration of the project's CI files, done by hand and reviewed. Magrathea
  provides no tool for it. `magrathea.json` is already under CODEOWNERS and in `high_paths`, so the
  edit is high risk.
- Validation of the value joins the lock check (the place DOMAIN-002 validates the other fields).
  The rule ID is TODO and is chosen when built; it must not collide with any ID in base or any
  distribution (ADR 0007). `ci` is allowed on both the `project` and `domain-platform` types, so
  the DOMAIN-002 validation is extended to accept it for both.

### 2. CI files are thin callers; the logic stays in the Makefile and scripts

Everything a CI job does must be a `make` target or a script in `.magrathea/scripts/`, which both
providers call. The provider file only: checks out, installs tools (`opa`, `conftest`), passes
provider-specific inputs (the target branch, whether this is a merge request, whether the
approval label is present) as arguments or environment variables, and runs targets. Consequences:

- The inline shell in the GitHub `ci.yml` (the `mode-change` step: `git fetch`, `git show`,
  `$RUNNER_TEMP`) moves into a `make` target or script that takes `--base-ref` and `--approved`.
  This is a refactor of the GitHub file as well, and is the first step so the GitHub file is the
  reference the GitLab file is compared with.
- There is one place to fix a check, and the two provider files cannot drift in what they check.
  A test that parses both rendered files and asserts they call the same targets is planned
  (see "Order of work").

### 3. Render `.gitlab-ci.yml` calling the same targets

When `ci` is `gitlab`, the project gets `.gitlab-ci.yml` (and not `.github/`). Stack CI files
(`service.yml`, `api.yml`, `web.yml`, `local-setup.yml`) get a GitLab equivalent under
`templates/stacks/<stack>/files/` selected by `ci`. The CODEOWNERS file location per provider is TODO (verify against GitLab's documentation). The layout of stack files by provider
(for example `files/github/` and `files/gitlab/` roots, or a per-file provider suffix) is a build
detail left to the first stack that is ported. Jobs, `rules:` for merge requests and the default
branch, runner image and caching: **TODO, to be written and checked against GitLab's documentation
when built.** This ADR does not assert GitLab CI syntax.

### 4. What each item becomes on GitLab

"TODO verify" means a human must check GitLab's documentation or a real instance. Nothing below
is a claim about GitLab.

| # | On GitLab (decided direction; details TODO) | Verify |
| --- | --- | --- |
| 1, 2 | `.gitlab-ci.yml` per above. The registry for `service.yml` is ECR (decided), not the GitLab container registry or ghcr.io. | TODO verify the predefined CI variables used for the image name, tag and registry login |
| 3 | The reviewer persona must check pipeline status, approve, merge and comment on a merge request. Tool: `glab` (the GitLab CLI; decided). `curl` against the GitLab REST API is the fallback if `glab` is unsuitable. The persona names the action, the provider notes give the command (section 5). | TODO verify `glab mr` subcommands and flags, the API calls, and the token scope an agent needs |
| 4 | Wording changes per section 5. `request-standard` says "open an issue or merge request on the Magrathea repo". | none |
| 5 | The mode-migration marker becomes a merge request label named `mode-migration` (decided); the approval control behind it is Open item 1. The check in CI needs the labels of the current merge request. `magrathea_lock.py mode-change --approved` is unchanged: the provider file decides how to compute the flag. | TODO verify that labels are available to merge request pipelines, and whether re-running when a label changes is possible (the GitHub file relies on `labeled`/`unlabeled` events) |
| 6 | Branch protection becomes protected branches plus required approvals. Code ownership: TODO verify: GitLab has its own CODEOWNERS file support. GitLab's docs label Code Owners and required code-owner approval Premium and Ultimate (see the note in the Decision section); below Premium they are not provided. Location, syntax and enforcement may differ from GitHub's. The template must render the file for the chosen provider (path and owner syntax), and `high_paths` in `base/review/risk.json` must include the GitLab CI file and CODEOWNERS location while keeping `.claude/**` and `scripts/**` (both already in `high_paths`) and `.github/**` for GitHub projects. | TODO verify CODEOWNERS file location and section syntax, whether required approval from code owners works as documented on a Premium instance, and how users and groups are written. See Open item 1 |
| 7 | Wording per section 5. | none |
| 8 | `magrathea_sync.py` clones with `git`, so a private GitLab base repo works if CI can authenticate. The unauthenticated-clone case is the only one tested today (local path and git sources in tests; ADR 0006 and `AGENTS.md` say a private GitHub repo is untested). On GitLab the CI job needs a token or a project access mechanism for a repo other than its own. | TODO verify the mechanism (job token allow-list, deploy token or project access token) and the git URL form. **Untested** |
| 9 | The domain platform's capacity request becomes a GitLab issue template in the domain platform repository (`.gitlab/issue_templates/`). | TODO verify directory and file format |
| 10 | The owner prompt becomes provider-aware: "Owner (GitLab username or group)" when `ci` is `gitlab`. The default placeholder follows. | none |
| 11 | The registry placeholder in the Kyverno policy keeps working for ECR; a GitLab registry host would be a different placeholder. Approved registries stay a project decision. | none |
| 12 | SETUP-006 text says "the CI template for the provider, per stack". | none |

### 5. How a tool-neutral persona says "merge" per provider

ADR 0004 keeps personas tool-neutral and puts tool-specific text in thin generated layers. The
reviewer persona today contains `gh` commands, which is already a gap against that ADR. Proposed:

- The reviewer persona names **actions**, not commands: *check pipeline status of the change,
  approve it, merge it (squash, delete the branch), comment on it, add the `needs-human-review`
  label if it exists*.
- The commands for each action live in a short, provider-keyed section of `base/docs/WORKFLOW.md`
  (decided: a new `base/docs/PROVIDERS.md`), one subsection per provider. The persona is told to
  read the subsection for the `ci` value in `magrathea.json`, defaulting to `github`. The commands
  go in a new `base/docs/PROVIDERS.md` (decided), so `WORKFLOW.md` stays about the flow. The
  reviewer's tool on GitLab is `glab` (decided; TODO verify its subcommands).
- "Pull request" stays in the persona and workflow text as the generic term, with one sentence
  saying "merge request on GitLab". This avoids a rewrite of every file for wording alone. A
  per-provider rewrite of the wording was considered and rejected as churn for no behaviour change.
- `review_risk.py gate` is unchanged. It already takes `--ci success|failure|pending` as an
  argument and has no provider dependency.

Moving the commands out of the persona has a cost: the merge path now depends on the persona
finding and reading the right subsection. Whether the personas follow their instructions has not
been evaluated (`AGENTS.md`). The reviewer's merge behaviour must therefore be re-checked after
the change on GitHub first, and on GitLab separately; "word for word" below applies to the
commands, not to proof that the persona uses them.

Four texts carry the mode-migration gate and `MUST`-level wording: DOMAIN-003, `iac-reviewer.md`
line 36, the `magrathea_lock.py` line 196 message, and the reviewer persona's gate text. Each
needs **explicit human approval** when changed, and the check strength must be unchanged: same
conditions block, same conditions pass.

Changing the reviewer persona changes a base file. It is a base change: version bump, changelog,
and the existing GitHub behaviour is preserved (the `github` subsection holds today's `gh`
commands word for word).

### 6. The domain-platform mode-change control must work on GitLab

ADR 0009's control has three parts: CODEOWNERS on `magrathea.json`, the CI check
(`mode-change`) that fails unless the change is marked as an approved migration, and the
`iac-reviewer` escalation. On GitLab:

- the CI check is the same script, called from `.gitlab-ci.yml` with the previous
  `magrathea.json` from the merge base and the approval flag;
- the CI check **must run for merge requests and must not be skippable by a direct push to the
  default branch**, so protected-branch settings that forbid direct pushes are required. This is
  the same caveat the GitHub file already states;
- **precondition:** the control is only as strong as required code-owner approval on
  `magrathea.json`, which GitLab labels Premium and Ultimate (see the note in the Decision
  section; not tested on an instance). On a lower tier this control is not provided. Until it is
  verified on a Premium instance, this section describes the intended design, not a control that
  can be relied on;
- the marker is a merge request label named `mode-migration` (decided, for parity with GitHub), with
  CODEOWNERS approval as the real control, as in ADR 0009. TODO verify that labels reach merge
  request pipelines before relying on it. **The label alone is not an approval**: anyone who can
  set a label could set it;
- DOMAIN-003 in `domain-platform.md` says "pull request" and the label `mode-migration`. When
  built, its wording is made neutral (decided: neutral wording, meaning unchanged).
  Loosening the rule is not proposed: this is a wording and mechanism change that needs the human's
  approval of the exact text because it touches a `MUST` rule.

### 7. Base fetch from a private GitLab repo

Out of scope to solve here, in scope to document. ADR 0006 already says a private Magrathea repo
needs a token in the CI job. For GitLab, the generated `.gitlab-ci.yml` carries a TODO comment
naming the same need. The mechanism is TODO verify (item 8). The first built version states "never
run" in its header, as the GitHub file does.

## Alternatives considered

1. **GitHub only; GitLab teams adapt the output by hand.** Cheapest. Rejected because the stated user runs GitLab, and hand-adapting `ci.yml` and the reviewer's `gh`
   commands would drift from the base on every `make upgrade`.
2. **A single abstract CI definition that renders to both** (a Magrathea-owned pipeline DSL).
   Rejected: a new language to maintain and test, and the logic is already in the Makefile and
   scripts, so a thin file per provider is enough.
3. **Distribution-only (ADR 0007): a GitLab distribution replaces `ci.yml` and the reviewer
   persona.** Works today with no engine change. Accepted as the stopgap while steps 2 to 6 are
   built (decided). Rejected as the main route because GitLab is expected to be common, and a replaced reviewer persona would
   duplicate the provider-neutral parts and track base changes by hand. A distribution can still
   add providers beyond these two.
4. **Per-provider rewrite of "pull request" wording.** Rejected, see section 5.
5. **Provider as a stack property.** Rejected: CI provider is orthogonal to the stack
   (`java-service` on GitHub or GitLab), so it would double the stack count.

## Consequences

- A GitLab project and a GitHub project run the same checks, from the same targets and scripts.
- The base gains a provider section and the reviewer persona changes; every project receives
  that on `make upgrade`. Behaviour for GitHub projects must be identical.
- More to test and more that cannot be tested here: no GitLab instance or runner is available in
  the build sandbox (assumed; TODO confirm). Rendering will be tested; execution will not be.
- Two sets of CI files per stack to keep in step. The same-targets test limits drift but does not
  prove equivalent behaviour.
- The mode-migration control depends on provider features (labels or approval rules, protected
  branches) that must be configured by a human outside the repository; Magrathea cannot check they
  are on.
- On GitLab tiers below Premium, required code-owner approval is not available, so the CODEOWNERS
  control that ADR 0004, 0005, 0006 and 0009 rely on has no equivalent there. Magrathea does not
  provide one; the user chooses a substitute (Open item 1 covers a supported fallback). Any
  substitute may make the mode-migration marker weaker than on GitHub.

## Backward compatibility

- `ci` is optional; absent means `github`. No existing `magrathea.json` changes. `make upgrade`
  does not add it.
- The current signature is `new_project(target, name, stack, description, owner, context_file,
  source=None, ref=None, distro=None, domain=None)` (`tools/magrathea.py` line 143), and
  `magrathea_cli.py` passes up to `distro` and `domain` positionally (lines 419-421). `ci` is added
  **after `domain`**, keyword-only and defaulted (`*, ci="github"` or equivalent), so no existing
  positional call changes meaning. `list_stacks(distro=None)` is unchanged. `ci` is accepted for
  both the project and the domain-platform types.
- ADR 0007: a distribution file replaces the upstream file at the same path and may not define a
  rule ID that upstream defines. Provider-specific files must have distinct paths per provider so a
  distribution can replace one without the other. A new rule ID for validating `ci` must not collide
  with any distribution's. Distributions that replace `.github/workflows/ci.yml` keep working for
  `ci: github`.
- The reviewer persona's `github` behaviour is preserved word for word.
- The refactor of the inline `mode-change` step changes a project-owned template file
  (`templates/project/`). Existing projects keep their copy; only new projects get it. The base
  scripts they call are unchanged in interface (additions only).

## Order of work

None of this is done. Two steps carry a **precondition**: they must not start until the GitLab
capability they depend on has been verified and Open item 1 is decided.

1. Decided items recorded (this ADR). Open item 1 remains for the human.
2. Refactor the GitHub `ci.yml` so each step is a `make` target or script call; add a test that
   the rendered file calls only targets that exist. No behaviour change. Engine bump.
3. Add `ci` to `new_project`, `new-domain`, the CLI prompt and `magrathea.json`; validate it;
   render `.github/` only for `github`. Tests for the flags-only path, the absent field, and
   `make upgrade` not touching it. Engine bump.
4. Provider-neutral reviewer persona and a provider section in the workflow doc, `github`
   subsection first (identical behaviour). Base bump and changelog.
5. `.gitlab-ci.yml` and CODEOWNERS for GitLab for the project template; same-targets test.
   **Precondition:** the GitLab capabilities in "Tested and untested" are verified on a GitLab
   Premium instance, in particular CODEOWNERS and required code-owner approval. Without that the
   file can be rendered but the control it names is not shown to work. Open item 1 (a fallback for
   lower tiers) does not block this step. The `.gitlab-ci.yml` part alone does not depend on it.
6. Port one stack's CI (`java-service`) to GitLab; then the others.
7. GitLab subsection of `PROVIDERS.md`, the mode-change marker, and DOMAIN-003 wording (needs human
   approval of the exact text; also `iac-reviewer.md` line 36 and the `magrathea_lock.py` message).
   **Precondition:** the same as step 5. The marker is not shipped as a control until the approval
   behind it is verified on a Premium instance.
8. Domain-platform issue template for GitLab.
9. Verify on a real GitLab Premium instance. Until then everything GitLab is "rendered, never run".

## Tested and untested (planned)

- Planned to test: option parsing and validation, rendering of the right CI files per `ci`, absent
  field means GitHub, `make upgrade` leaves `ci` alone, both provider files call the same targets,
  `new_project`/`list_stacks` positional compatibility, the provider-keyed reviewer text exists for
  every provider the validator accepts.
- GitLab capabilities to verify against current GitLab documentation **and the actual instance**
  before building (none verified; tier labels read from the docs only, nothing run on an instance): required code-owner
  approval; approval rules; CODEOWNERS support and enforcement; protected-branch push and merge
  settings; MR labels reaching the pipeline and a label change re-triggering it; merge request
  pipelines and "pipelines must succeed"; the token scope an agent needs to approve and merge via
  the API.
- Not testable here: a GitLab pipeline run, `glab` and API commands, the merge-request label flow,
  CODEOWNERS enforcement, protected branches, the private base fetch on GitLab, the container
  registry login.

## What changes when built

- `docs/guide/`: `01-getting-started.md` (the `ci` option and prompts), `02-using-a-project.md`
  (reviewer merges, CI), `03-customizing.md` (providers and distributions), `05-reference.md`
  (`magrathea.json` fields, CLI options), `06-faq.md`, `07-domain-platform.md` (mode-migration
  marker per provider), `04-sample-projects.md` if a GitLab sample is added.
- `AGENTS.md`: "Current state" (what is tested and not), the layout note about templates by
  provider, and the Rules section if a provider rule is added.
- `tools/test_examples.py`: a GitLab-rendered example project that generates and verifies, and
  the existing example unchanged.
- `tools/test_magrathea.py` and `tools/test_examples.py`: the tests that assert `.github` paths
  (inventory item 13) keep passing for `github`; add GitLab cases beside them.
- `templates/stacks/java-service/` text naming `ghcr.io` (item 2a) for GitLab projects (ECR).
- `base/`: reviewer, iac-reviewer, commands, `WORKFLOW.md` or a providers doc, `risk.json`
  (`high_paths` for the GitLab CI and CODEOWNERS files), `domain-platform.md` wording,
  `magrathea_lock.py` message text; `base/VERSION`, `CHANGELOG.md`; `VERSION`,
  `ENGINE_CHANGELOG.md` for `tools/` and `templates/project/`.

## Decided (2026-10-25, accepted by the human)

- **Direction**: a `ci` option, `github` default; absent in `magrathea.json` means `github`;
  `make upgrade` never adds or changes it.
- **Thin CI callers**: logic stays in the Makefile and scripts.
- **Mode-migration marker on GitLab**: a merge request label, for parity with GitHub, with CODEOWNERS
  approval as the real control (see Open item 1), after verifying that labels reach merge request
  pipelines.
- **Reviewer's tool on GitLab**: `glab`.
- **Provider commands**: a new `base/docs/PROVIDERS.md`.
- **Container registry on GitLab**: ECR.
- **DOMAIN-003**: neutral wording, meaning unchanged (exact text still needs human approval).
- **Distribution (alternative 3)** is the stopgap while steps 2 to 6 are built.
- **GitLab tier is the user's choice**: GitLab support targets users on Premium or higher, where
  the CODEOWNERS-based controls exist. Lower tiers pick their own substitute. No assumption about
  any one team's edition.

## Open

1. **Does Magrathea later ship a supported fallback control for users on GitLab tiers below
   Premium** (where required code-owner approval is unavailable)? Not needed for the Premium
   path and not decided here. Candidates if wanted: a CI job that fails unless a named human's
   approval is recorded; a protected branch where only humans merge with `auto_merge` off; an
   external gate. Any of them may be weaker than the GitHub control. Places that depend on the
   CODEOWNERS control:
   - ADRs: 0004 (lines 23, 30), 0005 (lines 27, 44), 0006 (line 42), 0009 (lines 120, 128, 290,
     355), and this ADR (table rows 5 and 6, section 6, Consequences, this Open list).
   - Outside the ADRs: `base/docs/WORKFLOW.md` line 105, `base/agents/personas/security.md` line
     49, `templates/project/.github/CODEOWNERS`, the comment at
     `templates/project/.github/workflows/ci.yml` line 22, `base/scripts/magrathea_lock.py` line
     24, `base/scripts/check_paths.py` line 10, `base/standards/README.md` line 28.

   Candidate fallbacks, listed without a choice:
   - a CI job that fails unless a named human's approval is recorded (needs an API token and a check
     of the approver's identity);
   - a protected default branch where only humans merge and `auto_merge` is off, which removes the
     reviewer persona's merge power on GitLab;
   - an external gate (outside the repository and GitLab settings).

   Any fallback may make the mode-migration marker in ADR 0009 weaker than on GitHub, and the label
   alone is not an approval. Steps 5 and 7 wait on this.
