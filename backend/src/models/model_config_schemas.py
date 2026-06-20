"""
Pydantic schemas for model configuration parameters.

These schemas validate the model constants configuration file.
"""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class SolarGenerationConfig(BaseModel):
    """Solar generation parameters."""
    specific_yield_kwh_per_kwp: float = Field(..., gt=0, description="Specific yield in kWh/kWp")
    solar_m2_per_kwp: float = Field(..., gt=0, description="Square meters per kWp")
    solar_max_kwp: float = Field(..., gt=0, description="Maximum system size in kWp")


class SelfConsumptionRatiosConfig(BaseModel):
    """Self-consumption ratios by component combination."""
    solar_pv: float = Field(..., ge=0, le=1, description="Solar only ratio")
    solar_pv_battery: float = Field(..., ge=0, le=1, description="Solar + battery ratio")
    solar_pv_heat_pump: float = Field(..., ge=0, le=1, description="Solar + heat pump ratio")
    solar_pv_ev_charger: float = Field(..., ge=0, le=1, description="Solar + EV ratio")
    solar_pv_battery_heat_pump: float = Field(..., ge=0, le=1, description="Solar + battery + heat pump ratio")
    solar_pv_battery_heat_pump_ev_charger: float = Field(..., ge=0, le=1, description="Full upgrade ratio")


class FeedInTariffConfig(BaseModel):
    """Feed-in tariff parameters."""
    eur_per_kwh: float = Field(..., ge=0, description="Feed-in tariff in EUR/kWh")


class HeatPumpConfig(BaseModel):
    """Heat pump parameters."""
    cop: float = Field(..., gt=0, description="Coefficient of performance")
    oil_kwh_per_litre: float = Field(..., gt=0, description="Energy content of oil in kWh/L")


class ElectricVehicleConfig(BaseModel):
    """Electric vehicle parameters."""
    efficiency_kwh_per_100km: float = Field(..., gt=0, description="Efficiency in kWh/100km")
    off_peak_discount_factor: float = Field(..., ge=0, le=1, description="Off-peak charging discount")


class FallbackFuelPricesConfig(BaseModel):
    """Fallback fuel prices when spend data not available."""
    gas_price_eur_per_kwh: float = Field(..., ge=0, description="Gas price in EUR/kWh")
    oil_price_eur_per_litre: float = Field(..., ge=0, description="Oil price in EUR/L")
    petrol_price_eur_per_litre: float = Field(..., ge=0, description="Petrol price in EUR/L")


class EquipmentCostsConfig(BaseModel):
    """Equipment installation costs."""
    solar_pv_eur_per_kwp: float = Field(..., ge=0, description="Solar PV cost per kWp")
    battery_eur_per_kwh: float = Field(..., ge=0, description="Battery cost per kWh")
    heat_pump_eur_flat: float = Field(..., ge=0, description="Heat pump flat cost")
    ev_charger_eur_flat: float = Field(..., ge=0, description="EV charger flat cost")


class DefaultComponentSizingConfig(BaseModel):
    """Default component sizing when not specified."""
    battery_kwh: float = Field(..., gt=0, description="Default battery size in kWh")
    heat_pump_kw: float = Field(..., gt=0, description="Default heat pump size in kW")


class SubsidyConfig(BaseModel):
    """Subsidy parameters."""
    default_subsidy_fraction: float = Field(..., ge=0, le=1, description="Default subsidy as fraction of system cost")


class EscalationRatesConfig(BaseModel):
    """Annual escalation rates for long-term forecasts."""
    electricity: float = Field(..., ge=0, description="Electricity price escalation rate")
    gas_oil: float = Field(..., ge=0, description="Gas/oil price escalation rate")
    fuel: float = Field(..., ge=0, description="Fuel price escalation rate")


class SeasonalHeatingWeightsConfig(BaseModel):
    """Seasonal heating weights for monthly variation."""
    raw: List[float] = Field(..., min_length=12, max_length=12, description="Raw monthly weights (Jan-Dec)")


class ScenarioDefinitionConfig(BaseModel):
    """Single scenario definition."""
    id: str = Field(..., description="Scenario identifier")
    requires: List[str] = Field(..., description="Required components")
    components: Dict[str, bool] = Field(..., description="Component configuration")


class UpgradePathConfig(BaseModel):
    """Upgrade path documentation."""
    priority_replacements: List[Dict[str, str]] = Field(..., description="Priority constant replacements")


class ModelConstantsConfig(BaseModel):
    """Complete model constants configuration."""
    model_version: str = Field(..., description="Model version")
    model_type: str = Field(..., description="Model type identifier")
    description: str = Field(..., description="Model description")
    
    solar_generation: SolarGenerationConfig
    self_consumption_ratios: SelfConsumptionRatiosConfig
    feed_in_tariff: FeedInTariffConfig
    heat_pump: HeatPumpConfig
    electric_vehicle: ElectricVehicleConfig
    fallback_fuel_prices: FallbackFuelPricesConfig
    equipment_costs: EquipmentCostsConfig
    default_component_sizing: DefaultComponentSizingConfig
    subsidy: SubsidyConfig
    escalation_rates: EscalationRatesConfig
    seasonal_heating_weights: SeasonalHeatingWeightsConfig
    scenario_definitions: List[ScenarioDefinitionConfig]
    upgrade_path: UpgradePathConfig
    
    @field_validator('seasonal_heating_weights')
    @classmethod
    def validate_heating_weights(cls, v):
        """Validate that heating weights are positive."""
        if any(w <= 0 for w in v.raw):
            raise ValueError("All heating weights must be positive")
        return v
    
    @field_validator('scenario_definitions')
    @classmethod
    def validate_scenario_definitions(cls, v):
        """Validate scenario definitions."""
        required_ids = {"solar_only", "pv_battery", "pv_heatpump", "pv_ev", "pv_battery_heatpump", "full_upgrade"}
        provided_ids = {s.id for s in v}
        if not required_ids.issubset(provided_ids):
            missing = required_ids - provided_ids
            raise ValueError(f"Missing required scenario IDs: {missing}")
        return v
