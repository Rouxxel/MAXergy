"""Suggest-then-confirm helpers for the onboarding flow.

Same pattern as the roof-size suggestion: give the advisor a concrete, transparent
anchor to propose, which the user then confirms or corrects. All heuristics are
German single-family calibrated and surfaced in the result so nothing is a black box.
"""

from __future__ import annotations

from .models import HeatingType
from .savings import FUEL_PRICE_EUR_PER_KWH

# Specific space-heating demand (kWh of heat per m² per year). One table spanning
# residential vintages AND commercial use types — a home is just one entry, so the same
# flow serves a flat or a 4,500 m² office without branching. German benchmarks.
HEATING_DEMAND_KWH_PER_M2 = {
    # residential by vintage
    "old": 200.0,       # unrenovated pre-1980s
    "average": 130.0,   # typical / partially renovated
    "modern": 80.0,     # post-2000 or renovated
    "efficient": 50.0,  # new-build / KfW-efficiency
    # building use types
    "home": 130.0,
    "office": 100.0,
    "retail": 130.0,
    "warehouse": 60.0,
    "hotel": 150.0,
    "school": 110.0,
}
DEFAULT_BUILDING = "average"

# Share of annual electricity consumed during daylight (when PV produces). Drives
# self-consumption: homes are evening-heavy (~0.3), daytime businesses much higher.
# A continuous spectrum, not a residential/commercial flag.
DAYTIME_LOAD_FRACTION = {
    "old": 0.30, "average": 0.30, "modern": 0.30, "efficient": 0.30, "home": 0.30,
    "office": 0.65, "retail": 0.70, "warehouse": 0.55, "hotel": 0.45, "school": 0.55,
}
DEFAULT_DAYTIME_LOAD_FRACTION = 0.30

HEAT_PUMP_SCOP = 3.5  # for converting thermal demand to heat-pump electricity

# Typical all-in electricity price by building type (€/kWh, German). Commercial/industrial
# buys far cheaper per kWh than residential retail — and the price drives how many kWh the
# stated monthly spend implies, so getting it right matters for the whole model.
ELECTRICITY_PRICE_BY_BUILDING = {
    "old": 0.35, "average": 0.35, "modern": 0.35, "efficient": 0.35, "home": 0.35,
    "office": 0.28, "retail": 0.28, "hotel": 0.28, "school": 0.27, "warehouse": 0.20,
}
DEFAULT_ELECTRICITY_PRICE = 0.35

# Installable PV per m² of roof footprint: module density (~0.19 kWp/m²) de-rated for the
# usable share of a roof (obstructions, spacing, walkways).
ROOF_USABLE_FRACTION = 0.6
KWP_PER_M2_MODULE = 0.19


def daytime_load_fraction_for(building_type: str | None) -> float:
    """Self-consumption load-shape for a building type; residential default if unknown."""
    return DAYTIME_LOAD_FRACTION.get((building_type or "").lower(), DEFAULT_DAYTIME_LOAD_FRACTION)


def suggest_electricity_price(building_type: str = "home", monthly_spend_eur: float | None = None) -> dict:
    """Propose a per-kWh electricity price for the building type, and the implied annual kWh.

    Residential ~0.35, commercial ~0.28, industrial/warehouse ~0.20 €/kWh. The advisor
    presents this to confirm — the user's real contract price is better if they know it."""
    price = ELECTRICITY_PRICE_BY_BUILDING.get((building_type or "").lower(), DEFAULT_ELECTRICITY_PRICE)
    out = {
        "suggested_price_eur_per_kwh": price,
        "basis": f"typical all-in price for '{building_type}' (German benchmark)",
        "note": "Use the actual contract €/kWh if known — it sets the implied annual kWh.",
    }
    if monthly_spend_eur:
        out["implied_annual_kwh"] = round(monthly_spend_eur * 12 / max(price, 0.01))
    return out


