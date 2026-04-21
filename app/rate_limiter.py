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
        valid_requests = self._prune_session(session_id, now)
        return max(0, self.max_requests - len(valid_requests))

    def get_used(self, session_id: str) -> int:
        """Get number of used requests in the current window for a session."""
        now = utc_now()
        valid_requests = self._prune_session(session_id, now)
        return len(valid_requests)

    def reset(self, session_id: str | None = None) -> dict[str, int]:
        """
        Reset rate limiter entries.

        Args:
            session_id: specific session to reset; when None resets all sessions

        Returns:
            metadata about removed sessions and removed request entries
        """
        if session_id is None:
            removed_sessions = len(self.requests)
            removed_requests = sum(len(v) for v in self.requests.values())
            self.requests.clear()
            return {
                "removed_sessions": removed_sessions,
                "removed_requests": removed_requests,
            }

        removed_requests = len(self.requests.get(session_id, []))
        removed_sessions = 1 if session_id in self.requests else 0
        self.requests.pop(session_id, None)
        return {
            "removed_sessions": removed_sessions,
            "removed_requests": removed_requests,
        }

    def tracked_sessions(self) -> int:
        """Return number of tracked sessions with in-window requests."""
        now = utc_now()
        for sid in list(self.requests.keys()):
            self._prune_session(sid, now)
        return len(self.requests)

    def _prune_session(self, session_id: str, now: datetime) -> list[datetime]:
        """Remove outdated request timestamps for a session and return active timestamps."""
        if session_id not in self.requests:
            return []

        valid_requests = [
            req_time for req_time in self.requests[session_id]
            if now - req_time < self.window
        ]
        if valid_requests:
            self.requests[session_id] = valid_requests
        else:
            self.requests.pop(session_id, None)
        return valid_requests
