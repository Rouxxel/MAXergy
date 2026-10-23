"""MAXergy MCP server.

Supports the MAXergy app: the client LLM runs the household onboarding conversation (script in
`instructions.py`) and these tools provide what it cannot do reliably in-context — roof
geometry (Google Solar), PV yield (PVGIS), proposals for unknown inputs, and the savings
overview. Every savings number comes from the MAXergy backend (`POST /plan`, production
engine); this server never computes savings itself.

Typical flow:
  1. start_advisor            -> onboarding script (ask one question at a time)
  2. geocode_address / get_roof_geometry / estimate_pv_production -> roof + site PV yield
  3. energy_savings_overview  -> forecast + recommendation from the backend
  4. compare_scenarios / project_savings / next_best_upgrade -> views of the same plan
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from .config import env


def _public_base_url() -> str:
    """Public https URL of this server, for OAuth metadata/redirects."""
    explicit = os.environ.get("PUBLIC_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    return f"https://{domain}" if domain else ""


def _warn(msg: str) -> None:
    import sys

    print(f"[maxergy] {msg}", file=sys.stderr)


def _bearer_auth():
    token = env("API_TOKEN")
    if not token:
        return None
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

    return StaticTokenVerifier(tokens={token: {"client_id": "maxergy", "scopes": []}})


def _build_auth():
    """Select the auth provider via MAXERGY_AUTH_MODE — switchable on redeploy, no code change.

      - "bearer" (default): shared-secret StaticTokenVerifier (MAXERGY_API_TOKEN). Simplest;
        for Claude Code / the Anthropic API MCP connector. Cannot be used by the claude.ai app.
      - "fastmcp": InMemoryOAuthProvider — FastMCP *is* the OAuth server (DCR + authorize +
        token), no external identity provider. Lets the claude.ai web/desktop/mobile connector
        attach with zero IdP setup. Caveat: it simulates consent (no real login) and keeps
        clients/tokens in memory, so it's effectively open access and re-auths after a redeploy.
      - "passphrase": self-hosted OAuth (as "fastmcp") but the authorization step is held
        behind one shared passphrase (MAXERGY_AUTH_PASSPHRASE). Works in the claude.ai app,
        no IdP, single shared secret (no per-user identity).
      - "google": GoogleProvider — real Google login via OAuth proxy. Needs
        GOOGLE_OAUTH_CLIENT_ID/SECRET; gives genuine per-user access control.

    Unknown/misconfigured modes fall back to bearer (with a warning) so a deploy never breaks.
    """
    mode = env("AUTH_MODE", "bearer").lower()
    base_url = _public_base_url()

    if mode == "passphrase":
        passphrase = env("AUTH_PASSPHRASE")
        if passphrase and base_url:
            from .passphrase_auth import PassphraseOAuthProvider

            return PassphraseOAuthProvider(base_url=base_url, passphrase=passphrase)
        _warn("MAXERGY_AUTH_MODE=passphrase but MAXERGY_AUTH_PASSPHRASE or base URL missing — using bearer.")

    if mode == "fastmcp":
        from fastmcp.server.auth.providers.in_memory import (
            ClientRegistrationOptions,
            InMemoryOAuthProvider,
        )

        # Enable Dynamic Client Registration so the claude.ai connector can self-register
        # (it ships no pre-issued client_id); without this the /register endpoint isn't
        # advertised and the connector's OAuth handshake fails.
        return InMemoryOAuthProvider(
            base_url=base_url or None,
            client_registration_options=ClientRegistrationOptions(enabled=True),
        )

    if mode == "google":
        client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "").strip()
        client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "").strip()
        if client_id and client_secret and base_url:
            from fastmcp.server.auth.providers.google import GoogleProvider

            # jwt_signing_key (optional) makes access tokens stateless JWTs so they
            # survive redeploys/restarts — avoids forcing a re-auth on every deploy.
            signing_key = env("JWT_SIGNING_KEY") or None
            return GoogleProvider(
                client_id=client_id,
                client_secret=client_secret,
                base_url=base_url,
                required_scopes=["openid", "email"],
                jwt_signing_key=signing_key,
            )
        _warn("MAXERGY_AUTH_MODE=google but GOOGLE_OAUTH_CLIENT_ID/SECRET or base URL missing — using bearer.")

    if mode not in {"bearer", "fastmcp", "passphrase", "google"}:
        _warn(f"unknown MAXERGY_AUTH_MODE={mode!r} — using bearer.")

    return _bearer_auth()


def _with_internal_tokens(public_auth):
    """Also accept the static bearer tokens in MAXERGY_INTERNAL_TOKENS (comma-separated).

    These are for internal services (the MAXergy backend calling the enrichment tools) so they
    don't need the public OAuth flow. Composed with the public mode via MultiAuth; when no public
    auth is configured, the internal tokens alone are required.
    """
    tokens = [t.strip() for t in env("INTERNAL_TOKENS").split(",") if t.strip()]
    if not tokens:
        return public_auth
    from fastmcp.server.auth import MultiAuth
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

    internal = StaticTokenVerifier(tokens={t: {"client_id": "maxergy-api", "scopes": []} for t in tokens})
    return internal if public_auth is None else MultiAuth(server=public_auth, verifiers=[internal])


from fastmcp.exceptions import ToolError

from . import providers, suggestions
from .api_client import BackendError, get_api
from .contract import HouseholdAssessment, PlanResponse, RecommendationMetric
from .instructions import ONBOARDING_SCRIPT, SERVER_INSTRUCTIONS
from .logging_middleware import ToolLoggingMiddleware
from .logging_setup import setup_logging

setup_logging()

_public_auth = _build_auth()
_auth = _with_internal_tokens(_public_auth)

mcp = FastMCP(
    name="maxergy-advisor",
    instructions=SERVER_INSTRUCTIONS,
    auth=_auth,
)
mcp.add_middleware(ToolLoggingMiddleware())

# Passphrase mode serves its own gate pages.
from .passphrase_auth import PassphraseOAuthProvider, register_gate_routes

if isinstance(_public_auth, PassphraseOAuthProvider):
    register_gate_routes(mcp, _public_auth)

# Serve favicons / logo (used by the gate page and browser tab; /favicon.ico was 404ing).
_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def _register_static() -> None:
    from starlette.responses import FileResponse, Response

    files = {
        "/favicon.ico": ("favicon.ico", "image/x-icon"),
        "/favicon-32.png": ("favicon-32.png", "image/png"),
        "/favicon-16.png": ("favicon-16.png", "image/png"),
        "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
        "/logo.png": ("logo.png", "image/png"),
    }
    for route, (name, media) in files.items():
        path = os.path.join(_STATIC_DIR, name)

        def make(p=path, m=media):
            async def handler(request):  # noqa: ANN202
                if not os.path.exists(p):
                    return Response(status_code=404)
                return FileResponse(p, media_type=m, headers={"Cache-Control": "public, max-age=86400"})

            return handler

        mcp.custom_route(route, methods=["GET"])(make())


_register_static()

# FastMCP serves protected-resource metadata only at the path-scoped
# /.well-known/oauth-protected-resource/mcp. Some Claude discovery paths also fetch the
# ROOT /.well-known/oauth-protected-resource and 404 on it — alias it to avoid stalling
# the connector handshake.
if _public_base_url() and env("AUTH_MODE", "bearer").lower() in {
    "fastmcp",
    "passphrase",
    "google",
}:
    from starlette.responses import JSONResponse

    @mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
    async def _root_protected_resource(request):  # noqa: ANN202
        base = _public_base_url()
        return JSONResponse(
            {
                "resource": f"{base}/mcp",
                "authorization_servers": [f"{base}/"],
                "scopes_supported": [],
                "bearer_methods_supported": ["header"],
            }
        )


def _assumptions() -> dict:
    try:
        return get_api().assumptions()
    except BackendError as e:
        raise ToolError(str(e)) from e


def _plan(assessment: HouseholdAssessment, metric: RecommendationMetric | None = None) -> dict:
    """POST /plan on the backend; validated against the generated contract (drift guard)."""
    try:
        plan = get_api().plan(assessment.model_dump(mode="json"), metric.value if metric else None)
    except BackendError as e:
        raise ToolError(str(e)) from e
    PlanResponse.model_validate(plan)
    return plan


def _headline(s: dict) -> str:
    now, after = s["monthly_saving_eur"], s["monthly_saving_post_payoff_eur"]
    if now >= 0:
        return f"saves about €{now:,.0f}/month now (loan included), €{after:,.0f}/month after payoff"
    return f"costs about €{-now:,.0f}/month more while the loan runs, saves €{after:,.0f}/month after payoff"


def _components(s: dict) -> set[str]:
    return {c for c, on in s["components"].items() if on}


def _summary(s: dict) -> dict:
    f = s.get("financials") or {}
    return {
        "id": s["id"],
        "components": sorted(_components(s)),
        "monthly_saving_eur": s["monthly_saving_eur"],
        "monthly_saving_post_payoff_eur": s["monthly_saving_post_payoff_eur"],
        "financing_installment_eur": s["monthly_cost_eur"]["financing_installment"],
        "cumulative_net_savings_central_eur": f.get("cumulative_net_savings_central_eur"),
        "break_even_year": f.get("break_even_year"),
        "payback_month": s.get("payback_month"),
        "headline": _headline(s),
    }


def _delta(better: dict, base: dict) -> dict:
    fb, fa = better.get("financials") or {}, base.get("financials") or {}
    return {
        "adds": sorted(_components(better) - _components(base)),
        "monthly_saving_delta_eur": round(better["monthly_saving_eur"] - base["monthly_saving_eur"], 2),
        "monthly_saving_post_payoff_delta_eur": round(
            better["monthly_saving_post_payoff_eur"] - base["monthly_saving_post_payoff_eur"], 2
        ),
        "cumulative_net_savings_delta_eur": round(
            (fb.get("cumulative_net_savings_central_eur") or 0) - (fa.get("cumulative_net_savings_central_eur") or 0), 2
        ),
    }


def _next_best_upgrade(plan: dict, current_scenario_id: str | None) -> dict:
    rec = plan["recommendation"]
    by_id = {s["id"]: s for s in plan["forecast"]["scenarios"]}
    ranked = [by_id[i["id"]] for i in rec["ranked_scenarios"]]
    if not ranked:
        return {"next_best_upgrade": None, "reason": _NO_SCENARIOS}

    if current_scenario_id:
        if current_scenario_id not in by_id:
            raise ToolError(f"Unknown scenario '{current_scenario_id}'; available: {', '.join(by_id)}")
        current = by_id[current_scenario_id]
        bigger = [s for s in ranked if _components(s) > _components(current)]
        if not bigger:
            return {"next_best_upgrade": None, "current": _summary(current),
                    "reason": "No larger upgrade option extends the current one."}
        return {"next_best_upgrade": _summary(bigger[0]), "current": _summary(current),
                "step": _delta(bigger[0], current)}

    best = ranked[0]
    steps = [{"from": s["id"], **_delta(best, s)} for s in ranked if _components(s) < _components(best)]
    return {"next_best_upgrade": _summary(best), "steps": steps, "rationale": rec["rationale"]}


_NO_SCENARIOS = "No upgrade scenario is available for this household with the selected options."
_RESIDENTIAL = {"", "home", "residential", "old", "average", "modern", "efficient"}
_COMMERCIAL_NOTE = (
    "MAXergy currently models residential buildings only; commercial buildings are not supported yet."
)


@mcp.tool
def start_advisor() -> str:
    """Begin a MAXergy home-energy savings analysis. Call this FIRST whenever the user
    wants to use MAXergy or asks about saving on home energy / solar / heat pump / EV.
    Returns the onboarding script — then ask the household the questions one at a time,
    like a form, before running `energy_savings_overview`."""
    return ONBOARDING_SCRIPT


@mcp.prompt(name="maxergy_advisor", title="Start MAXergy energy advisor")
def maxergy_advisor_prompt() -> str:
    """Kick off the MAXergy onboarding + savings analysis."""
    return "Act as the MAXergy home-energy advisor. " + ONBOARDING_SCRIPT


@mcp.tool
def default_assumptions() -> dict:
    """The MAXergy engine's default assumptions (tariff, solar, battery, heat pump, EV,
    investment costs, financing, price growth, supported inputs). Use them as the defaults
    you propose during onboarding."""
    return _assumptions()


@mcp.tool
def estimate_heating_spend(
    living_area_m2: float, heating_type: str = "gas", building_type: str = "average"
) -> dict:
    """Estimate annual heating consumption and spend from floor area, to PROPOSE to the user.

    heating_type: gas | oil (the only fuels MAXergy models).
    building_type: insulation class old | average | modern | efficient (residential only)."""
    kind = building_type.lower()
    if kind not in _RESIDENTIAL:
        return {"supported": False, "note": _COMMERCIAL_NOTE}
    insulation = kind if kind in suggestions.HEATING_DEMAND_KWH_PER_M2 else suggestions.DEFAULT_INSULATION
    return suggestions.estimate_heating_spend(_assumptions(), living_area_m2, heating_type, insulation)


@mcp.tool
def suggest_battery_kwh(pv_kwp: float, annual_electricity_kwh: float | None = None) -> dict:
    """Suggest a home-battery size (kWh) to propose: ~1 kWh per kWp of solar, 5–15 kWh."""
    return suggestions.suggest_battery_kwh(_assumptions(), pv_kwp, annual_electricity_kwh)


@mcp.tool
def geocode_address(address: str) -> dict:
    """Resolve a street address to latitude/longitude (Google Geocoding)."""
    lat, lon = providers.geocode(address)
    return {"address": address, "lat": lat, "lon": lon}


@mcp.tool
def get_roof_geometry(lat: float, lon: float) -> dict:
    """Roof planes (tilt, azimuth, area) and the installable system ceiling for a building.

    Roof pitch = the tilt of roof-mounted panels, so the largest segment's tilt/azimuth is the
    best proposal for household.roof. `max_array_area_m2` approximates the usable roof area.
    """
    return providers.get_roof_geometry(lat, lon).model_dump()


@mcp.tool
def estimate_pv_production(
    lat: float,
    lon: float,
    kwp: float,
    tilt_degrees: float,
    azimuth_degrees: float,
    system_loss_pct: float = 14.0,
) -> dict:
    """Annual + monthly PV yield (kWh) for a system, via PVGIS. azimuth: 0=N,90=E,180=S,270=W.

    Call with kwp=1 to get the site's `specific_yield_kwh_per_kwp` for
    household.roof.specific_yield_kwh_per_kwp."""
    return providers.estimate_pv_production(lat, lon, kwp, tilt_degrees, azimuth_degrees, system_loss_pct)


@mcp.tool
def suggest_electricity_price(building_type: str = "home", monthly_spend_eur: float | None = None) -> dict:
    """Propose the default German household tariff (work price €/kWh, base price €/month) and,
    from a monthly bill, the implied annual kWh — for the user to confirm."""
    if building_type.lower() not in _RESIDENTIAL:
        return {"supported": False, "note": _COMMERCIAL_NOTE}
    return suggestions.suggest_electricity_price(_assumptions(), monthly_spend_eur)


@mcp.tool
def estimate_roof_capacity_from_area(floor_area_m2: float, stories: int = 1) -> dict:
    """Fallback usable roof area (m²) and PV ceiling from floor area when get_roof_geometry
    fails or returns low_confidence."""
    return suggestions.estimate_roof_capacity_from_area(_assumptions(), floor_area_m2, stories)


@mcp.tool
def energy_savings_overview(
    assessment: HouseholdAssessment, metric: RecommendationMetric | None = None
) -> dict:
    """The headline overview: forecast + recommendation for a household, computed by the
    MAXergy backend's production engine (POST /plan).

    Returns `forecast` (baseline costs, up to six upgrade scenarios with monthly costs incl.
    the loan instalment, monthly net saving, saving after payoff, financials, short/long-term
    forecasts) and `recommendation` (best scenario, ranking, rationale). `metric` ranks by
    `cumulative_central` (default) or `monthly_net`. Lead the answer with the recommended
    scenario's monthly figure and be honest when it is negative during the loan."""
    return _plan(assessment, metric)


