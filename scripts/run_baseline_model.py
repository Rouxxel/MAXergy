"""
Baseline (naive) energy-savings forecast model — MAXergy modelling layer.

Non-hourly, lookup-table-based. Uses fixed placeholder constants for solar
yield, self-consumption ratios, escalation rates, equipment costs, and
financing. No hourly dispatch simulation is performed. Per the documented
modelling contract: upgrade these constants incrementally as real data
sources become available.

Usage:
    python scripts/run_baseline_model.py
    # reads  documentation/data/model_input1.json
    # writes documentation/data/model_output_1.json
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS — all placeholders; replace with real data sources as noted
# ─────────────────────────────────────────────────────────────────────────────

# Solar generation
SPECIFIC_YIELD_KWH_PER_KWP: float = 1000.0  # placeholder — Germany avg; replace with postcode lookup
SOLAR_M2_PER_KWP: float = 7.0               # placeholder — ~7 m² per kWp for standard panels
SOLAR_MAX_KWP: float = 10.0                  # placeholder — soft cap (grid / regulatory)

# Self-consumption ratios by active-component tuple — core simplification; replace with dispatch model
SELF_CONSUMPTION_RATIOS: dict[tuple[str, ...], float] = {
    ("solar_pv",):                                      0.30,
    ("solar_pv", "battery"):                            0.65,
    ("solar_pv", "heat_pump"):                          0.45,
    ("solar_pv", "ev_charger"):                         0.40,
    ("solar_pv", "battery", "heat_pump"):               0.75,
    ("solar_pv", "battery", "heat_pump", "ev_charger"): 0.80,
}

# Feed-in tariff
FEED_IN_TARIFF_EUR_PER_KWH: float = 0.082   # placeholder — EEG §21 simplified; replace with real tariff

# Heat pump
COP: float = 3.3                             # placeholder — seasonal average COP; replace with building-specific
OIL_KWH_PER_LITRE: float = 10.0             # placeholder — standard heating oil energy content

# EV
EV_EFFICIENCY_KWH_PER_100KM: float = 18.0   # placeholder — average BEV consumption
OFF_PEAK_DISCOUNT_FACTOR: float = 0.7        # placeholder — fraction of EV charging at cheap hours

# Fallback fuel prices (used only when annual_spend absent from input)
GAS_PRICE_EUR_PER_KWH: float = 0.10         # placeholder
OIL_PRICE_EUR_PER_LITRE: float = 1.05       # placeholder
PETROL_PRICE_EUR_PER_LITRE: float = 1.75    # placeholder

# Equipment installed costs
SOLAR_PV_EUR_PER_KWP: float = 1_400.0       # placeholder — per kWp installed
BATTERY_EUR_PER_KWH: float = 700.0          # placeholder — per usable kWh
HEAT_PUMP_EUR_FLAT: float = 12_000.0        # placeholder — installed, all-in flat rate
EV_CHARGER_EUR_FLAT: float = 1_200.0        # placeholder — wallbox installed

# Default component sizing when not specified in input
DEFAULT_BATTERY_KWH: float = 7.5            # placeholder
DEFAULT_HEAT_PUMP_KW: float = 9.0           # placeholder

# Subsidy
DEFAULT_SUBSIDY_FRACTION: float = 0.30      # placeholder — 30 % of system cost if no known subsidy

# Long-term annual escalation rates
ELECTRICITY_ESCALATION: float = 0.03        # placeholder
GAS_OIL_ESCALATION: float = 0.04            # placeholder
FUEL_ESCALATION: float = 0.03               # placeholder

# Seasonal heating weights Jan–Dec (raw), normalized so 12-month average = 1.0
_RAW_HEATING_WEIGHTS = [1.4, 1.3, 1.1, 0.9, 0.7, 0.6, 0.6, 0.6, 0.8, 1.0, 1.2, 1.4]
HEATING_SEASONAL_WEIGHTS: list[float] = [w / (sum(_RAW_HEATING_WEIGHTS) / 12) for w in _RAW_HEATING_WEIGHTS]

# Ordered scenario definitions; filtered at runtime against upgrade_candidates
SCENARIO_DEFS: list[dict] = [
    {
        "id": "solar_only",
        "requires": {"solar_pv"},
        "components": {"solar_pv": True, "battery": False, "heat_pump": False, "ev_charger": False},
        "scr_key": ("solar_pv",),
    },
    {
        "id": "pv_battery",
        "requires": {"solar_pv", "battery"},
        "components": {"solar_pv": True, "battery": True, "heat_pump": False, "ev_charger": False},
        "scr_key": ("solar_pv", "battery"),
    },
    {
        "id": "pv_heatpump",
        "requires": {"solar_pv", "heat_pump"},
        "components": {"solar_pv": True, "battery": False, "heat_pump": True, "ev_charger": False},
        "scr_key": ("solar_pv", "heat_pump"),
    },
    {
        "id": "pv_ev",
        "requires": {"solar_pv", "ev_charger"},
        "components": {"solar_pv": True, "battery": False, "heat_pump": False, "ev_charger": True},
        "scr_key": ("solar_pv", "ev_charger"),
    },
    {
        "id": "pv_battery_heatpump",
        "requires": {"solar_pv", "battery", "heat_pump"},
        "components": {"solar_pv": True, "battery": True, "heat_pump": True, "ev_charger": False},
        "scr_key": ("solar_pv", "battery", "heat_pump"),
    },
    {
        "id": "full_upgrade",
        "requires": {"solar_pv", "battery", "heat_pump", "ev_charger"},
        "components": {"solar_pv": True, "battery": True, "heat_pump": True, "ev_charger": True},
        "scr_key": ("solar_pv", "battery", "heat_pump", "ev_charger"),
    },
]

# ─────────────────────────────────────────────────────────────────────────────


def _amortizing_payment(principal: float, annual_rate_pct: float, term_years: int) -> float:
    r = annual_rate_pct / 100 / 12
    n = term_years * 12
    if r == 0:
        return principal / n
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def _iter_months(start_year: int, start_month: int, count: int):
    y, m = start_year, start_month
    for _ in range(count):
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


def run_model(input_path: Path, output_path: Path) -> None:
    with input_path.open() as f:
        inp = json.load(f)

    today = date.today()
    start_year = today.year

    # Short-term forecast starts from the month after today
    first_st_month = today.month + 1
    first_st_year = today.year
    if first_st_month > 12:
        first_st_month, first_st_year = 1, first_st_year + 1

    lt_years: int = inp["forecast_horizon"]["long_term_years"]
    st_months: int = inp["forecast_horizon"]["short_term_months"]

    elec = inp["household"]["electricity"]
    roof = inp["household"]["roof"]
    heating = inp["heating"]
    mobility = inp["mobility"]
    upgrades = inp["upgrade_candidates"]
    fin = inp["financing"]

    # ── Baseline annual cost components ──────────────────────────────────────
    arb: float = elec["arbeitspreis_eur_per_kwh"]
    gp: float = elec["grundpreis_eur_per_month"]
    annual_kwh: float = elec["annual_kwh"]

    base_elec_annual = annual_kwh * arb + gp * 12
    base_elec_monthly = base_elec_annual / 12

    if heating.get("annual_spend_eur"):
        base_heat_annual = float(heating["annual_spend_eur"])
    elif heating["fuel_type"] == "oil":
        base_heat_annual = heating["annual_consumption"] * OIL_PRICE_EUR_PER_LITRE
    else:
        base_heat_annual = heating["annual_consumption"] * GAS_PRICE_EUR_PER_KWH
    base_heat_monthly = base_heat_annual / 12

    # Handle both old single-vehicle and new multi-vehicle mobility structures
    if "vehicles" in mobility and isinstance(mobility["vehicles"], list):
        # New multi-vehicle structure
        vehicle_count = mobility.get("vehicle_count", 0)
        vehicles = mobility["vehicles"]
        
        # Calculate total mobility costs from all vehicles
        base_mob_annual = 0.0
        total_annual_mileage_km = 0.0
        
        for vehicle in vehicles:
            if vehicle.get("annual_fuel_spend_eur"):
                base_mob_annual += float(vehicle["annual_fuel_spend_eur"])
            else:
                # Calculate from mileage and fuel consumption
                annual_mileage_km = vehicle.get("annual_mileage_km", 0)
                fuel_consumption = vehicle.get("fuel_consumption_l_per_100km", 0)
                vehicle_type = vehicle.get("vehicle_type", "petrol")
                
                if annual_mileage_km and fuel_consumption:
                    if vehicle_type in ["petrol", "gas"]:
                        base_mob_annual += (
                            annual_mileage_km / 100
                            * fuel_consumption
                            * PETROL_PRICE_EUR_PER_LITRE
                        )
                    elif vehicle_type == "diesel":
                        DIESEL_PRICE_EUR_PER_LITRE = 1.65  # placeholder
                        base_mob_annual += (
                            annual_mileage_km / 100
                            * fuel_consumption
                            * DIESEL_PRICE_EUR_PER_LITRE
                        )
                    # EV vehicles handled separately in scenario calculations
            
            total_annual_mileage_km += vehicle.get("annual_mileage_km", 0)
        
        # If no vehicles or all fields missing, use fallback
        if base_mob_annual == 0.0 and vehicle_count == 0:
            base_mob_annual = 0.0
    else:
        # Old single-vehicle structure (backward compatibility)
        if mobility.get("annual_fuel_spend_eur"):
            base_mob_annual = float(mobility["annual_fuel_spend_eur"])
        else:
            base_mob_annual = (
                mobility["annual_mileage_km"] / 100
                * mobility["fuel_consumption_l_per_100km"]
                * PETROL_PRICE_EUR_PER_LITRE
            )
        total_annual_mileage_km = mobility.get("annual_mileage_km", 0)
    base_mob_monthly = base_mob_annual / 12

    base_total_monthly = base_elec_monthly + base_heat_monthly + base_mob_monthly

    # ── Baseline short-term forecast ─────────────────────────────────────────
    baseline_stf = []
    for y, m in _iter_months(first_st_year, first_st_month, st_months):
        heat_m = base_heat_monthly * HEATING_SEASONAL_WEIGHTS[m - 1]
        total = base_elec_monthly + heat_m + base_mob_monthly
        baseline_stf.append({"month": f"{y:04d}-{m:02d}", "total_eur": round(total, 2)})

    # ── Baseline long-term forecast ───────────────────────────────────────────
    # Store unrounded for use in saving computations
    baseline_ltf_raw: list[float] = []
    baseline_ltf = []
    for i in range(lt_years):
        yr = start_year + i
        annual = (
            base_elec_annual * (1 + ELECTRICITY_ESCALATION) ** i
            + base_heat_annual * (1 + GAS_OIL_ESCALATION) ** i
            + base_mob_annual * (1 + FUEL_ESCALATION) ** i
        )
        baseline_ltf_raw.append(annual)
        baseline_ltf.append({"year": yr, "annual_total_eur": round(annual, 2)})

    # ── Solar sizing ──────────────────────────────────────────────────────────
    kwp_override = upgrades.get("solar_pv_kwp")
    solar_pv_kwp: float = (
        float(kwp_override)
        if kwp_override
        else min(roof["usable_area_m2"] / SOLAR_M2_PER_KWP, SOLAR_MAX_KWP)
    )
    annual_generation_kwh = solar_pv_kwp * SPECIFIC_YIELD_KWH_PER_KWP

    # ── Heat pump load ────────────────────────────────────────────────────────
    heating_demand_kwh = (
        heating["annual_consumption"] * OIL_KWH_PER_LITRE
        if heating["fuel_type"] == "oil"
        else float(heating["annual_consumption"])
    )
    hp_load_kwh = heating_demand_kwh / COP

    # ── EV load ───────────────────────────────────────────────────────────────
    # Calculate total EV load from all vehicles in the new structure
    ev_load_kwh = 0.0
    if "vehicles" in mobility and isinstance(mobility["vehicles"], list):
        for vehicle in mobility["vehicles"]:
            if vehicle.get("vehicle_type") == "ev":
                annual_mileage_km = vehicle.get("annual_mileage_km", 0)
                ev_load_kwh += annual_mileage_km / 100 * EV_EFFICIENCY_KWH_PER_100KM
    else:
        # Old single-vehicle structure (backward compatibility)
        ev_load_kwh = mobility.get("annual_mileage_km", 0) / 100 * EV_EFFICIENCY_KWH_PER_100KM

    # ── Component sizing & costs ──────────────────────────────────────────────
    battery_kwh: float = float(upgrades.get("battery_kwh") or DEFAULT_BATTERY_KWH)
    heat_pump_kw: float = float(upgrades.get("heat_pump_kw") or DEFAULT_HEAT_PUMP_KW)

    component_costs: dict[str, float] = {
        "solar_pv": SOLAR_PV_EUR_PER_KWP * solar_pv_kwp,
        "battery": BATTERY_EUR_PER_KWH * battery_kwh,
        "heat_pump": HEAT_PUMP_EUR_FLAT,
        "ev_charger": EV_CHARGER_EUR_FLAT,
    }

    loan_rate: float = fin["loan_rate_pct"]
    loan_term: int = fin["loan_term_years"]
    known_subsidy = fin.get("known_subsidy_eur")

    available = {k for k, v in upgrades.items() if v is True}

    # ── Scenarios ─────────────────────────────────────────────────────────────
    scenarios_out = []

    for sdef in SCENARIO_DEFS:
        if not sdef["requires"].issubset(available):
            continue

        comp: dict[str, bool] = sdef["components"]
        scr: float = SELF_CONSUMPTION_RATIOS[sdef["scr_key"]]
        has_hp = comp.get("heat_pump", False)
        has_ev = comp.get("ev_charger", False)

        # PV generation split
        self_consumed = annual_generation_kwh * scr
        exported = annual_generation_kwh - self_consumed

        # New total household load (electricity meter basis)
        new_total_load = annual_kwh
        if has_hp:
            new_total_load += hp_load_kwh
        if has_ev:
            new_total_load += ev_load_kwh

        grid_import = max(new_total_load - self_consumed, 0.0)

        # Annual cost components under this scenario
        sc_elec_annual = grid_import * arb + gp * 12 - exported * FEED_IN_TARIFF_EUR_PER_KWH
        sc_heat_annual = 0.0 if has_hp else base_heat_annual
        sc_mob_annual = (
            ev_load_kwh * arb * OFF_PEAK_DISCOUNT_FACTOR if has_ev else base_mob_annual
        )

        # Monthly equivalents
        sc_elec_m = sc_elec_annual / 12
        sc_heat_m = sc_heat_annual / 12
        sc_mob_m = sc_mob_annual / 12

        # Financing
        total_system_cost = sum(component_costs[c] for c, active in comp.items() if active)
        subsidy = known_subsidy if known_subsidy is not None else DEFAULT_SUBSIDY_FRACTION * total_system_cost
        financed = total_system_cost - subsidy
        monthly_installment = _amortizing_payment(financed, loan_rate, loan_term)

        sc_total_m = sc_elec_m + sc_heat_m + sc_mob_m + monthly_installment
        monthly_saving = base_total_monthly - sc_total_m

        # Cost excluding financing installment (post-payoff state)
        sc_total_excl_inst_m = sc_elec_m + sc_heat_m + sc_mob_m
        monthly_saving_excl_inst = base_total_monthly - sc_total_excl_inst_m

        # Payback: first month where cumulative excl-installment savings ≥ financed amount
        if monthly_saving_excl_inst > 0:
            payback_raw = financed / monthly_saving_excl_inst
            payback_month: int | None = math.ceil(payback_raw)
            if payback_month > loan_term * 12:
                payback_month = None
        else:
            payback_month = None

        # Short-term scenario forecast
        # For HP scenarios, the heating cost is 0 but the HP drives seasonal electricity
        # demand. Split sc_elec_m into a flat non-HP portion and a seasonal HP portion
        # (hp_load × arb / 12), then apply the heating seasonal weight to the HP slice.
        # Weights average to 1.0, so the 12-month sum equals the annual total unchanged.
        hp_elec_m = (hp_load_kwh * arb / 12) if has_hp else 0.0
        sc_elec_flat_m = sc_elec_m - hp_elec_m  # non-seasonal remainder

        scen_stf = []
        for y, m in _iter_months(first_st_year, first_st_month, st_months):
            w = HEATING_SEASONAL_WEIGHTS[m - 1]
            if has_hp:
                total_m = sc_elec_flat_m + hp_elec_m * w + sc_mob_m + monthly_installment
            else:
                total_m = sc_elec_m + sc_heat_m * w + sc_mob_m + monthly_installment
            base_total_m = base_elec_monthly + base_heat_monthly * w + base_mob_monthly
            scen_stf.append({
                "month": f"{y:04d}-{m:02d}",
                "total_eur": round(total_m, 2),
                "saving_eur": round(base_total_m - total_m, 2),
            })

        # Long-term scenario forecast
        scen_ltf = []
        for i in range(lt_years):
            yr = start_year + i
            e_factor = (1 + ELECTRICITY_ESCALATION) ** i
            h_factor = (1 + GAS_OIL_ESCALATION) ** i if not has_hp else 1.0
            # EV mobility is electricity-priced; non-EV is fuel-priced
            mob_factor = (1 + ELECTRICITY_ESCALATION) ** i if has_ev else (1 + FUEL_ESCALATION) ** i
            inst_annual = monthly_installment * 12 if i < loan_term else 0.0

            sc_annual = (
                sc_elec_annual * e_factor
                + sc_heat_annual * h_factor
                + sc_mob_annual * mob_factor
                + inst_annual
            )
            saving_a = baseline_ltf_raw[i] - sc_annual
            scen_ltf.append({
                "year": yr,
                "annual_total_eur": round(sc_annual, 2),
                "annual_saving_eur": round(saving_a, 2),
            })

        # Sizing dict — only include fields relevant to this combo
        sizing: dict = {"solar_pv_kwp": round(solar_pv_kwp, 2)}
        if comp.get("battery"):
            sizing["battery_kwh"] = round(battery_kwh, 1)
        if comp.get("heat_pump"):
            sizing["heat_pump_kw"] = round(heat_pump_kw, 1)

        scenario_obj: dict = {
            "id": sdef["id"],
            "components": comp,
            "sizing": sizing,
            "monthly_cost_eur": {
                "electricity": round(sc_elec_m, 2),
                "heating": round(sc_heat_m, 2),
                "mobility": round(sc_mob_m, 2),
                "financing_installment": round(monthly_installment, 2),
                "total": round(sc_total_m, 2),
            },
            "monthly_saving_eur": round(monthly_saving, 2),
        }
        # Omit monthly_saving_post_payoff_eur entirely when saving is already positive
        if monthly_saving < 0:
            scenario_obj["monthly_saving_post_payoff_eur"] = round(monthly_saving_excl_inst, 2)

        scenario_obj["self_consumption_ratio"] = scr
        scenario_obj["short_term_forecast"] = scen_stf
        scenario_obj["long_term_forecast"] = scen_ltf
        scenario_obj["payback_month"] = payback_month

        scenarios_out.append(scenario_obj)

    # ── Assemble & write output ───────────────────────────────────────────────
    output = {
        "baseline": {
            "monthly_cost_eur": {
                "electricity": round(base_elec_monthly, 2),
                "heating": round(base_heat_monthly, 2),
                "mobility": round(base_mob_monthly, 2),
                "total": round(base_total_monthly, 2),
            },
            "short_term_forecast": baseline_stf,
            "long_term_forecast": baseline_ltf,
        },
        "scenarios": scenarios_out,
    }

    with output_path.open("w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"Wrote {output_path}")


if __name__ == "__main__":
    repo_root = Path(__file__).parent.parent
    input_path = repo_root / "documentation" / "data" / "model_input1.json"
    output_path = repo_root / "documentation" / "data" / "model_output_1.json"
    run_model(input_path, output_path)
