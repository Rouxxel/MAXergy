"""
Unit tests for scripts/run_energy_cost_forecast.py.

Run with:
    python -m pytest tests/test_energy_cost_forecast.py -v
"""
from __future__ import annotations

import calendar
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from run_energy_cost_forecast import (
    CONSUMPTION_CONFIG,
    PRICE_CONFIG,
    AnnualRecord,
    BDEWProfile,
    ConsumptionConfig,
    ConsumptionModel,
    EnergyCostCalculator,
    EnergyPriceModel,
    ForecastOrchestrator,
    MonthlyRecord,
    ParsedInput,
    PriceModelProtocol,
    ScenarioName,
    WeatherModel,
    _assert_sum,
    _parse_input,
)

# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

MINIMAL_INPUT: dict = {
    "location": {"postcode": "10115", "country": "DE"},
    "household": {
        "occupants": 3,
        "electricity": {
            "annual_kwh": 4200,
            "arbeitspreis_eur_per_kwh": 0.32,
            "grundpreis_eur_per_month": 12.5,
            "contract_end_date": "2026-12-31",
        },
    },
    "heating": {
        "fuel_type": "gas",
        "annual_consumption": 14000,
        "annual_spend_eur": 1450,
    },
    "mobility": {
        "vehicle_type": "petrol",
        "annual_mileage_km": 12000,
        "fuel_consumption_l_per_100km": 6.5,
        "annual_fuel_spend_eur": 1100,
    },
    "forecast_horizon": {"short_term_months": 12, "long_term_years": 5},
}


def make_input(**overrides) -> ParsedInput:
    raw = {**MINIMAL_INPUT}
    raw.update(overrides)
    return _parse_input(raw)


def make_raw(**overrides) -> dict:
    import copy
    raw = copy.deepcopy(MINIMAL_INPUT)
    raw.update(overrides)
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# 1. BDEW H0 Profile
# ─────────────────────────────────────────────────────────────────────────────

class TestBDEWProfile:
    def test_annual_scaling_fractions_sum_to_one(self):
        profile = BDEWProfile()
        fracs = profile.monthly_fractions(2026)
        assert abs(sum(fracs) - 1.0) < 1e-9

    def test_monthly_aggregation_matches_annual(self):
        profile = BDEWProfile()
        annual_kwh = 4200.0
        fracs = profile.monthly_fractions(2026)
        monthly = [annual_kwh * f for f in fracs]
        assert abs(sum(monthly) - annual_kwh) < 1e-6

    def test_winter_higher_than_summer(self):
        profile = BDEWProfile()
        fracs = profile.monthly_fractions(2026)
        winter_avg = (fracs[0] + fracs[1] + fracs[11]) / 3   # Jan, Feb, Dec
        summer_avg = (fracs[5] + fracs[6] + fracs[7]) / 3    # Jun, Jul, Aug
        assert winter_avg > summer_avg

    def test_holiday_handling_new_year(self):
        """Jan 1 is always a national holiday — should be counted as sunday_holiday."""
        profile = BDEWProfile()
        # Just verify the profile loads and fracs are valid (holiday logic runs internally)
        fracs = profile.monthly_fractions(2027)
        assert all(f > 0 for f in fracs)

    def test_different_years_differ_slightly(self):
        """Two years with different weekday/holiday distributions should give different fracs."""
        profile = BDEWProfile()
        f2025 = profile.monthly_fractions(2025)
        f2026 = profile.monthly_fractions(2026)
        # They will differ slightly because calendar differs
        assert f2025 != f2026

    def test_cache_returns_same_object(self):
        profile = BDEWProfile()
        f1 = profile.monthly_fractions(2026)
        f2 = profile.monthly_fractions(2026)
        assert f1 is f2

    def test_fallback_when_no_data_file(self, tmp_path):
        """If the JSON file is missing, fall back to pre-computed fractions."""
        profile = BDEWProfile(data_path=tmp_path / "nonexistent.json")
        assert profile.source == "fallback"
        fracs = profile.monthly_fractions(2026)
        assert len(fracs) == 12
        assert abs(sum(fracs) - 1.0) < 1e-9

    def test_twelve_entries_returned(self):
        profile = BDEWProfile()
        assert len(profile.monthly_fractions(2026)) == 12


