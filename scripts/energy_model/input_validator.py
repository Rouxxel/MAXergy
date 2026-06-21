"""Input validation and normalisation for the production pipeline.

ParsedInput is the validated, normalised view of raw JSON input.
validate_and_parse() applies German defaults, records provenance, and
raises ValueError on any invalid input.

EnergyCostCalculator contains only arithmetic — no forecasting logic.
_iter_months() is a utility month generator shared across the package.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from energy_model.price_models import PRICE_CONFIG
from energy_model.consumption import CONSUMPTION_CONFIG


def _iter_months(start_year: int, start_month: int, count: int):
    y, m = start_year, start_month
    for _ in range(count):
        yield y, m
        m += 1
        if m > 12:
            m, y = 1, y + 1


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
    heating_eur_per_unit: float
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


def validate_and_parse(raw: dict) -> ParsedInput:
    """Validate and normalise raw JSON input, applying German defaults where needed.

    Raises ValueError for any missing required field or invalid value.
    Records provenance for every field so the caller can report defaults used.
    """
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
        if annual_kwh < 0:
            raise ValueError(
                f"household.electricity.annual_kwh must be non-negative, got {annual_kwh}"
            )
        prov["annual_kwh"] = "user"
    else:
        annual_kwh = occupants * cfg.kwh_per_person_per_year
        prov["annual_kwh"] = f"default:{cfg.kwh_per_person_per_year} kWh/person/yr"
        warns.append(f"annual_kwh estimated from occupants: {annual_kwh:.0f} kWh")

    arb_raw = elec.get("arbeitspreis_eur_per_kwh")
    if arb_raw is not None:
        arb = float(arb_raw)
        if arb < 0:
            raise ValueError(
                f"household.electricity.arbeitspreis_eur_per_kwh must be non-negative, got {arb}"
            )
        prov["arbeitspreis_eur_per_kwh"] = "user"
    else:
        arb = pcfg.default_electricity_arbeitspreis_eur_per_kwh
        prov["arbeitspreis_eur_per_kwh"] = f"default:{arb} EUR/kWh"
        warns.append(f"arbeitspreis not provided; using default {arb} EUR/kWh")

    gp_raw = elec.get("grundpreis_eur_per_month")
    if gp_raw is not None:
        gp = float(gp_raw)
        if gp < 0:
            raise ValueError(
                f"household.electricity.grundpreis_eur_per_month must be non-negative, got {gp}"
            )
        prov["grundpreis_eur_per_month"] = "user"
    else:
        gp = pcfg.default_electricity_grundpreis_eur_per_month
        prov["grundpreis_eur_per_month"] = f"default:{gp} EUR/month"

    ced_raw = elec.get("contract_end_date")
    if ced_raw is not None:
        try:
            ced: date | None = date.fromisoformat(str(ced_raw))
        except (ValueError, TypeError):
            raise ValueError(
                f"household.electricity.contract_end_date is not a valid ISO date: {ced_raw!r}"
            )
    else:
        ced = None
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
        if heating_annual_value < 0:
            raise ValueError(
                f"heating.annual_consumption must be non-negative, got {heating_annual_value}"
            )
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
    _SUPPORTED_VEHICLE_TYPES = ("petrol", "diesel", "electric", "phev", "hybrid")
    mob = raw.get("mobility", {})
    vehicle_type_raw = mob.get("vehicle_type", "petrol")
    vehicle_type = str(vehicle_type_raw).lower()
    if vehicle_type not in _SUPPORTED_VEHICLE_TYPES:
        raise ValueError(
            f"mobility.vehicle_type '{vehicle_type_raw}' is not supported; "
            f"must be one of {_SUPPORTED_VEHICLE_TYPES}"
        )

    mileage_raw = mob.get("annual_mileage_km")
    fuel_cons_raw = mob.get("fuel_consumption_l_per_100km")
    if mileage_raw is None or fuel_cons_raw is None:
        raise ValueError(
            "mobility section must contain annual_mileage_km and fuel_consumption_l_per_100km"
        )
    annual_mileage_km = float(mileage_raw)
    if annual_mileage_km < 0:
        raise ValueError(
            f"mobility.annual_mileage_km must be non-negative, got {annual_mileage_km}"
        )
    fuel_cons = float(fuel_cons_raw)
    if fuel_cons < 0:
        raise ValueError(
            f"mobility.fuel_consumption_l_per_100km must be non-negative, got {fuel_cons}"
        )
    prov["annual_mileage_km"] = "user"
    prov["fuel_consumption_l_per_100km"] = "user"

    mob_spend_raw = mob.get("annual_fuel_spend_eur")
    annual_fuel_spend_eur = float(mob_spend_raw) if mob_spend_raw is not None else None

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
    if st_months < 1:
        raise ValueError(
            f"forecast_horizon.short_term_months must be >= 1, got {st_months}"
        )
    if lt_years < 1:
        raise ValueError(
            f"forecast_horizon.long_term_years must be >= 1, got {lt_years}"
        )

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
