"""
Tools the AI advisor (Gemini function calling) may use, and the shared onboarding script.

- Lookup/suggestion tools are forwarded to the MCP service (backend allow-list in mcp_client).
- `run_plan` runs in-process: forecasting + recommendation services, exactly like POST /plan
  (never through the MCP, so requests cannot loop between the services).
- The onboarding script is the MCP prompt `maxergy_advisor`, so web chat and claude.ai ask the
  same questions; cached for an hour.
"""

import time

from pydantic import ValidationError

from src.models.forecast_schemas import HouseholdAssessment, PlanResponse
from src.services.forecasting.baseline_service import get_forecasting_service
from src.services.llm.advisor_context import scenario_sentence
from src.services.mcp.mcp_client import McpToolError, McpUnavailable, get_mcp_client
from src.services.recommendation.recommendation_service import build_recommendation
from src.utils.custom_logger import log_handler

_NUM = {"type": "number"}

# Declarations mirror the MCP tool signatures (backend/mcp/src/maxergy_mcp/server.py).
MCP_TOOL_DECLARATIONS = [
    {
        "name": "geocode_address",
        "description": "Coordinates for a German street address or postcode.",
        "parameters": {"type": "object", "properties": {"address": {"type": "string"}}, "required": ["address"]},
    },
    {
        "name": "get_roof_geometry",
        "description": "Roof segments (tilt, azimuth, usable area) from the satellite roof scan.",
        "parameters": {"type": "object", "properties": {"lat": _NUM, "lon": _NUM}, "required": ["lat", "lon"]},
    },
    {
        "name": "estimate_pv_production",
        "description": "PVGIS yield; call with kwp=1 to get specific_yield_kwh_per_kwp for the roof.",
        "parameters": {
            "type": "object",
            "properties": {"lat": _NUM, "lon": _NUM, "kwp": _NUM, "tilt_degrees": _NUM, "azimuth_degrees": _NUM},
            "required": ["lat", "lon", "kwp", "tilt_degrees", "azimuth_degrees"],
        },
    },
    {
        "name": "estimate_roof_capacity_from_area",
        "description": "Usable roof area and max kWp estimated from the living area.",
        "parameters": {
            "type": "object",
            "properties": {"floor_area_m2": _NUM, "stories": {"type": "integer"}},
            "required": ["floor_area_m2"],
        },
    },
    {
        "name": "estimate_heating_spend",
        "description": "Typical yearly heating consumption and spend (gas or oil).",
        "parameters": {
            "type": "object",
            "properties": {"living_area_m2": _NUM, "heating_type": {"type": "string", "enum": ["gas", "oil"]}},
            "required": ["living_area_m2"],
        },
    },
    {
        "name": "suggest_battery_kwh",
        "description": "Battery size proposal for a PV system.",
        "parameters": {
            "type": "object",
            "properties": {"pv_kwp": _NUM, "annual_electricity_kwh": _NUM},
            "required": ["pv_kwp"],
        },
    },
    {
        "name": "suggest_electricity_price",
        "description": "Default tariff; with monthly_spend_eur also the implied yearly kWh.",
        "parameters": {"type": "object", "properties": {"monthly_spend_eur": _NUM}},
    },
]


def run_plan_declaration() -> dict:
    """`run_plan` takes a full HouseholdAssessment (JSON schema generated from the backend model)."""
    schema = HouseholdAssessment.model_json_schema()
    defs = schema.pop("$defs", {})  # `$ref`s point at the document root
    return {
        "name": "run_plan",
        "description": "Compute the MAXergy plan (forecast + recommendation) for a complete household "
        "assessment. Call it once all onboarding answers are collected.",
        "parameters_json_schema": {
            "type": "object",
            "properties": {"assessment": schema},
            "required": ["assessment"],
            "$defs": defs,
        },
    }


class ToolRunner:
    """Executes advisor tool calls; remembers the last plan computed in this conversation turn."""

    def __init__(self) -> None:
        self.assessment: HouseholdAssessment | None = None
        self.plan: PlanResponse | None = None
        self.used: list[str] = []

    def __call__(self, name: str, args: dict) -> dict:
        self.used.append(name)
        if name == "run_plan":
            return self._run_plan(args.get("assessment") or {})
        try:
            return get_mcp_client().call_tool(name, args)
        except ValueError as e:  # not allow-listed
            return {"error": str(e)}
        except (McpUnavailable, McpToolError) as e:
            log_handler.warning("[advisor_tools] %s failed: %s", name, str(e))
            return {"error": f"{name} is unavailable right now ({e}); ask the user or use defaults."}

    def _run_plan(self, raw: dict) -> dict:
        try:
            assessment = HouseholdAssessment.model_validate(raw)
            forecast = get_forecasting_service().generate_forecast(assessment)
        except ValidationError as e:
            return {"error": "Assessment incomplete or invalid", "details": e.errors(include_url=False)[:10]}
        except ValueError as e:  # outside what the engine models (e.g. heating fuel)
            return {"error": str(e)}
        recommendation = build_recommendation(forecast)
        self.assessment = assessment
        self.plan = PlanResponse(forecast=forecast, recommendation=recommendation)
        best = recommendation.selected_scenario
        return {
            "selected_scenario_id": recommendation.selected_scenario_id,
            "summary": scenario_sentence(best) if best else None,
            "rationale": recommendation.rationale,
            "ranked": [
                {"id": s.id, "summary": scenario_sentence(s)}
                for r in recommendation.ranked_scenarios[:3]
                for s in forecast.scenarios
                if s.id == r.id
            ],
            "validation_warnings": forecast.validation_warnings,
        }


# ── Shared onboarding script ──────────────────────────────────────────────────

_FALLBACK_ONBOARDING = (
    "The guided chat onboarding is unavailable right now. Ask the user to complete the assessment "
    "form in the app (Assessment tab); afterwards you can explain their plan here."
)
_SCRIPT_TTL = 3600.0
_script_cache: tuple[float, str] | None = None


def get_onboarding_script() -> tuple[str, bool]:
    """(script, from_mcp). The script is the MCP prompt `maxergy_advisor`, cached for an hour."""
    global _script_cache
    now = time.monotonic()
    if _script_cache and now - _script_cache[0] < _SCRIPT_TTL:
        return _script_cache[1], True
    try:
        script = get_mcp_client().get_prompt("maxergy_advisor")
    except (McpUnavailable, McpToolError) as e:
        log_handler.warning("[advisor_tools] onboarding script unavailable: %s", str(e))
        return _FALLBACK_ONBOARDING, False
    _script_cache = (now, script)
    return script, True


def clear_script_cache() -> None:
    global _script_cache
    _script_cache = None
