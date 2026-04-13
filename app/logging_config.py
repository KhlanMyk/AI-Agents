"""Structured logging and error tracking."""

import logging
import json
from typing import Any, Optional

from app.time_utils import utc_now


class StructuredJsonFormatter(logging.Formatter):
    """Log formatter that outputs structured JSON logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": utc_now().isoformat(),
            "level": record.levelname,
            "module": record.module,
            "function": record.funcName,
            "message": record.getMessage(),
        }
        
        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Include additional fields from record extras
        if hasattr(record, "session_id"):
            log_data["session_id"] = record.session_id
        if hasattr(record, "endpoint"):
            log_data["endpoint"] = record.endpoint
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        
        return json.dumps(log_data)


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger with JSON formatting."""
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredJsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    
    return logger


def log_error(
    logger: logging.Logger,
    message: str,
    endpoint: Optional[str] = None,
    session_id: Optional[str] = None,
    status_code: Optional[int] = None,
    exception: Optional[Exception] = None,
) -> None:
    """
    Log an error with structured context.
    
    Args:
        logger: Logger instance
        message: Error message
        endpoint: API endpoint where error occurred
        session_id: Session ID if applicable
        status_code: HTTP status code
        exception: Exception object if available
    """
    extra = {}
    if endpoint:
        extra["endpoint"] = endpoint
    if session_id:
        extra["session_id"] = session_id
    if status_code:
        extra["status_code"] = status_code
    
    if exception:
        logger.error(message, extra=extra, exc_info=exception)
    else:
        logger.error(message, extra=extra)
