"""
Pydantic schemas for MAXergy energy forecasting model.

These schemas mirror the input/output JSON structure defined in:
- Input: documentation/data/model_input1.json
- Output: documentation/data/model_output_1.json
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


# ============================================================================
# INPUT SCHEMAS
# ============================================================================

class Location(BaseModel):
    """Location information for the household."""
    postcode: str = Field(..., description="Postal code")
    country: str = Field(..., description="Country code (e.g., 'DE')")


class Roof(BaseModel):
    """Roof characteristics for solar PV potential."""
    available: bool = Field(..., description="Whether roof is available for solar")
    usable_area_m2: float = Field(..., description="Usable roof area in square meters")
    orientation: str = Field(..., description="Roof orientation (e.g., 'south')")
    tilt_deg: float = Field(..., description="Roof tilt in degrees")
    shading_factor: float = Field(..., description="Shading factor (0-1)")


class Electricity(BaseModel):
    """Electricity consumption and tariff information."""
    annual_kwh: float = Field(..., description="Annual electricity consumption in kWh")
    current_tariff_type: str = Field(..., description="Current tariff type (e.g., 'fixed')")
    arbeitspreis_eur_per_kwh: float = Field(..., description="Energy price in EUR/kWh")
    grundpreis_eur_per_month: float = Field(..., description="Base price in EUR/month")
    contract_end_date: str = Field(..., description="Contract end date (YYYY-MM-DD)")


class Household(BaseModel):
    """Household information including occupants, electricity, and roof."""
    occupants: int = Field(..., description="Number of occupants")
    electricity: Electricity = Field(..., description="Electricity consumption and tariff")
    roof: Roof = Field(..., description="Roof characteristics")


class Building(BaseModel):
    """Building characteristics for heating calculations."""
    floor_area_m2: float = Field(..., description="Floor area in square meters")
    insulation_class: str = Field(..., description="Insulation class (e.g., 'average')")


class Heating(BaseModel):
    """Heating system information."""
    fuel_type: str = Field(..., description="Fuel type (e.g., 'gas', 'oil')")
    annual_consumption: float = Field(..., description="Annual consumption in kWh or liters")
    annual_spend_eur: Optional[float] = Field(None, description="Annual spending in EUR")
    building: Building = Field(..., description="Building characteristics")


class Mobility(BaseModel):
    """Mobility/vehicle information."""
    vehicle_type: str = Field(..., description="Vehicle type (e.g., 'petrol', 'ev')")
    annual_mileage_km: float = Field(..., description="Annual mileage in kilometers")
    fuel_consumption_l_per_100km: float = Field(..., description="Fuel consumption in L/100km")
    annual_fuel_spend_eur: Optional[float] = Field(None, description="Annual fuel spending in EUR")


class UpgradeCandidates(BaseModel):
    """Available upgrade options and component sizing overrides."""
    solar_pv: bool = Field(..., description="Solar PV available")
    battery: bool = Field(..., description="Battery storage available")
    heat_pump: bool = Field(..., description="Heat pump available")
    ev_charger: bool = Field(..., description="EV charger available")
    solar_pv_kwp: Optional[float] = Field(None, description="Override solar PV size in kWp")
    battery_kwh: Optional[float] = Field(None, description="Override battery size in kWh")
    heat_pump_kw: Optional[float] = Field(None, description="Override heat pump size in kW")


class Financing(BaseModel):
    """Financing parameters for upgrades."""
    loan_term_years: int = Field(..., description="Loan term in years")
    loan_rate_pct: float = Field(..., description="Loan interest rate in percent")
    known_subsidy_eur: Optional[float] = Field(None, description="Known subsidy amount in EUR")


class ForecastHorizon(BaseModel):
    """Forecast time horizon parameters."""
    short_term_months: int = Field(..., description="Short-term forecast months")
    long_term_years: int = Field(..., description="Long-term forecast years")


class HouseholdAssessment(BaseModel):
    """Complete household assessment for energy forecasting."""
    location: Location = Field(..., description="Location information")
    household: Household = Field(..., description="Household details")
    heating: Heating = Field(..., description="Heating system information")
    mobility: Mobility = Field(..., description="Mobility information")
    upgrade_candidates: UpgradeCandidates = Field(..., description="Available upgrades")
    financing: Financing = Field(..., description="Financing parameters")
    forecast_horizon: ForecastHorizon = Field(..., description="Forecast horizon")


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
    year: int = Field(..., description="Year")
    annual_total_eur: float = Field(..., description="Annual total cost in EUR")
    annual_saving_eur: float = Field(..., description="Annual savings compared to baseline")


class Scenario(BaseModel):
    """Single upgrade scenario with costs and forecasts."""
    id: str = Field(..., description="Scenario ID (e.g., 'solar_only', 'pv_battery')")
    components: Components = Field(..., description="Component configuration")
    sizing: Sizing = Field(..., description="Component sizing")
    monthly_cost_eur: ScenarioMonthlyCostEUR = Field(..., description="Monthly cost breakdown")
    monthly_saving_eur: float = Field(..., description="Monthly savings compared to baseline")
    monthly_saving_post_payoff_eur: Optional[float] = Field(None, description="Monthly savings after loan payoff")
    self_consumption_ratio: float = Field(..., description="Self-consumption ratio (0-1)")
    short_term_forecast: list[ScenarioShortTermForecastPoint] = Field(..., description="12-month forecast")
    long_term_forecast: list[ScenarioLongTermForecastPoint] = Field(..., description="20-year forecast")
    payback_month: Optional[int] = Field(None, description="Payback month (null if beyond loan term)")


class ForecastResult(BaseModel):
    """Complete forecast result with baseline and scenarios."""
    baseline: Baseline = Field(..., description="Baseline costs and forecasts")
    scenarios: list[Scenario] = Field(..., description="List of upgrade scenarios")


# ============================================================================
# RECOMMENDATION SCHEMAS
# ============================================================================

class Recommendation(BaseModel):
    """Recommended upgrade scenario."""
    selected_scenario_id: str = Field(..., description="ID of recommended scenario")
    selected_scenario: Scenario = Field(..., description="Complete scenario details")
    ranked_scenarios: list[tuple[str, float]] = Field(..., description="Scenarios ranked by monthly savings (id, savings)")
    rationale: str = Field(..., description="Explanation of recommendation")


class AssessmentResponse(BaseModel):
    """Response to assessment submission."""
    assessment_id: str = Field(..., description="Unique assessment ID")
    status: str = Field(..., description="Assessment status")
    message: str = Field(..., description="Status message")


# ============================================================================
# AI ADVISOR SCHEMAS
# ============================================================================

class AdvisorChatRequest(BaseModel):
    """Request to AI advisor."""
    assessment_id: str = Field(..., description="Assessment ID for context")
    forecast_result: Optional[ForecastResult] = Field(None, description="Forecast result for context")
    user_message: str = Field(..., description="User's question")
    conversation_history: list[dict] = Field(default_factory=list, description="Previous conversation")


class AdvisorChatResponse(BaseModel):
    """Response from AI advisor."""
    advisor_message: str = Field(..., description="AI advisor's response")
    context_used: list[str] = Field(default_factory=list, description="Context sources used")
    suggestions: list[str] = Field(default_factory=list, description="Additional suggestions")
