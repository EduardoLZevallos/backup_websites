"""main script"""

import logging
import shutil
import subprocess
from pathlib import Path

import click

from .s3 import upload_all_files_to_s3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_articles(url: str, force_redownload: bool = False) -> None:
    """uses wget to scrap website and attempt to get configuration files."""
    wget_command = [
        "wget",
        "-e",  # Ignore robots.txt
        "robots=off",  # Ignore robots.txt
        # Connection settings
        "--timeout=30",  # Connection timeout
        "--waitretry=10",  # Time between retries
        "--tries=5",  # Number of retry attempts
        "--retry-connrefused",  # Retry on connection refused
        # Rate limiting
        "--wait=1",  # Wait between requests
        "--random-wait",  # Add randomization to wait
        "--limit-rate=20k",  # Limit download speed
        # Recursion and scope control
        "--recursive",  # Enable recursive downloading
        "--level=15",  # Maximum depth of 15 levels - deep enough for most sites
        "--no-parent",  # Don't ascend to parent directories
        f"--domains={url.replace('https://', '').rstrip('/')}",  # Stay within domain
        "--span-hosts",  # But allow subdomains
        # Content handling
        "--page-requisites",  # Get all page assets (CSS, images)
        "--convert-links",  # Fix links to work locally
        "--continue",  # Resume partial downloads
        "--content-disposition",  # Respect server's filename hints
        "--adjust-extension",  # Fix file extensions based on MIME
        # Output options
        "--no-verbose",  # Reduce output noise
        url,
    ]
    if force_redownload:
        wget_command.insert(-1, "--no-use-server-timestamps")
        wget_command.remove("--mirror")
    logger.info(wget_command)
    subprocess.run(wget_command, check=True)


def copy_nonexistent_files_from_tortillaconsal(
    target_path: Path, source_path: Path
) -> None:
    """used to copy files from one directory to another that might have duplicate files"""
    for source_file in source_path.rglob("*"):
        if not source_file.is_file():
            continue
        if (
            source_file.suffix == ".orig"
        ):  # wget creating these orig files not necessary
            continue
        relative_path = source_file.relative_to(source_path)
        target_file = target_path / relative_path
        if target_file.exists():
            continue
        target_file.parent.mkdir(
            parents=True, exist_ok=True
        )  # Create target subdirectory if necessary
        shutil.copy2(source_file, target_file)
        logger.info("Copied: %s -> %s", source_file, target_file)


def delete_source_directory(source_path: Path) -> None:
    """deletes directory"""
    if not source_path.exists() or not source_path.is_dir():
        logger.warning("could not delete directory: %s", source_path)
        return
    shutil.rmtree(source_path)
    logger.info("deleted directory: %s", source_path)


def merge_two_scraped_directories(main_path: Path, secondary_path: Path) -> None:
    """runs the workflow of merging two directories and deleting redundant directory"""
    logger.info(
        "copying files that dont exist from %s to %s", main_path, secondary_path
    )
    copy_nonexistent_files_from_tortillaconsal(main_path, secondary_path)
    delete_source_directory(secondary_path)


def check_important_files(domain_path: Path) -> None:
    """Check for important configuration and server files"""
    important_files = [
        "*.php",
        "*.config",
        "*.conf",
        "*.ini",
        "*.env",
        "wp-config.php",
        ".htaccess",
        "nginx.conf",
        "composer.json",
        "package.json",
        "requirements.txt",
    ]

    found_files = []
    for pattern in important_files:
        found = list(domain_path.rglob(pattern))
        if found:
            found_files.extend(found)

    if found_files:
        logger.warning("Found potential server configuration files:")
        for file in found_files:
            logger.warning(" - %s", file)
        logger.warning("You may need these files for a complete Docker deployment")
    else:
        logger.warning(
            "No server configuration files found. Site may be static or files may be protected"
        )


@click.option("--url", help="url to scrap", type=str, required=True)
@click.option(
    "--force_redownload",
    default=False,
    help="in case wget isn't downloading because of timestamp use this flag.",
)
@click.command()
def main(url, force_redownload):
    """main function"""
    # retrieves all the articles from tortilla con sal
    get_articles(url, force_redownload)

    # Check domain path for important files
    domain = url.replace("https://", "").replace("http://", "").rstrip("/")
    domain_path = Path(f"./{domain}")
    check_important_files(domain_path)

    # tortilla scrape downloads from two directories, this code merges the two seperate directories
    if url == "https://tortillaconsal.com/":
        main_path = Path("./www.tortillaconsal.com/")  # TODO: shouldn't be hardcoded
        secondary_path = Path("./tortillaconsal.com")  # TODO: shouldn't be hardcoded
        merge_two_scraped_directories(main_path, secondary_path)

    # uploads all the files to s3
    upload_all_files_to_s3()


if __name__ == "__main__":
    main()
