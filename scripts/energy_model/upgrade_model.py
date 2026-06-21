"""Core per-month energy flow calculation for an upgrade scenario.

UpgradeEnergyModel is stateless: call compute_month() independently for each
forecast month.  No price or consumption forecasting logic lives here.
"""

from __future__ import annotations

import calendar
import math
from dataclasses import dataclass

from energy_model.assumptions import (
    BatteryAssumptions,
    EVAssumptions,
    HeatPumpAssumptions,
    SolarAssumptions,
)
from energy_model.setup_models import MonthlyUpgradeRecord
from energy_model.solar import monthly_pv_generation


@dataclass(frozen=True)
class ScenarioFlags:
    """Which technologies are active for a given upgrade scenario."""

    has_solar: bool = False
    has_battery: bool = False
    has_heat_pump: bool = False
    has_ev: bool = False


# Scenario definitions — flags only; sizing comes from UpgradeInput.
SCENARIO_FLAGS: dict[str, ScenarioFlags] = {
    "solar_only":          ScenarioFlags(has_solar=True),
    "pv_battery":          ScenarioFlags(has_solar=True, has_battery=True),
    "pv_heatpump":         ScenarioFlags(has_solar=True, has_heat_pump=True),
    "pv_ev":               ScenarioFlags(has_solar=True, has_ev=True),
    "pv_battery_heatpump": ScenarioFlags(has_solar=True, has_battery=True, has_heat_pump=True),
    "full_upgrade":        ScenarioFlags(has_solar=True, has_battery=True,
                                         has_heat_pump=True, has_ev=True),
}


