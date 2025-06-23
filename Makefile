.PHONY: help venv install run test lint format clean setup-secrets

PYTHON=python
PIP=pip
VENV=.venv
ACTIVATE=. $(VENV)/bin/activate

help:
	@echo "Yuga Planner Makefile"
	@echo "Available targets:"
	@echo "  venv            Create a Python virtual environment"
	@echo "  install         Install all Python dependencies"
	@echo "  run             Run the Gradio app locally"
	@echo "  test            Run all tests with pytest"
	@echo "  lint            Run pre-commit hooks (includes black, yaml, gitleaks)"
	@echo "  format          Format code with black"
	@echo "  setup-secrets   Copy and edit secrets template for local dev"
	@echo "  clean           Remove Python cache and virtual environment"

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(ACTIVATE); $(PIP) install --upgrade pip
	$(ACTIVATE); $(PIP) install -r requirements.txt
	$(ACTIVATE); $(PIP) install pre-commit black

run:
	$(ACTIVATE); $(PYTHON) src/app.py

test:
	$(ACTIVATE); pytest -v -s

lint:
	$(ACTIVATE); pre-commit run --all-files

format:
	$(ACTIVATE); black src tests

setup-secrets:
	cp -n tests/secrets/nebius_secrets.py.template tests/secrets/cred.py; \
	echo "Edit tests/secrets/cred.py to add your own API credentials."

clean:
	rm -rf $(VENV) __pycache__ */__pycache__ .pytest_cache .mypy_cache .coverage .hypothesis
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
