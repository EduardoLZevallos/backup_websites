"""Tests for s3 module."""

from unittest.mock import MagicMock

import pytest
from backup_websites.s3 import (
    BUCKET,
    test_aws_credentials,
    upload_directory_to_s3,
    upload_to_s3,
)
from botocore.exceptions import ClientError, NoCredentialsError


def test_test_aws_credentials_success(mocker):
    """Test successful AWS credentials test."""
    mock_s3 = mocker.patch("backup_websites.s3.boto3.client")
    mock_client = MagicMock()
    mock_client.list_buckets.return_value = {}
    mock_s3.return_value = mock_client

    is_valid, message = test_aws_credentials()

    assert is_valid is True
    assert "valid" in message.lower()
    mock_client.list_buckets.assert_called_once()


def test_test_aws_credentials_invalid_signature(mocker):
    """Test AWS credentials with invalid signature."""
    mock_s3 = mocker.patch("backup_websites.s3.boto3.client")
    error = ClientError({"Error": {"Code": "SignatureDoesNotMatch"}}, "list_buckets")
    mock_s3.side_effect = error

    is_valid, message = test_aws_credentials()

    assert is_valid is False
    assert "invalid" in message.lower()


def test_test_aws_credentials_no_credentials(mocker):
    """Test AWS credentials when no credentials are found."""
    mocker.patch("backup_websites.s3.boto3.client", side_effect=NoCredentialsError())

    is_valid, message = test_aws_credentials()

    assert is_valid is False
    assert "no aws credentials" in message.lower()


def test_upload_to_s3_success(mocker, temp_dir):
    """Test successful file upload to S3."""
    mock_s3 = mocker.patch("backup_websites.s3.s3")
    test_file = temp_dir / "test.txt"
    test_file.write_text("test content")

    upload_to_s3(str(test_file), BUCKET, "test/key.txt", "STANDARD")

    mock_s3.upload_file.assert_called_once_with(
        str(test_file),
        BUCKET,
        "test/key.txt",
        ExtraArgs={"StorageClass": "STANDARD"},
    )


def test_upload_to_s3_file_not_found(mocker, temp_dir):
    """Test upload when file doesn't exist."""
    mock_s3 = mocker.patch("backup_websites.s3.s3")
    mock_s3.upload_file.side_effect = FileNotFoundError()

    with pytest.raises(FileNotFoundError):
        upload_to_s3("nonexistent.txt", BUCKET, "test/key.txt")


def test_upload_directory_to_s3_with_subdirs(mocker, temp_dir):
    """Test uploading directory with subdirectories."""
    mock_upload = mocker.patch("backup_websites.s3.upload_to_s3")

    # Create directory structure
    subdir = temp_dir / "subdir"
    subdir.mkdir()
    (subdir / "file1.txt").write_text("content1")
    (subdir / "file2.txt").write_text("content2")

    upload_directory_to_s3("s3-folder", str(temp_dir), "STANDARD", BUCKET)

    # Should be called twice (once for each file)
    assert mock_upload.call_count == 2
    # Verify paths are correct
    assert "s3-folder/subdir/file1.txt" in str(mock_upload.call_args_list[0][0][2])
    assert "s3-folder/subdir/file2.txt" in str(mock_upload.call_args_list[1][0][2])


def test_upload_directory_to_s3_no_subdirs(mocker, temp_dir):
    """Test uploading directory without subdirectories."""
    mock_upload = mocker.patch("backup_websites.s3.upload_to_s3")

    # Create files directly in directory
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.txt").write_text("content2")

    upload_directory_to_s3("s3-folder", str(temp_dir), "STANDARD", BUCKET)

    # Should be called twice
    assert mock_upload.call_count == 2
    # Verify paths are correct
    assert "s3-folder/file1.txt" in str(mock_upload.call_args_list[0][0][2])
    assert "s3-folder/file2.txt" in str(mock_upload.call_args_list[1][0][2])


def test_upload_directory_to_s3_nonexistent(mocker):
    """Test uploading nonexistent directory."""
    mock_upload = mocker.patch("backup_websites.s3.upload_to_s3")

    upload_directory_to_s3("s3-folder", "/nonexistent/path", "STANDARD", BUCKET)

    # Should not call upload
    mock_upload.assert_not_called()