class UpgradeEnergyModel:
    """Computes monthly energy flows and costs for one upgrade scenario.

    The model is pure: given consumption values, prices, and technology
    parameters it returns a MonthlyUpgradeRecord with no side effects.
    """

    def __init__(
        self,
        flags: ScenarioFlags,
        *,
        # PV sizing
        kwp: float = 0.0,
        postcode: str = "",
        orientation: str = "south",
        tilt_deg: float = 30.0,
        shading_factor: float = 0.0,
        solar_assumptions: SolarAssumptions | None = None,
        # Battery sizing
        battery_usable_kwh: float = 0.0,
        battery_assumptions: BatteryAssumptions | None = None,
        # Heat pump
        heat_pump_assumptions: HeatPumpAssumptions | None = None,
        fuel_type: str = "gas",           # "gas" | "oil"
        oil_kwh_per_litre: float = 10.0,  # energy content for oil
        # EV
        ev_assumptions: EVAssumptions | None = None,
        # Feed-in tariff
        feed_in_tariff_eur_per_kwh: float = 0.0820,
        # Fraction of electricity demand occurring during PV generation hours (~8–17h).
        # German residential average ~35% (VDI 4655 / Stromspiegel).
        # This governs how much demand can be served directly vs. from the battery.
        daytime_demand_fraction: float = 0.35,
    ) -> None:
        self._flags = flags
        self._kwp = kwp
        self._postcode = postcode
        self._orientation = orientation
        self._tilt_deg = tilt_deg
        self._shading_factor = shading_factor
        self._solar_a = solar_assumptions or SolarAssumptions()
        self._bat_kwh = battery_usable_kwh
        self._bat_a = battery_assumptions or BatteryAssumptions()
        self._hp_a = heat_pump_assumptions or HeatPumpAssumptions()
        self._fuel_type = fuel_type
        self._oil_kwh_per_litre = oil_kwh_per_litre
        self._ev_a = ev_assumptions or EVAssumptions()
        self._fit = feed_in_tariff_eur_per_kwh
        self._daytime_fraction = max(0.0, min(1.0, daytime_demand_fraction))

    def compute_month(
        self,
        *,
        # Baseline consumption for this month
        baseline_electricity_kwh: float,
        baseline_heating_value: float,   # kWh (gas) or litres (oil)
        baseline_petrol_litres: float,
        monthly_mileage_km: float,
        # Calendar
        year: int,
        month: int,
        year_index: int,                 # 0 = first year after install
        # Prices (same arrays used for baseline comparison)
        elec_unit_eur_per_kwh: float,
        elec_fixed_eur: float,
        heating_price_per_unit: float,
        petrol_price_eur_per_litre: float,
        # Baseline costs (pre-computed by caller for comparison)
        baseline_electricity_cost_eur: float,
        baseline_heating_cost_eur: float,
        baseline_mobility_cost_eur: float,
    ) -> MonthlyUpgradeRecord:
        """Return one month of energy flows and costs for this scenario."""
        days = calendar.monthrange(year, month)[1]
        flags = self._flags

        # ── Step 1: additional electricity demand from upgrades ────────────
        hp_electricity_kwh = 0.0
        remaining_heating_fuel = baseline_heating_value
        if flags.has_heat_pump:
            # Convert baseline heating to kWh of useful heat, then to HP electricity
            if self._fuel_type == "oil":
                heating_kwh = baseline_heating_value * self._oil_kwh_per_litre
            else:
                heating_kwh = baseline_heating_value
            useful_heat = heating_kwh * self._hp_a.existing_heating_efficiency
            hp_electricity_kwh = useful_heat / self._hp_a.heat_pump_scop
            remaining_heating_fuel = 0.0

        ev_home_kwh = 0.0
        remaining_petrol_litres = baseline_petrol_litres
        if flags.has_ev:
            monthly_km = monthly_mileage_km
            ev_total_kwh = (monthly_km / 100.0) * self._ev_a.kwh_per_100km / self._ev_a.charging_efficiency
            ev_home_kwh = ev_total_kwh * self._ev_a.home_charging_share
            remaining_petrol_litres = 0.0

        total_demand = baseline_electricity_kwh + hp_electricity_kwh + ev_home_kwh

        # ── Step 2: PV generation ──────────────────────────────────────────
        pv_gen = 0.0
        if flags.has_solar:
            pv_gen = monthly_pv_generation(
                kwp=self._kwp,
                postcode=self._postcode,
                orientation=self._orientation,
                tilt_deg=self._tilt_deg,
                shading_factor=self._shading_factor,
                year=year,
                month=month,
                year_index=year_index,
                assumptions=self._solar_a,
            )

        # ── Step 3: energy dispatch ────────────────────────────────────────
        # Split demand between daytime (concurrent with PV) and night-time.
        # Only the daytime portion can be served by direct self-consumption;
        # the rest requires either battery discharge or grid import.
        # Source: VDI 4655 / Stromspiegel Germany — ~35% of household
        # electricity demand falls within typical PV generation hours (8–17h).
        daytime_demand = total_demand * self._daytime_fraction
        nighttime_demand = total_demand * (1.0 - self._daytime_fraction)

        # Direct self-consumption: PV meets daytime demand first
        direct_sc = min(pv_gen, daytime_demand)
        pv_surplus = pv_gen - direct_sc           # ≥ 0
        remaining_daytime = daytime_demand - direct_sc  # unmet daytime demand

        # Total demand not met by direct consumption
        demand_remaining = nighttime_demand + remaining_daytime

        bat_charge_in = 0.0   # raw kWh entering battery (before charging loss)
        bat_discharge = 0.0   # useful kWh leaving battery to loads
        bat_loss = 0.0

        if flags.has_battery and pv_surplus > 0 and self._bat_kwh > 0:
            # Battery cycles approximately once per day; cap monthly throughput
            # at usable_capacity × days.  Also cap at available PV surplus.
            max_charge = min(pv_surplus, self._bat_kwh * days)
            bat_charge_in = max_charge
            bat_stored = bat_charge_in * self._bat_a.charge_efficiency

            # Discharge to cover remaining demand (night-time + unmet daytime)
            bat_discharge = min(demand_remaining, bat_stored)
            # bat_loss = stored energy not discharged (monthly remainder)
            bat_loss = bat_stored - bat_discharge

        # Energy balance: pv_gen == direct_sc + bat_charge_in + grid_export
        grid_export = max(0.0, pv_surplus - bat_charge_in)
        # Demand balance: total_demand == direct_sc + bat_discharge + grid_import
        grid_import = max(0.0, demand_remaining - bat_discharge)

        # ── Step 4: costs ─────────────────────────────────────────────────
        grid_elec_cost = grid_import * elec_unit_eur_per_kwh + elec_fixed_eur
        export_revenue = grid_export * self._fit
        heating_cost = remaining_heating_fuel * heating_price_per_unit
        mobility_cost = remaining_petrol_litres * petrol_price_eur_per_litre

        total_upgraded = grid_elec_cost - export_revenue + heating_cost + mobility_cost
        baseline_total = (
            baseline_electricity_cost_eur
            + baseline_heating_cost_eur
            + baseline_mobility_cost_eur
        )
        reduction = baseline_total - total_upgraded

        return MonthlyUpgradeRecord(
            month=f"{year:04d}-{month:02d}",
            baseline_household_electricity_kwh=baseline_electricity_kwh,
            pv_generation_kwh=pv_gen,
            pv_direct_self_consumption_kwh=direct_sc,
            battery_charge_kwh=bat_charge_in,
            battery_discharge_kwh=bat_discharge,
            battery_loss_kwh=bat_loss,
            grid_import_kwh=grid_import,
            grid_export_kwh=grid_export,
            heat_pump_electricity_kwh=hp_electricity_kwh,
            remaining_heating_fuel=remaining_heating_fuel,
            ev_charging_home_kwh=ev_home_kwh,
            remaining_petrol_litres=remaining_petrol_litres,
            electricity_unit_price_eur_per_kwh=elec_unit_eur_per_kwh,
            electricity_fixed_charge_eur=elec_fixed_eur,
            heating_price_per_unit=heating_price_per_unit,
            petrol_price_eur_per_litre=petrol_price_eur_per_litre,
            feed_in_tariff_eur_per_kwh=self._fit,
            grid_electricity_cost_eur=grid_elec_cost,
            solar_export_revenue_eur=export_revenue,
            remaining_heating_fuel_cost_eur=heating_cost,
            remaining_mobility_fuel_cost_eur=mobility_cost,
            total_upgraded_cost_eur=total_upgraded,
            baseline_total_cost_eur=baseline_total,
            energy_cost_reduction_eur=reduction,
        )
