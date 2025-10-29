"""
Request logging middleware for ERP Memory System

Logs all incoming requests with timing and context information
"""

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log all HTTP requests with timing and context"""
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log details"""
        
        # Generate unique request ID for tracing
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Log request start
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                'request_id': request_id,
                'method': request.method,
                'path': request.url.path,
                'query_params': str(request.query_params),
                'client_ip': request.client.host if request.client else None
            }
        )
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Log successful response
            logger.info(
                f"Request completed: {response.status_code}",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'status_code': response.status_code,
                    'duration_ms': round(duration_ms, 2)
                }
            )
            
            # Add request ID to response headers for client tracing
            response.headers['X-Request-ID'] = request_id
            
            return response
            
        except Exception as e:
            # Log error
            duration_ms = (time.time() - start_time) * 1000
            
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': round(duration_ms, 2),
                    'exception': str(e)
                },
                exc_info=True
            )
            raise


