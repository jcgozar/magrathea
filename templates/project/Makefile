.PHONY: setup upgrade test check fmt verify sync diagrams

# Fetch the Magrathea base at the pinned version into .magrathea/. Run after cloning.
setup:
	python3 scripts/magrathea_sync.py

# Move to the newest base for the configured ref (or: python3 scripts/magrathea_sync.py --update --ref v0.2.0).
upgrade:
	python3 scripts/magrathea_sync.py --update
	python3 .magrathea/scripts/sync_agents.py
	python3 .magrathea/scripts/magrathea_lock.py verify

# Unit-test the Rego policies, base and local (needs `opa`).
test:
	opa test .magrathea/policy/conftest local/policy -v

fmt:
	opa fmt -w local/policy

# Check a real plan against the base and local policies (needs `conftest`).
#   tofu plan -out tfplan && tofu show -json tfplan > plan.json
#   make check PLAN=plan.json
# The mode (standalone or domain, ADR 0009) comes from magrathea.json through a data file; for a
# project with no mode fields it says standalone and the domain checks do nothing.
check:
	python3 .magrathea/scripts/magrathea_lock.py mode-data --out .mode.json
	conftest test --policy .magrathea/policy/conftest --policy local/policy \
		--namespace main --namespace local --data .mode.json $(PLAN)

# Confirm the Magrathea base is untouched and local additions are valid.
verify:
	python3 .magrathea/scripts/magrathea_lock.py verify

# Regenerate .claude/agents and .claude/commands after editing local/personas/.
sync:
	python3 .magrathea/scripts/sync_agents.py

# Render docs/trd/*.puml to SVG next to the source (output is git-ignored). Optional: needs
# `plantuml` on PATH. If it is missing, this prints a message and skips (exit 0); run
# `make diagrams REQUIRE=1` to fail instead.
diagrams:
	@if ! command -v plantuml >/dev/null 2>&1; then \
		echo "plantuml not found: skipping diagram rendering (install it, or run with REQUIRE=1 to fail)."; \
		[ -z "$(REQUIRE)" ]; \
	else \
		files=$$(ls docs/trd/*.puml 2>/dev/null); \
		if [ -z "$$files" ]; then echo "no docs/trd/*.puml files to render."; \
		else plantuml -tsvg $$files; fi; \
	fi
