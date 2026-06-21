"""UpgradeInput and output record dataclasses.

UpgradeInput carries the upgrade-specific parameters that accompany a
ParsedInput when running the scenario comparison.  Neither class contains
price forecasting logic — both accept an external PriceModelProtocol.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from energy_model.assumptions import (
    BatteryAssumptions,
    EVAssumptions,
    GridAssumptions,
    HeatPumpAssumptions,
    SolarAssumptions,
)

# Ordered exactly as required by the task specification.
UPGRADE_SCENARIO_NAMES: list[str] = [
    "solar_only",
    "pv_battery",
    "pv_heatpump",
    "pv_ev",
    "pv_battery_heatpump",
    "full_upgrade",
]

PRICE_SCENARIOS: list[str] = ["low", "central", "high"]


@dataclass
class UpgradeInput:
    """Upgrade technology parameters for ScenarioOrchestrator.

    All technology sizing fields are optional — when None the model derives
    them from assumptions and a warning is recorded in provenance.
    """

    # Roof geometry — used to infer kWp when solar_kwp is None.
    usable_roof_area_m2: float | None = None
    roof_orientation: str = "south"
    roof_tilt_deg: float = 30.0
    shading_factor: float = 0.0        # 0 = no shading, 1 = fully shaded

    # Technology sizing (None → derive from assumptions / roof)
    solar_kwp: float | None = None
    battery_kwh: float | None = None   # usable capacity

    # EV parameters (used when EV scenario is active)
    ev_kwh_per_100km: float | None = None    # None → EVAssumptions default
    ev_home_charging_share: float | None = None

    # Per-run assumption overrides
    solar_assumptions: SolarAssumptions = field(default_factory=SolarAssumptions)
    battery_assumptions: BatteryAssumptions = field(default_factory=BatteryAssumptions)
    heat_pump_assumptions: HeatPumpAssumptions = field(default_factory=HeatPumpAssumptions)
    ev_assumptions: EVAssumptions = field(default_factory=EVAssumptions)
    grid_assumptions: GridAssumptions = field(default_factory=GridAssumptions)

    # Provenance populated by ScenarioOrchestrator
    provenance: dict[str, str] = field(default_factory=dict)
    warnings_list: list[str] = field(default_factory=list)


@dataclass
class MonthlyUpgradeRecord:
    """One month of energy flows, prices, and costs for an upgrade scenario."""

    month: str  # YYYY-MM

    # ── Energy flows ────────────────────────────────────────────────────────
    baseline_household_electricity_kwh: float  # baseline household demand (excl. HP/EV)
    pv_generation_kwh: float
    pv_direct_self_consumption_kwh: float
    battery_charge_kwh: float      # raw energy entering battery
    battery_discharge_kwh: float   # useful energy leaving battery to loads
    battery_loss_kwh: float        # charge + discharge conversion losses
    grid_import_kwh: float         # always ≥ 0
    grid_export_kwh: float         # always ≥ 0
    heat_pump_electricity_kwh: float
    remaining_heating_fuel: float  # kWh (gas) or litres (oil); 0 when HP active
    ev_charging_home_kwh: float    # home EV charging demand
    remaining_petrol_litres: float # 0 when EV active

    # ── Prices ──────────────────────────────────────────────────────────────
    electricity_unit_price_eur_per_kwh: float
    electricity_fixed_charge_eur: float
    heating_price_per_unit: float   # EUR/kWh (gas) or EUR/litre (oil)
    petrol_price_eur_per_litre: float
    feed_in_tariff_eur_per_kwh: float

    # ── Costs ───────────────────────────────────────────────────────────────
    grid_electricity_cost_eur: float    # grid_import × unit + fixed
    solar_export_revenue_eur: float     # grid_export × feed_in_tariff
    remaining_heating_fuel_cost_eur: float
    remaining_mobility_fuel_cost_eur: float
    total_upgraded_cost_eur: float      # net of export revenue
    baseline_total_cost_eur: float      # same period, no upgrades
    energy_cost_reduction_eur: float    # baseline − upgraded (positive = saving)

    def to_dict(self, scenario: str = "") -> dict:
        return {
            "month": self.month,
            "scenario": scenario,
            "energy_flows": {
                "household_electricity_kwh": round(self.baseline_household_electricity_kwh, 3),
                "pv_generation_kwh": round(self.pv_generation_kwh, 3),
                "pv_direct_self_consumption_kwh": round(self.pv_direct_self_consumption_kwh, 3),
                "battery_charge_kwh": round(self.battery_charge_kwh, 3),
                "battery_discharge_kwh": round(self.battery_discharge_kwh, 3),
                "battery_losses_kwh": round(self.battery_loss_kwh, 3),
                "grid_import_kwh": round(self.grid_import_kwh, 3),
                "grid_export_kwh": round(self.grid_export_kwh, 3),
                "heat_pump_electricity_kwh": round(self.heat_pump_electricity_kwh, 3),
                "remaining_heating_fuel": round(self.remaining_heating_fuel, 3),
                "ev_charging_kwh": round(self.ev_charging_home_kwh, 3),
                "remaining_petrol_litres": round(self.remaining_petrol_litres, 3),
            },
            "prices": {
                "electricity_eur_per_kwh": round(self.electricity_unit_price_eur_per_kwh, 5),
                "electricity_fixed_eur": round(self.electricity_fixed_charge_eur, 4),
                "heating_eur_per_unit": round(self.heating_price_per_unit, 5),
                "petrol_eur_per_litre": round(self.petrol_price_eur_per_litre, 4),
                "feed_in_tariff_eur_per_kwh": round(self.feed_in_tariff_eur_per_kwh, 4),
            },
            "cost_eur": {
                "electricity": round(self.grid_electricity_cost_eur, 2),
                "heating": round(self.remaining_heating_fuel_cost_eur, 2),
                "mobility": round(self.remaining_mobility_fuel_cost_eur, 2),
                "solar_export_revenue": round(self.solar_export_revenue_eur, 2),
                "upgraded_total": round(self.total_upgraded_cost_eur, 2),
                "baseline_total": round(self.baseline_total_cost_eur, 2),
                "energy_cost_reduction": round(self.energy_cost_reduction_eur, 2),
            },
        }


@dataclass
class AnnualUpgradeRecord:
    """12-month aggregate of an upgrade scenario."""

    year_label: str       # e.g. "Year 1"
    first_month: str      # YYYY-MM of first month in block
    last_month: str       # YYYY-MM of last month in block

    # Annual sums (energy flows)
    baseline_household_electricity_kwh: float
    pv_generation_kwh: float
    pv_direct_self_consumption_kwh: float
    battery_charge_kwh: float
    battery_discharge_kwh: float
    battery_loss_kwh: float
    grid_import_kwh: float
    grid_export_kwh: float
    heat_pump_electricity_kwh: float
    remaining_heating_fuel: float
    ev_charging_home_kwh: float
    remaining_petrol_litres: float

    # Annual upgrade costs
    grid_electricity_cost_eur: float
    solar_export_revenue_eur: float
    remaining_heating_fuel_cost_eur: float
    remaining_mobility_fuel_cost_eur: float
    total_upgraded_cost_eur: float
    baseline_total_cost_eur: float
    energy_cost_reduction_eur: float

    # Baseline cost breakdown (set by orchestrator from baseline_months)
    baseline_electricity_cost_eur: float = 0.0
    baseline_heating_cost_eur: float = 0.0
    baseline_mobility_cost_eur: float = 0.0

    # Running total across projection years (set by orchestrator)
    cumulative_energy_cost_reduction_eur: float = 0.0

    def to_dict(self) -> dict:
        return {
            "year_label": self.year_label,
            "first_month": self.first_month,
            "last_month": self.last_month,
            "energy_flows": {
                "household_electricity_kwh": round(self.baseline_household_electricity_kwh, 2),
                "pv_generation_kwh": round(self.pv_generation_kwh, 2),
                "pv_direct_self_consumption_kwh": round(self.pv_direct_self_consumption_kwh, 2),
                "battery_charge_kwh": round(self.battery_charge_kwh, 2),
                "battery_discharge_kwh": round(self.battery_discharge_kwh, 2),
                "battery_losses_kwh": round(self.battery_loss_kwh, 2),
                "grid_import_kwh": round(self.grid_import_kwh, 2),
                "grid_export_kwh": round(self.grid_export_kwh, 2),
                "heat_pump_electricity_kwh": round(self.heat_pump_electricity_kwh, 2),
                "remaining_heating_fuel": round(self.remaining_heating_fuel, 2),
                "ev_charging_kwh": round(self.ev_charging_home_kwh, 2),
                "remaining_petrol_litres": round(self.remaining_petrol_litres, 2),
            },
            "cost_eur": {
                "electricity": round(self.grid_electricity_cost_eur, 2),
                "heating": round(self.remaining_heating_fuel_cost_eur, 2),
                "mobility": round(self.remaining_mobility_fuel_cost_eur, 2),
                "solar_export_revenue": round(self.solar_export_revenue_eur, 2),
                "upgraded_total": round(self.total_upgraded_cost_eur, 2),
                "baseline_electricity": round(self.baseline_electricity_cost_eur, 2),
                "baseline_heating": round(self.baseline_heating_cost_eur, 2),
                "baseline_mobility": round(self.baseline_mobility_cost_eur, 2),
                "baseline_total": round(self.baseline_total_cost_eur, 2),
                "energy_cost_reduction": round(self.energy_cost_reduction_eur, 2),
                "cumulative_energy_cost_reduction": round(self.cumulative_energy_cost_reduction_eur, 2),
            },
        }
