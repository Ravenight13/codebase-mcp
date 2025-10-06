.PHONY: help install install-dev test test-unit test-integration test-contract lint format typecheck clean run

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	pip install -r requirements.txt

install-dev:  ## Install development dependencies
	pip install -r requirements-dev.txt
	pip install -e .

test:  ## Run all tests with coverage
	pytest

test-unit:  ## Run unit tests only
	pytest -m unit

test-integration:  ## Run integration tests only
	pytest -m integration

test-contract:  ## Run contract/API tests only
	pytest -m contract

lint:  ## Run ruff linter
	ruff check src tests

format:  ## Format code with ruff
	ruff format src tests

typecheck:  ## Run mypy type checking
	mypy src

clean:  ## Clean up generated files
	rm -rf build/ dist/ *.egg-info .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run:  ## Run the MCP server
	uvicorn src.main:app --reload --port 8000

db-migrate:  ## Run database migrations
	alembic upgrade head

db-rollback:  ## Rollback last database migration
	alembic downgrade -1

db-init:  ## Initialize database with pgvector extension
	python scripts/init_db.py

benchmark:  ## Run performance benchmarks
	python scripts/benchmark.py

all-checks: lint typecheck test  ## Run all quality checks
