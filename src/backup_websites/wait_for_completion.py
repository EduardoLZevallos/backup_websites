"""Wait for backup completion markers."""

import sys
import time
from pathlib import Path

import click
from loguru import logger

from .logging_config import setup_logging


@click.command()
@click.option(
    "--download-dir",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Download directory path for the site",
)
@click.option(
    "--name",
    required=True,
    type=str,
    help="Site name (for logging)",
)
@click.option(
    "--log-file",
    default="/home/me/projects/backup_websites/backup.log",
    type=click.Path(path_type=Path),
    help="Path to log file",
)
@click.option(
    "--timeout",
    default=600,
    type=int,
    help="Maximum time to wait (seconds)",
)
@click.option(
    "--check-interval",
    default=5,
    type=int,
    help="Interval between checks (seconds)",
)
def main(
    download_dir: Path, name: str, log_file: Path, timeout: int, check_interval: int
) -> None:
    """Wait for backup completion marker for a single site."""
    # Setup logging
    setup_logging(log_file)

    logger.info(f"Step 2: Waiting for completion marker for {name}...")

    completion_file = download_dir / ".backup_complete"

    elapsed = 0
    last_status_time = 0

    # First, check if completion file already exists (process may have finished quickly)
    if completion_file.exists():
        logger.info(f"✓ Completion marker found for {name}")
        completion_file.unlink()
        sys.exit(0)

    # Wait for completion file with timeout
    while not completion_file.exists() and elapsed < timeout:
        time.sleep(check_interval)
        elapsed += check_interval

        # Print status every 30 seconds
        if elapsed - last_status_time >= 30:
            logger.info(
                f"  Still waiting for {name} completion marker... ({elapsed}s elapsed)"
            )
            last_status_time = elapsed

    if completion_file.exists():
        logger.info(f"✓ Completion marker found for {name}")
        # Clean up the completion file for next run
        completion_file.unlink()
        sys.exit(0)
    else:
        # Check if backup directory was modified recently (backup might have run but file creation failed)
        if download_dir.exists():
            import os

            try:
                mtime = os.path.getmtime(download_dir)
                age_seconds = time.time() - mtime
                if age_seconds < 3600:  # Modified in last hour
                    logger.warning(
                        f"⚠ Warning: Completion marker not found for {name} after {timeout}s, but directory was recently modified ({int(age_seconds)}s ago). Proceeding with S3 upload."
                    )
                    # Proceed with S3 upload despite missing marker
                    sys.exit(0)
            except OSError:
                pass

        logger.error(
            f"❌ Error: Completion marker not found for {name} after {timeout}s and directory was not recently modified. Failing pipeline."
        )
        # Fail the pipeline
        sys.exit(1)


if __name__ == "__main__":
    main()
