"""
Factory for document parsers in the API service.

This module provides a factory for creating document parsers based on file type.
It abstracts the parser creation process and makes it easy to add support for
new file types.
"""
import logging
from typing import Dict, Optional, Type

from app.parsers.base_parser import BaseParser
from app.parsers.excel_parser import ExcelParser

logger = logging.getLogger(__name__)


class ParserFactory:
    """
    Factory for creating document parsers.
    
    This factory creates the appropriate parser based on file type and maintains
    a registry of available parsers.
    """
    
    _parsers: Dict[str, Type[BaseParser]] = {}
    
    @classmethod
    def register_parser(cls, parser_class: Type[BaseParser]) -> None:
        """
        Register a parser class with the factory.
        
        Args:
            parser_class: The parser class to register
        """
        parser_instance = parser_class()
        for file_type in parser_instance.get_supported_file_types():
            cls._parsers[file_type] = parser_class
    
    @classmethod
    def get_parser(cls, file_type: str) -> Optional[BaseParser]:
        """
        Get a parser for the specified file type.
        
        Args:
            file_type: The file type (extension without the dot)
            
        Returns:
            An instance of the appropriate parser, or None if no parser exists
        """
        if not cls._parsers:
            cls._initialize_parsers()
        
        file_type = file_type.lower().lstrip(".")
        parser_class = cls._parsers.get(file_type)
        
        if not parser_class:
            logger.warning(f"No parser found for file type: {file_type}")
            return None
        
        return parser_class()
    
    @classmethod
    def _initialize_parsers(cls) -> None:
        """Initialize the built-in parsers."""
        # Register built-in parsers
        cls.register_parser(ExcelParser)
    
    @classmethod
    def get_supported_file_types(cls) -> list:
        """
        Get a list of all supported file types.
        
        Returns:
            List of supported file extensions (without the dot)
        """
        if not cls._parsers:
            cls._initialize_parsers()
        
        return list(cls._parsers.keys()) 