"""Session lifecycle management with expiration tracking."""

from datetime import datetime, timedelta
from typing import Dict, Optional


class SessionManager:
    """Manages active sessions with TTL (time-to-live) tracking."""
    
    def __init__(self, default_ttl_minutes: int = 60):
        """
        Initialize session manager.
        
        Args:
            default_ttl_minutes: Session TTL in minutes (default 60 mins)
        """
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.sessions: Dict[str, datetime] = {}
    
    def mark_active(self, session_id: str) -> None:
        """Mark a session as active (update last access time)."""
        self.sessions[session_id] = datetime.utcnow()
    
    def is_active(self, session_id: str) -> bool:
        """Check if session is still within TTL window."""
        if session_id not in self.sessions:
            return False
        
        last_access = self.sessions[session_id]
        expiration_time = last_access + self.default_ttl
        return datetime.utcnow() < expiration_time
    
    def cleanup_expired(self) -> list[str]:
        """
        Remove expired sessions and return their IDs.
        
        Returns:
            List of session IDs that were cleaned up
        """
        now = datetime.utcnow()
        expired = [
            sid for sid, last_access in self.sessions.items()
            if now >= last_access + self.default_ttl
        ]
        for sid in expired:
            del self.sessions[sid]
        return expired
