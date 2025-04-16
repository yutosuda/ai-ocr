"""
Base validator for extracted data in the API service.

This module defines the base validator interface that all specific validators should implement.
The API validators are responsible for validating the structure and content of extracted data.
"""
import abc
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class BaseValidator(abc.ABC):
    """
    Abstract base class for data validators.
    
    All specific data type validators should inherit from this class
    and implement the required methods.
    """
    
    @abc.abstractmethod
    async def validate(
        self, 
        data: Dict[str, Any], 
        schema: Optional[Dict[str, Any]] = None,
        validation_level: str = "standard"
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate the extracted data against a schema.
        
        Args:
            data: The data to validate
            schema: Optional schema to validate against (if None, uses default schema)
            validation_level: Validation level (basic, standard, strict)
            
        Returns:
            Tuple containing:
                - Boolean indicating if validation passed
                - Dict with validation results including errors
            
        Raises:
            ValueError: If the data cannot be validated
        """
        pass
    
    @abc.abstractmethod
    async def get_default_schema(self, data_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the default schema for validating the data.
        
        Args:
            data_type: Optional data type to get specific schema
            
        Returns:
            Dict containing the default validation schema
        """
        pass
    
    @abc.abstractmethod
    def get_supported_data_types(self) -> List[str]:
        """
        Get the list of data types supported by this validator.
        
        Returns:
            List of supported data types
        """
        pass 