@mcp.tool
def compare_scenarios(
    assessment: HouseholdAssessment, metric: RecommendationMetric | None = None
) -> dict:
    """All upgrade options side by side, ranked exactly like the MAXergy app (same backend
    ranking), each with its monthly figures, long-term total and a one-line headline."""
    plan = _plan(assessment, metric)
    rec = plan["recommendation"]
    by_id = {s["id"]: s for s in plan["forecast"]["scenarios"]}
    return {
        "recommended": rec["selected_scenario_id"],
        "metric": rec["metric_used"],
        "ranked": [{**_summary(by_id[i["id"]]), "score_eur": i["score_eur"]} for i in rec["ranked_scenarios"]],
        "rationale": rec["rationale"],
    }


@mcp.tool
def project_savings(assessment: HouseholdAssessment) -> dict:
    """Cumulative net savings per upgrade option over the forecast horizon (central prices),
    for a multi-line chart: x = year, y = cumulative € saved vs. today, one line per option.
    Lines start negative while the loan runs and rise once savings exceed the instalments."""
    plan = _plan(assessment)
    years = [p["year"] for p in plan["forecast"]["baseline"]["long_term_forecast"]]
    series = [
        {
            "scenario": s["id"],
            "cumulative_eur": [round(p.get("cumulative_saving_eur") or 0) for p in s["long_term_forecast"]],
            "break_even_year": (s.get("financials") or {}).get("break_even_year"),
            "monthly_saving_eur": s["monthly_saving_eur"],
            "monthly_saving_post_payoff_eur": s["monthly_saving_post_payoff_eur"],
        }
        for s in plan["forecast"]["scenarios"]
    ]
    series.sort(key=lambda x: x["cumulative_eur"][-1] if x["cumulative_eur"] else 0, reverse=True)
    return {
        "years": years,
        "series": series,
        "recommended": plan["recommendation"]["selected_scenario_id"],
        "chart": {"x_label": "Year", "y_label": "Cumulative € saved vs. today", "type": "line"},
        "note": "Render as a line chart, one line per option; highlight the recommended one.",
    }