def estimate_roof_capacity_from_area(floor_area_m2: float, stories: int = 1) -> dict:
    """Fallback roof PV ceiling from building floor area, when the Solar API misses the roof.

    A single-story hall's roof ≈ its footprint. For multi-story, footprint = area / stories.
    ceiling_kwp ≈ footprint × usable-fraction × module-density. Far better than a wrong tiny
    Solar-API result for large/industrial buildings."""
    footprint = max(floor_area_m2, 0.0) / max(stories, 1)
    usable_m2 = footprint * ROOF_USABLE_FRACTION
    ceiling_kwp = round(usable_m2 * KWP_PER_M2_MODULE)
    return {
        "estimated_max_kwp": ceiling_kwp,
        "assumptions": {
            "footprint_m2": round(footprint),
            "usable_roof_fraction": ROOF_USABLE_FRACTION,
            "kwp_per_usable_m2": KWP_PER_M2_MODULE,
            "stories": stories,
        },
        "note": "Floor-area estimate — use when the Solar API roof result looks too small for the building.",
    }


def suggest_battery_kwh(pv_kwp: float, annual_electricity_kwh: float | None = None) -> dict:
    """Propose a home-battery size to confirm.

    Rule of thumb: ~1 kWh of usable storage per kWp of PV captures most of the
    self-consumption benefit for a single-family home; cross-checked against ~1 kWh per
    1,000 kWh of annual use. Clamped to the common residential 5–15 kWh range.
    """
    by_pv = pv_kwp if pv_kwp > 0 else 0.0
    by_load = (annual_electricity_kwh / 1000.0) if annual_electricity_kwh else 0.0
    raw = max(by_pv, by_load)
    # Floor at the smallest residential unit; the upper bound scales WITH the system
    # (no residential 15 kWh hard cap) so a large commercial array gets a sane suggestion.
    upper = max(15.0, round(raw * 1.5))
    suggested = int(max(5, min(upper, round(raw))))
    low = int(max(5, min(upper, round(raw * 0.7))))
    high = int(max(low, min(upper, round(raw * 1.3))))
    return {
        "suggested_battery_kwh": suggested,
        "typical_range_kwh": [low, high],
        "basis": "≈1 kWh per kWp of solar (and per 1,000 kWh/yr of use); bound scales with system size",
        "note": "A guess to confirm — final size depends on usage pattern, peak load, and budget.",
    }


def estimate_heating_spend(
    living_area_m2: float,
    heating_type: str = "gas",
    building_type: str = DEFAULT_BUILDING,
) -> dict:
    """Estimate current annual heating spend from floor area, to propose and confirm.

    building_type spans residential vintages (old/average/modern/efficient) AND use types
    (home/office/retail/warehouse/hotel/school) — same call for a flat or an office.
    spend ≈ area × specific-demand × fuel-price; a heat pump divides demand by SCOP and
    prices as electricity.
    """
    demand = HEATING_DEMAND_KWH_PER_M2.get(
        (building_type or "").lower(), HEATING_DEMAND_KWH_PER_M2[DEFAULT_BUILDING]
    )
    thermal_kwh = max(living_area_m2, 0.0) * demand

    try:
        ht = HeatingType(heating_type)
    except ValueError:
        ht = HeatingType.gas

    if ht == HeatingType.heat_pump:
        elec_kwh = thermal_kwh / HEAT_PUMP_SCOP
        spend = elec_kwh * FUEL_PRICE_EUR_PER_KWH[HeatingType.heat_pump]
    else:
        spend = thermal_kwh * FUEL_PRICE_EUR_PER_KWH.get(ht, FUEL_PRICE_EUR_PER_KWH[HeatingType.gas])

    return {
        "estimated_annual_heating_spend_eur": round(spend),
        "estimated_monthly_eur": round(spend / 12),
        "thermal_demand_kwh_per_year": round(thermal_kwh),
        "assumptions": {
            "living_area_m2": living_area_m2,
            "building_type": (building_type or "").lower() if (building_type or "").lower() in HEATING_DEMAND_KWH_PER_M2 else DEFAULT_BUILDING,
            "specific_demand_kwh_per_m2": demand,
            "heating_type": ht.value,
            "fuel_price_eur_per_kwh": FUEL_PRICE_EUR_PER_KWH.get(ht),
        },
        "note": "Estimate from floor area — confirm against an actual bill if they have one.",
    }
