"""Pytest configuration and shared fixtures."""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_url():
    """Sample URL for testing."""
    return "https://www.example.com"


@pytest.fixture
def sample_download_dir(temp_dir):
    """Sample download directory for testing."""
    return temp_dir / "downloads"


@pytest.fixture
def sample_log_file(temp_dir):
    """Sample log file path for testing."""
    return temp_dir / "test.log"
