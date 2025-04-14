"""
MinIO client for the document processor service.
"""
import logging
import os
import tempfile
import uuid
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import settings

logger = logging.getLogger(__name__)


class MinioClient:
    """Client for MinIO operations."""

    def __init__(
        self, minio_url: str, access_key: str, secret_key: str, bucket_name: str
    ):
        """
        Initialize MinIO client.

        Args:
            minio_url: MinIO server URL
            access_key: Access key
            secret_key: Secret key
            bucket_name: Bucket name
        """
        self.minio_url = minio_url.replace("http://", "").replace("https://", "")
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket_name = bucket_name
        self.secure = minio_url.startswith("https://")
        self.client: Optional[Minio] = None

        # Create MinIO client
        try:
            self.client = Minio(
                endpoint=self.minio_url,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure,
            )

            # Ensure bucket exists
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"Created bucket: {self.bucket_name}")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")
        except Exception as e:
            logger.error(f"Error initializing MinIO client: {str(e)}")
            self.client = None

    async def download_document(self, object_name: str) -> Optional[str]:
        """
        Download a document from MinIO.

        Args:
            object_name: Object name in MinIO

        Returns:
            Optional[str]: Local file path if downloaded successfully, None otherwise
        """
        if not self.client:
            logger.error("MinIO client not initialized")
            return None

        try:
            # Create a temporary file with the extension from object_name
            _, ext = os.path.splitext(object_name)
            local_file_fd, local_file_path = tempfile.mkstemp(
                suffix=ext, dir=settings.TEMP_DIR
            )
            os.close(local_file_fd)  # Close the file descriptor

            # Download the object
            self.client.fget_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=local_file_path,
            )
            
            logger.info(f"Downloaded {object_name} to {local_file_path}")
            return local_file_path
        except S3Error as e:
            logger.error(f"MinIO error downloading {object_name}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error downloading {object_name}: {str(e)}")
            return None

    async def upload_document(self, file_path: str, content_type: str) -> Optional[str]:
        """
        Upload a document to MinIO.

        Args:
            file_path: Local file path
            content_type: Content type

        Returns:
            Optional[str]: Object name if uploaded successfully, None otherwise
        """
        if not self.client:
            logger.error("MinIO client not initialized")
            return None

        try:
            # Create a unique object name
            _, ext = os.path.splitext(file_path)
            object_name = f"documents/{uuid.uuid4()}{ext}"
            
            # Upload the file
            self.client.fput_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
            )
            
            logger.info(f"Uploaded {file_path} to {object_name}")
            return object_name
        except S3Error as e:
            logger.error(f"MinIO error uploading {file_path}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error uploading {file_path}: {str(e)}")
            return None 