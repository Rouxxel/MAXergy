"""
Engine default assumptions, exposed by GET /assumptions.

Read directly from the production engine's configuration objects so no other component
(frontends, MCP suggestion tools) hard-codes its own values.
"""

from src.services.forecasting.engine import (
    BatteryAssumptions,
    CONSUMPTION_CONFIG,
    EVAssumptions,
    FinancingInput,
    HeatPumpAssumptions,
    InvestmentCostDefaults,
    PRICE_CONFIG,
    SolarAssumptions,
)


def get_assumptions() -> dict:
    """Return the engine defaults as a JSON-serialisable dict."""
    solar, battery, hp, ev = SolarAssumptions(), BatteryAssumptions(), HeatPumpAssumptions(), EVAssumptions()
    capex, financing = InvestmentCostDefaults(), FinancingInput()
    return {
        "tariff": {
            "arbeitspreis_eur_per_kwh": PRICE_CONFIG.default_electricity_arbeitspreis_eur_per_kwh,
            "grundpreis_eur_per_month": PRICE_CONFIG.default_electricity_grundpreis_eur_per_month,
            "gas_eur_per_kwh": PRICE_CONFIG.default_gas_eur_per_kwh,
            "oil_eur_per_litre": PRICE_CONFIG.default_oil_eur_per_litre,
            "petrol_eur_per_litre": PRICE_CONFIG.default_petrol_eur_per_litre,
        },
        "consumption": {
            "electricity_kwh_per_person_per_year": CONSUMPTION_CONFIG.kwh_per_person_per_year,
            "oil_kwh_per_litre": CONSUMPTION_CONFIG.oil_kwh_per_litre,
        },
        "solar": {
            "m2_per_kwp": solar.m2_per_kwp,
            "regional_yield_kwh_per_kwp": dict(solar.regional_yield_kwh_per_kwp),
            "default_yield_kwh_per_kwp": solar.default_yield_kwh_per_kwp,
            "annual_degradation_pct": solar.annual_degradation_pct,
            "feed_in_tariff_eur_per_kwh": {
                "up_to_10_kwp": solar.feed_in_tariff_small_eur_per_kwh,
                "10_to_40_kwp": solar.feed_in_tariff_medium_eur_per_kwh,
                "above_40_kwp": solar.feed_in_tariff_large_eur_per_kwh,
            },
        },
        "battery": {
            "default_usable_kwh": battery.default_usable_kwh,
            "round_trip_efficiency": round(battery.charge_efficiency * battery.discharge_efficiency, 4),
        },
        "heat_pump": {
            "scop": hp.heat_pump_scop,
            "existing_heating_efficiency": hp.existing_heating_efficiency,
        },
        "ev": {
            "kwh_per_100km": ev.kwh_per_100km,
            "charging_efficiency": ev.charging_efficiency,
            "home_charging_share": ev.home_charging_share,
        },
        "investment_costs": {
            "pv_eur_per_kwp": capex.pv_eur_per_kwp,
            "battery_eur_per_kwh": capex.battery_eur_per_kwh,
            "heat_pump_eur_fixed": capex.heat_pump_eur_fixed,
            "ev_charger_eur_fixed": capex.ev_charger_eur_fixed,
        },
        "financing": {
            "loan_term_years": financing.loan_term_years,
            "loan_rate_pct": financing.annual_rate_pct,
        },
        "long_term_price_growth": {
            "electricity": dict(PRICE_CONFIG.electricity_annual_trend),
            "gas": dict(PRICE_CONFIG.gas_annual_trend),
            "oil": dict(PRICE_CONFIG.oil_annual_trend),
            "petrol": dict(PRICE_CONFIG.petrol_annual_trend),
            "fixed_charge": dict(PRICE_CONFIG.fixed_charge_annual_trend),
        },
        "supported": {
            "country": ["DE"],
            "heating_fuels": ["gas", "oil"],
            "vehicle_types": ["petrol", "diesel", "electric", "phev", "hybrid"],
            "building_types": ["residential"],
        },
    }
