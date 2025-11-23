"""Tests for logging_config module."""

from pathlib import Path

from backup_websites.logging_config import setup_logging
from loguru import logger


def test_setup_logging_with_custom_file(temp_dir, sample_log_file):
    """Test that setup_logging creates log file and configures handlers."""
    # Remove default handler
    logger.remove()

    # Setup logging with custom file
    setup_logging(sample_log_file)

    # Verify log file directory was created
    assert sample_log_file.parent.exists()

    # Test that logging works
    logger.info("Test message")

    # Verify log file was created with timestamp and contains message
    # The filename will have a timestamp added, so we need to find it
    log_files = list(sample_log_file.parent.glob(f"{sample_log_file.stem}_*.log"))
    assert len(log_files) > 0, "No timestamped log file found"
    timestamped_log_file = log_files[0]
    assert timestamped_log_file.exists()
    content = timestamped_log_file.read_text()
    assert "Test message" in content


def test_setup_logging_with_default_file(mocker, temp_dir):
    """Test that setup_logging uses default log file when None is passed."""
    # Mock the default path
    default_path = Path("/home/me/projects/backup_websites/backup.log")
    mocker.patch("backup_websites.logging_config.Path", return_value=default_path)

    # Remove default handler
    logger.remove()

    # Setup logging with None (should use default)
    setup_logging(None)

    # Verify logging works
    logger.info("Default log test")


def test_setup_logging_creates_parent_directories(temp_dir):
    """Test that setup_logging creates parent directories if they don't exist."""
    nested_log_file = temp_dir / "nested" / "deep" / "log.log"

    # Remove default handler
    logger.remove()

    # Setup logging with nested path
    setup_logging(nested_log_file)

    # Verify parent directories were created
    assert nested_log_file.parent.exists()
    assert nested_log_file.parent.parent.exists()

    # Verify timestamped log file was created
    log_files = list(nested_log_file.parent.glob(f"{nested_log_file.stem}_*.log"))
    assert len(log_files) > 0, "No timestamped log file found"
