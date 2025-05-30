# Comedy Open Mic Manager - Development & CI Commands

.PHONY: help install test lint format clean run seed coverage security

help:
	@echo "Available commands:"
	@echo "  install    - Install development dependencies"
	@echo "  test       - Run all tests"
	@echo "  test-unit  - Run unit tests only"
	@echo "  test-integration - Run integration tests only"
	@echo "  lint       - Run code linting"
	@echo "  format     - Format code with black and isort"
	@echo "  coverage   - Generate coverage report"
	@echo "  security   - Run security scans"
	@echo "  clean      - Clean temporary files"
	@echo "  run        - Start development server"
	@echo "  seed       - Populate database with test data"
	@echo "  db-reset   - Reset database and reseed"

install:
	pip install -e .
	pip install pytest pytest-cov pytest-flask black isort flake8 mypy bandit safety

test:
	python -m pytest test_app.py tests/ -v

test-unit:
	python -m pytest test_app.py -v -m "not integration"

test-integration:
	python -m pytest tests/ -v -m "integration"

lint:
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
	mypy . --ignore-missing-imports

format:
	black .
	isort .

coverage:
	python -m pytest --cov=. --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/"

security:
	bandit -r . -f json -o bandit-report.json
	safety check --json --output safety-report.json
	@echo "Security reports generated: bandit-report.json, safety-report.json"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*~" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -f coverage.xml
	rm -f bandit-report.json
	rm -f safety-report.json

run:
	python main.py

seed:
	python seed_data.py

db-reset:
	python -c "from app import app, db; app.app_context().push(); db.drop_all(); db.create_all()"
	python seed_data.py