"""
Benchmark for the landing page: the average German household profile run through the same
forecasting and recommendation services as POST /plan.

Nothing is hard-coded: the input is documentation/data/test_profiles/average_german_household.json
(a full HouseholdAssessment) and every number comes from the engine. The engine starts its
forecast in the month after today, so the cumulative totals move slightly from month to month;
`forecast_start` says which month a response is based on. Results are cached for
`benchmark.cache_ttl_seconds` (config_file.json).
"""

import json
import time
from pathlib import Path

from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import HouseholdAssessment
from src.services.forecasting.baseline_service import get_forecasting_service
from src.services.recommendation.recommendation_service import build_recommendation

_REPO_ROOT = Path(__file__).resolve().parents[4]
_COMPONENT_NAMES = {
    "solar_pv": "Solar panels",
    "battery": "battery storage",
    "heat_pump": "heat pump",
    "ev_charger": "EV charger",
}

_cache: tuple[float, dict] | None = None


def _settings() -> dict:
    cfg = config_loader.get("benchmark", {})
    return {
        "profile_path": _REPO_ROOT / cfg.get(
            "profile_path", "documentation/data/test_profiles/average_german_household.json"
        ),
        "ttl": float(cfg.get("cache_ttl_seconds", 3600)),
    }


def load_benchmark_assessment() -> HouseholdAssessment:
    """The benchmark household as a validated HouseholdAssessment (profile notes are ignored)."""
    raw = json.loads(_settings()["profile_path"].read_text(encoding="utf-8"))
    return HouseholdAssessment.model_validate(raw)


def compute_benchmark() -> dict:
    """Run the benchmark household through forecast + recommendation; presentation dict."""
    assessment = load_benchmark_assessment()
    forecast = get_forecasting_service().generate_forecast(assessment)
    recommendation = build_recommendation(forecast)
    best = recommendation.selected_scenario
    if best is None or best.financials is None:
        raise RuntimeError("Benchmark household produced no recommendable scenario")

    components = [name for key, name in _COMPONENT_NAMES.items() if getattr(best.components, key)]
    f = best.financials
    roof = assessment.household.roof
    vehicle = assessment.mobility.vehicles[0] if assessment.mobility.vehicles else None
    return {
        "household": {
            "location": f"{assessment.location.postcode}, {assessment.location.country}",
            "occupants": assessment.household.occupants,
            "annual_electricity_kwh": assessment.household.electricity.annual_kwh,
            "heating_type": assessment.heating.fuel_type,
            "heating_annual_kwh": assessment.heating.annual_consumption or 0,
            "vehicle_type": vehicle.vehicle_type if vehicle else "none",
            "annual_mileage_km": (vehicle.annual_mileage_km or 0) if vehicle else 0,
            "roof_area_m2": roof.usable_area_m2 or 0,
            "roof_orientation": roof.orientation or "",
            "roof_tilt_deg": roof.tilt_deg or 0,
        },
        "recommendation": {
            "scenario": best.id,
            "description": " + ".join(components),
            "rationale": recommendation.rationale,
            "metric": recommendation.metric_used.value,
            "break_even_year": f.break_even_year,
            "monthly_instalment_eur": best.monthly_cost_eur.financing_installment,
            "monthly_saving_eur": best.monthly_saving_eur,
            "monthly_saving_post_payoff_eur": best.monthly_saving_post_payoff_eur,
            "cumulative_savings_eur": f.cumulative_net_savings_central_eur,
            "cumulative_savings_low_eur": f.cumulative_net_savings_low_eur,
            "cumulative_savings_high_eur": f.cumulative_net_savings_high_eur,
        },
        "scenarios_count": len(forecast.scenarios),
        "projection_years": f.horizon_years,
        "model_version": forecast.model.version if forecast.model else "unknown",
        "forecast_start": forecast.baseline.short_term_forecast[0].month
        if forecast.baseline.short_term_forecast
        else None,
    }


def get_benchmark() -> dict:
    """Cached benchmark (recomputed after the TTL, e.g. when the forecast start month moves on)."""
    global _cache
    now = time.monotonic()
    if _cache is None or now - _cache[0] > _settings()["ttl"]:
        _cache = (now, compute_benchmark())
    return _cache[1]


def clear_cache() -> None:
    global _cache
    _cache = None
