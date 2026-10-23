"""Internal service tokens (MAXERGY_INTERNAL_TOKENS) are accepted alongside the public auth mode."""

from __future__ import annotations

import asyncio

from fastmcp.server.auth import MultiAuth
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from maxergy_mcp.server import _with_internal_tokens


def _verify(auth, token: str):
    return asyncio.run(auth.verify_token(token))


def test_no_internal_tokens_keeps_public_auth(monkeypatch):
    monkeypatch.delenv("MAXERGY_INTERNAL_TOKENS", raising=False)
    assert _with_internal_tokens(None) is None
    public = StaticTokenVerifier(tokens={"public": {"client_id": "claude", "scopes": []}})
    assert _with_internal_tokens(public) is public


def test_internal_tokens_alone(monkeypatch):
    monkeypatch.setenv("MAXERGY_INTERNAL_TOKENS", "svc-a, svc-b")
    auth = _with_internal_tokens(None)
    assert _verify(auth, "svc-a").client_id == "maxergy-api"
    assert _verify(auth, "svc-b") is not None
    assert _verify(auth, "nope") is None


def test_internal_tokens_with_public_mode(monkeypatch):
    monkeypatch.setenv("MAXERGY_INTERNAL_TOKENS", "svc-a")
    public = StaticTokenVerifier(tokens={"public": {"client_id": "claude", "scopes": []}})
    auth = _with_internal_tokens(public)
    assert isinstance(auth, MultiAuth)
    assert _verify(auth, "public").client_id == "claude"
    assert _verify(auth, "svc-a").client_id == "maxergy-api"
    assert _verify(auth, "nope") is None
