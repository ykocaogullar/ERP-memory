"""
Enhanced logging configuration for ERP Memory System

Provides structured logging with JSON format and request tracing
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'session_id'):
            log_entry['session_id'] = record.session_id
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'duration_ms'):
            log_entry['duration_ms'] = record.duration_ms
        if hasattr(record, 'entity_id'):
            log_entry['entity_id'] = record.entity_id
        if hasattr(record, 'memory_id'):
            log_entry['memory_id'] = record.memory_id
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)


class SimpleFormatter(logging.Formatter):
    """Simple human-readable formatter for development"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as simple text"""
        
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        
        # Build basic message
        parts = [f"[{timestamp}] {record.levelname:8} {record.name}"]
        
        # Add user/session context if present
        if hasattr(record, 'user_id'):
            parts.append(f"user={record.user_id}")
        if hasattr(record, 'session_id'):
            parts.append(f"session={record.session_id}")
        if hasattr(record, 'request_id'):
            parts.append(f"req={record.request_id}")
        if hasattr(record, 'duration_ms'):
            parts.append(f"duration={record.duration_ms}ms")
        
        parts.append(f": {record.getMessage()}")
        
        return " | ".join(parts) + "\n"


def setup_logging(log_format: str = 'simple', log_level: str = 'INFO'):
    """
    Setup logging configuration for the application
    
    Args:
        log_format: 'json' for structured logs, 'simple' for human-readable
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Choose formatter based on log_format
    if log_format.lower() == 'json':
        formatter = JSONFormatter()
    else:
        formatter = SimpleFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with a specific name
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


