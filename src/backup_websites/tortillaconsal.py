"""Tortillaconsal-specific backup logic for Drupal node detection and download."""

import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import requests
from loguru import logger


class TortillaconsalBackupLogic:
    """Handles tortillaconsal.com-specific backup logic for Drupal node detection."""

    # Node paths to check (both bitacora and tortilla sections)
    NODE_PATHS = ["bitacora", "tortilla"]

    def __init__(self, url: str, download_dir: Path):
        """Initialize with URL and download directory."""
        self.url = url
        self.download_dir = download_dir
        parsed_url = urlparse(url)
        self.domain = parsed_url.netloc
        self.base_url = f"{parsed_url.scheme}://{self.domain}"

    def find_missing_nodes(self, node_path: str) -> list[int]:
        """Find missing node numbers by comparing backup with live site for a specific node path."""
        # Find nodes in backup for this path
        backup_nodes = set()
        node_dir_patterns = [
            self.download_dir / self.domain / node_path / "node",
            self.download_dir / f"www.{self.domain}" / node_path / "node",
        ]

        for node_dir in node_dir_patterns:
            if node_dir.exists():
                for file in node_dir.iterdir():
                    if file.is_file() and file.suffix == ".html":
                        match = re.match(r"^(\d+)\.html$", file.name)
                        if match:
                            backup_nodes.add(int(match.group(1)))

        if not backup_nodes:
            logger.info(
                f"No nodes found in backup for /{node_path}/node/, skipping check"
            )
            return []

        max_backup_node = max(backup_nodes)
        logger.info(f"Highest node in backup for /{node_path}/node/: {max_backup_node}")

        # Find highest node on live site by checking section homepage and archive
        try:
            live_nodes: set[int] = set()

            # Check section homepage
            try:
                response = requests.get(f"{self.base_url}/{node_path}/", timeout=30)
                response.raise_for_status()
                content = response.text
                node_pattern = rf"/{node_path}/node/(\d+)"
                live_nodes.update(
                    int(match) for match in re.findall(node_pattern, content)
                )
            except requests.RequestException as e:
                logger.warning(f"Failed to check {node_path} homepage: {e}")

            # Check archive page if it exists (mainly for bitacora)
            if node_path == "bitacora":
                try:
                    archive_response = requests.get(
                        f"{self.base_url}/archivos.html", timeout=30
                    )
                    if archive_response.status_code == 200:
                        node_pattern = rf"/{node_path}/node/(\d+)"
                        live_nodes.update(
                            int(match)
                            for match in re.findall(node_pattern, archive_response.text)
                        )
                except requests.RequestException:
                    # Archive might not exist, that's okay
                    pass

            if live_nodes:
                max_live_node = max(live_nodes)
                logger.info(
                    f"Highest node found on live site for /{node_path}/node/: {max_live_node}"
                )

                # Use binary search approach to find the actual highest node
                # Start from max_live_node and work forwards to find the real max
                actual_max = max_live_node
                for test_node in range(max_live_node, max_live_node + 200):
                    test_url = f"{self.base_url}/{node_path}/node/{test_node}"
                    try:
                        test_response = requests.head(
                            test_url, timeout=5, allow_redirects=True
                        )
                        if test_response.status_code == 200:
                            actual_max = test_node
                        else:
                            # Found the end, break
                            break
                    except requests.RequestException:
                        break

                logger.info(
                    f"Actual highest node on site for /{node_path}/node/: {actual_max}"
                )

                # For tortillaconsal, we know nodes are sequential, so check the entire range
                # But do it efficiently by sampling first
                missing_nodes = []
                test_range = range(1, actual_max + 1)  # Check from node 1 to actual_max

                logger.info(
                    f"Checking {len(test_range)} nodes for missing content in /{node_path}/node/ (this may take a while)..."
                )

                # First, get all nodes that exist in backup
                existing_in_backup = backup_nodes.copy()

                # For large ranges, identify gaps from backup and check those gaps
                if len(test_range) > 1000:
                    logger.info(
                        f"Analyzing backup to identify gap regions for /{node_path}/node/..."
                    )
                    sorted_backup = sorted(existing_in_backup)
                    gaps_found = []

                    # Find all gaps in the backup
                    for i in range(len(sorted_backup) - 1):
                        gap_size = sorted_backup[i + 1] - sorted_backup[i]
                        if gap_size > 1:
                            gap_start = sorted_backup[i] + 1
                            gap_end = sorted_backup[i + 1]
                            gaps_found.append((gap_start, gap_end))

                    # Also check from the last backup node to actual_max
                    if sorted_backup:
                        if sorted_backup[-1] < actual_max:
                            gaps_found.append((sorted_backup[-1] + 1, actual_max + 1))

                    # Also check from start to first backup node
                    if sorted_backup and sorted_backup[0] > 1:
                        gaps_found.append((1, sorted_backup[0]))

                    gaps_list = sorted(gaps_found)
                    total_to_check = sum(end - start for start, end in gaps_list)
                    logger.info(
                        f"Found {len(gaps_list)} gap regions totaling ~{total_to_check} nodes to check"
                    )

                    # Check all nodes in identified gaps
                    checked = 0
                    for gap_start, gap_end in gaps_list:
                        logger.info(
                            f"Checking gap {gap_start} to {gap_end - 1} ({gap_end - gap_start} nodes)..."
                        )
                        for node_num in range(gap_start, gap_end):
                            test_url = f"{self.base_url}/{node_path}/node/{node_num}"
                            try:
                                test_response = requests.head(
                                    test_url, timeout=5, allow_redirects=True
                                )
                                if test_response.status_code == 200:
                                    missing_nodes.append(node_num)
                            except requests.RequestException:
                                pass
                            checked += 1
                            if checked % 500 == 0:
                                logger.info(
                                    f"Checked {checked}/{total_to_check} nodes, found {len(missing_nodes)} missing so far..."
                                )
                else:
                    # For smaller ranges, check all nodes
                    logger.info(f"Checking all {len(test_range)} nodes individually...")
                    for node_num in test_range:
                        if node_num not in existing_in_backup:
                            test_url = f"{self.base_url}/{node_path}/node/{node_num}"
                            try:
                                test_response = requests.head(
                                    test_url, timeout=5, allow_redirects=True
                                )
                                if test_response.status_code == 200:
                                    missing_nodes.append(node_num)
                                    if len(missing_nodes) % 100 == 0:
                                        logger.info(
                                            f"Found {len(missing_nodes)} missing nodes so far..."
                                        )
                            except requests.RequestException:
                                pass

                return sorted(missing_nodes)
            else:
                logger.warning(
                    f"No node links found on live site for /{node_path}/node/"
                )
                return []
        except requests.RequestException as e:
            logger.warning(
                f"Failed to check live site for missing nodes in /{node_path}/node/: {e}"
            )
            return []

    def download_pagination_pages(self, node_path: str) -> None:
        """Explicitly download pagination pages to ensure wget finds all article links for a specific path."""
        logger.info(f"Finding all pagination pages for /{node_path}/...")

        # Use binary search to find the maximum page number efficiently
        # First, check if pagination exists
        test_url = f"{self.base_url}/{node_path}/?page=0"
        try:
            response = requests.head(test_url, timeout=10, allow_redirects=True)
            if response.status_code != 200:
                logger.info(
                    f"No pagination found for /{node_path}/, skipping pagination download"
                )
                return
        except requests.RequestException:
            logger.warning(f"Failed to check pagination for /{node_path}/, skipping")
            return

        # Binary search to find max page
        max_pages = 0
        low, high = 0, 1000  # Start with reasonable upper bound

        # First, find a rough upper bound by checking powers of 10
        for power in [10, 100, 500, 1000]:
            test_url = f"{self.base_url}/{node_path}/?page={power}"
            try:
                response = requests.head(test_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    low = power
                else:
                    high = power
                    break
            except requests.RequestException:
                high = power
                break

        # Binary search within the range
        logger.info(f"Binary searching for max page between {low} and {high}...")
        while low < high:
            mid = (low + high + 1) // 2
            test_url = f"{self.base_url}/{node_path}/?page={mid}"
            try:
                response = requests.head(test_url, timeout=10, allow_redirects=True)
                if response.status_code == 200:
                    low = mid
                else:
                    high = mid - 1
            except requests.RequestException:
                high = mid - 1

        max_pages = low

        if max_pages == 0:
            logger.info(f"Only page 0 exists for /{node_path}/, no pagination needed")
            return

        logger.info(
            f"Found {max_pages + 1} pagination pages (0 to {max_pages}) for /{node_path}/, downloading..."
        )

        # Download all pagination pages
        downloaded = 0
        for page in range(0, max_pages + 1):
            page_url = f"{self.base_url}/{node_path}/?page={page}"
            wget_command = [
                "wget",
                "-e",
                "robots=off",
                "--timeout=60",
                "--waitretry=30",
                "--tries=3",
                "--limit-rate=200k",
                "--page-requisites",
                "--adjust-extension",
                "--convert-links",
                "--no-parent",
                "--span-hosts",
                f"--domains={self.domain},www.{self.domain}",
                f"--directory-prefix={self.download_dir}",
                "--cut-dirs=0",
                "--continue",
                "--quiet",
                page_url,
            ]
            result = subprocess.run(wget_command, capture_output=True, text=True)
            if result.returncode == 0:
                downloaded += 1
                if page % 50 == 0 or page == max_pages:
                    logger.info(
                        f"Downloaded pagination page {page}/{max_pages} for /{node_path}/ ({downloaded} total)"
                    )

        logger.info(
            f"Completed downloading {downloaded} pagination pages for /{node_path}/"
        )

    def download_missing_nodes(self, missing_nodes: list[int], node_path: str) -> None:
        """Download missing node pages using wget for a specific node path."""
        if not missing_nodes:
            return

        logger.info(
            f"Downloading {len(missing_nodes)} missing nodes from /{node_path}/node/..."
        )

        # Download in batches to avoid overwhelming the server
        batch_size = 50
        for i in range(0, len(missing_nodes), batch_size):
            batch = missing_nodes[i : i + batch_size]
            logger.info(
                f"Downloading batch {i // batch_size + 1}/{(len(missing_nodes) - 1) // batch_size + 1} ({len(batch)} nodes) from /{node_path}/node/..."
            )

            for node_num in batch:
                node_url = f"{self.base_url}/{node_path}/node/{node_num}"
                wget_command = [
                    "wget",
                    "-e",
                    "robots=off",
                    "--timeout=60",
                    "--waitretry=30",
                    "--tries=3",
                    "--limit-rate=200k",
                    "--page-requisites",
                    "--adjust-extension",
                    "--convert-links",
                    "--no-parent",
                    "--span-hosts",
                    f"--domains={self.domain},www.{self.domain}",
                    f"--directory-prefix={self.download_dir}",
                    "--cut-dirs=0",
                    "--continue",
                    "--quiet",
                    node_url,
                ]

                result = subprocess.run(wget_command, capture_output=True, text=True)
                if result.returncode == 0:
                    if node_num % 100 == 0 or node_num == batch[-1]:
                        logger.info(
                            f"Downloaded node {node_num} from /{node_path}/node/ ({i + batch.index(node_num) + 1}/{len(missing_nodes)})"
                        )
                else:
                    logger.warning(
                        f"Failed to download node {node_num} from /{node_path}/node/: {result.stderr}"
                    )

    def verify_node_structure(self) -> bool:
        """Verify that the site has at least one of the known node structures."""
        for node_path in self.NODE_PATHS:
            test_node_url = f"{self.base_url}/{node_path}/node/1"
            try:
                response = requests.head(
                    test_node_url, timeout=10, allow_redirects=True
                )
                if response.status_code == 200:
                    logger.info(f"Found node structure at /{node_path}/node/")
                    return True
            except requests.RequestException:
                continue
        return False

    def run(self) -> None:
        """Run the complete tortillaconsal backup enhancement process."""
        if not self.verify_node_structure():
            logger.warning(
                "Node detection enabled but no known node structures found. Skipping node detection."
            )
            return

        # Process each node path separately
        for node_path in self.NODE_PATHS:
            logger.info(f"Processing node path: /{node_path}/node/")

            # First, download pagination pages to help wget find more links
            logger.info(
                f"Downloading pagination pages for /{node_path}/ to discover all articles..."
            )
            self.download_pagination_pages(node_path)

            # Then check for missing nodes
            logger.info(f"Checking for missing nodes in /{node_path}/node/...")
            missing_nodes = self.find_missing_nodes(node_path)
            if missing_nodes:
                logger.info(
                    f"Found {len(missing_nodes)} missing nodes in /{node_path}/node/"
                )
                logger.info(
                    f"Sample missing nodes: {missing_nodes[:20]}{'...' if len(missing_nodes) > 20 else ''}"
                )
                self.download_missing_nodes(missing_nodes, node_path)
                logger.info(f"Missing nodes download completed for /{node_path}/node/")
            else:
                logger.info(f"No missing nodes found in /{node_path}/node/")
