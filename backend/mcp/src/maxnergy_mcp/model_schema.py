"""Canonical model I/O contract — the schema the team standardizes on.

These pydantic v2 models mirror the teammate's template JSONs exactly so the modeling
backend (this engine) and the frontend agree on field names, nesting, and nullability:

  - Input:  documentation/data/model_input1.json   -> `ModelInput`
  - Output: documentation/data/model_output_1.json  -> `ModelOutput`

The engine in `model_engine.py` maps a validated `ModelInput` to a `ModelOutput`. Keep
this module a pure data contract — no math, no I/O. Output dumps use
`model_dump(mode="json", exclude_none=True)` so optional fields (a scenario's
`battery_kwh`/`heat_pump_kw` sizing, the conditional `monthly_saving_post_payoff_eur`)
are omitted when absent, matching the template's shape.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# INPUT  (mirrors model_input1.json)
# ---------------------------------------------------------------------------


class Location(BaseModel):
    postcode: str
    country: str = "DE"


class ElectricityInput(BaseModel):
    annual_kwh: float
    current_tariff_type: str = "fixed"
    arbeitspreis_eur_per_kwh: float = Field(description="Work price — €/kWh consumed")
    grundpreis_eur_per_month: float = Field(default=0.0, description="Base price — fixed €/month")
    contract_end_date: Optional[str] = None


class RoofInput(BaseModel):
    available: bool = True
    usable_area_m2: float = 0.0
    orientation: str = "south"
    tilt_deg: float = 30.0
    shading_factor: float = Field(default=0.0, description="0=no shade .. 1=fully shaded")


class HouseholdInput(BaseModel):
    occupants: int = 1
    electricity: ElectricityInput
    roof: RoofInput = RoofInput()


class BuildingInput(BaseModel):
    floor_area_m2: float
    insulation_class: str = Field(
        default="average", description="old | average | modern | efficient"
    )


class HeatingInput(BaseModel):
    fuel_type: str = "gas"
    annual_consumption: Optional[float] = Field(
        default=None, description="Fuel/thermal kWh per year; derived from floor area if null"
    )
    annual_spend_eur: float
    building: BuildingInput


class VehicleInput(BaseModel):
    vehicle_type: str = Field(description="petrol | diesel | ev")
    annual_mileage_km: float = 0.0
    fuel_consumption_l_per_100km: float = 0.0
    annual_fuel_spend_eur: float = 0.0


class MobilityInput(BaseModel):
    vehicle_count: int = 0
    vehicles: list[VehicleInput] = []


class UpgradeCandidates(BaseModel):
    """What's on the table, plus optional explicit sizing overrides (null = derive)."""

    solar_pv: bool = True
    battery: bool = True
    heat_pump: bool = True
    ev_charger: bool = True
    solar_pv_kwp: Optional[float] = None
    battery_kwh: Optional[float] = None
    heat_pump_kw: Optional[float] = None


class Financing(BaseModel):
    loan_term_years: int = 15
    loan_rate_pct: float = 4.5
    known_subsidy_eur: Optional[float] = None


class ForecastHorizon(BaseModel):
    short_term_months: int = 12
    long_term_years: int = 20


class ModelInput(BaseModel):
    location: Location
    household: HouseholdInput
    heating: HeatingInput
    mobility: MobilityInput = MobilityInput()
    upgrade_candidates: UpgradeCandidates = UpgradeCandidates()
    financing: Financing = Financing()
    forecast_horizon: ForecastHorizon = ForecastHorizon()


# ---------------------------------------------------------------------------
# OUTPUT  (mirrors model_output_1.json)
# ---------------------------------------------------------------------------


class BaselineMonthlyCost(BaseModel):
    electricity: float
    heating: float
    mobility: float
    total: float


class BaselineShortTermPoint(BaseModel):
    month: str = Field(description="YYYY-MM")
    total_eur: float


class BaselineLongTermPoint(BaseModel):
    year: int
    annual_total_eur: float


class Baseline(BaseModel):
    monthly_cost_eur: BaselineMonthlyCost
    short_term_forecast: list[BaselineShortTermPoint]
    long_term_forecast: list[BaselineLongTermPoint]


class ScenarioComponents(BaseModel):
    solar_pv: bool
    battery: bool
    heat_pump: bool
    ev_charger: bool


class ScenarioSizing(BaseModel):
    solar_pv_kwp: float
    battery_kwh: Optional[float] = None
    heat_pump_kw: Optional[float] = None


class ScenarioMonthlyCost(BaseModel):
    electricity: float
    heating: float
    mobility: float
    financing_installment: float
    total: float


class ScenarioShortTermPoint(BaseModel):
    month: str
    total_eur: float
    saving_eur: float


class ScenarioLongTermPoint(BaseModel):
    year: int
    annual_total_eur: float
    annual_saving_eur: float


class ScenarioOut(BaseModel):
    id: str
    components: ScenarioComponents
    sizing: ScenarioSizing
    monthly_cost_eur: ScenarioMonthlyCost
    monthly_saving_eur: float
    # Present ONLY when the now-saving is negative (cost-neutral-now → saves after payoff).
    monthly_saving_post_payoff_eur: Optional[float] = None
    self_consumption_ratio: float
    short_term_forecast: list[ScenarioShortTermPoint]
    long_term_forecast: list[ScenarioLongTermPoint]
    payback_month: Optional[int] = None


class ModelOutput(BaseModel):
    baseline: Baseline
    scenarios: list[ScenarioOut]
