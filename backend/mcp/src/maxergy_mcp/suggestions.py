"""Suggest-then-confirm helpers for the onboarding flow.

Each helper gives the advisor a concrete, transparent anchor to propose, which the user then
confirms or corrects. Prices, PV density and defaults come from the backend engine
(`GET /assumptions`, passed in as `assumptions`) so the MCP never uses its own constants for
anything the engine models. Only residential German buildings with gas or oil heating are
supported, matching the engine.
"""

from __future__ import annotations

# Specific space-heating demand (kWh of heat per m² per year) by residential insulation class.
# German benchmarks; the engine needs consumption or spend as input, so this only seeds a
# proposal for the user to confirm.
HEATING_DEMAND_KWH_PER_M2 = {
    "old": 200.0,       # unrenovated pre-1980s
    "average": 130.0,   # typical / partially renovated
    "modern": 80.0,     # post-2000 or renovated
    "efficient": 50.0,  # new-build / KfW-efficiency
}
DEFAULT_INSULATION = "average"
SUPPORTED_HEATING = ("gas", "oil")

# Share of a pitched roof's footprint that can carry modules (obstructions, spacing, walkways).
ROOF_USABLE_FRACTION = 0.6


def _unsupported(reason: str) -> dict:
    return {"supported": False, "note": reason}


def suggest_electricity_price(assumptions: dict, monthly_spend_eur: float | None = None) -> dict:
    """Propose the engine's default tariff and, from a monthly bill, the implied annual kWh."""
    t = assumptions["tariff"]
    arb, base = t["arbeitspreis_eur_per_kwh"], t["grundpreis_eur_per_month"]
    out = {
        "suggested_arbeitspreis_eur_per_kwh": arb,
        "suggested_grundpreis_eur_per_month": base,
        "basis": "MAXergy engine default German household tariff",
        "note": "Use the actual contract prices if known — they set the implied annual kWh.",
    }
    if monthly_spend_eur:
        out["implied_annual_kwh"] = round(max(monthly_spend_eur - base, 0.0) * 12 / max(arb, 0.01))
    return out


def estimate_roof_capacity_from_area(assumptions: dict, floor_area_m2: float, stories: int = 1) -> dict:
    """Fallback usable roof area and PV ceiling from floor area, when the Solar API misses the roof."""
    footprint = max(floor_area_m2, 0.0) / max(stories, 1)
    usable_m2 = footprint * ROOF_USABLE_FRACTION
    m2_per_kwp = assumptions["solar"]["m2_per_kwp"]
    return {
        "usable_area_m2": round(usable_m2),
        "estimated_max_kwp": round(usable_m2 / m2_per_kwp, 1),
        "assumptions": {
            "footprint_m2": round(footprint),
            "usable_roof_fraction": ROOF_USABLE_FRACTION,
            "m2_per_kwp": m2_per_kwp,
            "stories": stories,
        },
        "note": "Floor-area estimate — use `usable_area_m2` for household.roof when the roof scan is missing or implausible.",
    }


def suggest_battery_kwh(assumptions: dict, pv_kwp: float, annual_electricity_kwh: float | None = None) -> dict:
    """Propose a home-battery size: ~1 kWh per kWp (and per 1,000 kWh/yr), 5–15 kWh."""
    raw = max(pv_kwp if pv_kwp > 0 else 0.0, (annual_electricity_kwh or 0.0) / 1000.0)
    suggested = int(max(5, min(15, round(raw))))
    return {
        "suggested_battery_kwh": suggested,
        "typical_range_kwh": [max(5, round(suggested * 0.7)), min(15, round(suggested * 1.3))],
        "engine_default_kwh": assumptions["battery"]["default_usable_kwh"],
        "basis": "≈1 kWh per kWp of solar (and per 1,000 kWh/yr of use), residential 5–15 kWh",
        "note": "Leave upgrade_candidates.battery_kwh empty to use the engine default.",
    }


def estimate_heating_spend(
    assumptions: dict, living_area_m2: float, heating_type: str = "gas", insulation_class: str = DEFAULT_INSULATION
) -> dict:
    """Estimate annual heating consumption and spend from floor area, to propose and confirm."""
    fuel = (heating_type or "").lower()
    if fuel not in SUPPORTED_HEATING:
        return _unsupported(
            f"MAXergy currently models gas or oil heating only (got '{heating_type}')."
        )
    insulation = (insulation_class or "").lower()
    if insulation not in HEATING_DEMAND_KWH_PER_M2:
        insulation = DEFAULT_INSULATION
    thermal_kwh = max(living_area_m2, 0.0) * HEATING_DEMAND_KWH_PER_M2[insulation]
    tariff = assumptions["tariff"]
    if fuel == "oil":
        consumption = thermal_kwh / assumptions["consumption"]["oil_kwh_per_litre"]
        spend, unit, price = consumption * tariff["oil_eur_per_litre"], "litres", tariff["oil_eur_per_litre"]
    else:
        consumption = thermal_kwh
        spend, unit, price = consumption * tariff["gas_eur_per_kwh"], "kWh", tariff["gas_eur_per_kwh"]
    return {
        "supported": True,
        "estimated_annual_consumption": round(consumption),
        "consumption_unit": unit,
        "estimated_annual_heating_spend_eur": round(spend),
        "estimated_monthly_eur": round(spend / 12),
        "assumptions": {
            "living_area_m2": living_area_m2,
            "insulation_class": insulation,
            "specific_demand_kwh_per_m2": HEATING_DEMAND_KWH_PER_M2[insulation],
            "fuel_price": price,
        },
        "note": "Estimate from floor area — confirm against an actual bill if available.",
    }
