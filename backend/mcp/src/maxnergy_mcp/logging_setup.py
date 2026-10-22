"""Central logging configuration for MAXnergy.

Plain-text logs to stdout (Railway captures them). Level from LOG_LEVEL (default INFO;
set DEBUG for verbose internals). A per-request trace id ties a tool call together with
the Google API calls it triggers. Secrets are never logged; helpers here sanitize args.
"""

from __future__ import annotations

import logging
import os
from contextvars import ContextVar

# Short id shared across one tool invocation and the provider calls underneath it.
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="-")

_SECRET_KEYS = ("key", "token", "secret", "password", "authorization", "api_key")
_MAX_VAL = 200  # keep individual values short so lines stay < ~500 chars


class _TraceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = trace_id_var.get()
        return True


def environment() -> str:
    """'railway' on the cloud (RAILWAY_* env present), else 'local'."""
    return "railway" if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_SERVICE_NAME") else "local"


def setup_logging() -> None:
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.addFilter(_TraceFilter())
    handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(asctime)s %(name)s [%(trace_id)s] - %(message)s")
    )
    root = logging.getLogger("maxnergy")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
    root.propagate = False
    root.info("logging initialized: level=%s env=%s", level, environment())


def sanitize(value, _key: str = "") -> object:
    """Mask secret-looking fields; truncate long values. Coords/addresses/types stay visible."""
    if any(s in _key.lower() for s in _SECRET_KEYS):
        return "***"
    if isinstance(value, dict):
        return {k: sanitize(v, k) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        out = [sanitize(v, _key) for v in value[:5]]
        if len(value) > 5:
            out.append(f"...(+{len(value) - 5} more)")
        return out
    if isinstance(value, str) and len(value) > _MAX_VAL:
        return value[:_MAX_VAL] + "…"
    return value


def summarize_output(value) -> str:
    """One-line shape summary of a tool's structured output."""
    if isinstance(value, dict):
        keys = list(value.keys())
        head = ", ".join(keys[:8])
        return f"dict(keys=[{head}{'…' if len(keys) > 8 else ''}])"
    if isinstance(value, (list, tuple)):
        return f"list(len={len(value)})"
    s = str(value)
    return s[:120] + ("…" if len(s) > 120 else "")
