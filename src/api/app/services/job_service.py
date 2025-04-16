"""
Service functions for job management.
"""
import datetime
import logging
import uuid
from typing import List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document import Document
from app.models.job import Job

logger = logging.getLogger(__name__)


async def create_job(db: AsyncSession, document_id: uuid.UUID) -> Job:
    """
    Create a new processing job.

    Args:
        db: Database session
        document_id: Document ID to process

    Returns:
        Job: Created job
    """
    # Check if document exists
    document_query = select(Document).where(Document.id == document_id)
    result = await db.execute(document_query)
    document = result.scalars().first()
    
    if not document:
        raise ValueError(f"Document with ID {document_id} not found")
    
    # Create job
    job = Job(document_id=document_id, status="pending", progress=0.0)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    
    # Notify processor service asynchronously
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.PROCESSOR_URL}/api/process",
                json={"job_id": str(job.id), "document_id": str(document_id)},
                timeout=5.0,
            )
    except Exception as e:
        # Log error but don't fail - processor may poll for jobs
        logger.error(f"Error notifying processor: {str(e)}")
    
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Optional[Job]:
    """
    Get job by ID.

    Args:
        db: Database session
        job_id: Job ID

    Returns:
        Optional[Job]: Job if found, None otherwise
    """
    query = select(Job).where(Job.id == job_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_jobs(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Job]:
    """
    Get jobs with pagination.

    Args:
        db: Database session
        skip: Number of jobs to skip
        limit: Maximum number of jobs to return

    Returns:
        List[Job]: List of jobs
    """
    query = select(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def get_jobs_by_document(db: AsyncSession, document_id: uuid.UUID) -> List[Job]:
    """
    Get jobs for a document.

    Args:
        db: Database session
        document_id: Document ID

    Returns:
        List[Job]: List of jobs for the document
    """
    query = select(Job).where(Job.document_id == document_id).order_by(Job.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


async def update_job(
    db: AsyncSession,
    job_id: uuid.UUID,
    status: Optional[str] = None,
    progress: Optional[float] = None,
    error: Optional[str] = None,
) -> Optional[Job]:
    """
    Update job status and progress.

    Args:
        db: Database session
        job_id: Job ID
        status: New status
        progress: New progress value
        error: Error message if status is 'failed'

    Returns:
        Optional[Job]: Updated job if found, None otherwise
    """
    job = await get_job(db, job_id)
    if job:
        if status:
            job.status = status
            if status == "completed":
                job.progress = 100.0
                job.completed_at = datetime.datetime.utcnow()
            elif status == "failed":
                job.completed_at = datetime.datetime.utcnow()
        
        if progress is not None:
            job.progress = progress
        
        if error:
            job.error = error
        
        await db.commit()
        await db.refresh(job)
    
    return job


async def cancel_job(db: AsyncSession, job: Job) -> Job:
    """
    Cancel a job.

    Args:
        db: Database session
        job: Job to cancel

    Returns:
        Job: Canceled job
    """
    job.status = "canceled"
    job.completed_at = datetime.datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    
    # Notify processor service asynchronously
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"{settings.PROCESSOR_URL}/api/cancel",
                json={"job_id": str(job.id)},
                timeout=5.0,
            )
    except Exception as e:
        # Log error but don't fail
        logger.error(f"Error notifying processor about cancellation: {str(e)}")
    
    return job 