@mcp.tool
def next_best_upgrade(assessment: HouseholdAssessment, current_scenario_id: str | None = None) -> dict:
    """What each additional component adds, framed around the outcome.

    Without `current_scenario_id`: the recommended option and, for every smaller option it
    contains, what the extra components add per month and over the horizon.
    With `current_scenario_id` (e.g. "solar_only"): the best-ranked option that extends it, and
    what that step adds."""
    return _next_best_upgrade(_plan(assessment), current_scenario_id)


@mcp.tool
def recommend_upsell(assessment: HouseholdAssessment, current_scenario_id: str | None = None) -> dict:
    """Deprecated alias of `next_best_upgrade` (kept for existing clients; will be removed)."""
    return _next_best_upgrade(_plan(assessment), current_scenario_id)


@mcp.tool
def model_savings() -> dict:
    """Deprecated: replaced by `energy_savings_overview` (will be removed)."""
    return {
        "deprecated": True,
        "use_instead": "energy_savings_overview",
        "note": "Per-scenario savings now come from the MAXergy backend; call "
        "energy_savings_overview with the household assessment.",
    }


def main() -> None:
    """Run over stdio locally, or streamable HTTP when a PORT is present (Railway/cloud).

    Override explicitly with MCP_TRANSPORT (stdio|http|sse|streamable-http).
    """
    import os

    port = os.environ.get("PORT")
    transport = os.environ.get("MCP_TRANSPORT") or ("http" if port else "stdio")
    if transport == "stdio":
        mcp.run()
    else:
        # Stateless HTTP + JSON responses (no SSE streaming, no Mcp-Session-Id juggling).
        # This matches the proven-working kanban connector: the claude.ai connector
        # completes OAuth but fails tool discovery against the default stateful/SSE
        # session handshake (see FastMCP #1466). Stateless mode is what it expects.
        mcp.run(
            transport=transport,
            # HOST="::" listens on IPv6 only: set it only for legacy IPv6-only Railway environments.
            host=os.environ.get("HOST", "0.0.0.0"),
            port=int(port or 8000),
            stateless_http=True,
            json_response=True,
        )


if __name__ == "__main__":
    main()
