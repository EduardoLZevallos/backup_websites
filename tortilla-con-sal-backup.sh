#!/bin/bash
set -euo pipefail

# Script to backup tortillaconsal.com website using wget and upload to S3
# Requires: uv (Python package manager)

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create and activate virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install package in development mode
echo "Installing package..."
uv pip install -e .

# Run the backup script
echo "Starting website backup..."
uv run backup-website --url "https://tortillaconsal.com/"

echo "Backup completed successfully!"