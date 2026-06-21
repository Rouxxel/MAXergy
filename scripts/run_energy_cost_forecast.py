"""
Integrated energy cost forecast — MAXergy modelling layer.

Forecasts household energy costs (electricity, heating, mobility) WITHOUT any
home-energy upgrade.  Three cleanly separated modules:

  ConsumptionModel      — monthly consumption profiles (BDEW H0 + DWD HDD)
  EnergyPriceModel      — monthly unit-price trajectories with scenarios
  EnergyCostCalculator  — deterministic cost = consumption × price (no forecasting)
  ForecastOrchestrator  — wires the three modules, validates, writes output

Usage:
    python scripts/run_energy_cost_forecast.py
    # reads  documentation/data/model_input1.json
    # writes documentation/data/model_output_forecast.json
"""

from __future__ import annotations

import calendar
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

# ─────────────────────────────────────────────────────────────────────────────
# PATHS
# ─────────────────────────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).parent.parent
_DATA_DIR = _REPO_ROOT / "data"
_BDEW_PATH = _DATA_DIR / "bdew_h0_profile.json"
_DWD_PATH = _DATA_DIR / "dwd_climate_normals.json"

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION — all placeholder values are grouped here.
# Replace any section with a real data source without touching other modules.
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ConsumptionConfig:
    """Placeholder consumption parameters."""

    # German average kWh/person/year (Bundesnetzagentur Monitoring 2023)
    # PLACEHOLDER — replace with postcode-level demand model
    kwh_per_person_per_year: float = 1500.0

    # Monthly mobility weights Jan–Dec (uniform by default)
    # PLACEHOLDER — replace with VKZ mobility survey data
    mobility_monthly_weights: tuple[float, ...] = (
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
    )

    # Heating oil energy content (kWh per litre) — standard value
    oil_kwh_per_litre: float = 10.0

    # Heating base temperature for degree-day calculation (°C)
    # German standard: Gradtagszahl-Methode with 15°C base
    hdd_base_temp_c: float = 15.0

    # Fallback heating weights used when DWD data is unavailable
    # PLACEHOLDER — degree-day proxy based on Germany average temperatures
    fallback_heating_monthly_weights: tuple[float, ...] = (
        1.40, 1.30, 1.10, 0.90, 0.70, 0.60,
        0.60, 0.60, 0.80, 1.00, 1.20, 1.40,
    )


@dataclass(frozen=True)
class PriceConfig:
    """Placeholder price trajectories.

    Annual trends and seasonal factors are deliberately separated so the two
    can evolve independently as data sources improve.
    Replace with models trained on Destatis / BDEW historical price series.
    """

    # ── Current fallback prices (used only when input cannot provide them) ───
    # PLACEHOLDER — replace with real-time tariff API (e.g. Verivox / Tibber)
    default_electricity_arbeitspreis_eur_per_kwh: float = 0.32
    default_electricity_grundpreis_eur_per_month: float = 12.50
    default_gas_eur_per_kwh: float = 0.10
    default_oil_eur_per_litre: float = 1.05
    default_petrol_eur_per_litre: float = 1.75

    # ── Annual price trends per scenario ─────────────────────────────────────
    # PLACEHOLDER — replace with BDEW/Destatis long-run price projections
    electricity_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.01, "central": 0.03, "high": 0.05,
    })
    gas_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.01, "central": 0.04, "high": 0.07,
    })
    oil_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.01, "central": 0.04, "high": 0.07,
    })
    petrol_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.01, "central": 0.03, "high": 0.05,
    })
    # Fixed charge grows more slowly than unit price
    fixed_charge_annual_trend: dict[str, float] = field(default_factory=lambda: {
        "low": 0.005, "central": 0.02, "high": 0.03,
    })

    # ── Monthly price seasonality (post-contract only; relative to mean = 1.0) ─
    # PLACEHOLDER — replace with Destatis monthly price indices
    petrol_monthly_seasonality: tuple[float, ...] = (
        0.97, 0.97, 0.99, 1.01, 1.03, 1.04,
        1.04, 1.03, 1.01, 0.99, 0.97, 0.97,
    )

    # Reconstruction-vs-reported spend warning threshold (fraction)
    spend_warning_threshold: float = 0.15


CONSUMPTION_CONFIG = ConsumptionConfig()
PRICE_CONFIG = PriceConfig()

ScenarioName = Literal["low", "central", "high"]
SCENARIO_NAMES: list[ScenarioName] = ["low", "central", "high"]

# ─────────────────────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class MonthlyRecord:
    """Complete record for a single forecast month."""
    month: str                      # "YYYY-MM"
    # Consumption
    electricity_kwh: float
    heating_value: float            # original unit (kWh for gas, litres for oil)
    heating_unit: str               # "kwh" | "litres"
    mobility_km: float
    mobility_fuel_litres: float
    # Prices
    electricity_eur_per_kwh: float
    electricity_fixed_eur: float
    heating_eur_per_unit: float
    petrol_eur_per_litre: float
    # Costs
    electricity_cost_eur: float
    heating_cost_eur: float
    mobility_cost_eur: float
    total_cost_eur: float


