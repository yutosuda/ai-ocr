"""
Base parser for document files in the API service.

This module defines the base parser interface that all specific parsers should implement.
The API parsers are responsible for initial file processing and validation before
delegating heavy processing to the processor service.
"""
import abc
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class BaseParser(abc.ABC):
    """
    Abstract base class for document parsers.
    
    All specific file type parsers should inherit from this class
    and implement the required methods.
    """
    
    @abc.abstractmethod
    async def parse(self, file_path: Union[str, Path], file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Parse the document file and return structured data.
        
        Args:
            file_path: Path to the document file
            file_type: Optional file type override
            
        Returns:
            Dict containing the parsed document data
            
        Raises:
            ValueError: If the file cannot be parsed
            FileNotFoundError: If the file does not exist
        """
        pass
    
    @abc.abstractmethod
    async def validate(self, file_path: Union[str, Path], file_type: Optional[str] = None) -> bool:
        """
        Validate that the file can be parsed by this parser.
        
        Args:
            file_path: Path to the document file
            file_type: Optional file type override
            
        Returns:
            True if the file can be parsed, False otherwise
        """
        pass
    
    @abc.abstractmethod
    def get_supported_file_types(self) -> List[str]:
        """
        Get the list of file types supported by this parser.
        
        Returns:
            List of supported file extensions (without the dot)
        """
        pass 