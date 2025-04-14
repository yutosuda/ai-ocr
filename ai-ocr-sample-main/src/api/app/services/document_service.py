"""
Service functions for document management.
"""
import logging
import os
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.parsers import ParserFactory
from app.extractors import ExtractorFactory
from app.validators import ValidatorFactory
from app.services.job_service import create_job

logger = logging.getLogger(__name__)


async def create_document(
    db: AsyncSession, document_data: Dict[str, Union[str, int]]
) -> Document:
    """
    Create a new document record.

    Args:
        db: Database session
        document_data: Document data

    Returns:
        Document: Created document
    """
    try:
        document = Document(**document_data)
        db.add(document)
        await db.commit()
        await db.refresh(document)
        
        # Create a processing job for the document
        await create_job(db, document.id)
        
        return document
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating document: {str(e)}")
        raise


async def get_document(db: AsyncSession, document_id: uuid.UUID) -> Optional[Document]:
    """
    Get document by ID.

    Args:
        db: Database session
        document_id: Document ID

    Returns:
        Optional[Document]: Document if found, None otherwise
    """
    query = select(Document).where(Document.id == document_id)
    result = await db.execute(query)
    return result.scalars().first()


async def get_documents(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> List[Document]:
    """
    Get documents with pagination.

    Args:
        db: Database session
        skip: Number of documents to skip
        limit: Maximum number of documents to return

    Returns:
        List[Document]: List of documents
    """
    query = select(Document).order_by(Document.uploaded_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def update_document_status(
    db: AsyncSession, document_id: uuid.UUID, status: str, error: Optional[str] = None
) -> Optional[Document]:
    """
    Update document status.

    Args:
        db: Database session
        document_id: Document ID
        status: New status
        error: Error message if status is 'error'

    Returns:
        Optional[Document]: Updated document if found, None otherwise
    """
    document = await get_document(db, document_id)
    if document:
        document.status = status
        if error:
            document.error = error
        await db.commit()
        await db.refresh(document)
    return document


async def delete_document(db: AsyncSession, document: Document) -> None:
    """
    Delete a document.

    Args:
        db: Database session
        document: Document to delete

    Returns:
        None
    """
    await db.delete(document)
    await db.commit()


async def parse_document(file_path: Union[str, Path], file_type: Optional[str] = None) -> Dict:
    """
    Parse a document file into structured data.
    
    Args:
        file_path: Path to the document file
        file_type: Optional file type override
        
    Returns:
        Dict containing the parsed document data
        
    Raises:
        ValueError: If the file cannot be parsed
        FileNotFoundError: If the file does not exist
    """
    file_path = Path(file_path)
    
    # Get file extension if not provided
    if not file_type:
        file_type = file_path.suffix.lower().lstrip(".")
    
    # Get appropriate parser
    parser = ParserFactory.get_parser(file_type)
    if not parser:
        raise ValueError(f"No parser found for file type: {file_type}")
    
    # Parse document
    try:
        parsed_data = await parser.parse(file_path, file_type)
        return parsed_data
    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}")
        raise ValueError(f"Error parsing document: {str(e)}")


async def process_document(
    file_path: Union[str, Path],
    file_type: Optional[str] = None,
    extraction_options: Optional[Dict] = None,
    validation_level: str = "standard",
) -> Tuple[Dict, float, Dict]:
    """
    Process a document file by parsing, extracting, and validating data.
    
    Args:
        file_path: Path to the document file
        file_type: Optional file type override
        extraction_options: Optional configuration for extraction
        validation_level: Validation level (basic, standard, strict)
        
    Returns:
        Tuple containing:
            - Dict with extracted data
            - Float confidence score
            - Dict with validation results
            
    Raises:
        ValueError: If the file cannot be processed
    """
    try:
        # Parse document
        parsed_data = await parse_document(file_path, file_type)
        
        # Determine document type
        if not file_type:
            file_type = Path(file_path).suffix.lower().lstrip(".")
        
        # Get extractor based on file type
        extractor_factory = ExtractorFactory()
        extractor = extractor_factory.get_extractor_for_file(f".{file_type}")
        
        # Extract data
        extraction_options = extraction_options or {}
        extracted_data, confidence = await extractor.extract(parsed_data, extraction_options)
        
        # Get validator
        document_type = extraction_options.get("document_type", "excel_table")
        validator_factory = ValidatorFactory()
        validator = validator_factory.get_validator_for_document_type(document_type)
        
        # Validate extracted data
        is_valid, validation_results = await validator.validate(
            extracted_data, validation_level=validation_level
        )
        
        return extracted_data, confidence, validation_results
    
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise ValueError(f"Error processing document: {str(e)}") 