"""Shared fixtures for MCP tests.

The backend is replaced by an httpx.MockTransport that serves responses recorded from the real
backend (`fixtures/plan_model_input1.json` from POST /plan, `fixtures/assumptions.json` from
GET /assumptions), so the tests run offline and without the backend's dependencies.
Regenerate the fixtures when the backend contract changes (see backend/mcp/README.md).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastmcp import Client

from maxergy_mcp import api_client
from maxergy_mcp.server import mcp

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class FakeBackend:
    """Records requests and answers like the MAXergy backend."""

    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.plan_status = 200
        self.plan_body: dict = load("plan_model_input1.json")

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.url.path == "/plan":
            return httpx.Response(self.plan_status, json=self.plan_body)
        if request.url.path == "/assumptions":
            return httpx.Response(200, json=load("assumptions.json"))
        return httpx.Response(404, json={"detail": "Not Found"})


@pytest.fixture
def backend():
    fake = FakeBackend()
    api_client.set_api(api_client.ApiClient(base_url="http://backend.test", token="svc-token",
                                            transport=httpx.MockTransport(fake)))
    yield fake
    api_client.set_api(None)


@pytest.fixture
def assessment() -> dict:
    return load("model_input1.json")


def call_tool(name: str, args: dict | None = None):
    """Call an MCP tool through the in-memory FastMCP client and return its structured result."""

    async def run():
        async with Client(mcp) as client:
            result = await client.call_tool(name, args or {})
            return result.structured_content if result.structured_content is not None else result.data

    return asyncio.run(run())