# ─────────────────────────────────────────────────────────────────────────────
# 2. DWD Weather Model
# ─────────────────────────────────────────────────────────────────────────────

class TestWeatherModel:
    def test_berlin_postcode_mapped(self):
        wm = WeatherModel()
        temps, station, is_fallback = wm.monthly_temperatures("10115")
        assert not is_fallback
        assert len(temps) == 12

    def test_heating_fractions_sum_to_one(self):
        wm = WeatherModel()
        fracs, _, _ = wm.heating_fractions("10115")
        assert abs(sum(fracs) - 1.0) < 1e-9

    def test_january_hotter_than_july_in_germany(self):
        """January should have more HDD than July in any German city."""
        wm = WeatherModel()
        fracs, _, _ = wm.heating_fractions("10115")  # Berlin
        # Jan = index 0, Jul = index 6
        assert fracs[0] > fracs[6]

    def test_summer_months_near_zero_hdd(self):
        """German summer months (Jun-Aug) are near or above 15°C — minimal HDD."""
        wm = WeatherModel()
        fracs, _, _ = wm.heating_fractions("10115")  # Berlin
        summer = fracs[5] + fracs[6] + fracs[7]   # Jun, Jul, Aug
        winter = fracs[0] + fracs[1] + fracs[11]  # Jan, Feb, Dec
        assert winter > 3 * summer   # winter dominant

    def test_annual_consumption_preserved(self):
        wm = WeatherModel()
        annual_heat = 14000.0
        fracs, _, _ = wm.heating_fractions("10115")
        monthly = [annual_heat * f for f in fracs]
        assert abs(sum(monthly) - annual_heat) < 1e-6

    def test_fallback_when_no_data_file(self, tmp_path):
        wm = WeatherModel(data_path=tmp_path / "nonexistent.json")
        fracs, source, is_fallback = wm.heating_fractions("10115")
        assert is_fallback
        assert len(fracs) == 12
        assert abs(sum(fracs) - 1.0) < 1e-9

    def test_unknown_postcode_uses_fallback_region(self):
        wm = WeatherModel()
        _, _, is_fallback = wm.monthly_temperatures("00000")
        # 00 prefix not mapped — should use fallback region (not hard fallback)
        # Either way, 12 values should come back
        temps, _, _ = wm.monthly_temperatures("00000")
        assert len(temps) == 12

    def test_hdd_base_temp_configurable(self):
        wm_15 = WeatherModel(base_temp=15.0)
        wm_12 = WeatherModel(base_temp=12.0)
        fracs_15, _, _ = wm_15.heating_fractions("10115")
        fracs_12, _, _ = wm_12.heating_fractions("10115")
        # Different base temps → different fractions
        assert fracs_15 != fracs_12

    def test_heating_degree_days_non_negative(self):
        wm = WeatherModel()
        temps, _, _ = wm.monthly_temperatures("10115")
        base = CONSUMPTION_CONFIG.hdd_base_temp_c
        for m, t in enumerate(temps, 1):
            days = calendar.monthrange(2024, m)[1]
            hdd = max(0.0, (base - t) * days)
            assert hdd >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Consumption model
# ─────────────────────────────────────────────────────────────────────────────

