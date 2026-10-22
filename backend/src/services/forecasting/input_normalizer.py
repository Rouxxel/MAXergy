"""
Convert a validated HouseholdAssessment into the input dict of the production engine.

API-level rules applied here (engine-level rules such as multi-vehicle aggregation live in
energy_model.input_validator):
- heating fuel must be gas or oil (the only fuels the engine models);
- the effective upgrade candidates are the user's toggles, with solar disabled when no roof
  is available and the EV charger disabled when the household has no combustion vehicle.
"""

from src.models.forecast_schemas import HouseholdAssessment
from src.services.forecasting.engine import flatten_mobility

SUPPORTED_HEATING_FUELS = ("gas", "oil")


class UnsupportedInputError(ValueError):
    """Raised when an assessment is valid but outside what the engine can model."""


def normalize_assessment(assessment: HouseholdAssessment) -> dict:
    """Return the engine input dict, including the effective `upgrade_candidates` flags."""
    raw = assessment.model_dump()

    fuel = raw["heating"]["fuel_type"].lower()
    if fuel not in SUPPORTED_HEATING_FUELS:
        raise UnsupportedInputError(
            f"heating.fuel_type '{raw['heating']['fuel_type']}' is not supported; "
            f"supported fuels: {', '.join(SUPPORTED_HEATING_FUELS)}"
        )
    raw["heating"]["fuel_type"] = fuel

    flat_mobility, _ = flatten_mobility(raw["mobility"])
    has_combustion_vehicle = flat_mobility["annual_mileage_km"] > 0

    uc = raw["upgrade_candidates"]
    uc["solar_pv"] = bool(uc["solar_pv"] and raw["household"]["roof"]["available"])
    uc["ev_charger"] = bool(uc["ev_charger"] and has_combustion_vehicle)

    return raw