@dataclass
class AnnualRecord:
    year: int
    electricity_kwh: float
    heating_value: float
    heating_unit: str
    mobility_fuel_litres: float
    electricity_cost_eur: float
    heating_cost_eur: float
    mobility_cost_eur: float
    total_cost_eur: float


# ─────────────────────────────────────────────────────────────────────────────
# BDEW H0 PROFILE
# ─────────────────────────────────────────────────────────────────────────────


def _easter(year: int) -> date:
    """Anonymous Gregorian algorithm for Easter Sunday."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = (h + l - 7 * m + 114) % 31 + 1
    return date(year, month, day)


class BDEWProfile:
    """BDEW H0 standard household electricity load profile.

    Computes monthly consumption fractions from day-type energy levels,
    correctly accounting for the number of weekdays, Saturdays, and
    Sundays/public holidays in each calendar month.

    Data source: data/bdew_h0_profile.json (fallback to hardcoded values).
    """

    # Hardcoded fallback — pre-computed fractions for a representative year
    _FALLBACK_FRACTIONS = (
        0.0960, 0.0889, 0.0857, 0.0793, 0.0773, 0.0748,
        0.0741, 0.0753, 0.0783, 0.0831, 0.0878, 0.0994,
    )

    def __init__(self, data_path: Path = _BDEW_PATH) -> None:
        self._data: dict | None = None
        self._source = "fallback"
        self._cache: dict[int, tuple[float, ...]] = {}

        try:
            with data_path.open() as f:
                self._data = json.load(f)
            self._source = "bdew_h0_profile.json"
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    @property
    def source(self) -> str:
        return self._source

    def monthly_fractions(self, year: int) -> tuple[float, ...]:
        """Return 12 monthly electricity fractions summing to 1.0 for the given year."""
        if year in self._cache:
            return self._cache[year]
        result = self._compute(year)
        self._cache[year] = result
        return result

    def _compute(self, year: int) -> tuple[float, ...]:
        if self._data is None:
            return self._FALLBACK_FRACTIONS

        try:
            holidays = self._holidays(year)
            season_map: dict[int, str] = {}
            for season, months in self._data["seasons"].items():
                for m in months:
                    season_map[m] = season

            factors = self._data["daily_energy_by_season_daytype"]
            raw: list[float] = []
            for m in range(1, 13):
                days = calendar.monthrange(year, m)[1]
                season = season_map[m]
                sf = factors[season]
                energy = 0.0
                d0 = date(year, m, 1)
                for day_offset in range(days):
                    d = d0 + timedelta(days=day_offset)
                    if d in holidays or d.weekday() == 6:
                        energy += sf["sunday_holiday"]
                    elif d.weekday() == 5:
                        energy += sf["saturday"]
                    else:
                        energy += sf["weekday"]
                raw.append(energy)

            total = sum(raw)
            fractions = tuple(v / total for v in raw)
            # Sanity: must sum to 1.0 within floating-point tolerance
            if abs(sum(fractions) - 1.0) > 1e-9:
                return self._FALLBACK_FRACTIONS
            return fractions

        except (KeyError, TypeError, ValueError):
            return self._FALLBACK_FRACTIONS

    def _holidays(self, year: int) -> set[date]:
        if self._data is None:
            return set()
        result: set[date] = set()
        for h in self._data.get("national_holidays_fixed", []):
            result.add(date(year, h["month"], h["day"]))
        easter = _easter(year)
        for h in self._data.get("national_holidays_easter_offset", []):
            result.add(easter + timedelta(days=h["offset"]))
        return result


# ─────────────────────────────────────────────────────────────────────────────
# DWD WEATHER MODEL
# ─────────────────────────────────────────────────────────────────────────────


class WeatherModel:
    """DWD climate-normal temperatures and heating degree day distribution.

    Data source: data/dwd_climate_normals.json (fallback to Germany average).
    """

    _FALLBACK_TEMPS = (1.5, 2.9, 6.5, 10.9, 15.2, 18.2, 20.4, 19.9, 15.6, 10.3, 5.6, 2.3)

    def __init__(
        self,
        data_path: Path = _DWD_PATH,
        base_temp: float = CONSUMPTION_CONFIG.hdd_base_temp_c,
    ) -> None:
        self._base_temp = base_temp
        self._data: dict | None = None
        self._source = "fallback"
        self._is_fallback = True

        try:
            with data_path.open() as f:
                self._data = json.load(f)
            self._source = "dwd_climate_normals.json"
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def monthly_temperatures(self, postcode: str) -> tuple[tuple[float, ...], str, bool]:
        """Return (12 monthly mean °C, station name, is_fallback)."""
        if self._data is None:
            return self._FALLBACK_TEMPS, "Germany average (hardcoded fallback)", True

        prefix = postcode[:2] if len(postcode) >= 2 else ""
        plz_map: dict = self._data.get("postcode_prefix_to_region", {})
        region_key = plz_map.get(prefix)

        if not region_key:
            fb = self._data.get("fallback_region", "germany_average")
            region_key = fb

        regions: dict = self._data.get("regions", {})
        if region_key not in regions:
            return self._FALLBACK_TEMPS, "Germany average (fallback)", True

        rd = regions[region_key]
        temps = tuple(float(t) for t in rd["mean_temp_c"])
        return temps, rd.get("station", region_key), False

    def heating_fractions(self, postcode: str) -> tuple[tuple[float, ...], str, bool]:
        """Return (12 monthly heating fractions summing to 1.0, source, is_fallback)."""
        temps, source, is_fallback = self.monthly_temperatures(postcode)
        ref_year = 2024  # leap year — representative for days-per-month calculation
        hdds: list[float] = []
        for m, t in enumerate(temps, 1):
            days = calendar.monthrange(ref_year, m)[1]
            hdds.append(max(0.0, (self._base_temp - t) * days))

        total_hdd = sum(hdds)
        if total_hdd <= 0:
            fractions = tuple(1.0 / 12 for _ in range(12))
        else:
            fractions = tuple(h / total_hdd for h in hdds)

        return fractions, source, is_fallback


# ─────────────────────────────────────────────────────────────────────────────
# 1. CONSUMPTION MODEL
# ─────────────────────────────────────────────────────────────────────────────


class ConsumptionModel:
    """Distributes annual energy consumption into monthly fractions.

    Uses the BDEW H0 profile for electricity and DWD heating degree days for
    heating.  No price or cost logic lives here.
    """

    def __init__(
        self,
        config: ConsumptionConfig = CONSUMPTION_CONFIG,
        bdew_profile: BDEWProfile | None = None,
        weather_model: WeatherModel | None = None,
    ) -> None:
        self._cfg = config
        self._bdew = bdew_profile or BDEWProfile()
        self._weather = weather_model or WeatherModel()
        # In-memory cache: (year, postcode) → heating fractions
        self._heat_cache: dict[str, tuple[float, ...]] = {}

    def electricity_fraction(self, year: int, month: int) -> float:
        """Fraction of annual electricity consumed in the given month (0–1)."""
        fracs = self._bdew.monthly_fractions(year)
        return fracs[month - 1]

    def heating_fraction(self, month: int, postcode: str) -> float:
        """Fraction of annual heating consumed in the given month (0–1)."""
        if postcode not in self._heat_cache:
            fracs, _, _ = self._weather.heating_fractions(postcode)
            self._heat_cache[postcode] = fracs
        return self._heat_cache[postcode][month - 1]

    @staticmethod
    def mobility_fraction(month: int) -> float:
        """Fraction of annual mobility in the given month (uniform = 1/12)."""
        return 1.0 / 12

    def profile_metadata(self, postcode: str) -> dict:
        """Return metadata about which data sources were used."""
        _, heat_station, heat_is_fallback = self._weather.monthly_temperatures(postcode)
        return {
            "electricity_profile_source": f"BDEW H0 ({self._bdew.source})",
            "heating_profile_source": f"DWD HDD from {heat_station}",
            "heating_profile_is_fallback": heat_is_fallback,
            "weather_data_source": heat_station,
            "weather_data_cached": False,
        }

    # ── Convenience: full-year arrays for validation ──────────────────────────

    def annual_electricity_profile(self, annual_kwh: float, year: int) -> list[float]:
        """Return 12 monthly kWh values summing to annual_kwh for a calendar year."""
        fracs = self._bdew.monthly_fractions(year)
        values = [annual_kwh * f for f in fracs]
        _assert_sum(values, annual_kwh, "electricity")
        return values

    def annual_heating_profile(
        self, annual_value: float, postcode: str, fuel_type: str, cfg: ConsumptionConfig
    ) -> tuple[list[float], list[float]]:
        """Return (monthly_original_unit, monthly_kwh) for a calendar year."""
        fracs_tuple, _, _ = self._weather.heating_fractions(postcode)
        monthly = [annual_value * f for f in fracs_tuple]
        if fuel_type == "oil":
            monthly_kwh = [v * cfg.oil_kwh_per_litre for v in monthly]
        else:
            monthly_kwh = list(monthly)
        _assert_sum(monthly, annual_value, "heating")
        return monthly, monthly_kwh


def _assert_sum(values: list[float], expected: float, label: str) -> None:
    actual = sum(values)
    if abs(actual - expected) > 1e-6 * max(abs(expected), 1.0):
        raise AssertionError(
            f"{label} monthly sum {actual:.6f} != annual {expected:.6f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 2. PRICE MODEL
# ─────────────────────────────────────────────────────────────────────────────


class EnergyPriceModel:
    """Produces monthly unit-price forecasts.

    Behaviour during an electricity contract:
      - Unit price and fixed charge stay exactly constant until contract_end_date.
      - Post-contract: trend escalation starts from the first month after expiry.

    No consumption or cost logic lives here.
    """

    def __init__(self, config: PriceConfig = PRICE_CONFIG) -> None:
        self._cfg = config

    def forecast_monthly_prices(
        self,
        energy_type: str,
        current_price: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
        context: dict | None = None,
    ) -> list[float]:
        """Return a list of ``months`` monthly unit prices.

        Parameters
        ----------
        energy_type:
            One of "electricity_unit", "electricity_fixed", "gas", "oil", "petrol".
        current_price:
            Price at the start of the forecast (in relevant EUR unit).
        start_date:
            First calendar month of the forecast.
        months:
            Number of months to forecast.
        scenario:
            "low" | "central" | "high".
        context:
            Optional dict.  For electricity types supply
            ``{"contract_end_date": date | None}``.
        """
        if current_price < 0:
            raise ValueError(f"current_price must be non-negative, got {current_price}")
        if months < 1:
            raise ValueError("months must be >= 1")

        annual_trend = self._annual_trend(energy_type, scenario)
        seasonality = self._seasonality(energy_type)
        contract_end: date | None = (context or {}).get("contract_end_date")

        result: list[float] = []
        months_post_contract = 0
        y, m = start_date.year, start_date.month

        for _ in range(months):
            month_date = date(y, m, 1)

            if contract_end is not None and month_date <= contract_end:
                # Price locked exactly to contract rate — no seasonality, no trend
                price = current_price
            else:
                # Post-contract: trend starts from zero months after contract end
                yrs = months_post_contract / 12
                months_post_contract += 1
                price = current_price * (1 + annual_trend) ** yrs * seasonality[m - 1]

            result.append(max(price, 0.0))
            m += 1
            if m > 12:
                m, y = 1, y + 1

        return result

    def _annual_trend(self, energy_type: str, scenario: ScenarioName) -> float:
        cfg = self._cfg
        mapping = {
            "electricity_unit": cfg.electricity_annual_trend,
            "electricity_fixed": cfg.fixed_charge_annual_trend,
            "gas": cfg.gas_annual_trend,
            "oil": cfg.oil_annual_trend,
            "petrol": cfg.petrol_annual_trend,
        }
        trends = mapping.get(energy_type)
        if trends is None:
            raise ValueError(f"Unknown energy_type '{energy_type}'")
        return trends[scenario]

    def _seasonality(self, energy_type: str) -> tuple[float, ...]:
        if energy_type == "petrol":
            return self._cfg.petrol_monthly_seasonality
        # Electricity (post-contract), gas, oil: flat seasonality
        return tuple(1.0 for _ in range(12))

    def forecast_electricity_prices(
        self,
        arbeitspreis: float,
        grundpreis: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
        contract_end_date: date | None,
    ) -> tuple[list[float], list[float]]:
        """Return (unit_prices, fixed_charges) lists, each of length ``months``."""
        ctx = {"contract_end_date": contract_end_date}
        units = self.forecast_monthly_prices(
            "electricity_unit", arbeitspreis, start_date, months, scenario, ctx
        )
        fixed = self.forecast_monthly_prices(
            "electricity_fixed", grundpreis, start_date, months, scenario, ctx
        )
        return units, fixed

    def forecast_heating_prices(
        self,
        fuel_type: str,
        current_price_per_unit: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        etype = "gas" if fuel_type == "gas" else "oil"
        return self.forecast_monthly_prices(
            etype, current_price_per_unit, start_date, months, scenario
        )

    def forecast_petrol_prices(
        self,
        current_price: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        return self.forecast_monthly_prices(
            "petrol", current_price, start_date, months, scenario
        )

    def metadata(self) -> dict:
        """Return model identity and all configurable assumptions."""
        cfg = self._cfg
        return {
            "name": "deterministic_trend",
            "version": "1.0",
            "assumptions": {
                "electricity_annual_trend": dict(cfg.electricity_annual_trend),
                "gas_annual_trend": dict(cfg.gas_annual_trend),
                "oil_annual_trend": dict(cfg.oil_annual_trend),
                "petrol_annual_trend": dict(cfg.petrol_annual_trend),
                "fixed_charge_annual_trend": dict(cfg.fixed_charge_annual_trend),
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# PRICE MODEL INTERFACE
# ─────────────────────────────────────────────────────────────────────────────


@runtime_checkable
class PriceModelProtocol(Protocol):
    """Structural interface for price models injected into ForecastOrchestrator.

    Any object implementing these four methods can replace EnergyPriceModel
    without changing the consumption or cost modules.
    """

    def forecast_electricity_prices(
        self,
        arbeitspreis: float,
        grundpreis: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
        contract_end_date: date | None,
    ) -> tuple[list[float], list[float]]:
        """Return (unit_prices, fixed_charges), each a list of length ``months``."""
        ...

    def forecast_heating_prices(
        self,
        fuel_type: str,
        current_price_per_unit: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        """Return monthly heating fuel unit prices."""
        ...

    def forecast_petrol_prices(
        self,
        current_price: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        """Return monthly petrol prices (EUR/litre)."""
        ...

    def metadata(self) -> dict:
        """Return a dict describing the model name, version, and assumptions."""
        ...


# ─────────────────────────────────────────────────────────────────────────────
# 3. COST MODEL (deterministic — no forecasting logic)
# ─────────────────────────────────────────────────────────────────────────────


class EnergyCostCalculator:
    """Calculate energy costs from consumption and price inputs.

    Contains only arithmetic — no forecasting, no defaults.
    """

    @staticmethod
    def electricity_cost(kwh: float, unit_price: float, fixed_charge: float) -> float:
        if kwh < 0:
            raise ValueError("electricity consumption must be non-negative")
        return kwh * unit_price + fixed_charge

    @staticmethod
    def heating_cost(value: float, eur_per_unit: float) -> float:
        if value < 0:
            raise ValueError("heating consumption must be non-negative")
        return value * eur_per_unit

    @staticmethod
    def mobility_cost(litres: float, petrol_eur_per_litre: float) -> float:
        if litres < 0:
            raise ValueError("fuel consumption must be non-negative")
        return litres * petrol_eur_per_litre


# ─────────────────────────────────────────────────────────────────────────────
# INPUT PARSING
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class ParsedInput:
    """Validated, normalised view of the JSON input with provenance tracking."""

    postcode: str
    country: str
    occupants: int

    # Electricity
    annual_kwh: float
    arbeitspreis_eur_per_kwh: float
    grundpreis_eur_per_month: float
    contract_end_date: date | None

    # Heating
    fuel_type: str                   # "gas" | "oil"
    heating_annual_value: float      # kWh for gas, litres for oil
    heating_annual_kwh: float
    heating_eur_per_unit: float      # effective current price
    heating_unit: str                # "kwh" | "litres"

    # Mobility
    vehicle_type: str
    annual_mileage_km: float
    fuel_consumption_l_per_100km: float
    effective_petrol_eur_per_litre: float
    annual_fuel_spend_eur: float | None

    # Horizons
    short_term_months: int
    long_term_years: int

    # Provenance: field → "user" | "default:<description>"
    provenance: dict[str, str] = field(default_factory=dict)
    warnings_list: list[str] = field(default_factory=list)


def _parse_input(raw: dict) -> ParsedInput:
    """Validate and normalise raw JSON input, applying German defaults where needed."""
    cfg = CONSUMPTION_CONFIG
    pcfg = PRICE_CONFIG
    prov: dict[str, str] = {}
    warns: list[str] = []

    # ── Location ──────────────────────────────────────────────────────────────
    loc = raw.get("location", {})
    postcode = loc.get("postcode")
    country = loc.get("country", "DE")
    if not postcode:
        raise ValueError("Input must contain location.postcode")

    # ── Household / electricity ───────────────────────────────────────────────
    hh = raw.get("household", {})
    occupants_raw = hh.get("occupants")
    if occupants_raw is not None:
        occupants = int(occupants_raw)
        prov["occupants"] = "user"
    else:
        occupants = 2
        prov["occupants"] = "default:2-person German household"
        warns.append("occupants not provided; assumed 2")

    elec = hh.get("electricity", {})

    annual_kwh_raw = elec.get("annual_kwh")
    if annual_kwh_raw is not None:
        annual_kwh = float(annual_kwh_raw)
        prov["annual_kwh"] = "user"
    else:
        annual_kwh = occupants * cfg.kwh_per_person_per_year
        prov["annual_kwh"] = f"default:{cfg.kwh_per_person_per_year} kWh/person/yr"
        warns.append(f"annual_kwh estimated from occupants: {annual_kwh:.0f} kWh")

    arb_raw = elec.get("arbeitspreis_eur_per_kwh")
    if arb_raw is not None:
        arb = float(arb_raw)
        prov["arbeitspreis_eur_per_kwh"] = "user"
    else:
        arb = pcfg.default_electricity_arbeitspreis_eur_per_kwh
        prov["arbeitspreis_eur_per_kwh"] = f"default:{arb} EUR/kWh"
        warns.append(f"arbeitspreis not provided; using default {arb} EUR/kWh")

    gp_raw = elec.get("grundpreis_eur_per_month")
    if gp_raw is not None:
        gp = float(gp_raw)
        prov["grundpreis_eur_per_month"] = "user"
    else:
        gp = pcfg.default_electricity_grundpreis_eur_per_month
        prov["grundpreis_eur_per_month"] = f"default:{gp} EUR/month"

    ced_raw = elec.get("contract_end_date")
    ced: date | None = date.fromisoformat(ced_raw) if ced_raw else None
    prov["contract_end_date"] = "user" if ced_raw else "default:none"

    # ── Heating ───────────────────────────────────────────────────────────────
    heat = raw.get("heating", {})
    fuel_type = heat.get("fuel_type", "gas").lower()
    if fuel_type not in ("gas", "oil"):
        raise ValueError(f"Unsupported fuel_type '{fuel_type}'; must be 'gas' or 'oil'")

    annual_cons_raw = heat.get("annual_consumption")
    annual_spend_raw = heat.get("annual_spend_eur")

    if annual_cons_raw is not None:
        heating_annual_value = float(annual_cons_raw)
        prov["heating_annual_consumption"] = "user"
    elif annual_spend_raw is not None:
        fallback_price = (
            pcfg.default_gas_eur_per_kwh
            if fuel_type == "gas"
            else pcfg.default_oil_eur_per_litre
        )
        heating_annual_value = float(annual_spend_raw) / fallback_price
        prov["heating_annual_consumption"] = (
            f"default:derived from spend at {fallback_price} EUR/unit"
        )
        warns.append("heating annual_consumption derived from annual_spend_eur")
    else:
        raise ValueError(
            "Heating section must contain annual_consumption or annual_spend_eur"
        )

    if fuel_type == "oil":
        heating_annual_kwh = heating_annual_value * cfg.oil_kwh_per_litre
        heating_unit = "litres"
    else:
        heating_annual_kwh = heating_annual_value
        heating_unit = "kwh"

    # Effective heating price: prefer user-derived (spend / consumption) over default
    if annual_cons_raw is not None and annual_spend_raw is not None and float(annual_cons_raw) > 0:
        effective_heating_price = float(annual_spend_raw) / float(annual_cons_raw)
        prov["heating_eur_per_unit"] = (
            f"user:derived {effective_heating_price:.4f} EUR/unit from spend÷consumption"
        )
    else:
        effective_heating_price = (
            pcfg.default_gas_eur_per_kwh
            if fuel_type == "gas"
            else pcfg.default_oil_eur_per_litre
        )
        prov["heating_eur_per_unit"] = f"default:{effective_heating_price} EUR/unit"

    prov["fuel_type"] = "user" if heat.get("fuel_type") else "default:gas"

    # ── Mobility ──────────────────────────────────────────────────────────────
    mob = raw.get("mobility", {})
    vehicle_type = mob.get("vehicle_type", "petrol").lower()

    mileage_raw = mob.get("annual_mileage_km")
    fuel_cons_raw = mob.get("fuel_consumption_l_per_100km")
    if mileage_raw is None or fuel_cons_raw is None:
        raise ValueError(
            "mobility section must contain annual_mileage_km and fuel_consumption_l_per_100km"
        )
    annual_mileage_km = float(mileage_raw)
    fuel_cons = float(fuel_cons_raw)
    prov["annual_mileage_km"] = "user"
    prov["fuel_consumption_l_per_100km"] = "user"

    mob_spend_raw = mob.get("annual_fuel_spend_eur")
    annual_fuel_spend_eur = float(mob_spend_raw) if mob_spend_raw is not None else None

    # Effective petrol price: prefer user-derived
    annual_fuel_litres = annual_mileage_km / 100 * fuel_cons
    if annual_fuel_spend_eur is not None and annual_fuel_litres > 0:
        effective_petrol_price = annual_fuel_spend_eur / annual_fuel_litres
        prov["effective_petrol_eur_per_litre"] = (
            f"user:derived {effective_petrol_price:.4f} EUR/litre from spend÷litres"
        )
    else:
        effective_petrol_price = pcfg.default_petrol_eur_per_litre
        prov["effective_petrol_eur_per_litre"] = f"default:{effective_petrol_price} EUR/litre"

    # ── Forecast horizons ─────────────────────────────────────────────────────
    fh = raw.get("forecast_horizon", {})
    st_months = int(fh.get("short_term_months", 12))
    lt_years = int(fh.get("long_term_years", 20))

    return ParsedInput(
        postcode=postcode,
        country=country,
        occupants=occupants,
        annual_kwh=annual_kwh,
        arbeitspreis_eur_per_kwh=arb,
        grundpreis_eur_per_month=gp,
        contract_end_date=ced,
        fuel_type=fuel_type,
        heating_annual_value=heating_annual_value,
        heating_annual_kwh=heating_annual_kwh,
        heating_eur_per_unit=effective_heating_price,
        heating_unit=heating_unit,
        vehicle_type=vehicle_type,
        annual_mileage_km=annual_mileage_km,
        fuel_consumption_l_per_100km=fuel_cons,
        effective_petrol_eur_per_litre=effective_petrol_price,
        annual_fuel_spend_eur=annual_fuel_spend_eur,
        short_term_months=st_months,
        long_term_years=lt_years,
        provenance=prov,
        warnings_list=warns,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────


def _iter_months(start_year: int, start_month: int, count: int):
    y, m = start_year, start_month
    for _ in range(count):
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


# ─────────────────────────────────────────────────────────────────────────────
# ORCHESTRATOR
# ─────────────────────────────────────────────────────────────────────────────


class ForecastOrchestrator:
    """Wires ConsumptionModel, EnergyPriceModel, and EnergyCostCalculator together."""

    def __init__(
        self,
        consumption_model: ConsumptionModel | None = None,
        price_model: PriceModelProtocol | None = None,
        calculator: EnergyCostCalculator | None = None,
    ) -> None:
        self._cons = consumption_model or ConsumptionModel()
        self._price = price_model or EnergyPriceModel()
        self._calc = calculator or EnergyCostCalculator()

    def run(self, inp: ParsedInput) -> dict:
        today = date.today()
        sm, sy = today.month + 1, today.year
        if sm > 12:
            sm, sy = 1, sy + 1
        start_date = date(sy, sm, 1)

        # Current-year cost reconstruction for validation / output
        annual_fuel_litres = inp.annual_mileage_km / 100 * inp.fuel_consumption_l_per_100km
        current_elec_cost = (
            inp.annual_kwh * inp.arbeitspreis_eur_per_kwh + inp.grundpreis_eur_per_month * 12
        )
        current_heat_cost = inp.heating_annual_value * inp.heating_eur_per_unit
        current_mob_cost = annual_fuel_litres * inp.effective_petrol_eur_per_litre

        # Validation warnings (input-level)
        val_warns = list(inp.warnings_list)
        val_warns += self._validate_reconstruction(inp)

        # Profile metadata
        profile_meta = self._cons.profile_metadata(inp.postcode)

        # Total months to generate: covers both ST and all LT periods
        total_months = max(inp.short_term_months, inp.long_term_years * 12)

        # Per-scenario forecast
        scenarios: dict[str, dict] = {}
        for scenario in SCENARIO_NAMES:
            records = self._forecast_months(inp, scenario, start_date, total_months)
            st = records[: inp.short_term_months]
            lt = self._aggregate_periods(records, inp.long_term_years)
            scenarios[scenario] = {
                "short_term_forecast": [self._serialise_monthly(r) for r in st],
                "long_term_forecast": [self._serialise_annual(a) for a in lt],
            }

        self._validate_scenario_ordering(scenarios, val_warns)

        return {
            "model": {
                "name": "integrated_energy_cost_forecast",
                "version": "1.1",
                "forecast_type": "consumption_price_cost",
            },
            "input_summary": {
                "postcode": inp.postcode,
                "country": inp.country,
                "occupants": inp.occupants,
                "annual_electricity_kwh": inp.annual_kwh,
                "arbeitspreis_eur_per_kwh": inp.arbeitspreis_eur_per_kwh,
                "grundpreis_eur_per_month": inp.grundpreis_eur_per_month,
                "contract_end_date": inp.contract_end_date.isoformat() if inp.contract_end_date else None,
                "fuel_type": inp.fuel_type,
                "heating_annual_value": inp.heating_annual_value,
                "heating_unit": inp.heating_unit,
                "effective_heating_eur_per_unit": inp.heating_eur_per_unit,
                "vehicle_type": inp.vehicle_type,
                "annual_mileage_km": inp.annual_mileage_km,
                "fuel_consumption_l_per_100km": inp.fuel_consumption_l_per_100km,
                "annual_fuel_litres": round(annual_fuel_litres, 2),
                "effective_petrol_eur_per_litre": inp.effective_petrol_eur_per_litre,
                "forecast_start": start_date.isoformat(),
                "short_term_months": inp.short_term_months,
                "long_term_years": inp.long_term_years,
            },
            "defaults_used": [
                {"field": k, "source": v}
                for k, v in inp.provenance.items()
                if not v.startswith("user")
            ],
            "price_model": self._price.metadata(),
            "profile_sources": profile_meta,
            "current_estimated_annual_cost_eur": {
                "electricity": round(current_elec_cost, 2),
                "heating": round(current_heat_cost, 2),
                "mobility": round(current_mob_cost, 2),
                "total": round(current_elec_cost + current_heat_cost + current_mob_cost, 2),
            },
            "validation_warnings": val_warns,
            "scenarios": scenarios,
        }

    # ── Monthly forecast ──────────────────────────────────────────────────────

    def _forecast_months(
        self,
        inp: ParsedInput,
        scenario: ScenarioName,
        start_date: date,
        total_months: int,
    ) -> list[MonthlyRecord]:
        elec_units, elec_fixed = self._price.forecast_electricity_prices(
            arbeitspreis=inp.arbeitspreis_eur_per_kwh,
            grundpreis=inp.grundpreis_eur_per_month,
            start_date=start_date,
            months=total_months,
            scenario=scenario,
            contract_end_date=inp.contract_end_date,
        )
        heat_prices = self._price.forecast_heating_prices(
            fuel_type=inp.fuel_type,
            current_price_per_unit=inp.heating_eur_per_unit,
            start_date=start_date,
            months=total_months,
            scenario=scenario,
        )
        petrol_prices = self._price.forecast_petrol_prices(
            current_price=inp.effective_petrol_eur_per_litre,
            start_date=start_date,
            months=total_months,
            scenario=scenario,
        )

        records: list[MonthlyRecord] = []
        for i, (y, m) in enumerate(_iter_months(start_date.year, start_date.month, total_months)):
            elec_kwh = inp.annual_kwh * self._cons.electricity_fraction(y, m)
            heat_val = inp.heating_annual_value * self._cons.heating_fraction(m, inp.postcode)
            mob_km = inp.annual_mileage_km * self._cons.mobility_fraction(m)
            mob_litres = mob_km / 100 * inp.fuel_consumption_l_per_100km

            e_cost = self._calc.electricity_cost(elec_kwh, elec_units[i], elec_fixed[i])
            h_cost = self._calc.heating_cost(heat_val, heat_prices[i])
            m_cost = self._calc.mobility_cost(mob_litres, petrol_prices[i])

            records.append(MonthlyRecord(
                month=f"{y:04d}-{m:02d}",
                electricity_kwh=elec_kwh,
                heating_value=heat_val,
                heating_unit=inp.heating_unit,
                mobility_km=mob_km,
                mobility_fuel_litres=mob_litres,
                electricity_eur_per_kwh=elec_units[i],
                electricity_fixed_eur=elec_fixed[i],
                heating_eur_per_unit=heat_prices[i],
                petrol_eur_per_litre=petrol_prices[i],
                electricity_cost_eur=e_cost,
                heating_cost_eur=h_cost,
                mobility_cost_eur=m_cost,
                total_cost_eur=e_cost + h_cost + m_cost,
            ))
        return records

    # ── Annual aggregation — consecutive 12-month periods ─────────────────────

    @staticmethod
    def _aggregate_periods(
        records: list[MonthlyRecord], years: int
    ) -> list[AnnualRecord]:
        """Aggregate into consecutive 12-month blocks; no months are lost."""
        result: list[AnnualRecord] = []
        for yr_idx in range(years):
            start_i = yr_idx * 12
            end_i = start_i + 12
            block = records[start_i:end_i]
            if not block:
                break
            label_year = int(block[0].month[:4])
            result.append(AnnualRecord(
                year=label_year,
                electricity_kwh=sum(r.electricity_kwh for r in block),
                heating_value=sum(r.heating_value for r in block),
                heating_unit=block[0].heating_unit,
                mobility_fuel_litres=sum(r.mobility_fuel_litres for r in block),
                electricity_cost_eur=sum(r.electricity_cost_eur for r in block),
                heating_cost_eur=sum(r.heating_cost_eur for r in block),
                mobility_cost_eur=sum(r.mobility_cost_eur for r in block),
                total_cost_eur=sum(r.total_cost_eur for r in block),
            ))
        return result

    # ── Serialisation ─────────────────────────────────────────────────────────

    @staticmethod
    def _serialise_monthly(r: MonthlyRecord) -> dict:
        return {
            "month": r.month,
            "consumption": {
                "electricity_kwh": round(r.electricity_kwh, 3),
                "heating_value": round(r.heating_value, 3),
                "heating_unit": r.heating_unit,
                "mobility_km": round(r.mobility_km, 2),
                "mobility_fuel_litres": round(r.mobility_fuel_litres, 3),
            },
            "prices": {
                "electricity_eur_per_kwh": round(r.electricity_eur_per_kwh, 5),
                "electricity_fixed_eur": round(r.electricity_fixed_eur, 4),
                "heating_eur_per_unit": round(r.heating_eur_per_unit, 5),
                "petrol_eur_per_litre": round(r.petrol_eur_per_litre, 4),
            },
            "cost_eur": {
                "electricity": round(r.electricity_cost_eur, 2),
                "heating": round(r.heating_cost_eur, 2),
                "mobility": round(r.mobility_cost_eur, 2),
                "total": round(r.total_cost_eur, 2),
            },
        }

    @staticmethod
    def _serialise_annual(a: AnnualRecord) -> dict:
        return {
            "year": a.year,
            "consumption": {
                "electricity_kwh": round(a.electricity_kwh, 2),
                "heating": round(a.heating_value, 2),
                "heating_unit": a.heating_unit,
                "mobility_fuel_litres": round(a.mobility_fuel_litres, 2),
            },
            "cost_eur": {
                "electricity": round(a.electricity_cost_eur, 2),
                "heating": round(a.heating_cost_eur, 2),
                "mobility": round(a.mobility_cost_eur, 2),
                "total": round(a.total_cost_eur, 2),
            },
        }

    # ── Validation ────────────────────────────────────────────────────────────

    @staticmethod
    def _validate_reconstruction(inp: ParsedInput) -> list[str]:
        warns: list[str] = []
        # Mobility: effective price is derived from reported spend when available.
        # Only warn when no spend was provided (default price used instead).
        if inp.annual_fuel_spend_eur is None:
            warns.append(
                f"No annual_fuel_spend_eur provided; using default petrol price "
                f"{PRICE_CONFIG.default_petrol_eur_per_litre} EUR/litre"
            )

        return warns

    @staticmethod
    def _validate_scenario_ordering(scenarios: dict[str, dict], warns: list[str]) -> None:
        def first_period_total(sc: str) -> float:
            lt = scenarios[sc]["long_term_forecast"]
            return lt[0]["cost_eur"]["total"] if lt else 0.0

        low_t = first_period_total("low")
        cen_t = first_period_total("central")
        high_t = first_period_total("high")
        if not (low_t <= cen_t <= high_t):
            warns.append(
                f"Scenario ordering violated: "
                f"low={low_t:.0f} central={cen_t:.0f} high={high_t:.0f}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────


def run_forecast(input_path: Path, output_path: Path) -> None:
    with input_path.open() as f:
        raw = json.load(f)

    inp = _parse_input(raw)
    orchestrator = ForecastOrchestrator()
    output = orchestrator.run(inp)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    print(f"Wrote {output_path}")
    for w in output.get("validation_warnings", []):
        print(f"  WARNING: {w}")


if __name__ == "__main__":
    run_forecast(
        _REPO_ROOT / "documentation" / "data" / "model_input1.json",
        _REPO_ROOT / "documentation" / "data" / "model_output_forecast.json",
    )
