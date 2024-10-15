""" main script """

import logging
from pathlib import Path
import subprocess
import time
import functools
import shutil

import click
from s3 import upload_all_files_to_s3

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# TODO this should convert seconds to hour and mins
def timeit(func):
    """using to time function"""

    @functools.wraps(func)
    def wrapper_timeit(*args, **kwargs):
        start_time = time.time()  # Start timing
        result = func(*args, **kwargs)  # Run the function
        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time  # Calculate the elapsed time
        logger.info("Elapsed time: %.2f seconds", elapsed_time)
        return result  # Return the result of the function

    return wrapper_timeit


def get_articles(url: str, force_redownload: bool = False) -> None:
    """uses wget to scrap website"""
    wget_command = [
        "wget",
        "--mirror",  # Enables mirroring, equivalent to: -r -N -l inf --no-remove-listing
        "--recursive",  # Recursively download the entire website
        "--page-requisites",  # Download all the files (images, CSS, JS) needed to properly display the pages
        "--convert-links",  # Convert the links in the downloaded files to point to the local files
        f'--domains={url.replace("https://", "").rstrip("/")}',  # Restrict downloading to this domain
        "--span-hosts",  # Allow downloading across subdomains
        "--no-parent",  # Don't ascend to parent directories, only download from the specified directory and below
        "--level=inf",  # No limit to the depth of recursion (combined with --mirror)
        "--html-extension",  # Save files with a .html extension
        "--adjust-extension",  # Adjust extension to .html if necessary
        "--tries=5",  # Try downloading files up to 5 times in case of errors
        "--continue",  # Continue downloading partially downloaded files
        "--timeout=30",  # Set a 30-second timeout for each download
        "--waitretry=3",  # Wait 10 seconds between retries
        "--quiet",
        # '--wait=1',              # Wait 1 second between downloads to avoid overwhelming the server
        # '--limit-rate=20k',      # Limit download speed to 20 KB/s to reduce server load and manage bandwidth
        url,  # The URL to download
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


# TODO: add tortillaconsal flag, likely will use this script with other sites.
# TODO add required remove default from url.
@click.option(
    "--force_redownload",
    default=False,
    help="in case wget isn't downloading because of timestamp use this flag.",
)
@click.option(
    "--url", default=None, help="url to scrap", type=str
)  # 'https://tortillaconsal.com/'
@click.command()
@timeit
def main(url, force_redownload):
    """main function"""
    # retrieves all the articles from tortilla con sal
    get_articles(url, force_redownload)

    # tortilla scrape downloads from two directories, this code merges the two seperate directories
    main_path = Path("./www.tortillaconsal.com/")  # TODO: shouldn't be hardcoded
    secondary_path = Path("./tortillaconsal.com")  # TODO: shouldn't be hardcoded
    merge_two_scraped_directories(main_path, secondary_path)

    # uploads all the files to s3
    upload_all_files_to_s3()


if __name__ == "__main__":
    main()
