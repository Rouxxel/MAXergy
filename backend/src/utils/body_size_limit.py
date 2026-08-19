"""
#############################################################################
### Body Size Limit Middleware
###
### @file body_size_limit.py
### @date 2026
#############################################################################

Middleware to reject requests with bodies larger than a specified size.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import HTTPException


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Reject requests with bodies larger than the specified size limit."""

    def __init__(self, app, max_size: int = 256 * 1024):  # 256 KB default
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        # Check content-length header for POST/PUT/PATCH requests
        if request.method in ["POST", "PUT", "PATCH"]:
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    body_size = int(content_length)
                    if body_size > self.max_size:
                        raise HTTPException(
                            status_code=413,
                            detail=f"Request body too large. Maximum size is {self.max_size} bytes."
                        )
                except ValueError:
                    # Invalid content-length header, let the request proceed
                    # (will fail later if body is actually too large)
                    pass

        response: Response = await call_next(request)
        return response
