.PHONY: help install dev test lint format clean docker-build docker-up docker-down docker-logs

help:
	@echo "Available commands:"
	@echo "  make install       - Install dependencies with Poetry"
	@echo "  make dev          - Run development server with hot reload"
	@echo "  make test         - Run tests with pytest"
	@echo "  make test-cov     - Run tests with coverage report"
	@echo "  make lint         - Run linters (pylint, mypy, black)"
	@echo "  make format       - Format code with black and isort"
	@echo "  make clean        - Clean cache and build artifacts"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-dev   - Run Docker development environment"
	@echo "  make docker-prod  - Run Docker production environment"
	@echo "  make docker-down  - Stop Docker containers"
	@echo "  make docker-logs  - View Docker logs"

# Installation and setup
install:
	poetry install

install-dev:
	poetry install --with dev

# Development
dev:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Testing
test:
	poetry run pytest tests/ -v

test-cov:
	poetry run pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

test-watch:
	poetry run ptw tests/

# Code quality
lint:
	@echo "Running Pylint..."
	-poetry run pylint app/ --disable=C0114,C0115,C0116,R0903 || true
	@echo "Running Mypy..."
	-poetry run mypy app/ --ignore-missing-imports || true
	@echo "Checking code format..."
	poetry run black --check app/ tests/

format:
	@echo "Formatting code with Black..."
	poetry run black app/ tests/
	@echo "Sorting imports with isort..."
	poetry run isort app/ tests/ --profile=black

# Cleanup
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf build/ dist/ *.egg-info/ 2>/dev/null || true

# Docker commands
docker-build:
	docker build -t llm-api:latest .

docker-build-prod:
	docker build -t llm-api:prod --target runtime .

docker-dev:
	docker-compose -f deployment/docker-compose.dev.yml up -d
	@echo "Development environment started. Visit http://localhost:8000"

docker-prod:
	docker-compose -f deployment/docker-compose.prod.yml up -d
	@echo "Production environment started. Visit http://localhost"

docker-down:
	docker-compose -f deployment/docker-compose.dev.yml down 2>/dev/null || true
	docker-compose -f deployment/docker-compose.prod.yml down 2>/dev/null || true
	docker-compose down 2>/dev/null || true

docker-logs:
	docker-compose logs -f

docker-logs-api:
	docker-compose logs -f api

docker-logs-nginx:
	docker-compose logs -f nginx

docker-ps:
	docker-compose ps

# Combined commands
setup: install-dev lint
	@echo "Setup complete!"

all: format lint test
	@echo "All checks passed!"
