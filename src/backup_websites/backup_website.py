"""main script"""

import logging
import os
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path

import click

logger = logging.getLogger(__name__)


def setup_logging(log_file: Path) -> None:
    """Setup logging to both file and console"""
    # Clear any existing handlers
    logger.handlers.clear()
    logging.getLogger().handlers.clear()

    # Set up formatters
    formatter = logging.Formatter("[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S")

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # File handler
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def send_email(subject: str, body: str, email: str) -> None:
    """Send email notification using mail command"""
    try:
        # Use mail command to send email
        process = subprocess.Popen(
            ["mail", "-s", subject, email],
            stdin=subprocess.PIPE,
            text=True,
        )
        process.communicate(input=body)
        logger.info(f"Email notification sent to {email}")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def get_articles(url: str, download_dir: Path, force_redownload: bool = False) -> None:
    """uses wget to scrap website and attempt to get configuration files."""

    # Create download directory
    download_dir.mkdir(exist_ok=True)

    wget_command = [
        "wget",
        "-e",
        "robots=off",  # Ignore robots.txt
        # Connection settings
        "--timeout=60",
        "--waitretry=30",
        "--tries=5",
        # Rate limiting
        "--limit-rate=100k",  # Limit to 500 KB/s
        # Recursion and scope control
        "--recursive",
        "--level=15",
        "--no-parent",
        "--span-hosts",  # keep this else it will only download a few files from main domain
        # Content handling
        "--page-requisites",
        "--adjust-extension",
        # Link handling
        "--convert-links",
        # Download to specific directory
        f"--directory-prefix={download_dir}",
        "--cut-dirs=0",
        # Continue and force options
        "--continue",
        # Output options
        "--show-progress",
        "--timestamping",
        "--verbose",
        "--debug",
        url,
    ]

    if force_redownload:
        wget_command = [
            cmd for cmd in wget_command if cmd not in ["--timestamping", "--continue"]
        ]
        wget_command.extend(["--no-timestamping", "--force-directories"])

    result = subprocess.run(wget_command)
    match result.returncode:
        case 0:
            logger.info("Wget completed successfully")
        case 8:
            logger.info("wget exited with code 8, server side error will just continue")
        case _:
            logger.error(f"Wget failed with exit code {result.returncode}")
            print("STDERR:", result.stderr)
            raise subprocess.CalledProcessError(
                returncode=result.returncode,
                cmd=wget_command,
                output=result.stdout,
                stderr=result.stderr,
            )


@click.option("--url", help="url to scrap", type=str, required=True)
@click.option(
    "--force_redownload",
    default=False,
    is_flag=True,
    help="in case wget isn't downloading because of timestamp use this flag.",
)
@click.option(
    "--email",
    default="eduardolzevallos@gmail.com",
    help="Email address for notifications",
)
@click.option(
    "--log-file",
    default="/home/me/projects/backup_websites/backup.log",
    help="Path to log file",
    type=click.Path(path_type=Path),
)
@click.option(
    "--download-dir",
    default="curr-download",
    help="Directory to download files to",
    type=click.Path(path_type=Path),
)
@click.command()
def main(url, force_redownload, email, log_file, download_dir):
    """main function with integrated tortilla-con-sal-backup functionality"""
    script_dir = Path("/home/me/projects/backup_websites")
    detailed_errors = []

    try:
        # Setup logging
        try:
            setup_logging(log_file)
            logger.info("Starting backup script")
            logger.info(f"Backing up URL: {url}")
        except Exception as e:
            print(f"Failed to setup logging: {e}")
            detailed_errors.append(f"Logging setup failed: {str(e)}")
            raise

        # Change to script directory
        try:
            script_dir.mkdir(parents=True, exist_ok=True)
            os.chdir(script_dir)
            logger.info("Starting website backup...")
        except Exception as e:
            logger.error(f"Failed to change to script directory: {e}")
            detailed_errors.append(f"Directory change failed: {str(e)}")
            raise

        try:
            # retrieves all the articles from tortilla con sal
            logger.info(f"Starting wget download to {download_dir}...")
            get_articles(url, download_dir, force_redownload)
            logger.info("Wget download completed successfully")
        except Exception as e:
            logger.error(f"Failed to download articles with wget: {e}")
            detailed_errors.append(f"Wget download failed: {str(e)}")
            raise

        # try:
        #     # uploads all the files to s3
        #     logger.info("Starting S3 upload...")
        #     upload_all_files_to_s3()
        #     logger.info("S3 upload completed successfully")
        # except Exception as e:
        #     logger.error(f"Failed to upload files to S3: {e}")
        #     detailed_errors.append(f"S3 upload failed: {str(e)}")
        #     raise

        logger.info("Backup completed successfully")

        # Send success email
        subject = f"Website Backup Successful - {datetime.now().strftime('%Y-%m-%d')}"
        body = "Website backup completed successfully."
        if detailed_errors:
            body += "\n\nNon-critical issues encountered:\n" + "\n".join(
                f"- {err}" for err in detailed_errors
            )

        try:
            send_email(subject, body, email)
        except Exception as email_error:
            logger.error(f"Failed to send success email: {email_error}")

    except Exception as e:
        error_msg = f"Error occurred in backup script: {str(e)}"
        if detailed_errors:
            error_msg += "\n\nDetailed errors:\n" + "\n".join(
                f"- {err}" for err in detailed_errors
            )

        # Add full traceback to error message
        error_msg += f"\n\nFull traceback:\n{traceback.format_exc()}"

        logger.error(error_msg)

        # Send failure email
        subject = f"Website Backup Failed - {datetime.now().strftime('%Y-%m-%d')}"
        try:
            send_email(subject, error_msg, email)
        except Exception as email_error:
            logger.error(f"Failed to send failure email: {email_error}")

        raise


if __name__ == "__main__":
    main()
