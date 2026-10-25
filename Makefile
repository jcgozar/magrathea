.PHONY: test sample sync

# All tests: base scripts, the generator, and the base Rego policies (needs `opa`).
test:
	python3 -m unittest discover -s base/scripts -p 'test_*.py'
	cd tools && python3 -m unittest discover -p 'test_*.py'
	opa test base/policy/conftest

# Regenerate Magrathea's own .claude/ agents and commands from meta/.
sync:
	python3 base/scripts/sync_agents.py --root . --personas-dir meta/personas --commands-dir meta/commands --local-dir "" --scripts-dir base/scripts

# Generate a throwaway project and verify it.
sample:
	rm -rf .scratch/sample && mkdir -p .scratch
	rm -rf .scratch/sample-java
	python3 tools/magrathea.py new .scratch/sample-java --name "Sample Java" --stack java-service --description "Sample Java service"
	cd .scratch/sample-java && python3 .magrathea/scripts/magrathea_lock.py verify && python3 .magrathea/scripts/sync_agents.py --check
	python3 tools/magrathea.py new .scratch/sample --name "Sample" --stack react-java --description "Sample project"
	cd .scratch/sample && python3 .magrathea/scripts/magrathea_lock.py verify && python3 .magrathea/scripts/sync_agents.py --check
	rm -rf .scratch/sample-domain .scratch/sample-attached
	python3 tools/magrathea.py new-domain .scratch/sample-domain --name "Sample Domain"
	cd .scratch/sample-domain && python3 .magrathea/scripts/magrathea_lock.py verify && python3 .magrathea/scripts/sync_agents.py --check
	python3 tools/magrathea.py new .scratch/sample-attached --name "Sample Attached" --stack java-service --domain sample-domain
	cd .scratch/sample-attached && python3 .magrathea/scripts/magrathea_lock.py verify && python3 .magrathea/scripts/sync_agents.py --check
	rm -rf .scratch/acme-site
	python3 tools/magrathea.py new .scratch/acme-site --distro examples/acme-platform --name "Acme Site" --stack static-site
	cd .scratch/acme-site && python3 .magrathea/scripts/magrathea_lock.py verify && python3 .magrathea/scripts/sync_agents.py --check
	python3 base/scripts/sync_agents.py --root . --personas-dir meta/personas --commands-dir meta/commands --local-dir "" --scripts-dir base/scripts --check
