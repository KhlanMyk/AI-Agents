"""Input sanitization and security utilities."""

import html
import re


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.
    
    - Strips leading/trailing whitespace
    - Escapes HTML entities
    - Removes control characters
    - Limits repeated characters to prevent spam
    
    Args:
        text: Raw user input
        
    Returns:
        Sanitized text safe for processing
    """
    # Strip whitespace
    text = text.strip()
    
    # Escape HTML entities to prevent XSS
    text = html.escape(text)
    
    # Remove control characters (but keep newlines and tabs)
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    
    # Prevent spam: limit repeated characters to 3 in a row
    text = re.sub(r'(.)\1{3,}', r'\1\1\1', text)
    
    return text


def sanitize_for_sql(text: str) -> str:
    """
    Prepare text for safe SQL storage (additional layer).
    
    Note: SQLAlchemy parameterized queries handle injection prevention,
    but this adds defense-in-depth by removing null bytes.
    
    Args:
        text: Text to sanitize for SQL storage
        
    Returns:
        Text safe for SQL storage
    """
    # Remove null bytes which can cause issues
    return text.replace('\x00', '')
