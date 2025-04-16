"""
Document extraction package for the API service.

This package provides classes for extracting structured information from
various document types. It coordinates with the processor service for
complex extraction tasks.
"""

from app.extractors.base_extractor import BaseExtractor
from app.extractors.excel_extractor import ExcelExtractor
from app.extractors.extractor_factory import ExtractorFactory

__all__ = [
    "BaseExtractor",
    "ExcelExtractor",
    "ExtractorFactory",
]
