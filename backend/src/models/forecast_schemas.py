"""
Pydantic schemas for MAXergy energy forecasting model.

Canonical contract: documentation/app/API_CONTRACT.md
- Input example: documentation/data/model_input1.json
- Output example: documentation/data/model_output_v2.json
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Any, Optional
from pydantic import BaseModel, Field, model_validator


# ============================================================================
# INPUT SCHEMAS
# ============================================================================

class Location(BaseModel):
    """Location information for the household."""
    postcode: str = Field(..., min_length=3, max_length=10, description="Postal code")
    country: str = Field(..., min_length=2, max_length=2, description="Country code (e.g., 'DE')")

    model_config = {"extra": "ignore"}


class Roof(BaseModel):
    """Roof characteristics for solar PV potential."""
    available: bool = Field(..., description="Whether roof is available for solar")
    usable_area_m2: Optional[float] = Field(None, ge=0, le=500, description="Usable roof area in square meters")
    orientation: Optional[str] = Field(None, description="Roof orientation (e.g., 'south')")
    tilt_deg: Optional[float] = Field(None, ge=0, le=90, description="Roof tilt in degrees")
    shading_factor: Optional[float] = Field(None, ge=0, le=1, description="Shading factor (0-1)")
    specific_yield_kwh_per_kwp: Optional[float] = Field(
        None, gt=0, le=2000,
        description="Site-specific annual PV yield in kWh/kWp (e.g. PVGIS); null uses the regional table",
    )

    model_config = {"extra": "ignore"}


class Electricity(BaseModel):
    """Electricity consumption and tariff information."""
    annual_kwh: float = Field(..., ge=0, le=100000, description="Annual electricity consumption in kWh")
    current_tariff_type: str = Field(..., description="Current tariff type (e.g., 'fixed')")
    arbeitspreis_eur_per_kwh: float = Field(..., ge=0, le=2, description="Energy price in EUR/kWh")
    grundpreis_eur_per_month: float = Field(..., ge=0, le=100, description="Base price in EUR/month")
    contract_end_date: Optional[str] = Field(None, description="Contract end date (YYYY-MM-DD)")

    model_config = {"extra": "ignore"}


class Household(BaseModel):
    """Household information including occupants, electricity, and roof."""
    occupants: int = Field(..., ge=1, le=20, description="Number of occupants")
    electricity: Electricity = Field(..., description="Electricity consumption and tariff")
    roof: Roof = Field(..., description="Roof characteristics")

    model_config = {"extra": "ignore"}


class Building(BaseModel):
    """Building characteristics for heating calculations."""
    floor_area_m2: float = Field(..., ge=10, le=1000, description="Floor area in square meters")
    insulation_class: str = Field(..., description="Insulation class (e.g., 'average')")

    model_config = {"extra": "ignore"}


class Heating(BaseModel):
    """Heating system information."""
    fuel_type: str = Field(..., description="Fuel type (e.g., 'gas', 'oil')")
    annual_consumption: Optional[float] = Field(None, ge=0, le=100000, description="Annual consumption in kWh or liters")
    annual_spend_eur: Optional[float] = Field(None, ge=0, le=10000, description="Annual spending in EUR")
    building: Building = Field(..., description="Building characteristics")

    model_config = {"extra": "ignore"}


class Vehicle(BaseModel):
    """Individual vehicle information."""
    vehicle_type: str = Field(..., description="Vehicle type (e.g., 'petrol', 'ev')")
    annual_mileage_km: Optional[float] = Field(None, ge=0, le=200000, description="Annual mileage in kilometers")
    fuel_consumption_l_per_100km: Optional[float] = Field(None, ge=0, le=30, description="Fuel consumption in L/100km")
    annual_fuel_spend_eur: Optional[float] = Field(None, ge=0, le=10000, description="Annual fuel spending in EUR")

    model_config = {"extra": "ignore"}


class Mobility(BaseModel):
    """Mobility/vehicle information."""
    vehicle_count: int = Field(default=0, ge=0, le=10, description="Number of vehicles")
    vehicles: list[Vehicle] = Field(default_factory=list, description="List of vehicles")

    model_config = {"extra": "ignore"}


class UpgradeCandidates(BaseModel):
    """Available upgrade options and component sizing overrides."""
    solar_pv: bool = Field(..., description="Solar PV available")
    battery: bool = Field(..., description="Battery storage available")
    heat_pump: bool = Field(..., description="Heat pump available")
    ev_charger: bool = Field(..., description="EV charger available")
    solar_pv_kwp: Optional[float] = Field(None, ge=0, le=20, description="Override solar PV size in kWp")
    battery_kwh: Optional[float] = Field(None, ge=0, le=50, description="Override battery size in kWh")
    heat_pump_kw: Optional[float] = Field(None, ge=0, le=20, description="Override heat pump size in kW")

    model_config = {"extra": "ignore"}


class Financing(BaseModel):
    """Financing parameters for upgrades."""
    loan_term_years: int = Field(..., ge=1, le=30, description="Loan term in years")
    loan_rate_pct: float = Field(..., ge=0, le=20, description="Loan interest rate in percent")
    known_subsidy_eur: Optional[float] = Field(None, ge=0, le=100000, description="Known subsidy amount in EUR")

    model_config = {"extra": "ignore"}


class ForecastHorizon(BaseModel):
    """Forecast time horizon parameters."""
    short_term_months: int = Field(..., ge=1, le=24, description="Short-term forecast months")
    long_term_years: int = Field(..., ge=1, le=30, description="Long-term forecast years")

    model_config = {"extra": "ignore"}


class HouseholdAssessment(BaseModel):
    """Complete household assessment for energy forecasting."""
    location: Location = Field(..., description="Location information")
    household: Household = Field(..., description="Household details")
    heating: Heating = Field(..., description="Heating system information")
    mobility: Mobility = Field(default_factory=lambda: Mobility(), description="Mobility information")
    upgrade_candidates: UpgradeCandidates = Field(..., description="Available upgrades")
    financing: Financing = Field(..., description="Financing parameters")
    forecast_horizon: ForecastHorizon = Field(..., description="Forecast horizon")

    model_config = {"extra": "ignore"}


# ============================================================================
# OUTPUT SCHEMAS
# ============================================================================

class MonthlyCostEUR(BaseModel):
    """Monthly cost breakdown in EUR."""
    electricity: float = Field(..., description="Electricity cost")
    heating: float = Field(..., description="Heating cost")
    mobility: float = Field(..., description="Mobility cost")
    total: float = Field(..., description="Total monthly cost")


class ShortTermForecastPoint(BaseModel):
    """Single month in short-term forecast."""
    month: str = Field(..., description="Month in YYYY-MM format")
    total_eur: float = Field(..., description="Total cost for the month")


class LongTermForecastPoint(BaseModel):
    """Single year in long-term forecast."""
    year: int = Field(..., description="Year")
    annual_total_eur: float = Field(..., description="Annual total cost in EUR")


class Baseline(BaseModel):
    """Baseline energy costs and forecasts."""
    monthly_cost_eur: MonthlyCostEUR = Field(..., description="Monthly cost breakdown")
    short_term_forecast: list[ShortTermForecastPoint] = Field(..., description="12-month forecast")
    long_term_forecast: list[LongTermForecastPoint] = Field(..., description="20-year forecast")


class Components(BaseModel):
    """Component configuration for a scenario."""
    solar_pv: bool = Field(..., description="Solar PV included")
    battery: bool = Field(..., description="Battery included")
    heat_pump: bool = Field(..., description="Heat pump included")
    ev_charger: bool = Field(..., description="EV charger included")


class Sizing(BaseModel):
    """Component sizing for a scenario."""
    solar_pv_kwp: float = Field(..., description="Solar PV size in kWp")
    battery_kwh: Optional[float] = Field(None, description="Battery size in kWh")
    heat_pump_kw: Optional[float] = Field(None, description="Heat pump size in kW")


class ScenarioMonthlyCostEUR(BaseModel):
    """Monthly cost breakdown for a scenario including financing."""
    electricity: float = Field(..., description="Electricity cost")
    heating: float = Field(..., description="Heating cost")
    mobility: float = Field(..., description="Mobility cost")
    financing_installment: float = Field(..., description="Monthly financing installment")
    total: float = Field(..., description="Total monthly cost")


class ScenarioShortTermForecastPoint(BaseModel):
    """Single month in scenario short-term forecast."""
    month: str = Field(..., description="Month in YYYY-MM format")
    total_eur: float = Field(..., description="Total cost for the month")
    saving_eur: float = Field(..., description="Savings compared to baseline")


class ScenarioLongTermForecastPoint(BaseModel):
    """Single year in scenario long-term forecast."""
    year: int = Field(..., description="Calendar year in which the projection year starts")
    annual_total_eur: float = Field(..., description="Annual total cost in EUR (energy + financing)")
    annual_saving_eur: float = Field(..., description="Annual net savings compared to baseline")
    cumulative_saving_eur: Optional[float] = Field(None, description="Cumulative net savings up to this year")
    scenario: str = Field("central", description="Price scenario: low | central | high")


class ScenarioFinancials(BaseModel):
    """Investment, financing and long-run outcome of a scenario."""
    gross_investment_eur: float = Field(..., description="Total installed cost before subsidy")
    subsidy_eur: float = Field(..., description="Subsidy deducted from the investment")
    financed_principal_eur: float = Field(..., description="Loan principal")
    loan_term_months: int = Field(..., description="Loan term in months")
    horizon_years: int = Field(..., description="Long-term projection horizon in years")
    cumulative_net_savings_central_eur: float = Field(
        ..., description="Cumulative net savings at the end of the horizon (central price scenario)"
    )
    cumulative_net_savings_low_eur: float = Field(..., description="Same, low price scenario")
    cumulative_net_savings_high_eur: float = Field(..., description="Same, high price scenario")
    break_even_year: Optional[int] = Field(
        None, description="First projection year (1-based) with positive cumulative net savings (central)"
    )


class Scenario(BaseModel):
    """Single upgrade scenario with costs and forecasts."""
    id: str = Field(..., description="Scenario ID (e.g., 'solar_only', 'pv_battery')")
    components: Components = Field(..., description="Component configuration")
    sizing: Sizing = Field(..., description="Component sizing")
    monthly_cost_eur: ScenarioMonthlyCostEUR = Field(..., description="Average monthly cost breakdown over the first 12 forecast months")
    monthly_saving_eur: float = Field(..., description="Average monthly net saving (energy reduction minus instalment) over the first 12 forecast months")
    monthly_saving_post_payoff_eur: Optional[float] = Field(None, description="Average monthly energy cost reduction without the instalment (saving once the loan is repaid)")
    self_consumption_ratio: float = Field(..., description="Share of PV generation used on site in year 1 (0-1)")
    short_term_forecast: list[ScenarioShortTermForecastPoint] = Field(..., description="Monthly short-term forecast")
    long_term_forecast: list[ScenarioLongTermForecastPoint] = Field(..., description="Annual long-term forecast (central price scenario)")
    long_term_band: Optional[dict[str, list[ScenarioLongTermForecastPoint]]] = Field(
        None, description="Low/high price-scenario projections for uncertainty bands"
    )
    payback_month: Optional[int] = Field(None, description="Month in which cumulative net savings turn positive (central); null if not within the horizon")
    financials: Optional[ScenarioFinancials] = Field(None, description="Investment, financing and long-run outcome")


class ModelInfo(BaseModel):
    """Metadata of the engine that produced a forecast."""
    name: str = Field(..., description="Model name")
    version: str = Field(..., description="Model version")
    engine: str = Field(..., description="Engine package (energy_model)")


class ForecastResult(BaseModel):
    """Complete forecast result with baseline and scenarios."""
    model: Optional[ModelInfo] = Field(None, description="Engine metadata")
    assumptions_used: Optional[dict[str, Any]] = Field(None, description="Engine assumptions and their provenance")
    validation_warnings: list[str] = Field(default_factory=list, description="Inputs the engine estimated or defaulted")
    baseline: Baseline = Field(..., description="Baseline costs and forecasts")
    scenarios: list[Scenario] = Field(..., description="List of upgrade scenarios")

    model_config = {"protected_namespaces": ()}


# ============================================================================
# RECOMMENDATION SCHEMAS
# ============================================================================

class RecommendationMetric(str, Enum):
    """Metric used to rank scenarios."""
    MONTHLY_NET = "monthly_net"
    CUMULATIVE_CENTRAL = "cumulative_central"


class RankedScenarioItem(BaseModel):
    """One scenario in the ranking."""
    id: str = Field(..., description="Scenario ID")
    score_eur: float = Field(..., description="Value of the ranking metric for this scenario")
    metric: RecommendationMetric = Field(..., description="Metric the score refers to")


class Recommendation(BaseModel):
    """Recommended upgrade scenario."""
    selected_scenario_id: Optional[str] = Field(None, description="ID of recommended scenario (null when no scenario is available)")
    selected_scenario: Optional[Scenario] = Field(None, description="Complete scenario details")
    ranked_scenarios: list[RankedScenarioItem] = Field(..., description="Scenarios ranked best-first by metric_used")
    metric_used: RecommendationMetric = Field(..., description="Ranking metric")
    rationale: str = Field(..., description="Explanation built only from forecast fields")


class PlanResponse(BaseModel):
    """Forecast and recommendation computed from one engine run."""
    forecast: ForecastResult = Field(..., description="Forecast result")
    recommendation: Recommendation = Field(..., description="Recommendation derived from the forecast")


# ============================================================================
# LOCATION ENRICHMENT SCHEMAS
# ============================================================================

class EnrichmentRequest(BaseModel):
    """Address or postcode to enrich with roof geometry and site PV yield."""
    postcode: Optional[str] = Field(None, min_length=3, max_length=10, description="German postcode")
    address: Optional[str] = Field(None, min_length=3, max_length=200, description="Street address (more precise than a postcode)")
    country: str = Field("DE", pattern="^DE$", description="Country code (only 'DE' is supported)")

    model_config = {"extra": "ignore"}

    @model_validator(mode="after")
    def _needs_location(self) -> "EnrichmentRequest":
        if not (self.postcode or self.address):
            raise ValueError("postcode or address is required")
        return self


class EnrichmentRoof(BaseModel):
    """Roof proposal for household.roof, from the Google Solar API."""
    usable_area_m2: Optional[float] = Field(None, description="Installable array area in m²")
    tilt_deg: Optional[float] = Field(None, description="Tilt of the main roof plane")
    azimuth_deg: Optional[float] = Field(None, description="Azimuth of the main roof plane (0=N, 90=E, 180=S, 270=W)")
    orientation: Optional[str] = Field(None, description="Engine orientation: south, south_east, east, north_east, north, north_west, west, south_west")
    max_array_kwp: Optional[float] = Field(None, description="Largest installable PV system")
    low_confidence: bool = Field(False, description="True when the roof scan likely found a small adjacent building")


class EnrichmentSource(BaseModel):
    """Where each enrichment value came from."""
    roof: str = Field(..., description="google_solar | unavailable")
    pv_yield: str = Field(..., description="pvgis | unavailable (engine uses its regional table)")


class EnrichmentResponse(BaseModel):
    """Location, roof proposal and site PV yield for pre-filling the assessment."""
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    roof: Optional[EnrichmentRoof] = Field(None, description="Roof proposal (null when unavailable)")
    specific_yield_kwh_per_kwp: Optional[float] = Field(None, description="Site PV yield for household.roof.specific_yield_kwh_per_kwp")
    source: EnrichmentSource = Field(..., description="Data sources")
    warnings: list[str] = Field(default_factory=list, description="Lookups that failed and fell back")


class AssessmentResponse(BaseModel):
    """Response to assessment submission."""
    assessment_id: str = Field(..., description="Unique assessment ID")
    status: str = Field(..., description="Assessment status")
    message: str = Field(..., description="Status message")


# ============================================================================
# AI ADVISOR SCHEMAS
# ============================================================================

class AdvisorChatMessage(BaseModel):
    """One earlier turn of the advisor conversation."""
    role: Literal["user", "assistant"] = Field(..., description="Who wrote the message")
    content: str = Field(..., max_length=4000, description="Message text")


class AdvisorChatRequest(BaseModel):
    """Request to AI advisor."""
    assessment_id: Optional[str] = Field(None, description="Assessment ID for context")
    plan: Optional[PlanResponse] = Field(
        None, description="Plan (forecast + recommendation) the user is looking at; null → chat onboarding"
    )
    user_message: str = Field(..., min_length=1, max_length=1000, description="User's question")
    conversation_history: list[AdvisorChatMessage] = Field(
        default_factory=list, max_length=20, description="Previous conversation, oldest first"
    )

    model_config = {"extra": "ignore"}


class AdvisorChatResponse(BaseModel):
    """Response from AI advisor."""
    advisor_message: str = Field(..., description="AI advisor's response")
    context_used: list[str] = Field(default_factory=list, description="Context sources used")
    suggestions: list[str] = Field(default_factory=list, description="Additional suggestions")
    assessment: Optional[HouseholdAssessment] = Field(
        None, description="Assessment collected in chat onboarding (set when the advisor ran a plan)"
    )
    plan: Optional[PlanResponse] = Field(
        None, description="Plan computed in chat onboarding (same services as POST /plan)"
    )
