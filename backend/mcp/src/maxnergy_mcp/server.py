"""MAXnergy MCP server.

The client LLM runs the onboarding conversation and holds the HouseholdProfile.
These tools are the calculators it can't do reliably in-context: roof geometry,
irradiance, production, and the per-scenario monthly-saving math.

Typical flow:
  1. geocode_address  -> lat/lon
  2. get_roof_geometry -> existing tilt/azimuth + installable ceiling (upsell room)
  3. estimate_pv_production -> annual kWh for a given system
  4. compare_scenarios -> ranks the upgrade ladder by monthly saving
  5. recommend_upsell -> the single strongest next step, framed for a proposal
"""

from __future__ import annotations

import os

from fastmcp import FastMCP


def _public_base_url() -> str:
    """Public https URL of this server, for OAuth metadata/redirects."""
    explicit = os.environ.get("PUBLIC_BASE_URL", "").strip()
    if explicit:
        return explicit.rstrip("/")
    domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
    return f"https://{domain}" if domain else ""


def _warn(msg: str) -> None:
    import sys

    print(f"[maxnergy] {msg}", file=sys.stderr)


def _bearer_auth():
    token = os.environ.get("MAXNERGY_API_TOKEN", "").strip()
    if not token:
        return None
    from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

    return StaticTokenVerifier(tokens={token: {"client_id": "maxnergy", "scopes": []}})


def _build_auth():
    """Select the auth provider via MAXNERGY_AUTH_MODE — switchable on redeploy, no code change.

      - "bearer" (default): shared-secret StaticTokenVerifier (MAXNERGY_API_TOKEN). Simplest;
        for Claude Code / the Anthropic API MCP connector. Cannot be used by the claude.ai app.
      - "fastmcp": InMemoryOAuthProvider — FastMCP *is* the OAuth server (DCR + authorize +
        token), no external identity provider. Lets the claude.ai web/desktop/mobile connector
        attach with zero IdP setup. Caveat: it simulates consent (no real login) and keeps
        clients/tokens in memory, so it's effectively open access and re-auths after a redeploy.
      - "passphrase": self-hosted OAuth (as "fastmcp") but the authorization step is held
        behind one shared passphrase (MAXNERGY_AUTH_PASSPHRASE). Works in the claude.ai app,
        no IdP, single shared secret (no per-user identity).
      - "google": GoogleProvider — real Google login via OAuth proxy. Needs
        GOOGLE_OAUTH_CLIENT_ID/SECRET; gives genuine per-user access control.

    Unknown/misconfigured modes fall back to bearer (with a warning) so a deploy never breaks.
    """
    mode = os.environ.get("MAXNERGY_AUTH_MODE", "bearer").strip().lower()
    base_url = _public_base_url()

    if mode == "passphrase":
        passphrase = os.environ.get("MAXNERGY_AUTH_PASSPHRASE", "").strip()
        if passphrase and base_url:
            from .passphrase_auth import PassphraseOAuthProvider

            return PassphraseOAuthProvider(base_url=base_url, passphrase=passphrase)
        _warn("MAXNERGY_AUTH_MODE=passphrase but MAXNERGY_AUTH_PASSPHRASE or base URL missing — using bearer.")

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
            signing_key = os.environ.get("MAXNERGY_JWT_SIGNING_KEY", "").strip() or None
            return GoogleProvider(
                client_id=client_id,
                client_secret=client_secret,
                base_url=base_url,
                required_scopes=["openid", "email"],
                jwt_signing_key=signing_key,
            )
        _warn("MAXNERGY_AUTH_MODE=google but GOOGLE_OAUTH_CLIENT_ID/SECRET or base URL missing — using bearer.")

    if mode not in {"bearer", "fastmcp", "passphrase", "google"}:
        _warn(f"unknown MAXNERGY_AUTH_MODE={mode!r} — using bearer.")

    return _bearer_auth()


from . import providers, suggestions
from .logging_middleware import ToolLoggingMiddleware
from .logging_setup import setup_logging
from .model_engine import run_overview
from .model_schema import ModelInput
from .models import HouseholdProfile, Scenario
from .savings import evaluate_scenario

