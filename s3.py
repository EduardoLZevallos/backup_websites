# /// script
# dependencies = [
#   "boto3",
#   "click",
# ]
# ///


# TODO: need to figure out direct storage to s3 glacier
from pathlib import Path

import boto3
import click
from botocore.exceptions import ClientError, NoCredentialsError

BUCKET = "left-website-backups"

s3 = boto3.client("s3")


def test_aws_credentials():
    """Test if AWS credentials are valid by making a simple API call"""
    try:
        s3 = boto3.client("s3")
        # Test credentials with a simple operation
        s3.list_buckets()
        return True, "AWS credentials are valid"
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "SignatureDoesNotMatch":
            return False, "AWS credentials are invalid (wrong access key or secret)"
        elif error_code == "InvalidAccessKeyId":
            return False, "Invalid AWS Access Key ID"
        elif error_code == "AccessDenied":
            return False, "AWS credentials don't have permission to access S3"
        else:
            return False, f"AWS API error: {error_code}"
    except NoCredentialsError:
        return False, "No AWS credentials found"
    except Exception as e:
        return False, f"Error testing credentials: {e}"


def upload_to_s3(
    local_file: str, bucket: str, key: str, storage_class: str = "DEEP_ARCHIVE"
) -> None:
    """upload file to s3 with specified storage class"""
    try:
        s3.upload_file(
            local_file, bucket, key, ExtraArgs={"StorageClass": storage_class}
        )
        print(f"Upload Successful: {key} (Storage Class: {storage_class})")
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")
    except Exception as e:
        print(f"unexpected error: {e}")


def upload_directory_to_s3(
    s3_folder: str,
    local_directory_path: str,
    storage_class: str = "DEEP_ARCHIVE",
    bucket=BUCKET,
) -> None:
    """upload all files from specified local directory"""

    local_dir = Path(local_directory_path)
    if not local_dir.exists():
        print(f"Directory not found: {local_directory_path}")
        return

    # Check if directory contains subdirectories that look like website domains
    subdirs = [d for d in local_dir.iterdir() if d.is_dir()]

    if subdirs:
        # If there are subdirectories, upload each one as a separate S3 folder
        for subdir in subdirs:
            subdir_name = subdir.name
            print(f"Uploading subdirectory: {subdir_name}")

            for path in subdir.rglob("*"):
                if path.is_file():
                    # Create S3 path: s3_folder/subdirectory_name/relative_path
                    s3_path = f"{s3_folder}/{subdir_name}/{path.relative_to(subdir)}"
                    upload_to_s3(str(path), bucket, s3_path, storage_class)
    else:
        # If no subdirectories, upload files directly to the S3 folder
        for path in local_dir.rglob("*"):
            if path.is_file():
                s3_path = f"{s3_folder}/{path.relative_to(local_dir)}"
                upload_to_s3(str(path), bucket, s3_path, storage_class)


@click.command()
@click.argument(
    "directory_path", type=click.Path(exists=True, file_okay=False, dir_okay=True)
)
@click.option("--bucket", default=BUCKET, help="S3 bucket name")
@click.option("--s3-folder", help="S3 folder prefix", required=True)
@click.option(
    "--storage-class",
    default="DEEP_ARCHIVE",
    type=click.Choice(["STANDARD", "GLACIER", "DEEP_ARCHIVE", "INTELLIGENT_TIERING"]),
    help="S3 storage class (default: DEEP_ARCHIVE)",
)
def main(directory_path, bucket, s3_folder, storage_class):
    """Upload a directory to S3"""
    is_valid, message = test_aws_credentials()
    if not is_valid:
        click.echo(f"❌ {message}")
        click.echo("\n🔧 To fix this:")
        click.echo("1. Run: aws configure")
        click.echo("2. Enter your correct AWS Access Key ID and Secret Access Key")
        click.echo("3. Make sure your credentials have S3 write permissions")
        return

    click.echo(f"Uploading directory {directory_path} to s3://{bucket}/{s3_folder}")
    click.echo(f"Storage class: {storage_class}")
    upload_directory_to_s3(s3_folder, directory_path, storage_class)
    click.echo("Upload completed!")


if __name__ == "__main__":
    main()
