"""Shared logging configuration using loguru."""

import sys
from datetime import datetime
from pathlib import Path

from loguru import logger


def setup_logging(log_file: Path | None = None) -> None:
    """Setup loguru logging to both file and console.

    Args:
        log_file: Path to log file. If None, uses default backup.log location.
                  Timestamp and date will be added to the filename.
    """
    # Remove default handler
    logger.remove()

    # Default log file path
    if log_file is None:
        log_file = Path("/home/me/projects/backup_websites/backup.log")

    # Add timestamp and date to log filename
    # Format: original_name_YYYY-MM-DD_HH-MM-SS.ext
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_stem = log_file.stem  # filename without extension
    log_file_suffix = log_file.suffix  # extension including the dot
    log_file_dir = log_file.parent  # directory

    # Create new filename with timestamp
    timestamped_log_file = (
        log_file_dir / f"{log_file_stem}_{timestamp}{log_file_suffix}"
    )

    # Ensure log file directory exists
    timestamped_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Add console handler with timestamp format (to stdout)
    logger.add(
        sys.stdout,
        format="[{time:YYYY-MM-DD HH:mm:ss}] {message}",
        level="INFO",
    )

    # Add file handler with timestamp format
    logger.add(
        timestamped_log_file,
        format="[{time:YYYY-MM-DD HH:mm:ss}] {message}",
        level="INFO",
        mode="a",
        rotation="10 MB",
        retention="30 days",
    )
