"""Consumption distribution models: BDEW H0 electricity + DWD HDD heating.

No price or cost logic.  Extracted from run_energy_cost_forecast.py.
"""

from __future__ import annotations

import calendar
import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

_ENERGY_MODEL_DIR = Path(__file__).parent
_SCRIPTS_DIR = _ENERGY_MODEL_DIR.parent
_REPO_ROOT = _SCRIPTS_DIR.parent
_DATA_DIR = _REPO_ROOT / "data"
_BDEW_PATH = _DATA_DIR / "bdew_h0_profile.json"
_DWD_PATH = _DATA_DIR / "dwd_climate_normals.json"


@dataclass(frozen=True)
class ConsumptionConfig:
    # German average kWh/person/year (Bundesnetzagentur Monitoring 2023)
    kwh_per_person_per_year: float = 1500.0

    # Monthly mobility weights Jan–Dec (uniform by default)
    mobility_monthly_weights: tuple[float, ...] = (
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
        1.0, 1.0, 1.0, 1.0, 1.0, 1.0,
    )

    # Heating oil energy content (kWh per litre) — standard value
    oil_kwh_per_litre: float = 10.0

    # Heating base temperature for degree-day calculation (°C) — German Gradtagszahl standard
    hdd_base_temp_c: float = 15.0

    # Fallback heating weights used when DWD data is unavailable
    fallback_heating_monthly_weights: tuple[float, ...] = (
        1.40, 1.30, 1.10, 0.90, 0.70, 0.60,
        0.60, 0.60, 0.80, 1.00, 1.20, 1.40,
    )


CONSUMPTION_CONFIG = ConsumptionConfig()


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
        ref_year = 2024
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
        self._heat_cache: dict[str, tuple[float, ...]] = {}

    def electricity_fraction(self, year: int, month: int) -> float:
        fracs = self._bdew.monthly_fractions(year)
        return fracs[month - 1]

    def heating_fraction(self, month: int, postcode: str) -> float:
        if postcode not in self._heat_cache:
            fracs, _, _ = self._weather.heating_fractions(postcode)
            self._heat_cache[postcode] = fracs
        return self._heat_cache[postcode][month - 1]

    @staticmethod
    def mobility_fraction(month: int) -> float:
        return 1.0 / 12

    def profile_metadata(self, postcode: str) -> dict:
        _, heat_station, heat_is_fallback = self._weather.monthly_temperatures(postcode)
        return {
            "electricity_profile_source": f"BDEW H0 ({self._bdew.source})",
            "heating_profile_source": f"DWD HDD from {heat_station}",
            "heating_profile_is_fallback": heat_is_fallback,
            "weather_data_source": heat_station,
            "weather_data_cached": False,
        }

    def annual_electricity_profile(self, annual_kwh: float, year: int) -> list[float]:
        fracs = self._bdew.monthly_fractions(year)
        values = [annual_kwh * f for f in fracs]
        _assert_sum(values, annual_kwh, "electricity")
        return values

    def annual_heating_profile(
        self, annual_value: float, postcode: str, fuel_type: str, cfg: ConsumptionConfig
    ) -> tuple[list[float], list[float]]:
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
