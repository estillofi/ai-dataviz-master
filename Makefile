# Необязательный: все команды можно запускать напрямую (см. docs/BUILD-GUIDE.md)
PY ?= python3

.PHONY: test lint validate-example bundle clean

test: lint
	$(PY) -m unittest discover -s tests -p "test_*.py"

lint:
	$(PY) tests/lint_kit.py

validate-example:
	$(PY) tools/validate_skill.py 02-references/examples/acme-dataviz

bundle:
	$(PY) tools/bundle_single_file.py --styles yau,nyt

clean:
	rm -rf dist __pycache__ tests/__pycache__ tools/__pycache__
