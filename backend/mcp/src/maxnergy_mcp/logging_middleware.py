"""FastMCP middleware that logs every tool invocation in one place.

Entry/exit for all tools without touching their code: tool name, sanitized arguments,
output shape, wall-clock duration, and errors with traceback. Assigns a trace id so the
Google API calls a tool triggers (logged in providers.py) line up with it.
"""

from __future__ import annotations

import logging
import secrets
import time

from fastmcp.server.middleware import Middleware, MiddlewareContext

from .logging_setup import sanitize, summarize_output, trace_id_var

log = logging.getLogger("maxnergy.tools")


class ToolLoggingMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        params = context.message
        name = getattr(params, "name", "?")
        args = getattr(params, "arguments", {}) or {}

        token = trace_id_var.set(secrets.token_hex(4))
        start = time.perf_counter()
        try:
            log.info("→ %s args=%s", name, sanitize(args))
            result = await call_next(context)
            dur = (time.perf_counter() - start) * 1000
            out = getattr(result, "structured_content", None)
            is_err = getattr(result, "is_error", False)
            log.info("← %s %s %.0fms out=%s", name, "ERROR" if is_err else "ok", dur, summarize_output(out))
            return result
        except Exception as e:
            dur = (time.perf_counter() - start) * 1000
            log.exception("✗ %s failed after %.0fms: %s", name, dur, e)
            raise
        finally:
            trace_id_var.reset(token)
