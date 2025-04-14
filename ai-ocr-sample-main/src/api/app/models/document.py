"""
Document model for representing uploaded documents.
"""
import datetime
import uuid
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.db.session import Base


class Document(Base):
    """Document model for representing uploaded documents in the system."""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=False)
    file_path = Column(String(512), nullable=False)
    status = Column(
        String(20),
        nullable=False,
        default="uploaded",
        comment="uploaded, processing, processed, error",
    )
    metadata = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
    error = Column(Text, nullable=True)

    def __repr__(self) -> str:
        """String representation of the document."""
        return f"<Document {self.id}: {self.filename}>" 