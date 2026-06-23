"""Baseline (naive) energy-savings forecast model — runs IN THIS REPO.

This is a faithful in-repo port of the team's canonical modelling layer
(`scripts/run_baseline_model.py` in the Rouxxel/MAXergy monorepo). The MCP server runs
this model directly — it does NOT call the teammate's backend — so the calculation is
self-contained here and produces output identical to the canonical script for the same
input. When the canonical model changes, re-sync this file (the smoke test diffs the two).

Non-hourly, lookup-table-based. Every constant below is a placeholder the canonical model
marks for incremental upgrade (e.g. swap the flat specific yield for a PVGIS postcode
lookup — `providers.estimate_pv_production` is already available for that). Kept verbatim
here so numbers match the canonical model exactly.

Interface: `run_overview(ModelInput) -> dict` (the contract-shaped output). The pydantic
models in `model_schema.py` validate both ends.
"""

from __future__ import annotations

import logging
import math
from datetime import date

from .model_schema import ModelInput, ModelOutput

log = logging.getLogger("maxnergy.model")

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS — all placeholders (mirror the canonical run_baseline_model.py)
# ─────────────────────────────────────────────────────────────────────────────

# Solar generation
SPECIFIC_YIELD_KWH_PER_KWP: float = 1000.0  # Germany avg; replace with postcode lookup (PVGIS)
SOLAR_M2_PER_KWP: float = 7.0               # ~7 m² per kWp for standard panels
SOLAR_MAX_KWP: float = 10.0                 # soft cap (grid / regulatory)

# Self-consumption ratios by active-component tuple — core simplification
SELF_CONSUMPTION_RATIOS: dict[tuple[str, ...], float] = {
    ("solar_pv",):                                      0.30,
    ("solar_pv", "battery"):                            0.65,
    ("solar_pv", "heat_pump"):                          0.45,
    ("solar_pv", "ev_charger"):                         0.40,
    ("solar_pv", "battery", "heat_pump"):               0.75,
    ("solar_pv", "battery", "heat_pump", "ev_charger"): 0.80,
}

FEED_IN_TARIFF_EUR_PER_KWH: float = 0.082   # EEG §21 simplified

COP: float = 3.3                            # seasonal average heat-pump COP
OIL_KWH_PER_LITRE: float = 10.0             # heating-oil energy content

EV_EFFICIENCY_KWH_PER_100KM: float = 18.0   # average BEV consumption
OFF_PEAK_DISCOUNT_FACTOR: float = 0.7       # fraction of EV charging at cheap hours

# Fallback fuel prices (used only when annual_spend absent from input)
GAS_PRICE_EUR_PER_KWH: float = 0.10
OIL_PRICE_EUR_PER_LITRE: float = 1.05
PETROL_PRICE_EUR_PER_LITRE: float = 1.75
DIESEL_PRICE_EUR_PER_LITRE: float = 1.65

# Equipment installed costs
SOLAR_PV_EUR_PER_KWP: float = 1_400.0
BATTERY_EUR_PER_KWH: float = 700.0
HEAT_PUMP_EUR_FLAT: float = 12_000.0
EV_CHARGER_EUR_FLAT: float = 1_200.0

# Default component sizing when not specified in input
DEFAULT_BATTERY_KWH: float = 7.5
DEFAULT_HEAT_PUMP_KW: float = 9.0

DEFAULT_SUBSIDY_FRACTION: float = 0.30      # 30 % of system cost if no known subsidy

# Long-term annual escalation rates (per bucket)
ELECTRICITY_ESCALATION: float = 0.03
GAS_OIL_ESCALATION: float = 0.04
FUEL_ESCALATION: float = 0.03

# Seasonal heating weights Jan–Dec (raw), normalized so 12-month average = 1.0
_RAW_HEATING_WEIGHTS = [1.4, 1.3, 1.1, 0.9, 0.7, 0.6, 0.6, 0.6, 0.8, 1.0, 1.2, 1.4]
HEATING_SEASONAL_WEIGHTS: list[float] = [
    w / (sum(_RAW_HEATING_WEIGHTS) / 12) for w in _RAW_HEATING_WEIGHTS
]

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


