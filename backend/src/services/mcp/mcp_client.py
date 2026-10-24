"""
Client for the MAXergy MCP service (`maxergy-mcp`).

The backend only calls the MCP's enrichment tools (geocoding, roof geometry, PV yield and the
suggestion helpers). The MCP's savings tools call back into this API, so they are not on the
allow-list — that rules out API → MCP → API loops.

The MCP runs FastMCP's streamable HTTP transport in stateless JSON mode, so a tool call is a
single JSON-RPC `tools/call` POST; no session handshake or MCP client library is needed.

Settings (environment):
  MCP_ENABLED        "true" to enable (default off; enrichment then returns 503)
  MCP_BASE_URL       MCP base URL, e.g. http://maxergy-mcp.railway.internal:8080 (path /mcp added)
  MAXERGY_MCP_TOKEN  bearer token accepted by the MCP (its MAXERGY_INTERNAL_TOKENS)
"""

import itertools
import json
import os

import requests

from src.core_specs.configuration.config_loader import config_loader
from src.utils.custom_logger import log_handler

ALLOWED_TOOLS = frozenset({
    "geocode_address",
    "get_roof_geometry",
    "estimate_pv_production",
    "estimate_roof_capacity_from_area",
    "estimate_heating_spend",
    "suggest_battery_kwh",
    "suggest_electricity_price",
})


ALLOWED_PROMPTS = frozenset({"maxergy_advisor"})


class McpUnavailable(RuntimeError):
    """The MCP is disabled, unreachable, or rejected our credentials."""


class McpToolError(RuntimeError):
    """The MCP tool ran but reported an error (e.g. address not found, no roof data)."""


def _env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


class McpClient:
    def __init__(
        self,
        base_url: str | None = None,
        token: str | None = None,
        enabled: bool | None = None,
        timeout: float | None = None,
        session: requests.Session | None = None,
    ):
        url = (base_url if base_url is not None else os.getenv("MCP_BASE_URL", "")).strip().rstrip("/")
        self.url = url if url.endswith("/mcp") or not url else f"{url}/mcp"
        self.token = token if token is not None else os.getenv("MAXERGY_MCP_TOKEN", "").strip()
        self.enabled = (enabled if enabled is not None else _env_flag("MCP_ENABLED")) and bool(self.url)
        self.timeout = timeout or config_loader.get("mcp", {}).get("timeout_seconds", 10)
        self._session = session or requests.Session()
        self._ids = itertools.count(1)

    def _rpc(self, method: str, params: dict, label: str) -> dict:
        """One JSON-RPC request to the MCP; returns the `result` object."""
        if not self.enabled:
            raise McpUnavailable("MCP enrichment is disabled (MCP_ENABLED / MCP_BASE_URL)")
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {"jsonrpc": "2.0", "id": next(self._ids), "method": method, "params": params}
        try:
            resp = self._session.post(self.url, json=payload, headers=headers, timeout=self.timeout)
        except requests.RequestException as e:
            log_handler.warning("[mcp_client] %s unreachable: %s", label, type(e).__name__)
            raise McpUnavailable("MCP service unreachable") from e

        if resp.status_code in (401, 403):
            raise McpUnavailable("MCP service rejected the backend credentials")
        if resp.status_code >= 400:
            raise McpUnavailable(f"MCP service error (HTTP {resp.status_code})")

        message = self._parse(resp)
        if "error" in message:
            raise McpToolError(message["error"].get("message", "MCP error"))
        return message.get("result", {})

    def get_prompt(self, name: str) -> str:
        """Text of an allow-listed MCP prompt (e.g. the shared onboarding script)."""
        if name not in ALLOWED_PROMPTS:
            raise ValueError(f"MCP prompt '{name}' is not allowed from the backend")
        result = self._rpc("prompts/get", {"name": name, "arguments": {}}, f"prompt {name}")
        texts = [
            m.get("content", {}).get("text", "")
            for m in result.get("messages", [])
            if isinstance(m.get("content"), dict)
        ]
        text = "\n".join(t for t in texts if t)
        if not text:
            raise McpToolError(f"MCP prompt '{name}' is empty")
        return text

    def call_tool(self, name: str, arguments: dict) -> dict:
        """Call an allow-listed MCP tool and return its structured result."""
        if name not in ALLOWED_TOOLS:
            raise ValueError(f"MCP tool '{name}' is not allowed from the backend")
        result = self._rpc("tools/call", {"name": name, "arguments": arguments}, name)
        text = " ".join(c.get("text", "") for c in result.get("content", []) if c.get("type") == "text")
        if result.get("isError"):
            raise McpToolError(text or f"MCP tool '{name}' failed")
        if isinstance(result.get("structuredContent"), dict):
            return result["structuredContent"]
        try:
            return json.loads(text)
        except ValueError:
            return {"result": text}

    @staticmethod
    def _parse(resp: requests.Response) -> dict:
        if resp.headers.get("content-type", "").startswith("text/event-stream"):
            for line in resp.text.splitlines():
                if line.startswith("data:"):
                    return json.loads(line[5:].strip())
            raise McpUnavailable("Empty MCP event stream")
        return resp.json()


_client: McpClient | None = None


def get_mcp_client() -> McpClient:
    """Process-wide client (environment read at first use)."""
    global _client
    if _client is None:
        _client = McpClient()
    return _client


def set_mcp_client(client: McpClient | None) -> None:
    """Replace the process-wide client (tests)."""
    global _client
    _client = client
