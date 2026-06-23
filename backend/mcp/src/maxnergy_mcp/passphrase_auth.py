"""Shared-passphrase gate on top of FastMCP's self-hosted OAuth.

`InMemoryOAuthProvider` speaks full OAuth 2.1 + DCR (so the claude.ai connector can
attach with no external IdP) but auto-approves every authorization — anyone with the URL
gets in. This wraps it so the authorization step is held behind a single shared
passphrase: the auth code is generated as usual, but the redirect back to the client is
deferred until the user enters the correct passphrase on a small page we serve.

PKCE still applies at token exchange, so the passphrase only gates *who can start* the
flow.

State (registered clients + tokens) is persisted to a JSON file when MAXNERGY_OAUTH_STATE_PATH
is set (point it at a Railway volume, e.g. /data/oauth.json). Without it, state is in-memory
and a redeploy forces every client to re-register — which is why the claude.ai connector
breaks on each deploy. With it, the DCR client_id and tokens survive restarts.
"""

from __future__ import annotations

import json
import os
import secrets
import tempfile

from mcp.server.auth.provider import AccessToken, AuthorizationCode, RefreshToken
from mcp.shared.auth import OAuthClientInformationFull

from fastmcp.server.auth.providers.in_memory import (
    ClientRegistrationOptions,
    InMemoryOAuthProvider,
)
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse

# Persisted dicts of pydantic models: name -> the model class to rebuild each value with.
_MODEL_DICTS = {
    "clients": OAuthClientInformationFull,
    "auth_codes": AuthorizationCode,
    "access_tokens": AccessToken,
    "refresh_tokens": RefreshToken,
}
# Persisted plain str->str dicts.
_PLAIN_DICTS = ("_access_to_refresh_map", "_refresh_to_access_map")


class PassphraseOAuthProvider(InMemoryOAuthProvider):
    def __init__(self, *, base_url: str, passphrase: str, **kwargs):
        super().__init__(
            base_url=base_url,
            client_registration_options=ClientRegistrationOptions(enabled=True),
            **kwargs,
        )
        self._passphrase = passphrase
        self._gate_base = str(base_url).rstrip("/")
        # one-time gate token -> the real client redirect (carrying code + state)
        self._pending: dict[str, str] = {}
        self._state_path = os.environ.get("MAXNERGY_OAUTH_STATE_PATH", "").strip() or None
        self._load_state()

    # --- persistence ---

    def _load_state(self) -> None:
        if not self._state_path or not os.path.exists(self._state_path):
            return
        try:
            with open(self._state_path) as f:
                data = json.load(f)
            for name, model in _MODEL_DICTS.items():
                getattr(self, name).update(
                    {k: model.model_validate(v) for k, v in data.get(name, {}).items()}
                )
            for name in _PLAIN_DICTS:
                getattr(self, name).update(data.get(name, {}))
        except Exception as e:  # corrupt/old file shouldn't crash startup
            import sys

            print(f"[maxnergy] could not load OAuth state: {e}", file=sys.stderr)

    def _save_state(self) -> None:
        if not self._state_path:
            return
        try:
            data = {
                name: {k: v.model_dump(mode="json") for k, v in getattr(self, name).items()}
                for name in _MODEL_DICTS
            }
            for name in _PLAIN_DICTS:
                data[name] = dict(getattr(self, name))
            os.makedirs(os.path.dirname(self._state_path) or ".", exist_ok=True)
            d = os.path.dirname(self._state_path) or "."
            fd, tmp = tempfile.mkstemp(dir=d)
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)
            os.replace(tmp, self._state_path)  # atomic
        except Exception as e:
            import sys

            print(f"[maxnergy] could not save OAuth state: {e}", file=sys.stderr)

    # --- mutating methods: persist after the parent updates in-memory state ---

    async def register_client(self, client_info):  # type: ignore[override]
        r = await super().register_client(client_info)
        self._save_state()
        return r

    async def exchange_authorization_code(self, client, authorization_code):  # type: ignore[override]
        r = await super().exchange_authorization_code(client, authorization_code)
        self._save_state()
        return r

    async def exchange_refresh_token(self, client, refresh_token, scopes):  # type: ignore[override]
        r = await super().exchange_refresh_token(client, refresh_token, scopes)
        self._save_state()
        return r

    async def revoke_token(self, token):  # type: ignore[override]
        r = await super().revoke_token(token)
        self._save_state()
        return r

    async def authorize(self, client, params) -> str:  # type: ignore[override]
        # Let the parent mint + store the auth code and build the client redirect URL,
        # then stash it and send the browser to our passphrase page first.
        client_redirect = await super().authorize(client, params)
        self._save_state()  # the new auth code was added to self.auth_codes
        token = secrets.token_urlsafe(24)
        self._pending[token] = client_redirect
        return f"{self._gate_base}/gate?t={token}"

    def check(self, token: str, passphrase: str) -> str | None:
        """Validate passphrase for a pending gate token; return the client redirect or None."""
        target = self._pending.get(token)
        if target and secrets.compare_digest(passphrase, self._passphrase):
            self._pending.pop(token, None)
            return target
        return None


def _page(token: str, error: bool = False) -> str:
    note = (
        '<p style="color:#c0392b;margin:0 0 14px">Wrong passphrase — try again.</p>'
        if error
        else ""
    )
    return f"""<!doctype html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MAXnergy — access</title>
<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png"></head>
<body style="font-family:system-ui,sans-serif;background:#0f1115;color:#e6e6e6;
display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0">
  <form method="POST" action="/gate" style="background:#1a1d24;padding:32px;border-radius:14px;
  width:320px;box-shadow:0 8px 40px rgba(0,0,0,.4);text-align:center">
    <img src="/logo.png" alt="MAXnergy" width="64" height="64" style="margin:0 auto 8px;display:block">
    <h2 style="margin:0 0 4px">MAXnergy</h2>
    <p style="margin:0 0 18px;color:#9aa0aa;font-size:14px">Enter the access passphrase to connect.</p>
    {note}
    <input type="hidden" name="t" value="{token}">
    <input type="password" name="passphrase" autofocus placeholder="Passphrase"
      style="width:100%;box-sizing:border-box;padding:11px;border-radius:8px;border:1px solid #333;
      background:#0f1115;color:#e6e6e6;margin-bottom:14px">
    <button type="submit" style="width:100%;padding:11px;border:0;border-radius:8px;
      background:#2ecc71;color:#06281a;font-weight:600;cursor:pointer">Connect</button>
  </form>
</body></html>"""


def register_gate_routes(mcp, provider: PassphraseOAuthProvider) -> None:
    """Attach the GET/POST /gate passphrase pages to the FastMCP server."""

    @mcp.custom_route("/gate", methods=["GET"])
    async def gate_form(request: Request):  # noqa: ANN202
        return HTMLResponse(_page(request.query_params.get("t", "")))

    @mcp.custom_route("/gate", methods=["POST"])
    async def gate_submit(request: Request):  # noqa: ANN202
        form = await request.form()
        token = str(form.get("t", ""))
        target = provider.check(token, str(form.get("passphrase", "")))
        if target:
            return RedirectResponse(target, status_code=303)
        return HTMLResponse(_page(token, error=True), status_code=401)
