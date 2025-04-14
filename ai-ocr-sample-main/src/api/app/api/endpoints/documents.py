"""
API endpoints for document management.
"""
import logging
import os
import tempfile
import uuid
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.session import get_db
from app.models.document import Document
from app.services.document_service import (
    create_document,
    delete_document,
    get_document,
    get_documents,
    parse_document,
    process_document,
)
from app.services.storage_service import store_document, get_document_url
from app.services.extraction_service import create_extraction, extract_data
from app.utils.file_validator import validate_file

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=dict)
async def upload_document(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    """
    Upload a new document for processing.

    Args:
        file: The document file to upload
        db: Database session

    Returns:
        dict: Document info including ID and processing job ID
    """
    try:
        # Validate file
        validate_file(file)

        # Store file
        file_path = await store_document(file)

        # Create document record
        document = await create_document(
            db,
            {
                "filename": file.filename,
                "file_type": file.filename.split(".")[-1].lower(),
                "file_size": file.size,
                "file_path": file_path,
                "status": "uploaded",
            },
        )

        # Return document info
        return {
            "document_id": str(document.id),
            "status": "uploaded",
            "message": "Document uploaded successfully",
        }
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}",
        )


@router.post("/parse", status_code=status.HTTP_200_OK)
async def parse_uploaded_document(
    file: UploadFile = File(...),
):
    """
    Parse an uploaded document without storing it.
    
    This endpoint allows parsing a document to preview its structure
    before committing to processing it.
    
    Args:
        file: The document file to parse
        
    Returns:
        dict: The parsed document structure
    """
    try:
        # Validate file
        validate_file(file)
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            # Write content to temp file
            content = await file.read()
            temp_file.write(content)
            temp_file.close()
            
            # Parse the document
            file_ext = os.path.splitext(file.filename)[1][1:].lower()
            parsed_data = await parse_document(temp_file.name, file_ext)
            
            return {
                "file_name": file.filename,
                "file_type": file_ext,
                "parsed_data": parsed_data,
            }
            
        finally:
            # Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
    except Exception as e:
        logger.error(f"Error parsing document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error parsing document: {str(e)}",
        )


@router.post("/{document_id}/process", status_code=status.HTTP_200_OK)
async def process_uploaded_document(
    document_id: uuid.UUID,
    document_type: Optional[str] = Form(None),
    validation_level: str = Form("standard"),
    db: AsyncSession = Depends(get_db),
):
    """
    Process a previously uploaded document.
    
    This endpoint initiates the parsing, extraction, and validation process
    for a document that has already been uploaded.
    
    Args:
        document_id: ID of the document to process
        document_type: Optional document type to use for processing
        validation_level: Validation level (basic, standard, strict)
        db: Database session
        
    Returns:
        dict: The processing results including extraction and validation
    """
    try:
        # Get document
        document = await get_document(db, document_id)
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document with ID {document_id} not found",
            )
        
        # Get document URL
        document_url = await get_document_url(document.file_path)
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        try:
            # Download file content
            async with httpx.AsyncClient() as client:
                response = await client.get(document_url)
                response.raise_for_status()
                
                # Write content to temp file
                temp_file.write(response.content)
                temp_file.close()
                
                # Process the document
                file_ext = document.file_type
                extraction_options = {"document_type": document_type} if document_type else {}
                
                extracted_data, confidence, validation_results = await process_document(
                    temp_file.name,
                    file_ext,
                    extraction_options,
                    validation_level,
                )
                
                # Create extraction record
                extraction = await create_extraction(
                    db,
                    job_id=document.jobs[0].id if document.jobs else uuid.uuid4(),
                    document_id=document_id,
                    extracted_data=extracted_data,
                    confidence_score=confidence,
                    format_type="json",
                    validation_results=validation_results,
                )
                
                return {
                    "document_id": str(document_id),
                    "extraction_id": str(extraction.id),
                    "confidence": confidence,
                    "validation_results": validation_results,
                    "is_valid": validation_results.get("valid", False),
                }
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                
    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}",
        )


@router.get("/{document_id}", response_model=dict)
async def read_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Get document information by ID.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        dict: Document information
    """
    document = await get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    return {
        "id": str(document.id),
        "filename": document.filename,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "status": document.status,
        "uploaded_at": document.uploaded_at,
        "updated_at": document.updated_at,
    }


@router.get("/", response_model=List[dict])
async def read_documents(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    """
    Get a list of documents.

    Args:
        skip: Number of documents to skip
        limit: Maximum number of documents to return
        db: Database session

    Returns:
        List[dict]: List of document information
    """
    documents = await get_documents(db, skip, limit)
    
    return [
        {
            "id": str(doc.id),
            "filename": doc.filename,
            "file_type": doc.file_type,
            "status": doc.status,
            "uploaded_at": doc.uploaded_at,
        }
        for doc in documents
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Delete a document by ID.

    Args:
        document_id: Document ID
        db: Database session

    Returns:
        None
    """
    document = await get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found",
        )
    
    await delete_document(db, document)
    return None 