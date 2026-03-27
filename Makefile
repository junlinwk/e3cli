.PHONY: install dev lint test build clean

install:  ## Install e3cli
	pip install .

dev:  ## Install in development mode with dev dependencies
	pip install -e ".[dev]"

lint:  ## Run linter
	ruff check e3cli/

test:  ## Run tests
	pytest --tb=short -q

build:  ## Build distribution packages
	python -m build

clean:  ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +

formula:  ## Generate Homebrew formula (requires version tag, e.g. make formula TAG=v0.1.0)
	python scripts/generate-formula.py $(TAG)

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-12s\033[0m %s\n", $$1, $$2}'