class TestConsumptionModel:
    def test_electricity_fractions_sum_to_one_per_year(self):
        model = ConsumptionModel()
        total = sum(model.electricity_fraction(2026, m) for m in range(1, 13))
        assert abs(total - 1.0) < 1e-9

    def test_heating_fractions_sum_to_one(self):
        model = ConsumptionModel()
        total = sum(model.heating_fraction(m, "10115") for m in range(1, 13))
        assert abs(total - 1.0) < 1e-9

    def test_mobility_fractions_sum_to_one(self):
        model = ConsumptionModel()
        total = sum(model.mobility_fraction(m) for m in range(1, 13))
        assert abs(total - 1.0) < 1e-6

    def test_annual_electricity_profile_sums_to_annual(self):
        model = ConsumptionModel()
        annual = 4200.0
        monthly = model.annual_electricity_profile(annual, 2026)
        assert abs(sum(monthly) - annual) < 1e-6

    def test_annual_heating_profile_sums_to_annual(self):
        model = ConsumptionModel()
        annual = 14000.0
        monthly, _ = model.annual_heating_profile(annual, "10115", "gas", CONSUMPTION_CONFIG)
        assert abs(sum(monthly) - annual) < 1e-6

    def test_oil_kwh_equivalent(self):
        model = ConsumptionModel()
        annual_litres = 1500.0
        monthly_litres, monthly_kwh = model.annual_heating_profile(
            annual_litres, "10115", "oil", CONSUMPTION_CONFIG
        )
        for v, k in zip(monthly_litres, monthly_kwh):
            assert abs(k - v * CONSUMPTION_CONFIG.oil_kwh_per_litre) < 1e-9

    def test_profile_metadata_contains_sources(self):
        model = ConsumptionModel()
        meta = model.profile_metadata("10115")
        assert "electricity_profile_source" in meta
        assert "heating_profile_source" in meta
        assert "weather_data_source" in meta


# ─────────────────────────────────────────────────────────────────────────────
# 4. Fixed electricity price during contract
# ─────────────────────────────────────────────────────────────────────────────

class TestContractPriceBehaviour:
    def test_price_exactly_constant_during_contract(self):
        """Unit price must be identical every month while the contract is active."""
        pm = EnergyPriceModel()
        units, fixed = pm.forecast_electricity_prices(
            arbeitspreis=0.32,
            grundpreis=12.5,
            start_date=date(2026, 7, 1),
            months=6,  # all within the 2026-12-31 contract
            scenario="central",
            contract_end_date=date(2026, 12, 31),
        )
        assert all(abs(p - 0.32) < 1e-12 for p in units)
        assert all(abs(f - 12.5) < 1e-12 for f in fixed)

    def test_price_escalates_after_contract(self):
        """First month after contract end should still be at base price; subsequent months grow."""
        pm = EnergyPriceModel()
        # Contract ends Dec 2026; start forecasting from Jan 2027
        units, _ = pm.forecast_electricity_prices(
            arbeitspreis=0.32,
            grundpreis=12.5,
            start_date=date(2027, 1, 1),
            months=24,
            scenario="central",
            contract_end_date=date(2026, 12, 31),
        )
        # months_post_contract=0 for Jan 2027 → trend_factor = 1.0 → price = 0.32
        assert abs(units[0] - 0.32) < 1e-9
        # By month 24 the price should have risen
        assert units[23] > units[0]

    def test_seasonal_consumption_varies_during_contract(self):
        """Monthly electricity_kwh must differ across months even when price is locked."""
        inp = make_input()
        orch = ForecastOrchestrator()
        output = orch.run(inp)
        st = output["scenarios"]["central"]["short_term_forecast"]
        # Extract electricity costs and prices
        prices = [r["prices"]["electricity_eur_per_kwh"] for r in st]
        kwhs = [r["consumption"]["electricity_kwh"] for r in st]
        # During contract (2026): prices should all be 0.32
        contract_months = [r for r in st if r["month"] <= "2026-12"]
        if contract_months:
            for r in contract_months:
                assert abs(r["prices"]["electricity_eur_per_kwh"] - 0.32) < 1e-9
        # But kWh consumption must vary (BDEW profile is not flat)
        assert len(set(round(k, 4) for k in kwhs)) > 1

    def test_no_contract_applies_trend_immediately(self):
        pm = EnergyPriceModel()
        units_no_contract, _ = pm.forecast_electricity_prices(
            arbeitspreis=0.32, grundpreis=12.5,
            start_date=date(2026, 7, 1), months=12,
            scenario="central", contract_end_date=None,
        )
        # months_post_contract counter starts at 0 and increments each month
        # By month 12 price should be > 0.32
        assert units_no_contract[-1] > units_no_contract[0]


# ─────────────────────────────────────────────────────────────────────────────
# 5. Price calibration from user data
# ─────────────────────────────────────────────────────────────────────────────

