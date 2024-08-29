import logging
from pathlib import Path
import subprocess
import time
import functools
import shutil

import click
from bs4 import BeautifulSoup

#TODO:
    # need to merge the directories and rename all the htmls
    # remove unnecessary .orig files
    # run script once a month, and keep 3 snapshots at a given point.  
    # determine which file types to ignore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

#TODO this should convert seconds to hour and mins
def timeit(func):
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
    wget_command = [
        'wget',
        '--mirror',              # Enables mirroring, equivalent to: -r -N -l inf --no-remove-listing
        '--recursive',           # Recursively download the entire website
        '--page-requisites',     # Download all the files (images, CSS, JS) needed to properly display the pages
        '--convert-links',       # Convert the links in the downloaded files to point to the local files
        f'--domains={url.replace("https://", "").rstrip("/")}',  # Restrict downloading to this domain
        '--span-hosts',          # Allow downloading across subdomains
        '--no-parent',           # Don't ascend to parent directories, only download from the specified directory and below
        '--level=inf',           # No limit to the depth of recursion (combined with --mirror)
        '--html-extension',      # Save files with a .html extension
        '--adjust-extension',    # Adjust extension to .html if necessary
        '--tries=5',             # Try downloading files up to 5 times in case of errors
        '--continue',            # Continue downloading partially downloaded files
        '--timeout=30',          # Set a 30-second timeout for each download
        '--waitretry=3',        # Wait 10 seconds between retries
        '--quiet',
        # '--wait=1',              # Wait 1 second between downloads to avoid overwhelming the server
        # '--limit-rate=20k',      # Limit download speed to 20 KB/s to reduce server load and manage bandwidth
        url    # The URL to download
    ]
    if force_redownload:
         wget_command.insert(-1, '--no-use-server-timestamps')
         wget_command.remove('--mirror')
    logger.info(wget_command)
    subprocess.run(wget_command)


def rename_html_file(file_path, max_length=125):
    with file_path.open('r', encoding='utf-8') as file:
        content = file.read()
    
    # Parse the HTML content
    soup = BeautifulSoup(content, 'html.parser')
    
    # Extract the title
    title = soup.title.string.strip() if soup.title else 'untitled'
    
    # Create a valid filename from the title
    valid_filename = "".join([c for c in title if c.isalnum() or c in (' ', '_', '-')]).rstrip()

    if len(valid_filename) > max_length:
        valid_filename = valid_filename[:max_length]

    # Create the new file path with the new name
    new_file_path = file_path.with_name(f"{valid_filename}.html")
    
    # Rename the file
    file_path.rename(new_file_path)
    logger.info("Renamed: %s-> %s", file_path.name, new_file_path.name)       

def copy_nonexistent_files_from_tortillaconsal(target_path: Path ,source_path: Path) -> None:
    for source_file in source_path.rglob('*'):
        if not source_file.is_file():
            continue
        if source_file.suffix == '.orig': # wget creating these orig files not necessary 
            continue
        relative_path = source_file.relative_to(source_path)
        target_file = target_path / relative_path
        if target_file.exists():
            continue
        target_file.parent.mkdir(parents=True, exist_ok=True)  # Create target subdirectory if necessary
        shutil.copy2(source_file, target_file)
        logger.info("Copied: %s -> %s", source_file, target_file)

def delete_source_directory(source_path: Path) -> None:
    if not source_path.exists() or not source_path.is_dir():
        logger.warning("could not delete directory: %s", source_path)
        return
    shutil.rmtree(source_path)
    logger.info("deleted directory: %s", source_path)

#TODO: add tortillaconsal flag, likely will use this script with other sites.
#TODO add required remove default from url.
@click.option('--force_redownload', default=False, help="in case wget isn't downloading because of timestamp use this flag.")
@click.option('--url', default = None , help='url to scrap') # 'https://tortillaconsal.com/'
@click.command()
@timeit
def main(url, force_redownload):
    get_articles(url, force_redownload)
    target_path = Path("./www.tortillaconsal.com/")
    source_path = Path("./tortillaconsal.com")
    logger.info("copying files that dont exist from %s to %s", target_path, source_path)
    copy_nonexistent_files_from_tortillaconsal(target_path, source_path)
    delete_source_directory(source_path)
    # for file_path in target_path.rglob('*.html'):
    #     print(file_path)
    # TODO gather a list of files that I don't want to rename. some files if renamed 
    # will break website functionality such as index, any thing referenced etc, see
    # chatgpt recommendation 
        # rename_html_file(file_path)

if __name__ == "__main__":
    main()