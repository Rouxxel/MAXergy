"""Solar PV generation model.

Computes monthly PV generation in kWh from system size, location, and
roof geometry.  No cost logic lives here.
"""

from __future__ import annotations

import calendar

from energy_model.assumptions import SolarAssumptions


def resolve_kwp(
    solar_kwp: float | None,
    usable_roof_area_m2: float | None,
    assumptions: SolarAssumptions,
) -> tuple[float, str]:
    """Return (kwp, provenance_note).

    Raises ValueError when neither kwp nor roof area is provided.
    """
    if solar_kwp is not None:
        return float(solar_kwp), "user"
    if usable_roof_area_m2 is not None:
        kwp = usable_roof_area_m2 / assumptions.m2_per_kwp
        note = f"derived from {usable_roof_area_m2} m² at {assumptions.m2_per_kwp} m²/kWp"
        return kwp, note
    raise ValueError(
        "solar_kwp or usable_roof_area_m2 must be provided to size the PV system"
    )


def _regional_yield(postcode: str, assumptions: SolarAssumptions) -> float:
    """Return annual specific yield (kWh/kWp) for the postcode region."""
    prefix = postcode[:1] if postcode else ""
    return assumptions.regional_yield_kwh_per_kwp.get(
        prefix, assumptions.default_yield_kwh_per_kwp
    )


def _orientation_factor(orientation: str, assumptions: SolarAssumptions) -> float:
    """Return yield correction for roof orientation (south = 1.0)."""
    key = orientation.lower().replace(" ", "_").replace("-", "_")
    factor = assumptions.orientation_factors.get(key)
    if factor is None:
        raise ValueError(
            f"Unknown roof orientation '{orientation}'. "
            f"Valid values: {list(assumptions.orientation_factors)}"
        )
    return factor


def _tilt_factor(tilt_deg: float, assumptions: SolarAssumptions) -> float:
    """Interpolate yield correction for arbitrary tilt angle."""
    table = assumptions.tilt_yield_factors
    keys = sorted(table.keys())
    if tilt_deg <= keys[0]:
        return table[keys[0]]
    if tilt_deg >= keys[-1]:
        return table[keys[-1]]
    # Linear interpolation between the two nearest breakpoints
    for i in range(len(keys) - 1):
        lo, hi = keys[i], keys[i + 1]
        if lo <= tilt_deg <= hi:
            t = (tilt_deg - lo) / (hi - lo)
            return table[lo] + t * (table[hi] - table[lo])
    return table[keys[-1]]


def feed_in_tariff(kwp: float, assumptions: SolarAssumptions) -> float:
    """Return applicable German EEG 2024 feed-in tariff (EUR/kWh) by system size."""
    if kwp <= 10.0:
        return assumptions.feed_in_tariff_small_eur_per_kwh
    if kwp <= 40.0:
        return assumptions.feed_in_tariff_medium_eur_per_kwh
    return assumptions.feed_in_tariff_large_eur_per_kwh


def monthly_pv_generation(
    *,
    kwp: float,
    postcode: str,
    orientation: str,
    tilt_deg: float,
    shading_factor: float,
    year: int,
    month: int,
    year_index: int,          # 0-based: 0 = first forecast year
    assumptions: SolarAssumptions,
) -> float:
    """Return PV generation in kWh for one calendar month.

    Parameters
    ----------
    year_index:
        How many complete years have elapsed since installation (0 in year 1).
        Used for annual degradation.
    shading_factor:
        Fraction of irradiance lost to shading (0 = none, 1 = full).
    """
    if kwp <= 0:
        return 0.0

    annual_yield = _regional_yield(postcode, assumptions)
    orient_f = _orientation_factor(orientation, assumptions)
    tilt_f = _tilt_factor(tilt_deg, assumptions)
    shade_f = 1.0 - max(0.0, min(1.0, shading_factor))
    degrad_f = (1.0 - assumptions.annual_degradation_pct / 100.0) ** year_index

    monthly_fraction = assumptions.monthly_yield_fractions[month - 1]

    # Days correction: the monthly fractions assume an average month;
    # scale slightly by actual days vs. 30.417 (365/12).
    days = calendar.monthrange(year, month)[1]
    days_factor = days / (365.0 / 12.0)

    return (
        kwp
        * annual_yield
        * monthly_fraction
        * orient_f
        * tilt_f
        * shade_f
        * degrad_f
        * days_factor
    )
