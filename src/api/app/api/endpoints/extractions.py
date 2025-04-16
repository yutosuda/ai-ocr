"""
API endpoints for extraction data management.
"""
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.extraction import Extraction
from app.services.extraction_service import (
    get_extraction,
    get_extractions,
    get_extractions_by_document,
    get_extractions_by_job,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{extraction_id}", response_model=dict)
async def read_extraction(
    extraction_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """
    Get extraction data by ID.

    Args:
        extraction_id: Extraction ID
        db: Database session

    Returns:
        dict: Extraction data
    """
    extraction = await get_extraction(db, extraction_id)
    if not extraction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extraction with ID {extraction_id} not found",
        )
    
    return {
        "id": str(extraction.id),
        "job_id": str(extraction.job_id),
        "document_id": str(extraction.document_id),
        "extracted_data": extraction.extracted_data,
        "confidence_score": extraction.confidence_score,
        "format_type": extraction.format_type,
        "validation_results": extraction.validation_results,
        "extracted_at": extraction.extracted_at,
        "created_at": extraction.created_at,
    }


@router.get("/", response_model=List[dict])
async def read_extractions(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """
    Get a list of extractions.

    Args:
        skip: Number of extractions to skip
        limit: Maximum number of extractions to return
        db: Database session

    Returns:
        List[dict]: List of extraction information
    """
    extractions = await get_extractions(db, skip, limit)
    
    return [
        {
            "id": str(ext.id),
            "job_id": str(ext.job_id),
            "document_id": str(ext.document_id),
            "confidence_score": ext.confidence_score,
            "format_type": ext.format_type,
            "extracted_at": ext.extracted_at,
        }
        for ext in extractions
    ]


@router.get("/document/{document_id}", response_model=List[dict])
async def read_extractions_by_document(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """
    Get extractions for a specific document.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        List[dict]: List of extraction information
    """
    extractions = await get_extractions_by_document(db, document_id)
    
    return [
        {
            "id": str(ext.id),
            "job_id": str(ext.job_id),
            "confidence_score": ext.confidence_score,
            "format_type": ext.format_type,
            "extracted_at": ext.extracted_at,
        }
        for ext in extractions
    ]


@router.get("/job/{job_id}", response_model=List[dict])
async def read_extractions_by_job(
    job_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """
    Get extractions for a specific job.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        List[dict]: List of extraction information
    """
    extractions = await get_extractions_by_job(db, job_id)
    
    return [
        {
            "id": str(ext.id),
            "document_id": str(ext.document_id),
            "confidence_score": ext.confidence_score,
            "format_type": ext.format_type,
            "extracted_at": ext.extracted_at,
        }
        for ext in extractions
    ] 