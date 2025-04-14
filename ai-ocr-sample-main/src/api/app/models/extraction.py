"""
Extraction model for representing data extracted from documents.
"""
import datetime
import uuid

from sqlalchemy import Column, DateTime, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.db.session import Base


class Extraction(Base):
    """Extraction model for representing data extracted from documents."""

    __tablename__ = "extractions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False
    )
    extracted_data = Column(JSON, nullable=True)
    confidence_score = Column(Float, nullable=True)
    format_type = Column(String(50), nullable=True, comment="JSON schema format type")
    validation_results = Column(JSON, nullable=True)
    extracted_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
    notes = Column(Text, nullable=True)

    # Relationships
    job = relationship("Job", backref="extractions")
    document = relationship("Document", backref="extractions")

    def __repr__(self) -> str:
        """String representation of the extraction."""
        return f"<Extraction {self.id}: {self.format_type}>" 