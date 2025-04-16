"""
Factory for creating and managing document extractors.

This module provides a factory class for registering and retrieving extractors
based on document types. It ensures that the appropriate extractor is used
for each document type.
"""
from typing import Dict, List, Optional, Type

from app.extractors.base_extractor import BaseExtractor
from app.extractors.excel_extractor import ExcelExtractor


class ExtractorFactory:
    """
    Factory class for managing document extractors.
    
    This class handles the registration and retrieval of extractors based on
    document types. It ensures that only one instance of each extractor is
    created and reused.
    """
    
    _instance = None
    _extractors: Dict[str, BaseExtractor] = {}
    _extractor_classes: Dict[str, Type[BaseExtractor]] = {}
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the factory with default extractors."""
        # Register default extractors
        self.register_extractor("excel", ExcelExtractor)
    
    def register_extractor(
        self,
        document_type: str,
        extractor_class: Type[BaseExtractor],
    ) -> None:
        """
        Register a new extractor class for a document type.
        
        Args:
            document_type: The type of document this extractor handles
            extractor_class: The extractor class to register
            
        Raises:
            ValueError: If the document type is already registered
        """
        if document_type in self._extractor_classes:
            raise ValueError(f"Extractor already registered for type: {document_type}")
        
        self._extractor_classes[document_type] = extractor_class
    
    def get_extractor(self, document_type: str) -> BaseExtractor:
        """
        Get an extractor instance for the specified document type.
        
        This method returns a cached instance if one exists, otherwise creates
        a new instance of the appropriate extractor.
        
        Args:
            document_type: The type of document to get an extractor for
            
        Returns:
            An instance of the appropriate extractor
            
        Raises:
            ValueError: If no extractor is registered for the document type
        """
        # Check if we have a cached instance
        if document_type in self._extractors:
            return self._extractors[document_type]
        
        # Check if we have a registered class
        if document_type not in self._extractor_classes:
            raise ValueError(f"No extractor registered for type: {document_type}")
        
        # Create and cache a new instance
        extractor_class = self._extractor_classes[document_type]
        extractor = extractor_class()
        self._extractors[document_type] = extractor
        
        return extractor
    
    def get_supported_document_types(self) -> List[str]:
        """
        Get a list of all supported document types.
        
        Returns:
            List of document types that have registered extractors
        """
        return list(self._extractor_classes.keys())
    
    def get_extractor_for_file(
        self,
        file_extension: str,
        document_type: Optional[str] = None,
    ) -> BaseExtractor:
        """
        Get an appropriate extractor based on file extension and optional type.
        
        This method maps common file extensions to document types and returns
        the appropriate extractor.
        
        Args:
            file_extension: The file extension (e.g., '.xlsx', '.xls')
            document_type: Optional specific document type to use
            
        Returns:
            An instance of the appropriate extractor
            
        Raises:
            ValueError: If no appropriate extractor can be found
        """
        # Map file extensions to document types
        extension_map = {
            ".xlsx": "excel",
            ".xls": "excel",
            ".xlsm": "excel",
            ".xlsb": "excel",
        }
        
        # Use provided document type or look up by extension
        doc_type = document_type
        if not doc_type:
            ext = file_extension.lower()
            if ext not in extension_map:
                raise ValueError(f"Unsupported file extension: {ext}")
            doc_type = extension_map[ext]
        
        return self.get_extractor(doc_type) 