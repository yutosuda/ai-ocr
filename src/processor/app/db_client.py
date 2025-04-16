"""
Database client for the processor service.
"""
import json
import logging
import uuid
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

logger = logging.getLogger(__name__)


class DBClient:
    """Client for database operations."""

    def __init__(self, db_url: str):
        """
        Initialize database client.

        Args:
            db_url: Database connection URL
        """
        self.db_url = db_url
        self.engine: Optional[AsyncEngine] = None

    async def initialize(self):
        """Initialize database connection."""
        try:
            # Convert standard PostgreSQL URL to async version if needed
            if self.db_url.startswith("postgresql://"):
                async_db_url = self.db_url.replace(
                    "postgresql://", "postgresql+asyncpg://"
                )
            else:
                async_db_url = self.db_url

            # Create async engine
            self.engine = create_async_engine(
                async_db_url,
                echo=False,
                future=True,
                pool_pre_ping=True,
            )
            logger.info("Database connection initialized")
        except Exception as e:
            logger.error(f"Error initializing database connection: {str(e)}")
            raise

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")

    async def get_document(self, document_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get document by ID.

        Args:
            document_id: Document ID

        Returns:
            Optional[Dict[str, Any]]: Document data if found, None otherwise
        """
        if not self.engine:
            logger.error("Database not initialized")
            return None

        try:
            async with self.engine.connect() as conn:
                query = text(
                    """
                    SELECT id, filename, file_type, file_size, file_path, status, metadata, uploaded_at, updated_at, error
                    FROM documents
                    WHERE id = :document_id
                    """
                )
                result = await conn.execute(query, {"document_id": document_id})
                row = result.fetchone()
                if row:
                    return {
                        "id": row.id,
                        "filename": row.filename,
                        "file_type": row.file_type,
                        "file_size": row.file_size,
                        "file_path": row.file_path,
                        "status": row.status,
                        "metadata": json.loads(row.metadata) if row.metadata else None,
                        "uploaded_at": row.uploaded_at,
                        "updated_at": row.updated_at,
                        "error": row.error,
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting document {document_id}: {str(e)}")
            return None

    async def get_job(self, job_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        """
        Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Optional[Dict[str, Any]]: Job data if found, None otherwise
        """
        if not self.engine:
            logger.error("Database not initialized")
            return None

        try:
            async with self.engine.connect() as conn:
                query = text(
                    """
                    SELECT id, document_id, status, progress, created_at, updated_at, completed_at, error
                    FROM jobs
                    WHERE id = :job_id
                    """
                )
                result = await conn.execute(query, {"job_id": job_id})
                row = result.fetchone()
                if row:
                    return {
                        "id": row.id,
                        "document_id": row.document_id,
                        "status": row.status,
                        "progress": row.progress,
                        "created_at": row.created_at,
                        "updated_at": row.updated_at,
                        "completed_at": row.completed_at,
                        "error": row.error,
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting job {job_id}: {str(e)}")
            return None

    async def update_job_status(
        self,
        job_id: uuid.UUID,
        status: str,
        progress: Optional[float] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        Update job status.

        Args:
            job_id: Job ID
            status: New status
            progress: New progress value
            error: Error message if status is 'failed'

        Returns:
            bool: True if updated successfully, False otherwise
        """
        if not self.engine:
            logger.error("Database not initialized")
            return False

        try:
            async with self.engine.begin() as conn:
                update_values = {"job_id": job_id, "status": status}
                if progress is not None:
                    update_values["progress"] = progress
                if error:
                    update_values["error"] = error

                if status in ["completed", "failed", "canceled"]:
                    query = text(
                        """
                        UPDATE jobs
                        SET status = :status,
                            progress = COALESCE(:progress, progress),
                            error = COALESCE(:error, error),
                            completed_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :job_id
                        """
                    )
                else:
                    query = text(
                        """
                        UPDATE jobs
                        SET status = :status,
                            progress = COALESCE(:progress, progress),
                            error = COALESCE(:error, error),
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = :job_id
                        """
                    )

                await conn.execute(query, update_values)
                return True
        except Exception as e:
            logger.error(f"Error updating job {job_id} status: {str(e)}")
            return False

    async def update_document_status(
        self, document_id: uuid.UUID, status: str, error: Optional[str] = None
    ) -> bool:
        """
        Update document status.

        Args:
            document_id: Document ID
            status: New status
            error: Error message if status is 'error'

        Returns:
            bool: True if updated successfully, False otherwise
        """
        if not self.engine:
            logger.error("Database not initialized")
            return False

        try:
            async with self.engine.begin() as conn:
                update_values = {"document_id": document_id, "status": status}
                if error:
                    update_values["error"] = error

                query = text(
                    """
                    UPDATE documents
                    SET status = :status,
                        error = COALESCE(:error, error),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :document_id
                    """
                )
                await conn.execute(query, update_values)
                return True
        except Exception as e:
            logger.error(f"Error updating document {document_id} status: {str(e)}")
            return False

    async def create_extraction(
        self,
        job_id: uuid.UUID,
        document_id: uuid.UUID,
        extracted_data: Dict[str, Any],
        confidence_score: float,
        format_type: Optional[str] = None,
        validation_results: Optional[Dict[str, Any]] = None,
    ) -> Optional[uuid.UUID]:
        """
        Create extraction record.

        Args:
            job_id: Job ID
            document_id: Document ID
            extracted_data: Extracted data
            confidence_score: Confidence score
            format_type: Format type
            validation_results: Validation results

        Returns:
            Optional[uuid.UUID]: Extraction ID if created successfully, None otherwise
        """
        if not self.engine:
            logger.error("Database not initialized")
            return None

        try:
            async with self.engine.begin() as conn:
                # Generate new UUID for extraction
                extraction_id = uuid.uuid4()
                
                query = text(
                    """
                    INSERT INTO extractions (
                        id, job_id, document_id, extracted_data, confidence_score, 
                        format_type, validation_results, extracted_at, created_at, updated_at
                    )
                    VALUES (
                        :extraction_id, :job_id, :document_id, :extracted_data, :confidence_score,
                        :format_type, :validation_results, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                )
                
                await conn.execute(
                    query,
                    {
                        "extraction_id": extraction_id,
                        "job_id": job_id,
                        "document_id": document_id,
                        "extracted_data": json.dumps(extracted_data),
                        "confidence_score": confidence_score,
                        "format_type": format_type,
                        "validation_results": json.dumps(validation_results) if validation_results else None,
                    },
                )
                
                return extraction_id
        except Exception as e:
            logger.error(f"Error creating extraction for job {job_id}: {str(e)}")
            return None 