# Comedy Open Mic Manager - Development Commands

.PHONY: format check-format install-dev test clean help

# Format code using Black and isort
format:
        @echo "Formatting Python code with Black..."
        python -m black --line-length=88 *.py tests/ scripts/
        @echo "Sorting imports with isort..."
        python -m isort --profile=black *.py tests/ scripts/
        @echo "Code formatting completed!"

# Check code formatting without making changes
check-format:
        @echo "Checking code formatting..."
        python -m black --line-length=88 --check --diff *.py tests/ scripts/
        python -m isort --profile=black --check-only --diff *.py tests/ scripts/
        python -m flake8 --max-line-length=88 --extend-ignore=E203,W503 *.py tests/ scripts/
        @echo "Format check completed!"

# Install development dependencies
install-dev:
        @echo "Installing development dependencies..."
        pip install black isort flake8 pre-commit pytest
        @echo "Development dependencies installed!"

# Run all tests
test:
        @echo "Running all tests..."
        python -m pytest tests/ -v
        @echo "Tests completed!"

# Run unit tests only
test-unit:
        @echo "Running unit tests..."
        python -m pytest tests/ -v -m "unit" --cov=. --cov-report=term-missing
        @echo "Unit tests completed!"

# Run integration tests only
test-integration:
        @echo "Running integration tests..."
        python -m pytest tests/ -v -m "integration" --cov=. --cov-report=term-missing
        @echo "Integration tests completed!"

# Generate coverage report
coverage:
        @echo "Generating coverage report..."
        python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
        @echo "Coverage report generated!"

# Clean up temporary files
clean:
        @echo "Cleaning up temporary files..."
        find . -type f -name "*.pyc" -delete
        find . -type d -name "__pycache__" -delete
        find . -type d -name "*.egg-info" -exec rm -rf {} +
        @echo "Cleanup completed!"

# Show available commands
help:
        @echo "Available commands:"
        @echo "  format           - Format Python code with Black and isort"
        @echo "  check-format     - Check code formatting without changes"
        @echo "  install-dev      - Install development dependencies"
        @echo "  test             - Run all tests"
        @echo "  test-unit        - Run unit tests only"
        @echo "  test-integration - Run integration tests only"
        @echo "  coverage         - Generate coverage report"
        @echo "  clean            - Clean up temporary files"
        @echo "  help             - Show this help message"