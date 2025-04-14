"""
Factory for creating and managing data validators.

This module provides a factory class for registering and retrieving validators
based on data types. It ensures that the appropriate validator is used
for each data type.
"""
import logging
from typing import Dict, List, Optional, Type

from app.validators.base_validator import BaseValidator
from app.validators.excel_validator import ExcelValidator

logger = logging.getLogger(__name__)


class ValidatorFactory:
    """
    Factory class for managing data validators.
    
    This class handles the registration and retrieval of validators based on
    data types. It ensures that only one instance of each validator is
    created and reused.
    """
    
    _instance = None
    _validators: Dict[str, BaseValidator] = {}
    _validator_classes: Dict[str, Type[BaseValidator]] = {}
    
    def __new__(cls):
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the factory with default validators."""
        # Register default validators
        self.register_validator("excel", ExcelValidator)
    
    def register_validator(
        self,
        data_type: str,
        validator_class: Type[BaseValidator],
    ) -> None:
        """
        Register a new validator class for a data type.
        
        Args:
            data_type: The type of data this validator handles
            validator_class: The validator class to register
            
        Raises:
            ValueError: If the data type is already registered
        """
        if data_type in self._validator_classes:
            raise ValueError(f"Validator already registered for type: {data_type}")
        
        self._validator_classes[data_type] = validator_class
    
    def get_validator(self, data_type: str) -> BaseValidator:
        """
        Get a validator instance for the specified data type.
        
        This method returns a cached instance if one exists, otherwise creates
        a new instance of the appropriate validator.
        
        Args:
            data_type: The type of data to get a validator for
            
        Returns:
            An instance of the appropriate validator
            
        Raises:
            ValueError: If no validator is registered for the data type
        """
        # Check if we have a cached instance
        if data_type in self._validators:
            return self._validators[data_type]
        
        # Check if we have a registered class
        if data_type not in self._validator_classes:
            raise ValueError(f"No validator registered for type: {data_type}")
        
        # Create and cache a new instance
        validator_class = self._validator_classes[data_type]
        validator = validator_class()
        self._validators[data_type] = validator
        
        return validator
    
    def get_supported_data_types(self) -> List[str]:
        """
        Get a list of all supported data types.
        
        Returns:
            List of data types that have registered validators
        """
        return list(self._validator_classes.keys())
    
    def get_validator_for_document_type(
        self,
        document_type: str,
        data_type: Optional[str] = None,
    ) -> BaseValidator:
        """
        Get an appropriate validator based on document type.
        
        This method maps document types to data types and returns
        the appropriate validator.
        
        Args:
            document_type: The document type (e.g., "excel_table")
            data_type: Optional specific data type to use
            
        Returns:
            An instance of the appropriate validator
            
        Raises:
            ValueError: If no appropriate validator can be found
        """
        # Map document types to data types
        document_map = {
            "excel_table": "excel",
            "excel_form": "excel",
            "excel_report": "excel",
        }
        
        # Use provided data type or look up by document type
        dtype = data_type
        if not dtype:
            if document_type not in document_map:
                raise ValueError(f"Unsupported document type: {document_type}")
            dtype = document_map[document_type]
        
        return self.get_validator(dtype) 