"""Shared data models for the MAXnergy advisor.

Everything the LLM gathers during onboarding lands in `HouseholdProfile`.
The savings engine consumes a profile + a `Scenario` and returns a `SavingsResult`.
All money is EUR, all energy is kWh, unless a field name says otherwise.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class HeatingType(str, Enum):
    gas = "gas"
    oil = "oil"
    heat_pump = "heat_pump"
    district = "district"
    electric_resistive = "electric_resistive"
    wood = "wood"


class Car(BaseModel):
    kind: str = Field(description="'ev' or 'ice'")
    annual_km: float = Field(description="Yearly distance driven in km")
    # ICE only — used to value a future EV swap. Sensible EU defaults.
    liters_per_100km: float = 7.0
    fuel_price_eur_per_l: float = 1.75
    # EV only.
    kwh_per_100km: float = 18.0


class RoofSegment(BaseModel):
    """One pitched plane of the roof, from the Google Solar API."""

    tilt_degrees: float = Field(description="Pitch of the plane. For roof-mounted panels this IS the panel tilt.")
    azimuth_degrees: float = Field(description="Google convention: 0=N, 90=E, 180=S, 270=W")
    area_m2: float
    sunshine_hours_per_year: Optional[float] = None


class RoofGeometry(BaseModel):
    lat: float
    lon: float
    segments: list[RoofSegment] = []
    max_array_area_m2: Optional[float] = Field(
        default=None, description="Largest installable array area on the whole roof"
    )
    max_array_kwp: Optional[float] = Field(
        default=None, description="Largest installable system size — your upsell ceiling"
    )
    suggested_system_kwp: Optional[float] = Field(
        default=None,
        description="Plausible existing-system size (~70% of roof ceiling) to suggest to the "
        "user for confirmation. NOT a detected value — no API knows what's actually installed.",
    )
    low_confidence: bool = Field(
        default=False,
        description="True when the Solar API likely locked onto a small adjacent building "
        "(tiny roof). Cross-check against floor area via estimate_roof_capacity_from_area.",
    )
    source: str = "google_solar_api"


class HouseholdProfile(BaseModel):
    # --- location ---
    address: str
    lat: Optional[float] = None
    lon: Optional[float] = None

    # --- building (spans residential + commercial; a home is the default) ---
    building_type: str = Field(
        default="home",
        description="home/office/retail/warehouse/hotel/school (or a residential vintage). "
        "Sets the daytime-load share that drives PV self-consumption; commercial daytime "
        "loads self-consume far more solar than evening-heavy homes.",
    )

    # --- electricity ---
    monthly_electricity_spend_eur: float
    electricity_price_eur_per_kwh: float = 0.35  # DE retail default
    feed_in_tariff_eur_per_kwh: float = 0.08
    annual_electricity_kwh: Optional[float] = Field(
        default=None, description="If unknown, derived from spend / price"
    )
    # Optional commercial peak-demand charge (Leistungspreis). Absent for homes, so the
    # peak-shaving savings bucket only appears when these are provided.
    peak_demand_charge_eur_per_kw_month: Optional[float] = None
    billed_peak_kw: Optional[float] = None

    # --- existing solar ---
    existing_pv_kwp: float = 0.0
    pv_tilt_degrees: Optional[float] = None
    pv_azimuth_degrees: Optional[float] = None
    pv_financing_monthly_eur: float = 0.0
    pv_financing_months_remaining: int = 0

    # --- battery ---
    battery_installed: bool = False
    battery_kwh: float = 0.0

    # --- heating ---
    heating_type: HeatingType = HeatingType.gas
    annual_heating_spend_eur: Optional[float] = None
    annual_heating_kwh_thermal: Optional[float] = Field(
        default=None, description="Thermal demand; derived from spend if unknown"
    )

    # --- mobility ---
    cars: list[Car] = []

    def derived_annual_electricity_kwh(self) -> float:
        if self.annual_electricity_kwh:
            return self.annual_electricity_kwh
        annual_spend = self.monthly_electricity_spend_eur * 12
        return annual_spend / max(self.electricity_price_eur_per_kwh, 0.01)


class Scenario(BaseModel):
    """An upgrade configuration to evaluate against the household's status quo."""

    name: str
    add_pv_kwp: float = Field(default=0.0, description="Extra solar on top of existing")
    add_battery_kwh: float = 0.0
    add_heat_pump: bool = False
    heat_pump_scop: float = 3.5
    add_ev: bool = Field(default=False, description="Swap the largest ICE car for an EV")
    add_ev_charger: bool = False
    # Optional explicit financing for this scenario's capex.
    financing_monthly_eur: Optional[float] = None
    financing_months: int = 120


class SavingsBucket(BaseModel):
    label: str
    current_monthly_eur: float
    new_monthly_eur: float

    @property
    def monthly_saving_eur(self) -> float:
        return self.current_monthly_eur - self.new_monthly_eur


class SavingsResult(BaseModel):
    scenario: str
    buckets: list[SavingsBucket]
    financing_monthly_eur: float
    # North Star figures.
    monthly_saving_now_eur: float = Field(
        description="Total monthly saving including the new financing installment"
    )
    monthly_saving_after_payoff_eur: float = Field(
        description="Monthly saving once the financing is paid off"
    )
    annual_pv_production_kwh: float
    self_consumption_ratio: float
    assumptions: dict = {}
    headline: str = ""
