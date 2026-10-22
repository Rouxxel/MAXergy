"""The savings engine — the North Star math.

Given a household's status quo and an upgrade `Scenario`, compute the change in
total monthly outgoings across three buckets: electricity, heating, mobility.

The heuristics here are calibrated to German single-family homes and deliberately
transparent (every constant is named and surfaced in `assumptions`). For a
production model, replace the self-consumption curve with an hourly PV+load
simulation — the interfaces stay the same.
"""

from __future__ import annotations

import math

from .models import (
    Car,
    HeatingType,
    HouseholdProfile,
    SavingsBucket,
    SavingsResult,
    Scenario,
)

# --- fuel -> thermal kWh and price, for deriving heating demand from spend ---
FUEL_PRICE_EUR_PER_KWH = {
    HeatingType.gas: 0.12,
    HeatingType.oil: 0.11,
    HeatingType.district: 0.14,
    HeatingType.electric_resistive: 0.35,
    HeatingType.wood: 0.08,
    HeatingType.heat_pump: 0.35,  # already electric
}

# Battery: dynamic-tariff arbitrage on top of self-consumption.
BATTERY_CYCLES_PER_YEAR = 300
BATTERY_ROUND_TRIP_EFF = 0.90
DYNAMIC_PEAK_OFFPEAK_SPREAD_EUR = 0.10  # cheap-charge / expensive-discharge delta
EV_OFFPEAK_PRICE_EUR_PER_KWH = 0.20

# Rough capex for financing estimates when the user doesn't supply an installment.
CAPEX = {
    "pv_per_kwp": 1500.0,
    "battery_per_kwh": 800.0,
    "heat_pump": 18000.0,
    "ev_charger": 1500.0,
}


def _annuity_monthly(capex: float, months: int, annual_rate: float = 0.06) -> float:
    if capex <= 0 or months <= 0:
        return 0.0
    r = annual_rate / 12.0
    if r == 0:
        return capex / months
    return capex * (r * (1 + r) ** months) / ((1 + r) ** months - 1)


def _self_consumption_ratio(
    annual_pv: float,
    annual_load: float,
    battery_kwh: float,
    pv_kwp: float,
    daytime_load_fraction: float = 0.30,
) -> float:
    """Share of PV production consumed on-site (not exported).

    Load-shape driven, not residential-hardcoded: `daytime_load_fraction` is the share of
    consumption during daylight (homes ~0.30, offices ~0.65, shops ~0.70). Without a
    battery, self-consumed energy ≈ min(PV that lands during load hours, the daytime load),
    so the ratio is min(overlap_eff, daytime_load/PV). A battery shifts evening load onto
    stored daytime surplus. Replace with an hourly sim for production accuracy.
    """
    if annual_pv <= 0:
        return 0.0
    daytime_load = daytime_load_fraction * max(annual_load, 1.0)
    overlap_eff = 0.85  # instantaneous mismatch caps direct use below 100%
    base = min(overlap_eff, daytime_load / annual_pv)
    if battery_kwh > 0 and pv_kwp > 0:
        # Diminishing uplift; saturates around 1 kWh/kWp.
        uplift = 0.35 * (1.0 - math.exp(-battery_kwh / max(pv_kwp, 0.1)))
        base = min(0.92, base + uplift)
    return round(max(0.05, base), 3)


def _heating_thermal_kwh(p: HouseholdProfile) -> float:
    if p.annual_heating_kwh_thermal:
        return p.annual_heating_kwh_thermal
    if p.annual_heating_spend_eur:
        price = FUEL_PRICE_EUR_PER_KWH.get(p.heating_type, 0.12)
        return p.annual_heating_spend_eur / price
    return 0.0


def _largest_ice(cars: list[Car]) -> Car | None:
    ice = [c for c in cars if c.kind.lower() == "ice"]
    return max(ice, key=lambda c: c.annual_km) if ice else None


