#!/bin/bash
# Simple script to format code before committing

echo "🔧 Formatting Python code..."

# Format with Black
echo "Running Black formatter..."
python -m black --line-length=88 *.py tests/ scripts/

# Sort imports with isort
echo "Sorting imports..."
python -m isort --profile=black *.py tests/ scripts/

echo "✅ Code formatting completed!"
echo "Your code is now ready to commit."