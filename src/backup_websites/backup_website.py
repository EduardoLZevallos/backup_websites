"""main script"""

import os
import subprocess
import traceback
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import click
from loguru import logger

from .logging_config import setup_logging
from .tortillaconsal import TortillaconsalBackupLogic


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
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    # Remove www if present to get base domain
    if domain.startswith("www."):
        base_domain = domain[4:]
    else:
        base_domain = domain
    common_subdomains = [
        base_domain,  # example.com
        f"www.{base_domain}",  # www.example.com
        f"blog.{base_domain}",  # blog.example.com
        f"news.{base_domain}",  # news.example.com
        f"shop.{base_domain}",  # shop.example.com
        f"store.{base_domain}",  # store.example.com
        f"forum.{base_domain}",  # forum.example.com
        f"support.{base_domain}",  # support.example.com
        f"help.{base_domain}",  # help.example.com
        f"docs.{base_domain}",  # docs.example.com
        f"api.{base_domain}",  # api.example.com
        f"cdn.{base_domain}",  # cdn.example.com
        f"media.{base_domain}",  # media.example.com
        f"static.{base_domain}",  # static.example.com
        f"assets.{base_domain}",  # assets.example.com
        f"img.{base_domain}",  # img.example.com
        f"images.{base_domain}",  # images.example.com
        f"files.{base_domain}",  # files.example.com
        f"downloads.{base_domain}",  # downloads.example.com
        f"m.{base_domain}",  # m.example.com (mobile)
        f"mobile.{base_domain}",  # mobile.example.com
    ]
    allowed_domains = ",".join(common_subdomains)

    wget_command = [
        "wget",
        "-e",
        "robots=off",  # Ignore robots.txt
        # Connection settings
        "--timeout=60",
        "--waitretry=30",
        "--tries=5",
        # Rate limiting
        "--limit-rate=200k",  # Limit to 500 KB/s
        # Recursion and scope control
        # "--recursive",
        # "--level=15",
        "--no-parent",
        "--span-hosts",  # keep this else it will only download a few files from main domain
        f"--domains={allowed_domains}",
        # Content handling
        "--page-requisites",
        "--adjust-extension",
        "--convert-links",
        # Link handling
        "--convert-links",
        # Download to specific directory
        f"--directory-prefix={download_dir}",
        "--cut-dirs=0",
        # Continue and force options
        "--continue",
        # Output options
        "--show-progress",
        # "--timestamping",
        "--verbose",
        "--debug",
        # mirror
        "--mirror",  # coverts --level, --recursive, --timestamping
        url,
    ]

    if force_redownload:
        wget_command = [cmd for cmd in wget_command if cmd not in ["--continue"]]
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
@click.option(
    "--enable-node-detection",
    default=False,
    is_flag=True,
    help="Enable Drupal node detection and missing node download (for sites like tortillaconsal.com with /bitacora/node/ structure)",
)
@click.command()
def main(url, force_redownload, email, log_file, download_dir, enable_node_detection):
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
            logger.error(f"Failed to setup logging: {e}")
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

        # Check for and download missing nodes (specific to Drupal node-based sites)
        # Only run if explicitly enabled via CLI flag
        if enable_node_detection:
            try:
                tortillaconsal_logic = TortillaconsalBackupLogic(url, download_dir)
                tortillaconsal_logic.run()
            except Exception as e:
                logger.warning(f"Failed to check/download missing nodes: {e}")
                detailed_errors.append(f"Missing nodes check failed: {str(e)}")
                # Don't raise - this is a non-critical enhancement

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

        # Create completion marker file to signal that backup is fully done
        # This ensures S3 upload waits for all subprocesses (like pagination downloads) to complete
        completion_file = Path(download_dir) / ".backup_complete"
        try:
            completion_file.touch()
            logger.info(f"Backup fully completed. Completion marker: {completion_file}")
        except Exception as e:
            logger.warning(f"Failed to create completion marker: {e}")

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

        # Create completion marker even on failure so the script doesn't hang waiting
        completion_file = Path(download_dir) / ".backup_complete"
        try:
            completion_file.touch()
            logger.info(f"Completion marker created (backup failed): {completion_file}")
        except Exception as e:
            logger.warning(f"Failed to create completion marker: {e}")

        raise


if __name__ == "__main__":
    main()
