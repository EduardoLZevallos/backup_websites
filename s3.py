""" s3 functions """

import boto3
from botocore.exceptions import NoCredentialsError
from constants import BUCKET, LOCAL_DIRECTORY, S3_FOLDER

s3 = boto3.client("s3")


def upload_to_s3(local_file: str, bucket: str, key: str) -> None:
    """upload file to s3"""
    try:
        s3.upload_file(local_file, bucket, key)
        print(f"Upload Successful: {key}")
    except FileNotFoundError:
        print("The file was not found")
    except NoCredentialsError:
        print("Credentials not available")


def upload_all_files_to_s3() -> None:
    """upload all files from local directory constant"""
    for path in LOCAL_DIRECTORY.rglob("*"):
        if path.is_file():
            s3_path = f"{S3_FOLDER}/{path.relative_to(LOCAL_DIRECTORY)}"
            upload_to_s3(s3_path, BUCKET, str(s3_path))
