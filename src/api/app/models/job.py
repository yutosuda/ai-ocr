"""
Job model for representing document processing jobs.
"""
import datetime
import uuid
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Job(Base):
    """Job model for representing document processing jobs in the system."""

    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="pending, processing, completed, failed, canceled",
    )
    progress = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
    completed_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)

    # Relationships
    document = relationship("Document", backref="jobs")

    def __repr__(self) -> str:
        """String representation of the job."""
        return f"<Job {self.id}: {self.status}>" 