# eBay E2E automation - common tasks
# Usage: make <target>   (run `make help` for the list)

PYTHON         ?= python3
VENV           := .venv
BIN            := $(VENV)/bin
PROFILE        ?= local
ALLURE_VERSION ?= 2.32.0
TOOLS          := .tools
ALLURE_HOME    := $(TOOLS)/allure-$(ALLURE_VERSION)
ALLURE         := $(ALLURE_HOME)/bin/allure
RESULTS        := reports/allure-results
REPORT         := reports/allure-report

.DEFAULT_GOAL := help
.PHONY: help install test e2e unit ci allure-generate report open run clean

help: ## Show available targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

$(BIN)/activate:
	$(PYTHON) -m venv $(VENV)

install: $(BIN)/activate $(ALLURE) ## Create venv, install packages, Chromium and a local Allure CLI
	$(BIN)/pip install -q --upgrade pip
	$(BIN)/pip install -q -r requirements.txt
	$(BIN)/playwright install chromium
	@[ -f .env ] || cp .env.example .env

$(ALLURE):
	@command -v java >/dev/null || { echo "Java is required for the Allure report (brew install openjdk)"; exit 1; }
	@mkdir -p $(TOOLS)
	curl -sSL https://github.com/allure-framework/allure2/releases/download/$(ALLURE_VERSION)/allure-$(ALLURE_VERSION).tgz | tar -xz -C $(TOOLS)

test: ## Run all tests (unit + e2e)
	$(BIN)/pytest --profile=$(PROFILE)

e2e: ## Run only the eBay E2E scenarios (browser visible, see pytest.ini)
	$(BIN)/pytest -m e2e --profile=$(PROFILE)

unit: ## Run fast unit tests (no browser)
	$(BIN)/pytest tests/unit

ci: ## Headless run with trace always on
	$(BIN)/pytest -m e2e --profile=ci --headless

allure-generate: $(ALLURE) ## Build a single-file Allure HTML report (opens without a server)
	$(ALLURE) generate $(RESULTS) -o $(REPORT) --clean --single-file
	@echo "Report: $(REPORT)/index.html"

report: allure-generate ## Alias for allure-generate

open: ## Open the generated report in the browser
	open $(REPORT)/index.html 2>/dev/null || xdg-open $(REPORT)/index.html

run: ## Run e2e, then build and open the report
	-$(MAKE) e2e
	$(MAKE) allure-generate open

clean: ## Remove reports and caches
	rm -rf reports .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
