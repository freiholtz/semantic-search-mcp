#!/bin/bash
set -e

echo "🧪 Running available code quality checks..."
echo "==========================================="

echo ""
echo "📋 1. Type checking with ty..."
uv run ty check

echo ""  
echo "📋 2. Linting with ruff..."
uv run ruff check src/ scripts/ manage.py

echo ""
echo "📋 3. Running unit tests..."
uv run pytest tests/ -v

echo ""
echo "📋 4. Health check..."
uv run scripts/health_check.py

echo ""
echo "🎉 All checks passed! Code is ready."