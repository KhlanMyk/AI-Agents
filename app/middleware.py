"""Request/response middleware for tracking and metrics."""

from contextvars import ContextVar
from time import time
from typing import Callable
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import get_logger


logger = get_logger(__name__)

# Context variable for storing request ID across async operations
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()


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
        # Generate and set request ID
        request_id = str(uuid4())
        token = request_id_var.set(request_id)
        
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
                "request_id": request_id,
            }
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        # Clean up context
        request_id_var.reset(token)
        
        return response