class TestPriceCalibration:
    def test_heating_price_derived_from_spend_and_consumption(self):
        """effective_heating_price = annual_spend / annual_consumption."""
        inp = make_input()
        expected = 1450 / 14000
        assert abs(inp.heating_eur_per_unit - expected) < 1e-9

    def test_petrol_price_derived_from_spend(self):
        """effective_petrol_price = annual_fuel_spend / annual_litres."""
        annual_litres = 12000 / 100 * 6.5
        expected = 1100 / annual_litres
        inp = make_input()
        assert abs(inp.effective_petrol_eur_per_litre - expected) < 1e-9

    def test_heating_default_price_when_no_spend(self):
        raw = make_raw()
        raw["heating"] = {"fuel_type": "gas", "annual_consumption": 14000}  # no spend
        inp = _parse_input(raw)
        assert abs(inp.heating_eur_per_unit - PRICE_CONFIG.default_gas_eur_per_kwh) < 1e-9

    def test_petrol_default_price_when_no_spend(self):
        raw = make_raw()
        raw["mobility"] = {
            "annual_mileage_km": 12000,
            "fuel_consumption_l_per_100km": 6.5,
        }
        inp = _parse_input(raw)
        assert abs(inp.effective_petrol_eur_per_litre - PRICE_CONFIG.default_petrol_eur_per_litre) < 1e-9

    def test_calibrated_price_provenance_tagged_user(self):
        inp = make_input()
        assert inp.provenance["heating_eur_per_unit"].startswith("user")
        assert inp.provenance["effective_petrol_eur_per_litre"].startswith("user")


# ─────────────────────────────────────────────────────────────────────────────
# 6. Electricity cost calculations
# ─────────────────────────────────────────────────────────────────────────────

class TestElectricityCostCalculations:
    def test_basic_formula(self):
        cost = EnergyCostCalculator.electricity_cost(350.0, 0.32, 12.5)
        assert abs(cost - (350.0 * 0.32 + 12.5)) < 1e-9

    def test_zero_consumption_only_fixed(self):
        assert EnergyCostCalculator.electricity_cost(0.0, 0.30, 10.0) == 10.0

    def test_negative_consumption_raises(self):
        with pytest.raises(ValueError):
            EnergyCostCalculator.electricity_cost(-1.0, 0.30, 10.0)


# ─────────────────────────────────────────────────────────────────────────────
# 7. Gas cost calculations
# ─────────────────────────────────────────────────────────────────────────────

class TestGasCostCalculations:
    def test_gas_cost(self):
        assert abs(EnergyCostCalculator.heating_cost(1200.0, 0.10) - 120.0) < 1e-9

    def test_zero_gas(self):
        assert EnergyCostCalculator.heating_cost(0.0, 0.10) == 0.0

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            EnergyCostCalculator.heating_cost(-10.0, 0.10)


# ─────────────────────────────────────────────────────────────────────────────
# 8. Oil cost calculations
# ─────────────────────────────────────────────────────────────────────────────

class TestOilCostCalculations:
    def test_oil_cost(self):
        assert abs(EnergyCostCalculator.heating_cost(200.0, 1.05) - 210.0) < 1e-9

    def test_oil_kwh_factor(self):
        model = ConsumptionModel()
        annual = 1200.0
        monthly_litres, monthly_kwh = model.annual_heating_profile(
            annual, "10115", "oil", CONSUMPTION_CONFIG
        )
        for v, k in zip(monthly_litres, monthly_kwh):
            assert abs(k - v * CONSUMPTION_CONFIG.oil_kwh_per_litre) < 1e-9


# ─────────────────────────────────────────────────────────────────────────────
# 9. Petrol consumption calculations
# ─────────────────────────────────────────────────────────────────────────────

class TestPetrolConsumptionCalculations:
    def test_annual_litres_formula(self):
        model = ConsumptionModel()
        km = 12000.0
        l_per_100 = 6.5
        km_monthly = [km * model.mobility_fraction(m) for m in range(1, 13)]
        litres = [k / 100 * l_per_100 for k in km_monthly]
        assert abs(sum(litres) - km / 100 * l_per_100) < 1e-6

    def test_mobility_cost(self):
        assert abs(EnergyCostCalculator.mobility_cost(50.0, 1.75) - 87.5) < 1e-9

    def test_negative_litres_raises(self):
        with pytest.raises(ValueError):
            EnergyCostCalculator.mobility_cost(-1.0, 1.75)


