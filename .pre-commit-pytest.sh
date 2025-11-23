#!/bin/bash
# Pre-commit hook script to run pytest
# This script ensures pytest runs in the correct environment

# Try to use pytest from the virtual environment if it exists
if [ -f ".venv/bin/pytest" ]; then
    .venv/bin/pytest "$@"
elif [ -f "venv/bin/pytest" ]; then
    venv/bin/pytest "$@"
elif command -v python3 &> /dev/null && python3 -m pytest --version &> /dev/null; then
    # Fall back to python3 -m pytest
    python3 -m pytest "$@"
elif command -v python &> /dev/null && python -m pytest --version &> /dev/null; then
    # Last resort: try python
    python -m pytest "$@"
else
    echo "Error: pytest not found. Please install dev dependencies with: uv pip install -e '.[dev]'"
    exit 1
fi

