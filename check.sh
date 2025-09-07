#!/bin/bash
set -e

echo "🧪 Running comprehensive code quality checks..."
echo "=============================================="

echo ""
echo "📋 1. Type checking with ty..."
uv run ty check

echo ""
echo "📋 2. Code formatting check with black..."
uv run black --check --diff src/ scripts/ manage.py

echo ""  
echo "📋 3. Linting with ruff..."
uv run ruff check src/ scripts/ manage.py

echo ""
echo "📋 4. Running tests with pytest..."
uv run pytest -v

echo ""
echo "📋 5. Health check..."
uv run scripts/health_check.py

echo ""
echo "🎉 All checks passed! Code is ready for production."