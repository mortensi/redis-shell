"""
Logging utilities for redis-shell.

This module contains utilities for logging and error handling.
"""

import logging
import sys
import os
from typing import Optional, Dict, Any

# Define log levels
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}


def setup_logging(
    level: str = 'info',
    log_file: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Set up logging for redis-shell.
    
    Args:
        level: Log level (debug, info, warning, error, critical)
        log_file: Optional log file path
        log_format: Optional log format string
        
    Returns:
        Logger instance
    """
    # Get the log level
    log_level = LOG_LEVELS.get(level.lower(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger('redis_shell')
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Set up console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(log_level)
    
    # Set up formatter
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)
    console_handler.setFormatter(formatter)
    
    # Add console handler to logger
    logger.addHandler(console_handler)
    
    # Set up file handler if log file is specified
    if log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        
        # Add file handler to logger
        logger.addHandler(file_handler)
    
    return logger


class RedisShellException(Exception):
    """Base exception class for redis-shell."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the exception.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        
    def __str__(self) -> str:
        """Return string representation of the exception."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class ConnectionError(RedisShellException):
    """Exception raised for Redis connection errors."""
    pass


class CommandError(RedisShellException):
    """Exception raised for command execution errors."""
    pass


class ConfigurationError(RedisShellException):
    """Exception raised for configuration errors."""
    pass


class ExtensionError(RedisShellException):
    """Exception raised for extension-related errors."""
    pass


def format_exception(exc: Exception) -> str:
    """
    Format an exception for display.
    
    Args:
        exc: The exception to format
        
    Returns:
        Formatted exception string
    """
    if isinstance(exc, RedisShellException):
        return str(exc)
    return f"Error: {str(exc)}"
