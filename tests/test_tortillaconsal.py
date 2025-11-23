"""Tests for tortillaconsal module."""

from unittest.mock import MagicMock

import requests
from backup_websites.tortillaconsal import TortillaconsalBackupLogic


def test_tortillaconsal_backup_logic_init(sample_url, sample_download_dir):
    """Test TortillaconsalBackupLogic initialization."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    assert logic.url == sample_url
    assert logic.download_dir == sample_download_dir
    assert logic.domain == "www.example.com"
    assert logic.base_url == "https://www.example.com"


def test_verify_node_structure_success(mocker, sample_url, sample_download_dir):
    """Test successful node structure verification."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mocker.patch(
        "backup_websites.tortillaconsal.requests.head", return_value=mock_response
    )

    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)
    result = logic.verify_node_structure()

    assert result is True


def test_verify_node_structure_failure(mocker, sample_url, sample_download_dir):
    """Test node structure verification failure."""
    mocker.patch(
        "backup_websites.tortillaconsal.requests.head",
        side_effect=requests.RequestException(),
    )

    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)
    result = logic.verify_node_structure()

    assert result is False


def test_verify_node_structure_wrong_status(mocker, sample_url, sample_download_dir):
    """Test node structure verification with wrong status code."""
    mock_response = MagicMock()
    mock_response.status_code = 404
    mocker.patch(
        "backup_websites.tortillaconsal.requests.head", return_value=mock_response
    )

    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)
    result = logic.verify_node_structure()

    assert result is False


def test_find_missing_nodes_no_nodes_in_backup(mocker, sample_url, sample_download_dir):
    """Test find_missing_nodes when no nodes found in backup."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    # Mock backup directory with no node files
    backup_dir = sample_download_dir / "www.example.com" / "bitacora" / "node"
    backup_dir.mkdir(parents=True, exist_ok=True)

    missing_nodes = logic.find_missing_nodes("bitacora")

    assert missing_nodes == []


def test_find_missing_nodes_with_nodes(mocker, sample_url, sample_download_dir):
    """Test find_missing_nodes when nodes exist in backup."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    # Create mock backup directory with node HTML files (not directories)
    backup_dir = sample_download_dir / "www.example.com" / "bitacora" / "node"
    backup_dir.mkdir(parents=True, exist_ok=True)
    (backup_dir / "1.html").write_text("content")
    (backup_dir / "2.html").write_text("content")
    (backup_dir / "5.html").write_text("content")

    # Mock live site responses
    mock_response = MagicMock()
    mock_response.text = (
        '<a href="/bitacora/node/1">Node 1</a><a href="/bitacora/node/10">Node 10</a>'
    )
    mock_response.raise_for_status = MagicMock()
    mocker.patch(
        "backup_websites.tortillaconsal.requests.get", return_value=mock_response
    )
    # Mock the head request for binary search
    mock_head_response = MagicMock()
    mock_head_response.status_code = 200
    mocker.patch(
        "backup_websites.tortillaconsal.requests.head", return_value=mock_head_response
    )

    missing_nodes = logic.find_missing_nodes("bitacora")

    # Should find missing nodes (3, 4, 6, 7, 8, 9, 10)
    assert len(missing_nodes) > 0
    assert 3 in missing_nodes
    assert 10 in missing_nodes


def test_download_pagination_pages_no_pagination(
    mocker, sample_url, sample_download_dir
):
    """Test download_pagination_pages when no pagination exists."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    # Mock response with no pagination
    mock_response = MagicMock()
    mock_response.text = "<html>No pagination here</html>"
    mock_response.raise_for_status = MagicMock()
    mock_response.status_code = 404  # No pagination
    mocker.patch(
        "backup_websites.tortillaconsal.requests.head", return_value=mock_response
    )
    mocker.patch("backup_websites.tortillaconsal.subprocess.run")

    logic.download_pagination_pages("bitacora")

    # Should not download any pages


def test_download_pagination_pages_with_pagination(
    mocker, sample_url, sample_download_dir
):
    """Test download_pagination_pages when pagination exists."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    # Mock head responses for binary search - all pages up to 5 exist
    def mock_head(url, **kwargs):
        mock_response = MagicMock()
        # Extract page number from URL
        if "?page=" in url:
            page_num = int(url.split("?page=")[1].split("&")[0])
            # Pages 0-5 exist, others don't
            if page_num <= 5:
                mock_response.status_code = 200
            else:
                mock_response.status_code = 404
        else:
            mock_response.status_code = 200
        return mock_response

    mocker.patch("backup_websites.tortillaconsal.requests.head", side_effect=mock_head)

    mock_run = mocker.patch("backup_websites.tortillaconsal.subprocess.run")
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    logic.download_pagination_pages("bitacora")

    # Should attempt to download pages (0-5 = 6 pages)
    assert mock_run.called
    # Should be called 6 times (pages 0-5)
    assert mock_run.call_count == 6


def test_download_missing_nodes(mocker, sample_url, sample_download_dir):
    """Test downloading missing nodes."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    missing_nodes = [1, 2, 3]
    mock_run = mocker.patch("backup_websites.tortillaconsal.subprocess.run")
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    logic.download_missing_nodes(missing_nodes, "bitacora")

    # Should call wget for each missing node
    assert mock_run.call_count == len(missing_nodes)


def test_run_without_node_structure(mocker, sample_url, sample_download_dir):
    """Test run() when node structure doesn't exist."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    mocker.patch.object(logic, "verify_node_structure", return_value=False)
    mocker.patch.object(logic, "download_pagination_pages")
    mocker.patch.object(logic, "find_missing_nodes")

    logic.run()

    # Should not run pagination or missing node detection
    logic.download_pagination_pages.assert_not_called()
    logic.find_missing_nodes.assert_not_called()


def test_run_with_node_structure(mocker, sample_url, sample_download_dir):
    """Test run() when node structure exists."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    mocker.patch.object(logic, "verify_node_structure", return_value=True)
    mocker.patch.object(logic, "download_pagination_pages")
    mocker.patch.object(logic, "find_missing_nodes", return_value=[1, 2])
    mocker.patch.object(logic, "download_missing_nodes")

    logic.run()

    # Should run all steps
    logic.verify_node_structure.assert_called_once()
    # Should be called twice (once for each node path: bitacora and tortilla)
    assert logic.download_pagination_pages.call_count == 2
    # Should be called twice (once for each node path)
    assert logic.find_missing_nodes.call_count == 2
    # Should be called twice (once for each node path if nodes are found)
    assert logic.download_missing_nodes.call_count == 2


def test_run_no_missing_nodes(mocker, sample_url, sample_download_dir):
    """Test run() when no missing nodes are found."""
    logic = TortillaconsalBackupLogic(sample_url, sample_download_dir)

    mocker.patch.object(logic, "verify_node_structure", return_value=True)
    mocker.patch.object(logic, "download_pagination_pages")
    mocker.patch.object(logic, "find_missing_nodes", return_value=[])
    mocker.patch.object(logic, "download_missing_nodes")

    logic.run()

    # Should not download missing nodes
    logic.download_missing_nodes.assert_not_called()
