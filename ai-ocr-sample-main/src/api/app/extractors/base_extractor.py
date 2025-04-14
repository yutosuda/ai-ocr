"""
Base extractor for document data in the API service.

This module defines the base extractor interface that all specific extractors should implement.
The API extractors coordinate with the processor service for complex extraction tasks.
"""
import abc
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)


class BaseExtractor(abc.ABC):
    """
    Abstract base class for document data extractors.
    
    All specific file type extractors should inherit from this class
    and implement the required methods.
    """
    
    @abc.abstractmethod
    async def extract(self, parsed_data: Dict[str, Any], extraction_options: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], float]:
        """
        Extract structured information from parsed document data.
        
        Args:
            parsed_data: The parsed document data
            extraction_options: Optional configuration for the extraction process
            
        Returns:
            Tuple containing:
                - Dict with the extracted structured data
                - Float confidence score (0.0 to 1.0)
            
        Raises:
            ValueError: If the data cannot be extracted
        """
        pass
    
    @abc.abstractmethod
    async def get_schema(self, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the expected schema for the extracted data.
        
        Args:
            document_type: Optional document type to get specific schema
            
        Returns:
            Dict containing the expected schema for extracted data
        """
        pass
    
    @abc.abstractmethod
    def get_supported_document_types(self) -> List[str]:
        """
        Get the list of document types supported by this extractor.
        
        Returns:
            List of supported document types
        """
        pass 