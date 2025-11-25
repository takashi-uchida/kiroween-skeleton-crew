"""
Structured logging configuration for Agent Runner.

This module provides JSON-formatted structured logging with configurable
log levels and automatic secret masking.

Requirements: 12.1, 12.2, 12.4
"""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from necrocode.agent_runner.security import SecretMasker


class StructuredFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Formats log records as JSON objects with consistent fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger: Logger name
    - message: Log message
    - runner_id: Runner ID (if available)
    - task_id: Task ID (if available)
    - spec_name: Spec name (if available)
    - Additional context fields
    
    Requirements: 12.1, 12.2
    """
    
    def __init__(
        self,
        secret_masker: Optional[SecretMasker] = None,
        include_extra: bool = True
    ):
        """
        Initialize structured formatter.
        
        Args:
            secret_masker: Secret masker for sensitive data
            include_extra: Whether to include extra fields from log record
        """
        super().__init__()
        self.secret_masker = secret_masker
        self.include_extra = include_extra
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            JSON-formatted log string
        """
        # Build base log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add runner context if available
        if hasattr(record, "runner_id"):
            log_entry["runner_id"] = record.runner_id
        if hasattr(record, "task_id"):
            log_entry["task_id"] = record.task_id
        if hasattr(record, "spec_name"):
            log_entry["spec_name"] = record.spec_name
        
        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if enabled
        if self.include_extra:
            # Get extra fields (excluding standard fields)
            standard_fields = {
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "message", "pathname", "process", "processName",
                "relativeCreated", "thread", "threadName", "exc_info",
                "exc_text", "stack_info", "runner_id", "task_id", "spec_name"
            }
            
            extra_fields = {
                key: value
                for key, value in record.__dict__.items()
                if key not in standard_fields
            }
            
            if extra_fields:
                log_entry["extra"] = extra_fields
        
        # Convert to JSON
        json_str = json.dumps(log_entry, default=str)
        
        # Mask secrets if masker is available
        if self.secret_masker:
            json_str = self.secret_masker.mask(json_str)
        
        return json_str


class RunnerLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds runner context to log records.
    
    Automatically adds runner_id, task_id, and spec_name to all log records,
    making it easy to trace logs back to specific task executions.
    
    Requirements: 12.1, 12.2
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        runner_id: str,
        task_id: Optional[str] = None,
        spec_name: Optional[str] = None
    ):
        """
        Initialize logger adapter.
        
        Args:
            logger: Base logger
            runner_id: Runner ID
            task_id: Task ID (optional)
            spec_name: Spec name (optional)
        """
        super().__init__(logger, {})
        self.runner_id = runner_id
        self.task_id = task_id
        self.spec_name = spec_name
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """
        Process log message and add context.
        
        Args:
            msg: Log message
            kwargs: Keyword arguments
            
        Returns:
            Tuple of (message, kwargs) with added context
        """
        # Add runner context to extra fields
        extra = kwargs.get("extra", {})
        extra["runner_id"] = self.runner_id
        if self.task_id:
            extra["task_id"] = self.task_id
        if self.spec_name:
            extra["spec_name"] = self.spec_name
        kwargs["extra"] = extra
        
        return msg, kwargs
    
    def update_context(
        self,
        task_id: Optional[str] = None,
        spec_name: Optional[str] = None
    ) -> None:
        """
        Update logger context.
        
        Args:
            task_id: New task ID
            spec_name: New spec name
        """
        if task_id is not None:
            self.task_id = task_id
        if spec_name is not None:
            self.spec_name = spec_name


def setup_logging(
    log_level: str = "INFO",
    structured: bool = True,
    log_file: Optional[Path] = None,
    secret_masker: Optional[SecretMasker] = None
) -> None:
    """
    Setup logging configuration for Agent Runner.
    
    Configures the root logger with either structured (JSON) or
    plain text formatting, and optionally writes to a file.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        structured: Whether to use structured (JSON) logging
        log_file: Optional file path for log output
        secret_masker: Optional secret masker for sensitive data
        
    Requirements: 12.1, 12.2, 12.4
    """
    # Validate log level
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create formatter
    if structured:
        formatter = StructuredFormatter(secret_masker=secret_masker)
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log configuration
    root_logger.info(
        f"Logging configured: level={log_level}, structured={structured}, "
        f"file={log_file}"
    )


def get_runner_logger(
    runner_id: str,
    task_id: Optional[str] = None,
    spec_name: Optional[str] = None,
    logger_name: str = "necrocode.agent_runner"
) -> RunnerLoggerAdapter:
    """
    Get a logger adapter with runner context.
    
    Creates a logger adapter that automatically adds runner_id, task_id,
    and spec_name to all log records.
    
    Args:
        runner_id: Runner ID
        task_id: Task ID (optional)
        spec_name: Spec name (optional)
        logger_name: Base logger name
        
    Returns:
        Logger adapter with runner context
        
    Requirements: 12.1, 12.2
    """
    base_logger = logging.getLogger(logger_name)
    return RunnerLoggerAdapter(
        logger=base_logger,
        runner_id=runner_id,
        task_id=task_id,
        spec_name=spec_name
    )
