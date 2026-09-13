.PHONY: install-dev format format-check lint typecheck test package check

install-dev:
	python -m pip install -e .[dev]

format:
	ruff format src tests
	ruff check --fix src tests

format-check:
	ruff format --check src tests

lint: format-check
	ruff check src tests

typecheck:
	mypy src

test:
	pytest

package:
	python -m build

check: lint typecheck test package
