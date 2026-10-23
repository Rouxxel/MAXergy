"""Client for the MAXergy backend API (`maxergy-api`).

The MCP never computes savings itself: every number comes from the backend's production
engine via `POST /plan`. Engine defaults for the suggestion tools come from
`GET /assumptions` (cached for an hour).

Settings:
  MAXERGY_API_BASE_URL   backend base URL (default http://localhost:8000)
  MAXERGY_SERVICE_TOKEN  bearer token sent to the backend (service-to-service auth)
"""

from __future__ import annotations

import logging
import time

import httpx

from .config import env
from .logging_setup import trace_id_var

log = logging.getLogger("maxergy.api")

_TIMEOUT = httpx.Timeout(15.0)
_ASSUMPTIONS_TTL_S = 3600.0


class BackendError(RuntimeError):
    """The backend rejected the request or could not be reached (message is user-relayable)."""


class ApiClient:
    def __init__(self, base_url: str | None = None, token: str | None = None, transport: httpx.BaseTransport | None = None):
        self.base_url = (base_url or env("API_BASE_URL", "http://localhost:8000")).rstrip("/")
        token = token if token is not None else env("SERVICE_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._http = httpx.Client(base_url=self.base_url, headers=headers, timeout=_TIMEOUT, transport=transport)
        self._assumptions: tuple[float, dict] | None = None

    def _request(self, method: str, path: str, **kwargs) -> dict:
        headers = {"X-Trace-Id": trace_id_var.get()}
        for attempt in (1, 2):
            t0 = time.perf_counter()
            try:
                resp = self._http.request(method, path, headers=headers, **kwargs)
            except httpx.TransportError as e:
                log.warning("%s %s transport error (attempt %d): %s", method, path, attempt, e)
                if attempt == 2:
                    raise BackendError(f"MAXergy API unreachable at {self.base_url}: {e}") from e
                continue
            dur = (time.perf_counter() - t0) * 1000
            log.info("%s %s http=%s %.0fms", method, path, resp.status_code, dur)
            if resp.status_code >= 500 and attempt == 1:
                continue
            if resp.status_code >= 400:
                detail = resp.json().get("detail") if resp.headers.get("content-type", "").startswith("application/json") else resp.text
                raise BackendError(f"MAXergy API {resp.status_code} on {path}: {detail}")
            return resp.json()
        raise BackendError(f"MAXergy API failed on {path}")

    def plan(self, assessment: dict, metric: str | None = None) -> dict:
        """POST /plan → {forecast, recommendation} from the production engine."""
        params = {"metric": metric} if metric else None
        return self._request("POST", "/plan", json=assessment, params=params)

    def assumptions(self) -> dict:
        """GET /assumptions (engine defaults), cached for an hour."""
        now = time.monotonic()
        if self._assumptions and now - self._assumptions[0] < _ASSUMPTIONS_TTL_S:
            return self._assumptions[1]
        data = self._request("GET", "/assumptions")
        self._assumptions = (now, data)
        return data


_api: ApiClient | None = None


def get_api() -> ApiClient:
    """Process-wide client (created lazily so env vars are read at first use)."""
    global _api
    if _api is None:
        _api = ApiClient()
    return _api


def set_api(client: ApiClient | None) -> None:
    """Replace the process-wide client (tests)."""
    global _api
    _api = client
