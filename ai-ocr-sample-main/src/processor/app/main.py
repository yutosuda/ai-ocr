"""
Main application entry point for the document processor service.
"""
import os
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
import uuid

from app.parsers.excel_parser import ExcelParser
from app.extractors.langchain_extractor import LangChainExtractor
from app.validators.schema_validator import SchemaValidator
from app.config import settings
from app.db_client import DBClient
from app.minio_client import MinioClient
from app.redis_client import RedisClient
from app.logger import get_logger

# Initialize logger
logger = get_logger("main")

# Initialize clients
db_client = DBClient(settings.DATABASE_URL)
minio_client = MinioClient(
    settings.MINIO_URL,
    settings.MINIO_ROOT_USER,
    settings.MINIO_ROOT_PASSWORD,
    settings.MINIO_BUCKET,
)
redis_client = RedisClient(settings.REDIS_URL)

# Initialize FastAPI app
app = FastAPI(
    title="AI-OCR Document Processor",
    description="Document processor service for AI-powered OCR and data extraction",
    version="0.1.0",
)

# Initialize processing components
excel_parser = ExcelParser()
langchain_extractor = LangChainExtractor(
    model_name=settings.MODEL_NAME,
    model_temperature=settings.MODEL_TEMPERATURE,
    api_key=settings.MODEL_API_KEY,
)
schema_validator = SchemaValidator()


class ProcessRequest(BaseModel):
    """Process request model."""
    job_id: uuid.UUID = Field(..., description="Job ID")
    document_id: uuid.UUID = Field(..., description="Document ID")


class CancelRequest(BaseModel):
    """Cancel request model."""
    job_id: uuid.UUID = Field(..., description="Job ID")


async def process_document(job_id: uuid.UUID, document_id: uuid.UUID):
    """
    Process a document in the background.

    Args:
        job_id: Job ID
        document_id: Document ID
    """
    # Create a logger with job and document context
    job_logger = logger.with_context(job_id=str(job_id), document_id=str(document_id))
    
    try:
        # Update job status to processing
        await db_client.update_job_status(job_id, "processing", progress=10.0)
        
        # Get document information
        document = await db_client.get_document(document_id)
        if not document:
            job_logger.error("Document not found")
            await db_client.update_job_status(
                job_id, "failed", error="Document not found"
            )
            return
        
        # Download document from MinIO
        job_logger.info(f"Downloading document {document.filename} from storage")
        local_file_path = await minio_client.download_document(document.file_path)
        if not local_file_path:
            job_logger.error("Failed to download document")
            await db_client.update_job_status(
                job_id, "failed", error="Failed to download document"
            )
            return
        
        # Update job progress
        await db_client.update_job_status(job_id, "processing", progress=20.0)
        
        # Parse document based on file type
        try:
            file_extension = os.path.splitext(document.filename)[1].lower()[1:]
            
            if file_extension in ["xlsx", "xls", "csv"]:
                job_logger.info(f"Parsing Excel document {document.filename}")
                parsed_data = await excel_parser.parse(local_file_path, file_extension)
            else:
                job_logger.error(f"Unsupported file type: {file_extension}")
                await db_client.update_job_status(
                    job_id, "failed", error=f"Unsupported file type: {file_extension}"
                )
                return
            
            # Update job progress
            await db_client.update_job_status(job_id, "processing", progress=40.0)
            
            # Extract structured data using LangChain/LangGraph
            job_logger.info(f"Extracting data from document {document.filename}")
            extracted_data, confidence_score = await langchain_extractor.extract(parsed_data)
            
            # Update job progress
            await db_client.update_job_status(job_id, "processing", progress=70.0)
            
            # Validate extracted data
            job_logger.info(f"Validating extracted data for document {document.filename}")
            validation_results = await schema_validator.validate(extracted_data)
            
            # Update job progress
            await db_client.update_job_status(job_id, "processing", progress=90.0)
            
            # Store extraction results
            job_logger.info(f"Storing extraction results for document {document.filename}")
            await db_client.create_extraction(
                job_id=job_id,
                document_id=document_id,
                extracted_data=extracted_data,
                confidence_score=confidence_score,
                format_type="json",  # Default format type
                validation_results=validation_results,
            )
            
            # Update document status
            await db_client.update_document_status(document_id, "processed")
            
            # Complete the job
            await db_client.update_job_status(job_id, "completed", progress=100.0)
            job_logger.info(f"Document {document.filename} processed successfully")
            
        except Exception as e:
            job_logger.exception(f"Error processing document", exc=e)
            await db_client.update_job_status(
                job_id, "failed", error=f"Processing error: {str(e)}"
            )
            
        finally:
            # Clean up temporary file
            if local_file_path and os.path.exists(local_file_path):
                os.remove(local_file_path)
                
    except Exception as e:
        job_logger.exception(f"Unhandled error in process_document", exc=e)
        try:
            await db_client.update_job_status(
                job_id, "failed", error=f"System error: {str(e)}"
            )
        except Exception:
            pass


@app.post("/api/process")
async def api_process_document(
    request: ProcessRequest, background_tasks: BackgroundTasks
):
    """
    Process a document asynchronously.

    Args:
        request: Process request containing job and document IDs
        background_tasks: FastAPI background tasks

    Returns:
        dict: Response with status
    """
    try:
        logger.info(f"Received processing request", job_id=str(request.job_id), document_id=str(request.document_id))
        
        # Validate that job exists
        job = await db_client.get_job(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")
        
        # Add the processing task to background tasks
        background_tasks.add_task(
            process_document, request.job_id, request.document_id
        )
        
        return {
            "status": "processing",
            "message": f"Document processing started for job {request.job_id}",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error processing document request", exc=e)
        raise HTTPException(
            status_code=500,
            detail=f"Error processing document: {str(e)}",
        )


@app.post("/api/cancel")
async def api_cancel_processing(request: CancelRequest):
    """
    Cancel a processing job.

    Args:
        request: Cancel request containing job ID

    Returns:
        dict: Response with status
    """
    try:
        logger.info(f"Received cancellation request for job {request.job_id}")
        
        # Update job status to canceled
        job = await db_client.get_job(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {request.job_id} not found")
        
        if job["status"] not in ["pending", "processing"]:
            return {
                "status": "not_canceled",
                "message": f"Job {request.job_id} is already in status {job['status']}",
            }
        
        # Update job status
        await db_client.update_job_status(request.job_id, "canceled")
        
        return {
            "status": "canceled",
            "message": f"Job {request.job_id} canceled",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error handling cancel request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error canceling job: {str(e)}")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_event():
    """Initialize components on application startup."""
    logger.info("Initializing document processor service")
    
    # Initialize services
    await redis_client.initialize()
    await db_client.initialize()
    
    logger.info("Document processor service initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    logger.info("Shutting down document processor service")
    
    # Close connections
    await redis_client.close()
    await db_client.close() 