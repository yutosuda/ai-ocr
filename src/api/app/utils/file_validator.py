"""
Utility functions for file validation.
"""
import logging
import os
from typing import List, Optional

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

logger = logging.getLogger(__name__)


def validate_file(file: UploadFile) -> None:
    """
    Validate an uploaded file.

    Args:
        file: The file to validate

    Raises:
        HTTPException: If the file is invalid
    """
    # Check if file exists
    if not file:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided",
        )
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1][1:].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.ALLOWED_EXTENSIONS)}",
        )
    
    # Check file size
    try:
        file.file.seek(0, os.SEEK_END)
        file_size = file.file.tell()
        file.file.seek(0)  # Reset file position
        
        if file_size > settings.MAX_DOCUMENT_SIZE:
            max_size_mb = settings.MAX_DOCUMENT_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum allowed size is {max_size_mb:.1f} MB",
            )
    except Exception as e:
        logger.error(f"Error checking file size: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error validating file",
        )


def get_excel_file_type(file_ext: str) -> Optional[str]:
    """
    Get the Excel file type based on extension.

    Args:
        file_ext: File extension

    Returns:
        Optional[str]: Excel file type or None
    """
    excel_types = {
        "xlsx": "excel",
        "xls": "excel_legacy",
        "csv": "csv",
    }
    return excel_types.get(file_ext.lower())