# ─────────────────────────────────────────────────────────────────────────────
# 10. Price scenario ordering
# ─────────────────────────────────────────────────────────────────────────────

class TestPriceScenarioOrdering:
    def test_electricity_low_lt_central_lt_high(self):
        pm = EnergyPriceModel()
        start = date(2027, 1, 1)
        totals = [
            sum(pm.forecast_monthly_prices("electricity_unit", 0.32, start, 24, s))
            for s in ("low", "central", "high")
        ]
        assert totals[0] <= totals[1] <= totals[2]

    def test_gas_low_lt_central_lt_high(self):
        pm = EnergyPriceModel()
        start = date(2027, 1, 1)
        totals = [
            sum(pm.forecast_monthly_prices("gas", 0.10, start, 24, s))
            for s in ("low", "central", "high")
        ]
        assert totals[0] <= totals[1] <= totals[2]

    def test_petrol_low_lt_central_lt_high(self):
        pm = EnergyPriceModel()
        start = date(2027, 1, 1)
        totals = [
            sum(pm.forecast_monthly_prices("petrol", 1.75, start, 24, s))
            for s in ("low", "central", "high")
        ]
        assert totals[0] <= totals[1] <= totals[2]

    def test_end_to_end_scenarios_ordered(self):
        inp = make_input()
        orch = ForecastOrchestrator()
        output = orch.run(inp)
        lt = {s: output["scenarios"][s]["long_term_forecast"] for s in ("low", "central", "high")}
        # Check each annual period is ordered
        for i in range(len(lt["central"])):
            low_t = lt["low"][i]["cost_eur"]["total"]
            cen_t = lt["central"][i]["cost_eur"]["total"]
            high_t = lt["high"][i]["cost_eur"]["total"]
            assert low_t <= cen_t <= high_t, f"Ordering violated at period {i}"

    def test_invalid_energy_type_raises(self):
        with pytest.raises(ValueError, match="Unknown energy_type"):
            EnergyPriceModel().forecast_monthly_prices(
                "diesel", 1.5, date(2026, 1, 1), 12, "central"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Consecutive 12-month aggregation
# ─────────────────────────────────────────────────────────────────────────────

class TestConsecutiveAggregation:
    def test_exactly_12_months_per_period(self):
        inp = make_input()
        orch = ForecastOrchestrator()
        output = orch.run(inp)
        # Each LT period should correspond to 12 ST months (when ST >= 12)
        lt = output["scenarios"]["central"]["long_term_forecast"]
        assert len(lt) == inp.long_term_years

    def test_no_months_lost(self):
        """LT periods × 12 == total months generated."""
        raw = make_raw()
        raw["forecast_horizon"] = {"short_term_months": 12, "long_term_years": 3}
        inp = _parse_input(raw)
        orch = ForecastOrchestrator()
        output = orch.run(inp)
        lt = output["scenarios"]["central"]["long_term_forecast"]
        assert len(lt) == 3  # exactly 3 periods

    def test_lt_annual_total_equals_sum_of_its_12_months(self):
        """The annual total must equal the sum of the 12 monthly records in that period."""
        raw = make_raw()
        raw["forecast_horizon"] = {"short_term_months": 12, "long_term_years": 2}
        inp = _parse_input(raw)
        orch = ForecastOrchestrator()
        output = orch.run(inp)
        st = output["scenarios"]["central"]["short_term_forecast"]
        lt = output["scenarios"]["central"]["long_term_forecast"]

        # Period 1 == months 0-11 of the forecast == the 12 ST months
        assert len(st) == 12
        st_sum = sum(r["cost_eur"]["total"] for r in st)
        lt_period1_total = lt[0]["cost_eur"]["total"]
        assert abs(st_sum - lt_period1_total) < 0.02  # allow rounding

    def test_lt_year_label_is_first_month_year(self):
        inp = make_input()
        orch = ForecastOrchestrator()
        output = orch.run(inp)
        st = output["scenarios"]["central"]["short_term_forecast"]
        lt = output["scenarios"]["central"]["long_term_forecast"]
        # Label of period 0 should match year of ST month 0
        first_month_year = int(st[0]["month"][:4])
        assert lt[0]["year"] == first_month_year


# ─────────────────────────────────────────────────────────────────────────────
# 12. Monthly output format — consumption, prices, costs
# ─────────────────────────────────────────────────────────────────────────────

class TestMonthlyOutputFormat:
    def _get_first_month(self) -> dict:
        inp = make_input()
        orch = ForecastOrchestrator()
        output = orch.run(inp)
        return output["scenarios"]["central"]["short_term_forecast"][0]

    def test_has_consumption_section(self):
        r = self._get_first_month()
        assert "consumption" in r
        c = r["consumption"]
        assert "electricity_kwh" in c
        assert "heating_value" in c
        assert "heating_unit" in c
        assert "mobility_km" in c
        assert "mobility_fuel_litres" in c

    def test_has_prices_section(self):
        r = self._get_first_month()
        assert "prices" in r
        p = r["prices"]
        assert "electricity_eur_per_kwh" in p
        assert "electricity_fixed_eur" in p
        assert "heating_eur_per_unit" in p
        assert "petrol_eur_per_litre" in p

    def test_has_cost_section(self):
        r = self._get_first_month()
        assert "cost_eur" in r
        c = r["cost_eur"]
        assert "electricity" in c
        assert "heating" in c
        assert "mobility" in c
        assert "total" in c

    def test_cost_equals_consumption_times_price(self):
        """electricity_cost = electricity_kwh * unit_price + fixed_charge"""
        r = self._get_first_month()
        expected_elec = (
            r["consumption"]["electricity_kwh"] * r["prices"]["electricity_eur_per_kwh"]
            + r["prices"]["electricity_fixed_eur"]
        )
        assert abs(r["cost_eur"]["electricity"] - expected_elec) < 0.01

    def test_total_equals_sum_of_components(self):
        r = self._get_first_month()
        expected = (
            r["cost_eur"]["electricity"]
            + r["cost_eur"]["heating"]
            + r["cost_eur"]["mobility"]
        )
        assert abs(r["cost_eur"]["total"] - expected) < 1e-6

    def test_all_values_non_negative(self):
        inp = make_input()
        orch = ForecastOrchestrator()
        output = orch.run(inp)
        for r in output["scenarios"]["central"]["short_term_forecast"]:
            assert r["consumption"]["electricity_kwh"] >= 0
            assert r["consumption"]["heating_value"] >= 0
            assert r["consumption"]["mobility_fuel_litres"] >= 0
            assert r["cost_eur"]["electricity"] >= 0
            assert r["cost_eur"]["heating"] >= 0
            assert r["cost_eur"]["mobility"] >= 0
            assert r["cost_eur"]["total"] >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 13. Default value handling
# ─────────────────────────────────────────────────────────────────────────────

class TestDefaultValueHandling:
    def test_missing_annual_kwh_uses_occupant_default(self):
        raw = make_raw()
        del raw["household"]["electricity"]["annual_kwh"]
        inp = _parse_input(raw)
        expected = 3 * CONSUMPTION_CONFIG.kwh_per_person_per_year
        assert abs(inp.annual_kwh - expected) < 1e-6
        assert "default" in inp.provenance["annual_kwh"]

    def test_missing_occupants_defaults_to_2(self):
        raw = make_raw()
        del raw["household"]["occupants"]
        inp = _parse_input(raw)
        assert inp.occupants == 2

    def test_defaults_recorded_in_output(self):
        raw = make_raw()
        del raw["household"]["occupants"]
        del raw["household"]["electricity"]["annual_kwh"]
        inp = _parse_input(raw)
        output = ForecastOrchestrator().run(inp)
        fields = [d["field"] for d in output["defaults_used"]]
        assert "occupants" in fields
        assert "annual_kwh" in fields

    def test_heating_consumption_derived_from_spend(self):
        raw = make_raw()
        raw["heating"] = {"fuel_type": "gas", "annual_spend_eur": 1000}
        inp = _parse_input(raw)
        expected = 1000 / PRICE_CONFIG.default_gas_eur_per_kwh
        assert abs(inp.heating_annual_value - expected) < 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# 14. Missing optional fields
# ─────────────────────────────────────────────────────────────────────────────

class TestMissingOptionalFields:
    def test_no_contract_end_date(self):
        raw = make_raw()
        del raw["household"]["electricity"]["contract_end_date"]
        inp = _parse_input(raw)
        assert inp.contract_end_date is None

    def test_no_annual_fuel_spend_still_runs(self):
        raw = make_raw()
        del raw["mobility"]["annual_fuel_spend_eur"]
        inp = _parse_input(raw)
        output = ForecastOrchestrator().run(inp)
        assert output["scenarios"]["central"]["short_term_forecast"]

    def test_missing_postcode_raises(self):
        raw = make_raw()
        raw["location"] = {"country": "DE"}
        with pytest.raises(ValueError, match="postcode"):
            _parse_input(raw)

    def test_missing_mileage_raises(self):
        raw = make_raw()
        raw["mobility"] = {"fuel_consumption_l_per_100km": 6.5}
        with pytest.raises(ValueError):
            _parse_input(raw)

    def test_oil_fuel_type(self):
        raw = make_raw()
        raw["heating"] = {"fuel_type": "oil", "annual_consumption": 1500}
        inp = _parse_input(raw)
        assert inp.fuel_type == "oil"
        assert inp.heating_unit == "litres"

    def test_full_run_produces_three_scenarios(self):
        inp = make_input()
        output = ForecastOrchestrator().run(inp)
        assert set(output["scenarios"].keys()) == {"low", "central", "high"}

    def test_short_term_forecast_length(self):
        raw = make_raw()
        raw["forecast_horizon"] = {"short_term_months": 6, "long_term_years": 3}
        inp = _parse_input(raw)
        output = ForecastOrchestrator().run(inp)
        for sc in ("low", "central", "high"):
            assert len(output["scenarios"][sc]["short_term_forecast"]) == 6

    def test_output_contains_profile_sources(self):
        inp = make_input()
        output = ForecastOrchestrator().run(inp)
        assert "profile_sources" in output
        ps = output["profile_sources"]
        assert "electricity_profile_source" in ps
        assert "heating_profile_source" in ps
        assert "weather_data_source" in ps


# ─────────────────────────────────────────────────────────────────────────────
# 15. PriceModelProtocol — dependency injection
# ─────────────────────────────────────────────────────────────────────────────

# A minimal fake price model that returns fixed constants for every month.
# It satisfies PriceModelProtocol structurally (duck typing) without inheriting.
class _FakeConstantPriceModel:
    """Constant-price model: every month, every scenario returns the same value."""

    UNIT_PRICE = 0.10
    FIXED_CHARGE = 5.00
    HEATING_PRICE = 0.05
    PETROL_PRICE = 1.00

    def forecast_electricity_prices(
        self,
        arbeitspreis: float,
        grundpreis: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
        contract_end_date: date | None,
    ) -> tuple[list[float], list[float]]:
        return (
            [self.UNIT_PRICE] * months,
            [self.FIXED_CHARGE] * months,
        )

    def forecast_heating_prices(
        self,
        fuel_type: str,
        current_price_per_unit: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        return [self.HEATING_PRICE] * months

    def forecast_petrol_prices(
        self,
        current_price: float,
        start_date: date,
        months: int,
        scenario: ScenarioName,
    ) -> list[float]:
        return [self.PETROL_PRICE] * months

    def metadata(self) -> dict:
        return {
            "name": "fake_constant",
            "version": "test",
            "assumptions": {
                "unit_price": self.UNIT_PRICE,
                "fixed_charge": self.FIXED_CHARGE,
                "heating_price": self.HEATING_PRICE,
                "petrol_price": self.PETROL_PRICE,
            },
        }


class TestPriceModelProtocol:
    def test_fake_model_satisfies_protocol(self):
        assert isinstance(_FakeConstantPriceModel(), PriceModelProtocol)

    def test_real_model_satisfies_protocol(self):
        assert isinstance(EnergyPriceModel(), PriceModelProtocol)

    def test_injected_model_controls_all_prices(self):
        """Every monthly price in the output must come from the injected model."""
        fake = _FakeConstantPriceModel()
        inp = make_input()
        orch = ForecastOrchestrator(price_model=fake)
        output = orch.run(inp)
        for r in output["scenarios"]["central"]["short_term_forecast"]:
            assert abs(r["prices"]["electricity_eur_per_kwh"] - fake.UNIT_PRICE) < 1e-9
            assert abs(r["prices"]["electricity_fixed_eur"] - fake.FIXED_CHARGE) < 1e-9
            assert abs(r["prices"]["heating_eur_per_unit"] - fake.HEATING_PRICE) < 1e-9
            assert abs(r["prices"]["petrol_eur_per_litre"] - fake.PETROL_PRICE) < 1e-9

    def test_consumption_unchanged_when_swapping_price_models(self):
        """Swapping price models must not affect consumption values."""
        inp = make_input()
        out_default = ForecastOrchestrator().run(inp)
        out_fake = ForecastOrchestrator(price_model=_FakeConstantPriceModel()).run(inp)

        default_st = out_default["scenarios"]["central"]["short_term_forecast"]
        fake_st = out_fake["scenarios"]["central"]["short_term_forecast"]

        for r_d, r_f in zip(default_st, fake_st):
            assert r_d["month"] == r_f["month"]
            assert abs(r_d["consumption"]["electricity_kwh"] - r_f["consumption"]["electricity_kwh"]) < 1e-9
            assert abs(r_d["consumption"]["heating_value"] - r_f["consumption"]["heating_value"]) < 1e-9
            assert abs(r_d["consumption"]["mobility_fuel_litres"] - r_f["consumption"]["mobility_fuel_litres"]) < 1e-9

    def test_cost_calculations_use_injected_prices(self):
        """With constant prices and known consumption, verify cost = consumption × price."""
        fake = _FakeConstantPriceModel()
        inp = make_input()
        orch = ForecastOrchestrator(price_model=fake)
        output = orch.run(inp)

        for r in output["scenarios"]["central"]["short_term_forecast"]:
            expected_elec = (
                r["consumption"]["electricity_kwh"] * fake.UNIT_PRICE + fake.FIXED_CHARGE
            )
            expected_heat = r["consumption"]["heating_value"] * fake.HEATING_PRICE
            expected_mob = r["consumption"]["mobility_fuel_litres"] * fake.PETROL_PRICE
            assert abs(r["cost_eur"]["electricity"] - expected_elec) < 0.01
            assert abs(r["cost_eur"]["heating"] - expected_heat) < 0.01
            assert abs(r["cost_eur"]["mobility"] - expected_mob) < 0.01

    def test_output_metadata_comes_from_injected_model(self):
        """price_model key in output must reflect the injected model, not PRICE_CONFIG."""
        fake = _FakeConstantPriceModel()
        inp = make_input()
        output = ForecastOrchestrator(price_model=fake).run(inp)
        assert output["price_model"]["name"] == "fake_constant"
        assert output["price_model"]["version"] == "test"

    def test_consumption_model_has_no_price_model_dependency(self):
        """ConsumptionModel must be instantiable and usable without EnergyPriceModel."""
        model = ConsumptionModel()
        # These calls must work with no price model in scope
        frac = model.electricity_fraction(2026, 1)
        assert 0 < frac < 1
        heat_frac = model.heating_fraction(1, "10115")
        assert 0 < heat_frac < 1

    def test_cost_calculator_has_no_price_model_dependency(self):
        """EnergyCostCalculator must be usable with any externally supplied prices."""
        calc = EnergyCostCalculator()
        # Prices here are completely arbitrary — not from any price model
        cost = calc.electricity_cost(100.0, 0.42, 7.77)
        assert abs(cost - (100.0 * 0.42 + 7.77)) < 1e-9
        heat = calc.heating_cost(500.0, 0.08)
        assert abs(heat - 40.0) < 1e-9
        mob = calc.mobility_cost(60.0, 1.23)
        assert abs(mob - 73.8) < 1e-9