def compute_overview(inp: dict, today: date | None = None) -> dict:
    """Faithful port of the canonical `run_model`: input dict -> contract-shaped output dict."""
    today = today or date.today()
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

    # Mobility — multi-vehicle structure (combustion spend totalled; EVs handled per scenario)
    vehicles = mobility.get("vehicles") or []
    base_mob_annual = 0.0
    for vehicle in vehicles:
        if vehicle.get("annual_fuel_spend_eur"):
            base_mob_annual += float(vehicle["annual_fuel_spend_eur"])
        else:
            km = vehicle.get("annual_mileage_km", 0)
            cons = vehicle.get("fuel_consumption_l_per_100km", 0)
            vtype = vehicle.get("vehicle_type", "petrol")
            if km and cons:
                if vtype in ("petrol", "gas"):
                    base_mob_annual += km / 100 * cons * PETROL_PRICE_EUR_PER_LITRE
                elif vtype == "diesel":
                    base_mob_annual += km / 100 * cons * DIESEL_PRICE_EUR_PER_LITRE
    base_mob_monthly = base_mob_annual / 12

    base_total_monthly = base_elec_monthly + base_heat_monthly + base_mob_monthly

    # ── Baseline short-term forecast ─────────────────────────────────────────
    baseline_stf = []
    for y, m in _iter_months(first_st_year, first_st_month, st_months):
        heat_m = base_heat_monthly * HEATING_SEASONAL_WEIGHTS[m - 1]
        total = base_elec_monthly + heat_m + base_mob_monthly
        baseline_stf.append({"month": f"{y:04d}-{m:02d}", "total_eur": round(total, 2)})

    # ── Baseline long-term forecast ──────────────────────────────────────────
    baseline_ltf_raw: list[float] = []
    baseline_ltf = []
    for i in range(lt_years):
        annual = (
            base_elec_annual * (1 + ELECTRICITY_ESCALATION) ** i
            + base_heat_annual * (1 + GAS_OIL_ESCALATION) ** i
            + base_mob_annual * (1 + FUEL_ESCALATION) ** i
        )
        baseline_ltf_raw.append(annual)
        baseline_ltf.append({"year": start_year + i, "annual_total_eur": round(annual, 2)})

    # ── Solar sizing ─────────────────────────────────────────────────────────
    kwp_override = upgrades.get("solar_pv_kwp")
    solar_pv_kwp: float = (
        float(kwp_override) if kwp_override
        else min(roof["usable_area_m2"] / SOLAR_M2_PER_KWP, SOLAR_MAX_KWP)
    )
    annual_generation_kwh = solar_pv_kwp * SPECIFIC_YIELD_KWH_PER_KWP

    # ── Heat-pump load ───────────────────────────────────────────────────────
    heating_demand_kwh = (
        heating["annual_consumption"] * OIL_KWH_PER_LITRE
        if heating["fuel_type"] == "oil"
        else float(heating["annual_consumption"])
    )
    hp_load_kwh = heating_demand_kwh / COP

    # ── EV load (from vehicles already typed "ev") ───────────────────────────
    ev_load_kwh = 0.0
    for vehicle in vehicles:
        if vehicle.get("vehicle_type") == "ev":
            ev_load_kwh += vehicle.get("annual_mileage_km", 0) / 100 * EV_EFFICIENCY_KWH_PER_100KM

    # ── Component sizing & costs ─────────────────────────────────────────────
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

    # ── Scenarios ────────────────────────────────────────────────────────────
    scenarios_out = []
    for sdef in SCENARIO_DEFS:
        if not sdef["requires"].issubset(available):
            continue

        comp: dict[str, bool] = sdef["components"]
        scr: float = SELF_CONSUMPTION_RATIOS[sdef["scr_key"]]
        has_hp = comp.get("heat_pump", False)
        has_ev = comp.get("ev_charger", False)

        self_consumed = annual_generation_kwh * scr
        exported = annual_generation_kwh - self_consumed

        new_total_load = annual_kwh
        if has_hp:
            new_total_load += hp_load_kwh
        if has_ev:
            new_total_load += ev_load_kwh
        grid_import = max(new_total_load - self_consumed, 0.0)

        sc_elec_annual = grid_import * arb + gp * 12 - exported * FEED_IN_TARIFF_EUR_PER_KWH
        sc_heat_annual = 0.0 if has_hp else base_heat_annual
        sc_mob_annual = ev_load_kwh * arb * OFF_PEAK_DISCOUNT_FACTOR if has_ev else base_mob_annual

        sc_elec_m = sc_elec_annual / 12
        sc_heat_m = sc_heat_annual / 12
        sc_mob_m = sc_mob_annual / 12

        # Financing (system cost less subsidy, amortized)
        total_system_cost = sum(component_costs[c] for c, active in comp.items() if active)
        subsidy = known_subsidy if known_subsidy is not None else DEFAULT_SUBSIDY_FRACTION * total_system_cost
        financed = total_system_cost - subsidy
        monthly_installment = _amortizing_payment(financed, loan_rate, loan_term)

        sc_total_m = sc_elec_m + sc_heat_m + sc_mob_m + monthly_installment
        monthly_saving = base_total_monthly - sc_total_m

        sc_total_excl_inst_m = sc_elec_m + sc_heat_m + sc_mob_m
        monthly_saving_excl_inst = base_total_monthly - sc_total_excl_inst_m

        # Payback: months for excl-installment saving to repay the financed amount
        if monthly_saving_excl_inst > 0:
            payback_month: int | None = math.ceil(financed / monthly_saving_excl_inst)
            if payback_month > loan_term * 12:
                payback_month = None
        else:
            payback_month = None

        # Short-term: heat-pump electricity carries the seasonal weight (heating is 0 then)
        hp_elec_m = (hp_load_kwh * arb / 12) if has_hp else 0.0
        sc_elec_flat_m = sc_elec_m - hp_elec_m
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

        # Long-term: per-bucket escalation; installment present until the loan term ends
        scen_ltf = []
        for i in range(lt_years):
            e_factor = (1 + ELECTRICITY_ESCALATION) ** i
            h_factor = (1 + GAS_OIL_ESCALATION) ** i if not has_hp else 1.0
            mob_factor = (1 + ELECTRICITY_ESCALATION) ** i if has_ev else (1 + FUEL_ESCALATION) ** i
            inst_annual = monthly_installment * 12 if i < loan_term else 0.0
            sc_annual = (
                sc_elec_annual * e_factor
                + sc_heat_annual * h_factor
                + sc_mob_annual * mob_factor
                + inst_annual
            )
            scen_ltf.append({
                "year": start_year + i,
                "annual_total_eur": round(sc_annual, 2),
                "annual_saving_eur": round(baseline_ltf_raw[i] - sc_annual, 2),
            })

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
        if monthly_saving < 0:
            scenario_obj["monthly_saving_post_payoff_eur"] = round(monthly_saving_excl_inst, 2)
        scenario_obj["self_consumption_ratio"] = scr
        scenario_obj["short_term_forecast"] = scen_stf
        scenario_obj["long_term_forecast"] = scen_ltf
        scenario_obj["payback_month"] = payback_month
        scenarios_out.append(scenario_obj)

    return {
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


def run_overview(inp: ModelInput, today: date | None = None) -> dict:
    """Validate the input, run the in-repo baseline model, and return the contract output dict.

    The output is validated against `ModelOutput` for structural safety, then returned as the
    plain dict (preserving the canonical shape: explicit null `payback_month`, omitted
    sizing/post-payoff keys) so it matches the canonical model byte-for-byte.
    """
    result = compute_overview(inp.model_dump(), today)
    ModelOutput.model_validate(result)  # structural guard; raises on contract drift
    log.info("overview computed: %d scenarios, baseline %.2f €/mo",
             len(result["scenarios"]), result["baseline"]["monthly_cost_eur"]["total"])
    return result
