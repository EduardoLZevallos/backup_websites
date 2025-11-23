"""Tests for backup_website module."""

import subprocess
from unittest.mock import MagicMock

import pytest
from backup_websites.backup_website import get_articles, main, send_email
from click.testing import CliRunner


def test_send_email_success(mocker):
    """Test successful email sending."""
    mock_popen = mocker.patch("backup_websites.backup_website.subprocess.Popen")
    mock_process = MagicMock()
    mock_popen.return_value = mock_process

    send_email("Test Subject", "Test Body", "test@example.com")

    mock_popen.assert_called_once_with(
        ["mail", "-s", "Test Subject", "test@example.com"],
        stdin=subprocess.PIPE,
        text=True,
    )
    mock_process.communicate.assert_called_once_with(input="Test Body")


def test_send_email_failure(mocker):
    """Test email sending failure."""
    mocker.patch(
        "backup_websites.backup_website.subprocess.Popen",
        side_effect=Exception("Mail error"),
    )

    # Should not raise, just log error
    send_email("Test Subject", "Test Body", "test@example.com")


def test_get_articles_success(mocker, temp_dir, sample_url):
    """Test successful article download."""
    mock_run = mocker.patch("backup_websites.backup_website.subprocess.run")
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    download_dir = temp_dir / "downloads"
    get_articles(sample_url, download_dir, force_redownload=False)

    # Verify wget was called
    assert mock_run.called
    call_args = mock_run.call_args[0][0]
    assert "wget" in call_args
    assert "--mirror" in call_args
    assert sample_url in call_args


def test_get_articles_with_force_redownload(mocker, temp_dir, sample_url):
    """Test article download with force redownload flag."""
    mock_run = mocker.patch("backup_websites.backup_website.subprocess.run")
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    download_dir = temp_dir / "downloads"
    get_articles(sample_url, download_dir, force_redownload=True)

    # Verify --continue is not in command
    call_args = mock_run.call_args[0][0]
    assert "--continue" not in call_args
    assert "--no-timestamping" in call_args


def test_get_articles_wget_exit_code_8(mocker, temp_dir, sample_url):
    """Test handling of wget exit code 8 (server error)."""
    mock_run = mocker.patch("backup_websites.backup_website.subprocess.run")
    mock_result = MagicMock()
    mock_result.returncode = 8
    mock_run.return_value = mock_result

    download_dir = temp_dir / "downloads"
    # Should not raise, just log
    get_articles(sample_url, download_dir, force_redownload=False)


def test_get_articles_wget_failure(mocker, temp_dir, sample_url):
    """Test wget failure with non-zero exit code."""
    mock_run = mocker.patch("backup_websites.backup_website.subprocess.run")
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "Error message"
    mock_run.return_value = mock_result

    download_dir = temp_dir / "downloads"

    with pytest.raises(subprocess.CalledProcessError):
        get_articles(sample_url, download_dir, force_redownload=False)


def test_get_articles_creates_download_dir(mocker, temp_dir, sample_url):
    """Test that get_articles creates download directory."""
    mock_run = mocker.patch("backup_websites.backup_website.subprocess.run")
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    download_dir = temp_dir / "new_downloads"
    get_articles(sample_url, download_dir, force_redownload=False)

    # Directory should be created
    assert download_dir.exists()


def test_main_success(mocker, temp_dir, sample_url, sample_log_file):
    """Test successful main function execution."""
    runner = CliRunner()

    # Mock dependencies
    mocker.patch("backup_websites.backup_website.setup_logging")
    mocker.patch("backup_websites.backup_website.get_articles")
    mocker.patch("backup_websites.backup_website.send_email")
    mocker.patch("backup_websites.backup_website.os.chdir")
    mocker.patch("backup_websites.backup_website.Path.mkdir")

    download_dir = temp_dir / "downloads"
    download_dir.mkdir()

    result = runner.invoke(
        main,
        [
            "--url",
            sample_url,
            "--download-dir",
            str(download_dir),
            "--log-file",
            str(sample_log_file),
            "--email",
            "test@example.com",
        ],
    )

    # Should complete successfully
    assert result.exit_code == 0


def test_main_with_node_detection(mocker, temp_dir, sample_url, sample_log_file):
    """Test main function with node detection enabled via name parameter."""
    runner = CliRunner()

    # Mock dependencies
    mocker.patch("backup_websites.backup_website.setup_logging")
    mocker.patch("backup_websites.backup_website.get_articles")
    mocker.patch("backup_websites.backup_website.send_email")
    mocker.patch("backup_websites.backup_website.os.chdir")
    mocker.patch("backup_websites.backup_website.Path.mkdir")
    mock_tortillaconsal = mocker.patch(
        "backup_websites.backup_website.TortillaconsalBackupLogic"
    )
    mock_instance = MagicMock()
    mock_tortillaconsal.return_value = mock_instance

    download_dir = temp_dir / "downloads"
    download_dir.mkdir()

    result = runner.invoke(
        main,
        [
            "--url",
            sample_url,
            "--download-dir",
            str(download_dir),
            "--log-file",
            str(sample_log_file),
            "--name",
            "tortillaconsal",
        ],
    )

    # Should call tortillaconsal logic
    assert mock_tortillaconsal.called
    mock_instance.run.assert_called_once()
    assert result.exit_code == 0
