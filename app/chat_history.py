"""Chat history tracking and export functionality."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List
import json


@dataclass
class ChatMessage:
    """Single chat message in conversation history."""
    
    timestamp: str  # ISO format
    sender: str  # "user" or "assistant"
    message: str
    intent: str | None = None


class ChatHistory:
    """Manages conversation history for a session."""
    
    def __init__(self):
        """Initialize empty history."""
        self.messages: List[ChatMessage] = []
    
    def add_message(self, sender: str, message: str, intent: str | None = None) -> None:
        """
        Add a message to history.
        
        Args:
            sender: "user" or "assistant"
            message: The message text
            intent: Optional detected intent
        """
        msg = ChatMessage(
            timestamp=datetime.utcnow().isoformat(),
            sender=sender,
            message=message,
            intent=intent,
        )
        self.messages.append(msg)
    
    def to_dict(self) -> dict:
        """Export history as structured dict."""
        return {
            "message_count": len(self.messages),
            "timestamp": datetime.utcnow().isoformat(),
            "messages": [asdict(m) for m in self.messages],
        }
    
    def to_json(self) -> str:
        """Export history as JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def clear(self) -> None:
        """Clear all messages from history."""
        self.messages = []
