"""Configurable defaults for energy system upgrade modelling.

Every assumption documents its source or rationale.  When a caller provides
an explicit value it overrides the default; the provenance trail records which
values came from the user and which from these defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SolarAssumptions:
    """PV system sizing and yield assumptions."""

    # Monocrystalline panels ~200 W/m²; 6 m²/kWp leaves margin for framing/gaps.
    m2_per_kwp: float = 6.0

    # LID + standard cell degradation; manufacturer warranty typically 0.5%/yr.
    annual_degradation_pct: float = 0.5

    # Regional annual specific yield by first digit of PLZ (kWh/kWp/year).
    # Source: PVGIS SARAH-2 south-facing 30° tilt, Germany.
    regional_yield_kwh_per_kwp: dict[str, float] = field(default_factory=lambda: {
        "0": 1000.0,  # East (Leipzig, Dresden)
        "1": 950.0,   # Berlin
        "2": 950.0,   # North (Hamburg, Kiel)
        "3": 990.0,   # Hannover, Magdeburg
        "4": 1030.0,  # Cologne, Dortmund
        "5": 1060.0,  # Frankfurt, Wiesbaden
        "6": 1080.0,  # Mannheim, Karlsruhe
        "7": 1100.0,  # Stuttgart, Freiburg
        "8": 1150.0,  # Munich, Augsburg
        "9": 1120.0,  # Nuremberg, Regensburg
    })

    default_yield_kwh_per_kwp: float = 1000.0

    # Monthly fractions of annual yield (Jan–Dec, sum = 1.0).
    # Source: PVGIS mean monthly irradiation, Germany average.
    monthly_yield_fractions: tuple[float, ...] = (
        0.027, 0.043, 0.083, 0.104, 0.132, 0.138,
        0.138, 0.126, 0.093, 0.063, 0.031, 0.022,
    )

    # Yield correction factors relative to south (1.0) at optimal tilt.
    orientation_factors: dict[str, float] = field(default_factory=lambda: {
        "south": 1.00, "s": 1.00,
        "south_east": 0.95, "se": 0.95,
        "south_west": 0.95, "sw": 0.95,
        "east": 0.85, "e": 0.85,
        "west": 0.85, "w": 0.85,
        "north_east": 0.70, "ne": 0.70,
        "north_west": 0.70, "nw": 0.70,
        "north": 0.55, "n": 0.55,
    })

    # Tilt angle (degrees) → yield correction for south-facing roof, Germany ~50°N.
    # Optimal tilt is 30–35°.
    tilt_yield_factors: dict[int, float] = field(default_factory=lambda: {
        0: 0.87, 10: 0.92, 15: 0.94, 20: 0.97, 25: 0.99,
        30: 1.00, 35: 1.00, 40: 0.98, 45: 0.96,
        50: 0.93, 60: 0.85, 75: 0.72, 90: 0.58,
    })

    # Feed-in tariff (Germany EEG 2024, §48).
    feed_in_tariff_small_eur_per_kwh: float = 0.0820   # ≤ 10 kWp
    feed_in_tariff_medium_eur_per_kwh: float = 0.0710  # 10–40 kWp
    feed_in_tariff_large_eur_per_kwh: float = 0.0580   # 40–100 kWp


@dataclass(frozen=True)
class BatteryAssumptions:
    """Residential battery storage defaults."""

    # Common residential BESS in Germany (e.g. BYD HVM 10.2, Sonnenbatterie 10).
    default_usable_kwh: float = 10.0

    # Lithium-ion round-trip ~90%; split symmetrically: 0.95 × 0.95 = 0.9025.
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95


@dataclass(frozen=True)
class HeatPumpAssumptions:
    """Heat pump and existing boiler defaults."""

    # Modern condensing boiler (Brennwert) η ~0.90; older atmospheric ~0.80.
    existing_heating_efficiency: float = 0.85

    # Air-to-water heat pump SCOP at A7/W35 operating point.
    # Source: Eurovent Certified Performance, typical German installation.
    heat_pump_scop: float = 3.0


@dataclass(frozen=True)
class EVAssumptions:
    """Electric vehicle charging defaults."""

    # WLTP range for compact/mid-size EVs: 15–22 kWh/100km.
    kwh_per_100km: float = 18.0

    # AC home EVSE charging efficiency (grid → battery).  Typical: 90–95%.
    charging_efficiency: float = 0.92

    # Share of annual EV charging done at home vs. public/work chargers.
    # German KBA survey average: ~80%.
    home_charging_share: float = 0.80


@dataclass(frozen=True)
class GridAssumptions:
    """Grid interaction assumptions."""

    # Determined by system size when not explicitly set.
    # Computed from SolarAssumptions.feed_in_tariff_* — this field is a fallback.
    feed_in_tariff_eur_per_kwh: float = 0.0820
