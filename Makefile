.PHONY: test smoke

test:
	python3 -m pytest -q

smoke:
	bash tests/smoke_cli.sh
