"""
Service functions for extraction data management.
"""
import datetime
import json
import logging
import uuid
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.extraction import Extraction
from app.extractors import ExtractorFactory
from app.validators import ValidatorFactory

logger = logging.getLogger(__name__)


async def create_extraction(
    db: AsyncSession,
    job_id: uuid.UUID,
    document_id: uuid.UUID,
    extracted_data: Dict,
    confidence_score: float,
    format_type: str = None,
    validation_results: Dict = None,
) -> Extraction:
    """
    Create a new extraction record.

    Args:
        db: Database session
        job_id: Job ID
        document_id: Document ID
        extracted_data: Extracted data
        confidence_score: Confidence score
        format_type: Format type
        validation_results: Validation results

    Returns:
        Extraction: Created extraction
    """
    try:
        extraction = Extraction(
            job_id=job_id,
            document_id=document_id,
            extracted_data=extracted_data,
            confidence_score=confidence_score,
            format_type=format_type,
            validation_results=validation_results,
            extracted_at=datetime.datetime.utcnow(),
        )
        db.add(extraction)
        await db.commit()
        await db.refresh(extraction)
        return extraction
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating extraction: {str(e)}")
        raise


async def get_extraction(
    db: AsyncSession, extraction_id: uuid.UUID
) -> Optional[Extraction]:
    """
    Get extraction by ID.

    Args:
        db: Database session
        extraction_id: Extraction ID

    Returns:
        Optional[Extraction]: Extraction if found, None otherwise
    """
    query = select(Extraction).where(Extraction.id == extraction_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_extractions(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[Extraction]:
    """
    Get extractions with pagination.

    Args:
        db: Database session
        skip: Number of extractions to skip
        limit: Maximum number of extractions to return

    Returns:
        List[Extraction]: List of extractions
    """
    query = (
        select(Extraction)
        .order_by(Extraction.extracted_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_extractions_by_document(
    db: AsyncSession, document_id: uuid.UUID
) -> List[Extraction]:
    """
    Get extractions for a document.

    Args:
        db: Database session
        document_id: Document ID

    Returns:
        List[Extraction]: List of extractions for the document
    """
    query = (
        select(Extraction)
        .where(Extraction.document_id == document_id)
        .order_by(Extraction.extracted_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


async def get_extractions_by_job(
    db: AsyncSession, job_id: uuid.UUID
) -> List[Extraction]:
    """
    Get extractions for a job.

    Args:
        db: Database session
        job_id: Job ID

    Returns:
        List[Extraction]: List of extractions for the job
    """
    query = (
        select(Extraction)
        .where(Extraction.job_id == job_id)
        .order_by(Extraction.extracted_at.desc())
    )
    result = await db.execute(query)
    return result.scalars().all()


async def update_extraction_notes(
    db: AsyncSession, extraction_id: uuid.UUID, notes: str
) -> Optional[Extraction]:
    """
    Update extraction notes.

    Args:
        db: Database session
        extraction_id: Extraction ID
        notes: Notes text

    Returns:
        Optional[Extraction]: Updated extraction if found, None otherwise
    """
    extraction = await get_extraction(db, extraction_id)
    if extraction:
        extraction.notes = notes
        await db.commit()
        await db.refresh(extraction)
    return extraction


async def extract_data(
    parsed_data: Dict,
    file_type: str,
    document_type: Optional[str] = None,
    extraction_options: Optional[Dict] = None,
    validation_level: str = "standard",
) -> Tuple[Dict, float, Dict]:
    """
    Extract structured data from parsed document data.
    
    Args:
        parsed_data: The parsed document data
        file_type: File type (e.g., 'xlsx', 'csv')
        document_type: Optional document type
        extraction_options: Optional configuration for extraction
        validation_level: Validation level (basic, standard, strict)
        
    Returns:
        Tuple containing:
            - Dict with extracted data
            - Float confidence score
            - Dict with validation results
            
    Raises:
        ValueError: If the data cannot be extracted
    """
    try:
        # Get extractor based on file type
        extractor_factory = ExtractorFactory()
        extractor = extractor_factory.get_extractor_for_file(f".{file_type}", document_type)
        
        # Extract data
        options = extraction_options or {}
        if document_type:
            options["document_type"] = document_type
            
        extracted_data, confidence = await extractor.extract(parsed_data, options)
        
        # Get validator
        actual_document_type = options.get("document_type", document_type or "excel_table")
        validator_factory = ValidatorFactory()
        validator = validator_factory.get_validator_for_document_type(actual_document_type)
        
        # Validate extracted data
        is_valid, validation_results = await validator.validate(
            extracted_data, validation_level=validation_level
        )
        
        return extracted_data, confidence, validation_results
    
    except Exception as e:
        logger.error(f"Error extracting data: {str(e)}")
        raise ValueError(f"Error extracting data: {str(e)}")