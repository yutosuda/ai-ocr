"""
Logger module for the AI-OCR processor service.

This module provides a centralized logging interface using loguru for enhanced logging
features. It supports structured logging with context information, different output
formats, and multiple destinations.
"""
import os
import sys
import json
from typing import Any, Dict, Optional, Union

from loguru import logger

from app.config import settings

# Remove default handler
logger.remove()

# Add console handler with appropriate log level
log_level = settings.LOG_LEVEL.upper()
logger.add(
    sys.stdout,
    level=log_level,
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
    serialize=False,  # Set to True for JSON output
)

# Add file handler for error logs if not in debug mode
if not settings.DEBUG:
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/processor_errors.log",
        level="ERROR",
        rotation="10 MB",
        retention="1 month",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | {name}:{function}:{line} | {message}",
    )


class Logger:
    """
    Logger class that provides a centralized logging interface.
    
    This class uses loguru for enhanced logging features and provides methods
    for different log levels. It supports structured logging with context information
    and can be configured to output logs in different formats and to different
    destinations.
    """
    
    def __init__(self, name: str):
        """
        Initialize logger with module name for context.
        
        Args:
            name: Module name
        """
        self.name = name
        self.context: Dict[str, Any] = {"service": "processor"}
    
    def with_context(self, **kwargs) -> "Logger":
        """
        Add context information to the logger.
        
        Args:
            **kwargs: Context key-value pairs
            
        Returns:
            Logger with updated context
        """
        logger_instance = Logger(self.name)
        logger_instance.context = {**self.context, **kwargs}
        return logger_instance
    
    def with_job(self, job_id: str) -> "Logger":
        """
        Add job ID to logger context.
        
        Args:
            job_id: Job ID
            
        Returns:
            Logger with job ID in context
        """
        return self.with_context(job_id=job_id)
    
    def with_document(self, document_id: str) -> "Logger":
        """
        Add document ID to logger context.
        
        Args:
            document_id: Document ID
            
        Returns:
            Logger with document ID in context
        """
        return self.with_context(document_id=document_id)
    
    def _log(self, level: str, message: str, **kwargs):
        """
        Log a message with context information.
        
        Args:
            level: Log level
            message: Log message
            **kwargs: Additional context key-value pairs
        """
        context = {**self.context, **kwargs}
        context_str = json.dumps(context) if context else ""
        
        # Get the calling function's module
        frame = sys._getframe(2)
        module = frame.f_globals.get("__name__", "")
        function = frame.f_code.co_name
        line = frame.f_lineno
        
        # Log with module name as name
        logger.bind(name=self.name, function=function, line=line).log(
            level, f"{message} {context_str}" if context_str else message
        )
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log("DEBUG", message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log("INFO", message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log("WARNING", message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log("ERROR", message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log("CRITICAL", message, **kwargs)
    
    def exception(self, message: str, exc: Optional[Exception] = None, **kwargs):
        """
        Log exception with traceback.
        
        Args:
            message: Log message
            exc: Exception object
            **kwargs: Additional context key-value pairs
        """
        if exc:
            kwargs["exception"] = str(exc)
        self._log("ERROR", message, **kwargs)
        if exc:
            logger.exception(exc)


# Create a singleton instance for each module
_loggers: Dict[str, Logger] = {}


def get_logger(name: str) -> Logger:
    """
    Get or create a logger for a module.
    
    Args:
        name: Module name
        
    Returns:
        Logger instance
    """
    if name not in _loggers:
        _loggers[name] = Logger(name)
    return _loggers[name] 