"""
#############################################################################
### Timeout Decorator
###
### @file timeout.py
### @date 2026
#############################################################################

Decorator to add timeout to async functions.
"""

import asyncio
from functools import wraps
from typing import Callable, Any
from fastapi import HTTPException


def timeout(seconds: int):
    """Decorator to add timeout to async functions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                raise HTTPException(
                    status_code=504,
                    detail=f"Request timed out after {seconds} seconds"
                )
        return wrapper
    return decorator
