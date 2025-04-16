"""
Excel data extractor for the API service.

This module provides an extractor for Excel data that coordinates with the
processor service for complex extraction tasks. It handles the initial extraction
setup and validation before delegating to the processor service.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.extractors.base_extractor import BaseExtractor

logger = logging.getLogger(__name__)


class ExcelExtractor(BaseExtractor):
    """
    Extractor for Excel document data.
    
    This extractor coordinates with the processor service to extract structured
    information from Excel data.
    """
    
    SUPPORTED_DOCUMENT_TYPES = ["excel_table", "excel_form", "excel_report"]
    
    def __init__(self):
        """Initialize the Excel extractor."""
        self.processor_url = settings.PROCESSOR_URL
    
    async def extract(
        self,
        parsed_data: Dict[str, Any],
        extraction_options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], float]:
        """
        Extract structured information from parsed Excel data.
        
        This method performs initial validation and setup, then delegates the
        heavy extraction work to the processor service.
        
        Args:
            parsed_data: The parsed Excel data
            extraction_options: Optional configuration for the extraction process
            
        Returns:
            Tuple containing:
                - Dict with the extracted structured data
                - Float confidence score (0.0 to 1.0)
            
        Raises:
            ValueError: If the data cannot be extracted
        """
        try:
            # Validate parsed data structure
            if not parsed_data.get("sheets"):
                raise ValueError("No sheet data found in parsed data")
            
            # Prepare extraction options
            options = extraction_options or {}
            options.update({
                "document_type": options.get("document_type", "excel_table"),
                "extraction_mode": options.get("extraction_mode", "standard"),
                "confidence_threshold": options.get("confidence_threshold", 0.7),
            })
            
            # Validate document type
            if options["document_type"] not in self.SUPPORTED_DOCUMENT_TYPES:
                raise ValueError(f"Unsupported document type: {options['document_type']}")
            
            # Prepare request data
            request_data = {
                "parsed_data": parsed_data,
                "extraction_options": options,
            }
            
            # Send extraction request to processor service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.processor_url}/api/process",
                    json=request_data,
                    timeout=30.0,
                )
                response.raise_for_status()
                
                result = response.json()
                extracted_data = result["extracted_data"]
                confidence_score = result["confidence_score"]
            
            return extracted_data, confidence_score
        
        except httpx.HTTPError as e:
            logger.error(f"HTTP error during extraction: {str(e)}")
            raise ValueError(f"Error communicating with processor service: {str(e)}")
        except Exception as e:
            logger.error(f"Error extracting data: {str(e)}")
            raise ValueError(f"Error extracting data: {str(e)}")
    
    async def get_schema(self, document_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the expected schema for the extracted data.
        
        Args:
            document_type: Optional document type to get specific schema
            
        Returns:
            Dict containing the expected schema for extracted data
        """
        # Default schema for excel_table type
        default_schema = {
            "type": "object",
            "properties": {
                "tables": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "sheet_name": {"type": "string"},
                            "table_name": {"type": "string"},
                            "headers": {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                            "data": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": True,
                                },
                            },
                        },
                        "required": ["sheet_name", "headers", "data"],
                    },
                },
                "metadata": {
                    "type": "object",
                    "properties": {
                        "document_type": {"type": "string"},
                        "extraction_mode": {"type": "string"},
                        "confidence_threshold": {"type": "number"},
                    },
                },
            },
            "required": ["tables", "metadata"],
        }
        
        # Return schema based on document type
        doc_type = document_type or "excel_table"
        if doc_type not in self.SUPPORTED_DOCUMENT_TYPES:
            raise ValueError(f"Unsupported document type: {doc_type}")
        
        # For now, return the same schema for all types
        # In the future, we can add specific schemas for different document types
        return default_schema
    
    def get_supported_document_types(self) -> List[str]:
        """
        Get the list of document types supported by this extractor.
        
        Returns:
            List of supported document types
        """
        return self.SUPPORTED_DOCUMENT_TYPES 