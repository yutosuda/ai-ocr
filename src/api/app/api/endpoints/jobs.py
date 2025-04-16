"""
API endpoints for job management.
"""
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.job import Job
from app.services.job_service import (
    cancel_job,
    create_job,
    get_job,
    get_jobs,
    get_jobs_by_document,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_processing_job(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """
    Create a new document processing job.

    Args:
        document_id: Document ID to process
        db: Database session

    Returns:
        dict: Job information
    """
    try:
        job = await create_job(db, document_id)
        
        return {
            "job_id": str(job.id),
            "document_id": str(job.document_id),
            "status": job.status,
            "created_at": job.created_at,
        }
    except Exception as e:
        logger.error(f"Error creating job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating job: {str(e)}",
        )


@router.get("/{job_id}", response_model=dict)
async def read_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Get job information by ID.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        dict: Job information
    """
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    
    return {
        "id": str(job.id),
        "document_id": str(job.document_id),
        "status": job.status,
        "progress": job.progress,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "completed_at": job.completed_at,
        "error": job.error,
    }


@router.get("/", response_model=List[dict])
async def read_jobs(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """
    Get a list of jobs.

    Args:
        skip: Number of jobs to skip
        limit: Maximum number of jobs to return
        db: Database session

    Returns:
        List[dict]: List of job information
    """
    jobs = await get_jobs(db, skip, limit)
    
    return [
        {
            "id": str(job.id),
            "document_id": str(job.document_id),
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
        for job in jobs
    ]


@router.get("/document/{document_id}", response_model=List[dict])
async def read_jobs_by_document(
    document_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    """
    Get jobs for a specific document.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        List[dict]: List of job information
    """
    jobs = await get_jobs_by_document(db, document_id)
    
    return [
        {
            "id": str(job.id),
            "status": job.status,
            "progress": job.progress,
            "created_at": job.created_at,
            "updated_at": job.updated_at,
        }
        for job in jobs
    ]


@router.post("/{job_id}/cancel", status_code=status.HTTP_200_OK, response_model=dict)
async def cancel_processing_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Cancel a processing job.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        dict: Job status information
    """
    job = await get_job(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID {job_id} not found",
        )
    
    if job.status not in ["pending", "processing"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status '{job.status}'",
        )
    
    await cancel_job(db, job)
    
    return {
        "id": str(job.id),
        "status": "canceled",
        "message": "Job canceled successfully",
    }