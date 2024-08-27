import logging
from pathlib import Path
import subprocess
import time
import functools

from bs4 import BeautifulSoup

#TODO:
    # run script once a month, and keep 3 snapshots at a given point.  
    # determine which file types to ignore

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def timeit(func):
    @functools.wraps(func)
    def wrapper_timeit(*args, **kwargs):
        start_time = time.time()  # Start timing
        result = func(*args, **kwargs)  # Run the function
        end_time = time.time()  # End timing
        elapsed_time = end_time - start_time  # Calculate the elapsed time
        print(f"Elapsed time: {elapsed_time:.2f} seconds")
        return result  # Return the result of the function
    return wrapper_timeit

def get_articles(url, force_redownload = False):
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
        '--backup-converted',   # Create a backup of files before they are converted/modified by wget. Original files are saved with a .orig extension.
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





@timeit
def main():
    url = 'https://tortillaconsal.com/'
    get_articles(url, True)
    # directory_path = Path("./tortillaconsal.com")
    # for file_path in directory_path.glob('*.html'):
    #     rename_html_file(file_path)

if __name__ == "__main__":
    main()