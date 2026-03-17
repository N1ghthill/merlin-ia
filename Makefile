.PHONY: install-dev test compile smoke

install-dev:
	python3 -m pip install -r requirements.txt -r requirements-dev.txt

test:
	python3 -m pytest -q tests/

compile:
	python3 -m compileall merlin_cli.py merlin_api.py rag_indexer.py executor merlin

smoke:
	bash tests/smoke_cli.sh
