"""Rate limiting utilities to prevent abuse."""

from datetime import datetime, timedelta
from typing import Dict

from app.time_utils import utc_now


class RateLimiter:
    """Simple rate limiter using sliding window to prevent abuse."""
    
    def __init__(self, max_requests: int = 30, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Max requests allowed in time window (default 30)
            window_seconds: Time window in seconds (default 60)
        """
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests: Dict[str, list[datetime]] = {}
    
    def is_allowed(self, session_id: str) -> bool:
        """
        Check if a request from session is allowed.
        
        Args:
            session_id: Session to check
            
        Returns:
            True if request is allowed, False if rate limit exceeded
        """
        now = utc_now()
        
        if session_id not in self.requests:
            self.requests[session_id] = []
        
        # Remove old requests outside the window
        self.requests[session_id] = [
            req_time for req_time in self.requests[session_id]
            if now - req_time < self.window
        ]
        
        # Check if limit exceeded
        if len(self.requests[session_id]) >= self.max_requests:
            return False
        
        # Record this request
        self.requests[session_id].append(now)
        return True
    
    def get_remaining(self, session_id: str) -> int:
        """
        Get remaining requests allowed for session.
        
        Args:
            session_id: Session to check
            
        Returns:
            Number of remaining requests allowed
        """
        now = utc_now()
        
        if session_id not in self.requests:
            return self.max_requests
        
        # Clean old requests
        valid_requests = [
            req_time for req_time in self.requests[session_id]
            if now - req_time < self.window
        ]
        
        return max(0, self.max_requests - len(valid_requests))