def evaluate_scenario(p: HouseholdProfile, s: Scenario, production_annual_kwh: float | None = None) -> SavingsResult:
    """Status quo vs scenario, per bucket, in EUR/month."""
    elec_price = p.electricity_price_eur_per_kwh
    feed_in = p.feed_in_tariff_eur_per_kwh

    # ---- system sizes in each world ----
    pv_now = p.existing_pv_kwp
    pv_new = p.existing_pv_kwp + s.add_pv_kwp
    batt_now = p.battery_kwh if p.battery_installed else 0.0
    batt_new = batt_now + s.add_battery_kwh

    # Specific yield from PVGIS (passed in) or a DE default.
    specific_yield = (production_annual_kwh / pv_new) if (production_annual_kwh and pv_new > 0) else 950.0
    annual_pv_now = pv_now * specific_yield
    annual_pv_new = pv_new * specific_yield

    base_load = p.derived_annual_electricity_kwh()

    # ---- added electrical loads from heat pump / EV (scenario only) ----
    thermal = _heating_thermal_kwh(p)
    hp_added_load = (thermal / s.heat_pump_scop) if s.add_heat_pump and thermal > 0 else 0.0

    ice = _largest_ice(p.cars)
    ev_added_load = 0.0
    if s.add_ev and ice:
        ev_added_load = ice.annual_km / 100.0 * ice.kwh_per_100km

    # ---- ELECTRICITY bucket ----
    # Covers the BASE household load only. Heat-pump and EV electricity are
    # accounted in their own buckets below, so they are NOT added here — charging
    # the same kWh in both places would double-count it.
    from .suggestions import daytime_load_fraction_for

    dlf = daytime_load_fraction_for(p.building_type)
    scr_now = _self_consumption_ratio(annual_pv_now, base_load, batt_now, pv_now, dlf)
    scr_new = _self_consumption_ratio(annual_pv_new, base_load, batt_new, pv_new, dlf)

    def electricity_cost(annual_pv, load, scr, batt):
        self_used = min(annual_pv * scr, load)
        exported = max(annual_pv - self_used, 0.0)
        grid_import = max(load - self_used, 0.0)
        cost = grid_import * elec_price - exported * feed_in
        # Dynamic-tariff battery arbitrage (only the existing base load benefits here).
        if batt > 0:
            arb = batt * BATTERY_CYCLES_PER_YEAR * DYNAMIC_PEAK_OFFPEAK_SPREAD_EUR * BATTERY_ROUND_TRIP_EFF
            cost -= arb
        return cost

    elec_now = electricity_cost(annual_pv_now, base_load, scr_now, batt_now)
    elec_new = electricity_cost(annual_pv_new, base_load, scr_new, batt_new)

    buckets = [
        SavingsBucket(label="Electricity", current_monthly_eur=elec_now / 12, new_monthly_eur=elec_new / 12)
    ]

    # ---- HEATING bucket ----
    heat_now_annual = p.annual_heating_spend_eur or (thermal * FUEL_PRICE_EUR_PER_KWH.get(p.heating_type, 0.12))
    if s.add_heat_pump and thermal > 0:
        # HP electricity is mostly grid (winter, low PV) — blend with a little self-supply.
        hp_self_share = 0.15
        hp_price = elec_price * (1 - hp_self_share) + 0.0 * hp_self_share
        heat_new_annual = hp_added_load * hp_price
    else:
        heat_new_annual = heat_now_annual
    if heat_now_annual or heat_new_annual:
        buckets.append(
            SavingsBucket(label="Heating", current_monthly_eur=heat_now_annual / 12, new_monthly_eur=heat_new_annual / 12)
        )

    # ---- MOBILITY bucket ----
    if s.add_ev and ice:
        ice_fuel_annual = ice.annual_km / 100.0 * ice.liters_per_100km * ice.fuel_price_eur_per_l
        ev_charge_annual = ev_added_load * EV_OFFPEAK_PRICE_EUR_PER_KWH
        buckets.append(
            SavingsBucket(label="Mobility", current_monthly_eur=ice_fuel_annual / 12, new_monthly_eur=ev_charge_annual / 12)
        )

    # ---- PEAK DEMAND bucket (commercial only) ----
    # Present only when the site has a demand charge (Leistungspreis). Adding a battery
    # shaves the billed peak by roughly its discharge power (~0.5C), capped at 40% of the
    # current peak. Homes have no demand charge, so this bucket simply never appears.
    charge = p.peak_demand_charge_eur_per_kw_month
    if charge and batt_new > batt_now and p.billed_peak_kw:
        shave_kw = min(0.5 * (batt_new - batt_now), 0.40 * p.billed_peak_kw)
        peak_now_monthly = p.billed_peak_kw * charge
        peak_new_monthly = max(p.billed_peak_kw - shave_kw, 0.0) * charge
        buckets.append(
            SavingsBucket(label="Peak demand", current_monthly_eur=peak_now_monthly, new_monthly_eur=peak_new_monthly)
        )

    # ---- financing for this scenario's capex ----
    if s.financing_monthly_eur is not None:
        financing = s.financing_monthly_eur
    else:
        # Heat-pump capex scales with thermal load: ~€1,200 per kW of heat output
        # (peak ≈ annual thermal / 1800 full-load hours), floored at a residential unit.
        # Without this, a commercial hall's heat pump looks absurdly cheap (flat €18k).
        if s.add_heat_pump and thermal > 0:
            hp_kw = thermal / 1800.0
            hp_capex = max(CAPEX["heat_pump"], hp_kw * 1200.0)
        else:
            hp_capex = 0.0
        capex = (
            s.add_pv_kwp * CAPEX["pv_per_kwp"]
            + s.add_battery_kwh * CAPEX["battery_per_kwh"]
            + hp_capex
            + (CAPEX["ev_charger"] if s.add_ev_charger or s.add_ev else 0.0)
        )
        financing = _annuity_monthly(capex, s.financing_months)

    saving_before_fin = sum(b.monthly_saving_eur for b in buckets)
    saving_now = saving_before_fin - financing

    headline = (
        f"{s.name}: €{saving_now:,.0f}/mo saved now"
        if saving_now >= 0
        else f"{s.name}: about cost-neutral now (€{saving_now:,.0f}/mo), "
        f"€{saving_before_fin:,.0f}/mo once financing is paid off"
    )

    return SavingsResult(
        scenario=s.name,
        buckets=buckets,
        financing_monthly_eur=round(financing, 2),
        monthly_saving_now_eur=round(saving_now, 2),
        monthly_saving_after_payoff_eur=round(saving_before_fin, 2),
        annual_pv_production_kwh=round(annual_pv_new, 1),
        self_consumption_ratio=scr_new,
        assumptions={
            "electricity_price_eur_per_kwh": elec_price,
            "feed_in_tariff_eur_per_kwh": feed_in,
            "specific_yield_kwh_per_kwp": round(specific_yield, 1),
            "heat_pump_scop": s.heat_pump_scop if s.add_heat_pump else None,
            "added_load_heat_pump_kwh": round(hp_added_load, 0) or None,
            "added_load_ev_kwh": round(ev_added_load, 0) or None,
        },
        headline=headline,
    )
