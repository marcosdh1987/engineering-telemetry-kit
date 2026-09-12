.PHONY: install-dev lint typecheck test check

install-dev:
	python -m pip install -e .[dev]

lint:
	ruff check src tests

typecheck:
	mypy src

test:
	pytest

check: lint typecheck test
