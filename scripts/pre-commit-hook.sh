#!/bin/bash
# Simple pre-commit hook that runs Black formatting

echo "Running pre-commit checks..."

# Run Black on Python files
echo "Formatting Python files with Black..."
python -m black --line-length=88 --check --diff .
if [ $? -ne 0 ]; then
    echo "Code formatting issues found. Running Black to fix them..."
    python -m black --line-length=88 .
    echo "Files have been formatted. Please review and commit again."
    exit 1
fi

# Run isort on imports
echo "Checking import sorting..."
python -m isort --profile=black --check-only --diff .
if [ $? -ne 0 ]; then
    echo "Import sorting issues found. Running isort to fix them..."
    python -m isort --profile=black .
    echo "Imports have been sorted. Please review and commit again."
    exit 1
fi

echo "All pre-commit checks passed!"
exit 0