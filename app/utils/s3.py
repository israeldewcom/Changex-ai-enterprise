"""
AWS S3 file upload and management.
"""
import boto3
from botocore.exceptions import ClientError
from flask import current_app
from werkzeug.utils import secure_filename
import uuid
import os
from typing import Optional, BinaryIO

class S3Client:
    """Singleton S3 client."""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_client()
        return cls._instance

    def _init_client(self):
        self.client = boto3.client(
            's3',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY_ID'],
            aws_secret_access_key=current_app.config['AWS_SECRET_ACCESS_KEY'],
            region_name=current_app.config['AWS_REGION']
        )
        self.bucket = current_app.config['AWS_S3_BUCKET']

    def upload_fileobj(self, file_obj: BinaryIO, folder: str = 'uploads') -> Optional[str]:
        """
        Upload a file-like object to S3.
        Returns the public URL or None on failure.
        """
        filename = secure_filename(getattr(file_obj, 'filename', 'file'))
        unique_id = uuid.uuid4().hex
        key = f"{folder}/{unique_id}_{filename}"
        try:
            self.client.upload_fileobj(
                file_obj,
                self.bucket,
                key,
                ExtraArgs={'ACL': 'private'}
            )
            # Generate URL (could also use cloudfront)
            url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
            return url
        except ClientError as e:
            current_app.logger.error(f"S3 upload failed: {e}")
            return None

    def delete_file(self, key: str) -> bool:
        """Delete file from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            current_app.logger.error(f"S3 delete failed: {e}")
            return False

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> Optional[str]:
        """Generate a presigned URL for temporary access."""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expiration
            )
            return url
        except ClientError as e:
            current_app.logger.error(f"S3 presigned URL failed: {e}")
            return None

# Global instance
s3_client = S3Client()

def upload_file_to_s3(file, folder='uploads'):
    return s3_client.upload_fileobj(file, folder)

def delete_file_from_s3(key):
    return s3_client.delete_file(key)

def get_presigned_url(key, expiration=3600):
    return s3_client.generate_presigned_url(key, expiration)
