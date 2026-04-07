"""Request/response middleware for tracking and metrics."""

from time import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.logging_config import get_logger


logger = get_logger(__name__)


class RequestMetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track request/response metrics and performance."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request, track metrics, and log response.
        
        Measures:
        - Request processing time
        - Request/response sizes
        - HTTP method and status code
        """
        start_time = time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate metrics
        process_time = time() - start_time
        
        # Log request completion
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} ({process_time:.3f}s)",
            extra={
                "endpoint": request.url.path,
                "method": request.method,
                "status_code": response.status_code,
                "process_time_ms": round(process_time * 1000),
            }
        )
        
        return response
