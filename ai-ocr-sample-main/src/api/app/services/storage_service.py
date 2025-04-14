"""
Service functions for file storage using MinIO.
"""
import io
import logging
import os
import uuid
from typing import Optional

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize MinIO client
minio_client = Minio(
    endpoint=settings.MINIO_URL.replace("http://", "").replace("https://", ""),
    access_key=settings.MINIO_ROOT_USER,
    secret_key=settings.MINIO_ROOT_PASSWORD,
    secure=settings.MINIO_URL.startswith("https://"),
)

# Ensure bucket exists
try:
    if not minio_client.bucket_exists(settings.MINIO_BUCKET):
        minio_client.make_bucket(settings.MINIO_BUCKET)
        logger.info(f"Created bucket: {settings.MINIO_BUCKET}")
except Exception as e:
    logger.error(f"Error initializing MinIO bucket: {str(e)}")


async def store_document(file: UploadFile) -> str:
    """
    Store a document file in MinIO.

    Args:
        file: The file to store

    Returns:
        str: The file path in MinIO
    """
    try:
        # Create a unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        object_name = f"documents/{unique_filename}"
        
        # Read file content
        content = await file.read()
        file_size = len(content)
        
        # Store file in MinIO
        minio_client.put_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            data=io.BytesIO(content),
            length=file_size,
            content_type=file.content_type,
        )
        
        # Reset file cursor for potential future reads
        await file.seek(0)
        
        return object_name
    except S3Error as e:
        logger.error(f"MinIO error storing document: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error storing document: {str(e)}")
        raise


async def get_document_url(object_name: str, expires: int = 3600) -> str:
    """
    Get a presigned URL for a document.

    Args:
        object_name: The object name in MinIO
        expires: URL expiration time in seconds

    Returns:
        str: Presigned URL for the document
    """
    try:
        url = minio_client.presigned_get_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
            expires=expires,
        )
        return url
    except Exception as e:
        logger.error(f"Error getting document URL: {str(e)}")
        raise


async def delete_document(object_name: str) -> bool:
    """
    Delete a document from MinIO.

    Args:
        object_name: The object name in MinIO

    Returns:
        bool: True if deleted successfully, False otherwise
    """
    try:
        minio_client.remove_object(
            bucket_name=settings.MINIO_BUCKET,
            object_name=object_name,
        )
        return True
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        return False 