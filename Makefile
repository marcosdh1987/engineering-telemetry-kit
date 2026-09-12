.PHONY: install-dev lint typecheck test package check

install-dev:
	python -m pip install -e .[dev]

lint:
	ruff check src tests

typecheck:
	mypy src

test:
	pytest

package:
	python -m build

check: lint typecheck test package
