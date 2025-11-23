"""Shared logging configuration using loguru."""

import sys
from pathlib import Path

from loguru import logger


def setup_logging(log_file: Path | None = None) -> None:
    """Setup loguru logging to both file and console.

    Args:
        log_file: Path to log file. If None, uses default backup.log location.
    """
    # Remove default handler
    logger.remove()

    # Default log file path
    if log_file is None:
        log_file = Path("/home/me/projects/backup_websites/backup.log")

    # Ensure log file directory exists
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Add console handler with timestamp format (to stdout)
    logger.add(
        sys.stdout,
        format="[{time:YYYY-MM-DD HH:mm:ss}] {message}",
        level="INFO",
    )

    # Add file handler with timestamp format
    logger.add(
        log_file,
        format="[{time:YYYY-MM-DD HH:mm:ss}] {message}",
        level="INFO",
        mode="a",
        rotation="10 MB",
        retention="30 days",
    )
