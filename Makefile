.PHONY: help venv install run test lint format clean setup-secrets check-creds deploy-k8s deploy-helm cleanup-k8s cleanup-helm

# Colors and formatting
BOLD := \033[1m
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
MAGENTA := \033[35m
CYAN := \033[36m
RESET := \033[0m

PYTHON := python
PIP := pip
VENV := .venv
ACTIVATE := . $(VENV)/bin/activate

help:
	@printf "$(BOLD)🚀 Yuga Planner$(RESET)\n"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)\n"
	@printf "\n"
	@printf "$(BOLD)📦 Development Commands:$(RESET)\n"
	@printf "  $(GREEN)venv$(RESET)            🐍 Create Python virtual environment\n"
	@printf "  $(GREEN)install$(RESET)         📋 Install all dependencies\n"
	@printf "  $(GREEN)run$(RESET)             🏃 Run the Gradio app locally\n"
	@printf "  $(GREEN)test$(RESET)            🧪 Run tests with pytest\n"
	@printf "\n"
	@printf "$(BOLD)🔧 Code Quality:$(RESET)\n"
	@printf "  $(BLUE)lint$(RESET)            ✨ Run pre-commit hooks (black, yaml, gitleaks)\n"
	@printf "  $(BLUE)format$(RESET)          🎨 Format code with black\n"
	@printf "\n"
	@printf "$(BOLD)🔐 Credentials:$(RESET)\n"
	@printf "  $(YELLOW)setup-secrets$(RESET)   🔑 Setup credential template\n"
	@printf "  $(YELLOW)check-creds$(RESET)     🔍 Validate all credentials\n"
	@printf "\n"
	@printf "$(BOLD)☸️  Deployment:$(RESET)\n"
	@printf "  $(MAGENTA)deploy-k8s$(RESET)      🚀 Deploy to Kubernetes\n"
	@printf "  $(MAGENTA)deploy-helm$(RESET)     ⎈  Deploy using Helm\n"
	@printf "\n"
	@printf "$(BOLD)🧹 Cleanup:$(RESET)\n"
	@printf "  $(RED)cleanup-k8s$(RESET)     🗑️  Remove Kubernetes deployment\n"
	@printf "  $(RED)cleanup-helm$(RESET)    🗑️  Remove Helm deployment\n"
	@printf "  $(RED)clean$(RESET)           🧽 Remove cache and virtual environment\n"
	@printf "\n"
	@printf "$(CYAN)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)\n"

venv:
	@printf "$(GREEN)🐍 Creating virtual environment...$(RESET)\n"
	@$(PYTHON) -m venv $(VENV)
	@printf "$(GREEN)✅ Virtual environment created$(RESET)\n"

install: venv
	@printf "$(BLUE)📦 Installing dependencies...$(RESET)\n"
	@$(ACTIVATE); $(PIP) install --upgrade pip
	@$(ACTIVATE); $(PIP) install -r requirements.txt
	@$(ACTIVATE); $(PIP) install pre-commit black
	@printf "$(GREEN)✅ Dependencies installed$(RESET)\n"

run:
	@printf "$(CYAN)🏃 Starting Yuga Planner...$(RESET)\n"
	@$(ACTIVATE); $(PYTHON) src/app.py

test:
	@printf "$(YELLOW)🧪 Running tests...$(RESET)\n"
	@$(ACTIVATE); pytest -v -s

lint:
	@printf "$(BLUE)✨ Running code quality checks...$(RESET)\n"
	@$(ACTIVATE); pre-commit run --all-files

format:
	@printf "$(MAGENTA)🎨 Formatting code...$(RESET)\n"
	@$(ACTIVATE); black src tests
	@printf "$(GREEN)✅ Code formatted$(RESET)\n"

setup-secrets:
	@printf "$(YELLOW)🔑 Setting up credential template...$(RESET)\n"
	@cp -n tests/secrets/nebius_secrets.py.template tests/secrets/cred.py || true
	@printf "$(GREEN)✅ Template created$(RESET)\n"
	@printf "$(CYAN)💡 Edit tests/secrets/cred.py to add your API credentials$(RESET)\n"

check-creds:
	@printf "$(CYAN)🔍 Validating credentials...$(RESET)\n"
	@./scripts/load-credentials.sh

deploy-k8s:
	@./scripts/deploy-k8s.sh

deploy-helm:
	@./scripts/deploy-helm.sh

cleanup-k8s:
	@./scripts/cleanup-k8s.sh

cleanup-helm:
	@./scripts/cleanup-helm.sh

clean:
	@printf "$(RED)🧽 Cleaning up...$(RESET)\n"
	@rm -rf $(VENV) __pycache__ */__pycache__ .pytest_cache .mypy_cache .coverage .hypothesis
	@find . -type f -name '*.pyc' -delete
	@find . -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
	@printf "$(GREEN)✅ Cleanup complete$(RESET)\n"
