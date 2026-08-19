"""
#############################################################################
### Input Sanitization Utilities
###
### @file sanitize.py
### @date 2026
#############################################################################

Utilities for sanitizing user input to prevent injection attacks.
"""

import re
from typing import Optional


def sanitize_prompt(user_input: str, max_length: int = 1000) -> str:
    """
    Sanitize user input for LLM prompts.

    Args:
        user_input: Raw user input string.
        max_length: Maximum allowed length.

    Returns:
        Sanitized string.

    Raises:
        ValueError: If input is empty or exceeds max length after sanitization.
    """
    if not user_input or not user_input.strip():
        raise ValueError("User message cannot be empty")

    # Remove control characters (except common whitespace)
    sanitized = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', user_input)

    # Normalize whitespace
    sanitized = ' '.join(sanitized.split())

    # Check length
    if len(sanitized) > max_length:
        raise ValueError(f"User message exceeds maximum length of {max_length} characters")

    return sanitized
