"""
Service-to-service authentication for internal callers (the MAXergy MCP service).

Public clients (web, mobile) call the API without credentials. Internal services send
`Authorization: Bearer $MAXERGY_SERVICE_TOKEN`; a valid token gives the caller the "service"
identity, which has its own (higher) rate limit. A bearer token that is present but wrong is
rejected with 401 so misconfigured services fail loudly instead of silently falling back to
the public per-IP limits.
"""

import os
import secrets

from fastapi import HTTPException, Request

SERVICE_TOKEN_ENV = "MAXERGY_SERVICE_TOKEN"
SERVICE_KEY = "service:maxergy-mcp"


def _configured_token() -> str:
    return os.getenv(SERVICE_TOKEN_ENV, "").strip()


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None


def is_service_request(request: Request) -> bool:
    """True when the request carries the configured service token."""
    token, expected = _bearer(request), _configured_token()
    return bool(token and expected and secrets.compare_digest(token, expected))


async def verify_service_token(request: Request) -> None:
    """Router dependency: allow anonymous requests, reject invalid bearer tokens (401)."""
    if _bearer(request) is not None and not is_service_request(request):
        raise HTTPException(
            status_code=401,
            detail="Invalid service token",
            headers={"WWW-Authenticate": "Bearer"},
        )
