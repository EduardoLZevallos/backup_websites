"""Tests for wait_for_completion module."""

import time

from backup_websites.wait_for_completion import main
from click.testing import CliRunner


def test_wait_for_completion_file_exists_immediately(mocker, temp_dir, sample_log_file):
    """Test when completion file already exists."""
    mocker.patch("backup_websites.wait_for_completion.setup_logging")

    download_dir = temp_dir / "downloads"
    download_dir.mkdir()
    completion_file = download_dir / ".backup_complete"
    completion_file.touch()

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--download-dir",
            str(download_dir),
            "--name",
            "test-site",
            "--log-file",
            str(sample_log_file),
            "--timeout",
            "600",
            "--check-interval",
            "5",
        ],
    )

    assert result.exit_code == 0
    # File should be removed
    assert not completion_file.exists()


def test_wait_for_completion_file_created_during_wait(
    mocker, temp_dir, sample_log_file
):
    """Test when completion file is created during wait."""
    mocker.patch("backup_websites.wait_for_completion.setup_logging")

    download_dir = temp_dir / "downloads"
    download_dir.mkdir()
    completion_file = download_dir / ".backup_complete"

    # Create file after a short delay
    def create_file():
        time.sleep(0.1)
        completion_file.touch()

    import threading

    thread = threading.Thread(target=create_file)
    thread.start()

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--download-dir",
            str(download_dir),
            "--name",
            "test-site",
            "--log-file",
            str(sample_log_file),
            "--timeout",
            "600",
            "--check-interval",
            "5",
        ],
    )

    thread.join()
    assert result.exit_code == 0
    assert not completion_file.exists()


def test_wait_for_completion_timeout_with_recent_modification(
    mocker, temp_dir, sample_log_file
):
    """Test timeout but directory was recently modified."""
    mocker.patch("backup_websites.wait_for_completion.setup_logging")

    download_dir = temp_dir / "downloads"
    download_dir.mkdir()

    # Ensure log file directory exists
    sample_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Mock os.path.getmtime - since os is imported inside the function,
    # we need to patch it in a way that works with dynamic imports
    # Patch it in the builtin os module
    import os as os_module

    mocker.patch.object(
        os_module.path, "getmtime", return_value=time.time() - 100
    )  # Modified 100 seconds ago

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--download-dir",
            str(download_dir),
            "--name",
            "test-site",
            "--log-file",
            str(sample_log_file),
            "--timeout",
            "1",
            "--check-interval",
            "1",
        ],
    )  # Short timeout

    # Debug: print error if it failed
    if result.exit_code != 0:
        print(f"Error output: {result.output}")
        print(f"Exception: {result.exception}")

    # Should exit with 0 (proceed despite missing marker)
    assert (
        result.exit_code == 0
    ), f"Expected exit code 0, got {result.exit_code}. Output: {result.output}"


def test_wait_for_completion_timeout_no_recent_modification(
    mocker, temp_dir, sample_log_file
):
    """Test timeout with no recent modification (should fail)."""
    mocker.patch("backup_websites.wait_for_completion.setup_logging")

    download_dir = temp_dir / "downloads"
    download_dir.mkdir()

    # Ensure log file directory exists
    sample_log_file.parent.mkdir(parents=True, exist_ok=True)

    # Mock os.path.getmtime - since os is imported inside the function,
    # we need to patch it in a way that works with dynamic imports
    # Patch it in the builtin os module
    import os as os_module

    mocker.patch.object(
        os_module.path, "getmtime", return_value=time.time() - 7200
    )  # Modified 2 hours ago

    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--download-dir",
            str(download_dir),
            "--name",
            "test-site",
            "--log-file",
            str(sample_log_file),
            "--timeout",
            "1",
            "--check-interval",
            "1",
        ],
    )  # Short timeout

    # Debug: print error if it failed
    if result.exit_code != 1:
        print(f"Error output: {result.output}")
        print(f"Exception: {result.exception}")

    # Should exit with 1 (fail)
    assert (
        result.exit_code == 1
    ), f"Expected exit code 1, got {result.exit_code}. Output: {result.output}"


def test_wait_for_completion_directory_not_exists(mocker, temp_dir, sample_log_file):
    """Test when download directory doesn't exist."""
    mocker.patch("backup_websites.wait_for_completion.setup_logging")

    download_dir = temp_dir / "nonexistent"

    runner = CliRunner()
    # Click validates that the directory exists (exists=True), so it will fail with exit code 2
    # This is expected behavior - Click validates before our code runs
    result = runner.invoke(
        main,
        [
            "--download-dir",
            str(download_dir),
            "--name",
            "test-site",
            "--log-file",
            str(sample_log_file),
            "--timeout",
            "1",
            "--check-interval",
            "1",
        ],
    )

    # Click validation fails with exit code 2 when directory doesn't exist
    assert result.exit_code == 2
    assert "does not exist" in result.output.lower() or "error" in result.output.lower()