setup_logging()

_auth = _build_auth()

mcp = FastMCP(
    name="maxnergy-advisor",
    instructions=(
        "MAXnergy is a household energy-transition advisor. When the user wants to use "
        "MAXnergy (or asks about home-energy savings), FIRST call the `start_advisor` "
        "tool and follow the onboarding script it returns: ask the household questions "
        "ONE AT A TIME like a form, wait for each answer, and never dump the whole "
        "questionnaire at once. After collecting the inputs, call `compare_scenarios` and "
        "`recommend_upsell`, then present the result led by €/month saved (and, when the "
        "financing installment outweighs savings early, say so honestly)."
    ),
    auth=_auth,
)
mcp.add_middleware(ToolLoggingMiddleware())

# Passphrase mode serves its own gate pages.
from .passphrase_auth import PassphraseOAuthProvider, register_gate_routes

if isinstance(_auth, PassphraseOAuthProvider):
    register_gate_routes(mcp, _auth)

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
if _public_base_url() and os.environ.get("MAXNERGY_AUTH_MODE", "bearer").strip().lower() in {
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


ONBOARDING_SCRIPT = """You are running the MAXnergy home-energy onboarding. Conduct it like a
friendly form: ask ONE question at a time, wait for the answer, then ask the next. Do NOT
list all questions at once. If the user doesn't know a value, apply the stated default,
say which default you used, and move on. Keep each question to one short sentence.

MAXnergy serves both private homes and commercial buildings with ONE flow — a home is just
the default building type. Set the profile's `building_type` from the user's answer
(home | office | retail | warehouse | hotel | school); it drives the heating benchmark and,
importantly, how much solar is self-consumed (daytime businesses self-consume far more than
evening-heavy homes). For a large/commercial building, add the honest caveat that heating and
tariff figures are benchmark estimates, good for a first read, not a substitute for an audit.

Ask in this order:
1. Address — street, postcode, city. (Used for roof geometry + sun/irradiance.)
2. Building — is this a home or a business? If a business, what type (office, retail,
   warehouse, hotel, school)? Set `building_type` accordingly (default "home").
3. Heating — gas, oil, heat pump, district, or electric? Then ask the floor area in m².
   Call `estimate_heating_spend` with the building_type and PROPOSE the figure to confirm —
   e.g. "For a ~{m2} m² {building} on gas, that's roughly €{spend}/year on heating. Sound
   about right, or do you have a bill handy?" Use their actual number if they give one.
4. Cars — how many vehicles (a fleet is fine), and for each: electric or petrol/diesel, and
   roughly how many km per year? (Default 13,000 km/yr if unsure.)
5. Existing solar — first call `geocode_address` then `get_roof_geometry`. It returns
   `suggested_system_kwp`, `max_array_kwp`, and `low_confidence`. If `low_confidence` is true
   (the Solar API likely found a small adjacent building — common for large/industrial sites),
   DON'T trust the tiny ceiling: call `estimate_roof_capacity_from_area` with the floor area
   from step 3 and use that instead, telling the user the automatic roof scan looked off so
   you estimated from the building size. Then ask whether they have panels and propose the
   number — e.g. "Your roof could fit about {max} kWp; a typical install is ~{suggested} kWp.
   Does that match, or do you know the exact size?" No API reads the installed size — refine it.
6. Solar financing — if financed, monthly installment and months left? (Skip if owned/none.)
7. Battery — installed? If yes, ask capacity in kWh. If NOT, call `suggest_battery_kwh` and
   mention what size would suit them — framed as upsell info, not a required answer.
8. Electricity — ask their monthly electricity spend in euros. Then call
   `suggest_electricity_price` with the building_type and PROPOSE the per-kWh price to confirm
   — e.g. "For a business like yours I'd assume about €0.20/kWh, which works out to ~{kwh}
   kWh/year. Does that price sound right, or do you know your contract rate?" Set the
   confirmed price on the profile (it determines the implied annual kWh, which matters a lot).
9. Feed-in tariff — what do you get paid per kWh exported? (Default €0.08/kWh if unsure.)
10. (Commercial only) Peak demand charge — ask whether the power bill has a demand charge
    (Leistungspreis, €/kW per month) and the billed peak in kW. If so, set
    `peak_demand_charge_eur_per_kw_month` and `billed_peak_kw` — a battery then shaves peak
    costs. Skip entirely for homes.

When done: build the profile (building_type, confirmed electricity price, roof size), then
call `compare_scenarios`, `project_savings`, and `recommend_upsell`.
- RENDER `project_savings` as a line chart (an artifact / chart): x = months, y = cumulative
  € saved, one line per upgrade path — so the user sees every upsell option compared visually.
- Lead the written summary with the best path's €/month saved (now, and after payoff if they
  differ), explain in plain language why across the savings buckets, and name the single
  strongest next upgrade. Then list the OTHER upgrade options with their €/month so a bigger
  package that saves more is on the table. Currency EUR, round to whole euros, no jargon."""


@mcp.tool
def start_advisor() -> str:
    """Begin a MAXnergy home-energy savings analysis. Call this FIRST whenever the user
    wants to use MAXnergy or asks about saving on home energy / solar / heat pump / EV.
    Returns the onboarding script — then ask the household the questions one at a time,
    like a form, before running the savings tools."""
    return ONBOARDING_SCRIPT


@mcp.prompt(name="maxnergy_advisor", title="Start MAXnergy energy advisor")
def maxnergy_advisor_prompt() -> str:
    """Kick off the MAXnergy onboarding + savings analysis."""
    return (
        "Act as the MAXnergy home-energy advisor. " + ONBOARDING_SCRIPT
    )


@mcp.tool
def estimate_heating_spend(
    living_area_m2: float, heating_type: str = "gas", building_type: str = "average"
) -> dict:
    """Estimate annual heating spend from floor area, to PROPOSE to the user for confirmation.

    heating_type: gas|oil|heat_pump|district|electric_resistive|wood.
    building_type: residential vintage (old|average|modern|efficient) OR use type
    (home|office|retail|warehouse|hotel|school). Same tool for a flat or a 4,500 m² office."""
    return suggestions.estimate_heating_spend(living_area_m2, heating_type, building_type)


@mcp.tool
def suggest_battery_kwh(pv_kwp: float, annual_electricity_kwh: float | None = None) -> dict:
    """Suggest a home-battery size (kWh) for the household, to propose for the upsell.

    Anchored to ~1 kWh per kWp of solar (and per 1,000 kWh/yr of use), 5–15 kWh typical."""
    return suggestions.suggest_battery_kwh(pv_kwp, annual_electricity_kwh)


@mcp.tool
def geocode_address(address: str) -> dict:
    """Resolve a street address to latitude/longitude (Google Geocoding)."""
    lat, lon = providers.geocode(address)
    return {"address": address, "lat": lat, "lon": lon}


@mcp.tool
def get_roof_geometry(lat: float, lon: float) -> dict:
    """Roof planes (tilt, azimuth, area) and the installable system ceiling for a building.

    Roof pitch = the tilt of any roof-mounted panels, so the largest segment's
    tilt/azimuth is your best estimate of the existing array's orientation.
    `max_array_kwp` is the upsell ceiling — how big the system could get.
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
    """Annual + monthly PV yield (kWh) for a system, via PVGIS. azimuth: 0=N,90=E,180=S,270=W."""
    return providers.estimate_pv_production(lat, lon, kwp, tilt_degrees, azimuth_degrees, system_loss_pct)


@mcp.tool
def suggest_electricity_price(building_type: str = "home", monthly_spend_eur: float | None = None) -> dict:
    """Propose a €/kWh electricity price for the building type (and implied annual kWh), to confirm.

    Residential ~0.35, commercial ~0.28, industrial/warehouse ~0.20. Set the profile's
    electricity_price_eur_per_kwh from the confirmed value — it drives the kWh the spend implies."""
    return suggestions.suggest_electricity_price(building_type, monthly_spend_eur)


@mcp.tool
def estimate_roof_capacity_from_area(floor_area_m2: float, stories: int = 1) -> dict:
    """Fallback PV roof ceiling from floor area when get_roof_geometry returns low_confidence
    (a tiny roof for a large building). A single-story hall's roof ≈ its footprint."""
    return suggestions.estimate_roof_capacity_from_area(floor_area_m2, stories)


@mcp.tool
def project_savings(profile: HouseholdProfile, horizon_months: int = 180) -> dict:
    """Cumulative-savings time series per upgrade path, for charting as a multi-line graph.

    Returns months on the x-axis and, for each scenario in the upgrade ladder, the cumulative
    net saving (vs. doing nothing) on the y-axis — savings_now while its financing runs, then
    savings_after_payoff. The horizon runs past the financing term (default 15y) so the chart
    shows each path crossing above the baseline once it's paid off. Includes each path's monthly
    figures and break-even month. Render as a line chart: one line per scenario, x = months."""
    ladder = _build_ladder(profile)
    months = list(range(0, horizon_months + 1, 3))  # quarterly points keep the chart light
    series = []
    for s in ladder:
        production = _production_for(profile, s)
        r = evaluate_scenario(profile, s, production)
        fin_months = s.financing_months if (s.add_pv_kwp or s.add_battery_kwh or s.add_heat_pump or s.add_ev or s.add_ev_charger) else 0
        cumulative, running, breakeven = [], 0.0, None
        for m in range(0, horizon_months + 1):
            rate = r.monthly_saving_now_eur if m < fin_months else r.monthly_saving_after_payoff_eur
            running += rate
            if breakeven is None and running >= 0 and m > 0:
                breakeven = m
            if m % 3 == 0:
                cumulative.append(round(running))
        series.append({
            "scenario": r.scenario,
            "cumulative_eur": cumulative,
            "monthly_saving_now_eur": r.monthly_saving_now_eur,
            "monthly_saving_after_payoff_eur": r.monthly_saving_after_payoff_eur,
            "financing_months": fin_months,
            "breakeven_month": breakeven,
        })
    series.sort(key=lambda x: x["cumulative_eur"][-1], reverse=True)
    return {
        "months": months,
        "series": series,
        "chart": {"x_label": "Months", "y_label": "Cumulative € saved vs. today", "type": "line"},
        "note": "Render as a line chart, one line per scenario. Lead the summary with the best path.",
    }


@mcp.tool
def model_savings(profile: HouseholdProfile, scenario: Scenario) -> dict:
    """Evaluate ONE upgrade scenario against the household's status quo.

    Returns the per-bucket (electricity/heating/mobility) split plus the North Star:
    monthly saving now (incl. new financing) and after the financing is paid off.
    Pass production_annual_kwh implicitly by setting the profile's existing kWp and
    letting the engine use PVGIS-derived yield where available.
    """
    production = _production_for(profile, scenario)
    return evaluate_scenario(profile, scenario, production).model_dump()


@mcp.tool
def compare_scenarios(profile: HouseholdProfile) -> dict:
    """Build and rank the standard upgrade ladder for this household by monthly saving.

    Ladder: status quo solar -> +battery -> +heat pump -> +EV (each step cumulative),
    plus a "max" scenario stacking everything. Returns every scenario sorted best-first
    so the LLM can recommend the configuration with the biggest €/month saving.
    """
    ladder = _build_ladder(profile)
    results = []
    for s in ladder:
        production = _production_for(profile, s)
        results.append(evaluate_scenario(profile, s, production).model_dump())
    results.sort(key=lambda r: r["monthly_saving_now_eur"], reverse=True)
    return {
        "best": results[0] if results else None,
        "ranked": results,
        "north_star": "monthly_saving_now_eur",
    }


@mcp.tool
def recommend_upsell(profile: HouseholdProfile) -> dict:
    """Spot the single strongest next upgrade vs. what the household has today.

    Compares each individual add-on (battery, heat pump, EV) as a standalone step and
    returns the one with the best marginal monthly saving, with proposal-ready copy.
    """
    candidates: list[Scenario] = []
    if profile.heating_type.value in {"gas", "oil"}:
        candidates.append(Scenario(name="Add heat pump", add_heat_pump=True))
    if not profile.battery_installed:
        candidates.append(Scenario(name="Add home battery", add_battery_kwh=max(profile.existing_pv_kwp, 5.0)))
    if any(c.kind.lower() == "ice" for c in profile.cars):
        candidates.append(Scenario(name="Switch to EV", add_ev=True, add_ev_charger=True))

    if not candidates:
        return {"recommendation": None, "reason": "Household already has battery, heat pump, and EV."}

    scored = []
    for s in candidates:
        production = _production_for(profile, s)
        scored.append(evaluate_scenario(profile, s, production).model_dump())
    scored.sort(key=lambda r: r["monthly_saving_after_payoff_eur"], reverse=True)
    best = scored[0]
    return {
        "recommendation": best["scenario"],
        "headline": best["headline"],
        "monthly_saving_after_payoff_eur": best["monthly_saving_after_payoff_eur"],
        "monthly_saving_now_eur": best["monthly_saving_now_eur"],
        "all_candidates": scored,
    }


@mcp.tool
def energy_savings_overview(model: ModelInput) -> dict:
    """The headline overview: one structured, outcome-first read of a building's energy future.

    Takes the canonical model input (location, electricity tariff, heating, mobility,
    upgrade candidates, financing, forecast horizon) and returns the full picture:
      - baseline monthly cost (electricity/heating/mobility) + seasonal short-term and
        escalating long-term forecasts;
      - the fixed upgrade ladder (solar_only, pv_battery, pv_heatpump, pv_ev,
        pv_battery_heatpump, full_upgrade), each with sizing, monthly cost incl. financing,
        €/month saved now, the honest "saves €X/mo after payoff" figure when it's
        cost-neutral early, self-consumption ratio, forecasts, and the payback month.

    This is the primary, positively-framed entry point — lead the summary with the clear
    monthly number. Works for homes and commercial buildings alike.
    """
    return run_overview(model)


# --- helpers ---

def _production_for(profile: HouseholdProfile, scenario: Scenario) -> float | None:
    """Best-effort PVGIS yield for the scenario's total system; None if no geometry/key."""
    total_kwp = profile.existing_pv_kwp + scenario.add_pv_kwp
    if total_kwp <= 0 or profile.lat is None or profile.lon is None:
        return None
    tilt = profile.pv_tilt_degrees if profile.pv_tilt_degrees is not None else 35.0
    azimuth = profile.pv_azimuth_degrees if profile.pv_azimuth_degrees is not None else 180.0
    try:
        return providers.estimate_pv_production(profile.lat, profile.lon, total_kwp, tilt, azimuth)["annual_kwh"]
    except Exception:
        return None  # fall back to the engine's default specific yield


def _build_ladder(profile: HouseholdProfile) -> list[Scenario]:
    """Upgrade ladder: individual steps (so each upsell shows as its own line on the chart)
    plus the cumulative combos. Battery sized to the system (commercial scales up)."""
    batt = max(profile.existing_pv_kwp, 5.0)
    has_ice = any(c.kind.lower() == "ice" for c in profile.cars)
    ladder = [
        Scenario(name="Keep current setup"),
        Scenario(name="+ Battery", add_battery_kwh=batt),
        Scenario(name="+ Heat pump", add_heat_pump=True),
    ]
    if has_ice:
        ladder.append(Scenario(name="+ EV fleet", add_ev=True, add_ev_charger=True))
    ladder.append(Scenario(name="+ Battery + Heat pump", add_battery_kwh=batt, add_heat_pump=True))
    ladder.append(
        Scenario(
            name="+ Battery + Heat pump + EV" if has_ice else "+ Battery + Heat pump (max)",
            add_battery_kwh=batt,
            add_heat_pump=True,
            add_ev=has_ice,
            add_ev_charger=has_ice,
        )
    )
    return ladder


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
            host="0.0.0.0",
            port=int(port or 8000),
            stateless_http=True,
            json_response=True,
        )


if __name__ == "__main__":
    main()
