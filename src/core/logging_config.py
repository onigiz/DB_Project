"""
Centralized logging configuration for the application.
This module provides a consistent logging setup across all components.
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

class LogConfig:
    # Log directory
    LOG_DIR = "logs"
    
    # Log files
    SECURITY_LOG = "security.log"
    DATABASE_LOG = "database.log"
    USER_LOG = "user.log"
    SYSTEM_LOG = "system.log"
    
    # Log format
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
    
    # Log rotation settings
    MAX_BYTES = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5
    
    @classmethod
    def setup_logging(cls) -> None:
        """
        Set up the basic logging configuration.
        Creates log directory if it doesn't exist.
        """
        # Create logs directory if it doesn't exist
        os.makedirs(cls.LOG_DIR, exist_ok=True)
    
    @classmethod
    def get_logger(cls, name: str, log_file: Optional[str] = None) -> logging.Logger:
        """
        Get a logger with the specified name and configuration.
        
        Args:
            name: The name of the logger
            log_file: Optional specific log file name. If not provided, uses system.log
            
        Returns:
            logging.Logger: Configured logger instance
        """
        # Create logger
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        
        # Determine log file
        if not log_file:
            log_file = cls.SYSTEM_LOG
            
        # Create rotating file handler
        handler = RotatingFileHandler(
            os.path.join(cls.LOG_DIR, log_file),
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT
        )
        handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(cls.LOG_FORMAT, cls.DATE_FORMAT)
        handler.setFormatter(formatter)
        
        # Add handler to logger if it doesn't already have one
        if not logger.handlers:
            logger.addHandler(handler)
        
        return logger
    
    @classmethod
    def get_security_logger(cls) -> logging.Logger:
        """Get logger for security events"""
        return cls.get_logger('security_manager', cls.SECURITY_LOG)
    
    @classmethod
    def get_database_logger(cls) -> logging.Logger:
        """Get logger for database operations"""
        return cls.get_logger('database_manager', cls.DATABASE_LOG)
    
    @classmethod
    def get_user_logger(cls) -> logging.Logger:
        """Get logger for user operations"""
        return cls.get_logger('user_manager', cls.USER_LOG)
    
    @classmethod
    def log_security_event(cls, event_type: str, details: str, level: str = "INFO") -> None:
        """
        Log a security event with proper formatting.
        
        Args:
            event_type: Type of security event
            details: Event details
            level: Log level (default: INFO)
        """
        logger = cls.get_security_logger()
        log_method = getattr(logger, level.lower())
        log_method(f"{event_type}: {details}")
    
    @classmethod
    def log_database_event(cls, event_type: str, details: str, level: str = "INFO") -> None:
        """
        Log a database event with proper formatting.
        
        Args:
            event_type: Type of database event
            details: Event details
            level: Log level (default: INFO)
        """
        logger = cls.get_database_logger()
        log_method = getattr(logger, level.lower())
        log_method(f"{event_type}: {details}")
    
    @classmethod
    def log_user_event(cls, event_type: str, details: str, level: str = "INFO") -> None:
        """
        Log a user event with proper formatting.
        
        Args:
            event_type: Type of user event
            details: Event details
            level: Log level (default: INFO)
        """
        logger = cls.get_user_logger()
        log_method = getattr(logger, level.lower())
        log_method(f"{event_type}: {details}") 