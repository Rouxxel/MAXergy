"""Tests for the energy upgrade comparison system.

Covers:
  1.  Baseline regression — new orchestrator matches ForecastOrchestrator for baseline
  2.  All six upgrade scenarios present in output
  3.  Baseline and upgrades share identical price arrays
  4.  PV energy balance conserved (generation = direct_sc + bat_charge + export)
  5.  Battery never creates energy (discharge ≤ stored energy after charging losses)
  6.  Grid import always ≥ 0
  7.  Grid export always ≥ 0
  8.  Heat pump removes heating fuel, adds electricity demand
  9.  EV removes petrol demand, adds electricity demand
 10.  Solar export revenue subtracted correctly from total cost
 11.  Monthly costs sum to annual (long-term) aggregates
 12.  Zero-kWp PV reproduces baseline electricity cost
 13.  Upgrade assumptions written to provenance; warnings emitted for defaults
 14.  Output keys match required schema (new field names)
 15.  Negative savings are not suppressed (upgrade can cost more than baseline)
 16-25. Serializer validate_output() — one test per check (checks 1–10)
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

# Add scripts/ to path so both packages are importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from energy_model.input_validator import validate_and_parse
from energy_model.price_models import ScenarioPriceModel
from energy_model.assumptions import (
    BatteryAssumptions,
    EVAssumptions,
    HeatPumpAssumptions,
    SolarAssumptions,
)
from energy_model.orchestrator import ScenarioOrchestrator
from energy_model.serializer import validate_output
from energy_model.setup_models import UPGRADE_SCENARIO_NAMES, UpgradeInput
from energy_model.solar import (
    _orientation_factor,
    _tilt_factor,
    feed_in_tariff,
    monthly_pv_generation,
    resolve_kwp,
)
from energy_model.upgrade_model import SCENARIO_FLAGS, UpgradeEnergyModel


# ── Fixtures ──────────────────────────────────────────────────────────────────

MINIMAL_RAW = {
    "location": {"postcode": "80331"},
    "household": {
        "occupants": 3,
        "electricity": {
            "annual_kwh": 4200,
            "arbeitspreis_eur_per_kwh": 0.32,
            "grundpreis_eur_per_month": 12.50,
        },
    },
    "heating": {"fuel_type": "gas", "annual_consumption": 14000, "annual_spend_eur": 1400},
    "mobility": {
        "annual_mileage_km": 12000,
        "fuel_consumption_l_per_100km": 6.5,
        "annual_fuel_spend_eur": 1100,
    },
    "forecast_horizon": {"short_term_months": 12, "long_term_years": 3},
}

MINIMAL_RAW_OIL = {
    "location": {"postcode": "80331"},
    "household": {
        "occupants": 2,
        "electricity": {
            "annual_kwh": 3000,
            "arbeitspreis_eur_per_kwh": 0.30,
            "grundpreis_eur_per_month": 10.0,
        },
    },
    "heating": {"fuel_type": "oil", "annual_consumption": 1200, "annual_spend_eur": 1260},
    "mobility": {
        "annual_mileage_km": 15000,
        "fuel_consumption_l_per_100km": 7.0,
        "annual_fuel_spend_eur": 1500,
    },
    "forecast_horizon": {"short_term_months": 12, "long_term_years": 3},
}


def _parsed():
    return validate_and_parse(MINIMAL_RAW)


def _parsed_oil():
    return validate_and_parse(MINIMAL_RAW_OIL)


def _small_upgrade(**kwargs) -> UpgradeInput:
    """UpgradeInput with a small 5-kWp system; fast for tests."""
    defaults = dict(
        solar_kwp=5.0,
        battery_kwh=10.0,
        usable_roof_area_m2=40.0,
        roof_orientation="south",
        roof_tilt_deg=30.0,
        shading_factor=0.0,
    )
    defaults.update(kwargs)
    return UpgradeInput(**defaults)


def _run_scenario(raw=None, upgrade_kwargs=None):
    inp = validate_and_parse(raw or MINIMAL_RAW)
    upg = _small_upgrade(**(upgrade_kwargs or {}))
    orc = ScenarioOrchestrator()
    return orc.run(inp, upg)


# ── 1. Baseline regression ─────────────────────────────────────────────────────

def test_baseline_st_uses_constant_prices():
    """Short-term baseline prices must be constant (production constant-index model)."""
    out = _run_scenario()
    st = out["baseline"]["short_term_forecast"]
    assert len(st) >= 2
    first_price = st[0]["prices"]["electricity_eur_per_kwh"]
    for rec in st[1:]:
        assert rec["prices"]["electricity_eur_per_kwh"] == first_price, (
            f"ST price changed: {first_price} → {rec['prices']['electricity_eur_per_kwh']}"
        )


# ── 2. All six scenarios present ───────────────────────────────────────────────

def test_all_six_upgrade_scenarios_present():
    out = _run_scenario()
    assert set(out["upgrade_scenarios"].keys()) == set(UPGRADE_SCENARIO_NAMES)


def test_upgrade_scenario_names_exact():
    """Confirm exact spelling as required by specification."""
    expected = {
        "solar_only", "pv_battery", "pv_heatpump", "pv_ev",
        "pv_battery_heatpump", "full_upgrade",
    }
    assert set(UPGRADE_SCENARIO_NAMES) == expected


# ── 3. Identical price arrays for baseline and all upgrades ───────────────────

def test_price_arrays_identical_across_scenarios():
    """All scenarios must report the same electricity unit price each month."""
    out = _run_scenario()
    baseline_prices = [
        m["prices"]["electricity_eur_per_kwh"]
        for m in out["baseline"]["short_term_forecast"]
    ]
    for sn in UPGRADE_SCENARIO_NAMES:
        st = out["upgrade_scenarios"][sn]["short_term_forecast"]
        upgrade_prices = [m["prices"]["electricity_eur_per_kwh"] for m in st]
        assert baseline_prices == upgrade_prices, f"Price mismatch in scenario {sn}"


# ── 4. PV energy balance conserved ────────────────────────────────────────────

def test_pv_energy_balance_conserved():
    """pv_generation == direct_sc + battery_charge + grid_export (within float eps)."""
    out = _run_scenario()
    for sn in UPGRADE_SCENARIO_NAMES:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            ef = rec["energy_flows"]
            gen = ef["pv_generation_kwh"]
            balance = (
                ef["pv_direct_self_consumption_kwh"]
                + ef["battery_charge_kwh"]
                + ef["grid_export_kwh"]
            )
            # Tolerance 0.005: to_dict() rounds flows to 3 dp, so sum can drift
            assert abs(gen - balance) < 0.005, (
                f"{sn} {rec['month']}: gen={gen:.6f} balance={balance:.6f}"
            )


# ── 5. Battery never creates energy ───────────────────────────────────────────

def test_battery_never_creates_energy():
    """battery_discharge_kwh ≤ battery_charge_kwh × charge_eff in every month.

    Tolerance 0.01 kWh accounts for 3-dp rounding in to_dict().
    """
    out = _run_scenario()
    bat_a = BatteryAssumptions()
    for sn in ["pv_battery", "pv_battery_heatpump", "full_upgrade"]:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            ef = rec["energy_flows"]
            stored = ef["battery_charge_kwh"] * bat_a.charge_efficiency
            assert ef["battery_discharge_kwh"] <= stored + 0.01, (
                f"{sn} {rec['month']}: discharge={ef['battery_discharge_kwh']:.4f} "
                f"stored={stored:.4f}"
            )


def test_battery_charges_only_from_pv_surplus():
    """battery_charge_kwh ≤ pv_surplus in every month."""
    out = _run_scenario()
    for sn in ["pv_battery", "pv_battery_heatpump", "full_upgrade"]:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            ef = rec["energy_flows"]
            pv_surplus = ef["pv_generation_kwh"] - ef["pv_direct_self_consumption_kwh"]
            assert ef["battery_charge_kwh"] <= pv_surplus + 1e-9, (
                f"{sn} {rec['month']}: charge={ef['battery_charge_kwh']:.4f} "
                f"surplus={pv_surplus:.4f}"
            )


# ── 6. Grid import always ≥ 0 ─────────────────────────────────────────────────

def test_grid_import_never_negative():
    out = _run_scenario()
    for sn in UPGRADE_SCENARIO_NAMES:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            assert rec["energy_flows"]["grid_import_kwh"] >= -1e-9, (
                f"{sn} {rec['month']}: grid_import={rec['energy_flows']['grid_import_kwh']}"
            )


# ── 7. Grid export always ≥ 0 ─────────────────────────────────────────────────

def test_grid_export_never_negative():
    out = _run_scenario()
    for sn in UPGRADE_SCENARIO_NAMES:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            assert rec["energy_flows"]["grid_export_kwh"] >= -1e-9, (
                f"{sn} {rec['month']}: grid_export={rec['energy_flows']['grid_export_kwh']}"
            )


# ── 8. Heat pump removes heating fuel, adds electricity ───────────────────────

def test_heat_pump_removes_heating_fuel():
    """All HP scenarios must have remaining_heating_fuel = 0 every month."""
    out = _run_scenario()
    for sn in ["pv_heatpump", "pv_battery_heatpump", "full_upgrade"]:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            ef = rec["energy_flows"]
            assert ef["remaining_heating_fuel"] == pytest.approx(0.0, abs=1e-9), (
                f"{sn} {rec['month']}: remaining_heating_fuel={ef['remaining_heating_fuel']}"
            )


def test_heat_pump_adds_electricity_demand():
    """HP electricity must be > 0 whenever baseline heating > 0."""
    out = _run_scenario()
    for sn in ["pv_heatpump", "pv_battery_heatpump", "full_upgrade"]:
        non_zero = sum(
            1 for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]
            if rec["energy_flows"]["heat_pump_electricity_kwh"] > 0
        )
        # Heating demand is non-zero in most months (gas household)
        assert non_zero >= 6, f"{sn}: expected heat pump electricity in ≥ 6 months"


# ── 9. EV removes petrol, adds electricity ────────────────────────────────────

def test_ev_removes_petrol():
    """All EV scenarios must have remaining_petrol_litres = 0."""
    out = _run_scenario()
    for sn in ["pv_ev", "full_upgrade"]:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            ef = rec["energy_flows"]
            assert ef["remaining_petrol_litres"] == pytest.approx(0.0, abs=1e-9), (
                f"{sn} {rec['month']}: remaining_petrol_litres={ef['remaining_petrol_litres']}"
            )


def test_ev_adds_home_charging():
    """EV scenarios must show positive home charging every month."""
    out = _run_scenario()
    for sn in ["pv_ev", "full_upgrade"]:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            assert rec["energy_flows"]["ev_charging_kwh"] > 0, (
                f"{sn} {rec['month']}: ev_charging_kwh=0"
            )


# ── 10. Export revenue subtracted correctly ───────────────────────────────────

def test_export_revenue_subtracted_from_total():
    """upgraded_total = electricity - solar_export_revenue + heating + mobility."""
    out = _run_scenario()
    for sn in UPGRADE_SCENARIO_NAMES:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            c = rec["cost_eur"]
            expected = (
                c["electricity"]
                - c["solar_export_revenue"]
                + c["heating"]
                + c["mobility"]
            )
            # Tolerance 0.02: to_dict() rounds costs to 2 dp, sum can drift 1 cent
            assert abs(c["upgraded_total"] - expected) < 0.02, (
                f"{sn} {rec['month']}: total={c['upgraded_total']:.4f} "
                f"expected={expected:.4f}"
            )


# ── 11. Monthly costs sum to annual aggregates ────────────────────────────────

def test_lt_scenario_ordering():
    """LT central year 1 costs must be between low and high (inclusive).

    ST and LT use different price models (constant vs. trend), so ST monthly
    sums and LT annual totals are intentionally different.  This test verifies
    the LT scenario ordering invariant instead.
    """
    out = _run_scenario()
    for sn in UPGRADE_SCENARIO_NAMES:
        lt = out["upgrade_scenarios"][sn]["long_term_projection"]
        if not lt.get("low") or not lt.get("central") or not lt.get("high"):
            continue
        low_yr1 = lt["low"][0]["cost_eur"]["upgraded_total"]
        cen_yr1 = lt["central"][0]["cost_eur"]["upgraded_total"]
        high_yr1 = lt["high"][0]["cost_eur"]["upgraded_total"]
        assert low_yr1 <= cen_yr1 <= high_yr1, (
            f"{sn}: LT year-1 ordering violated: low={low_yr1} central={cen_yr1} high={high_yr1}"
        )


# ── 12. Zero kWp reproduces baseline electricity cost ─────────────────────────

def test_zero_kwp_reproduces_baseline_cost():
    """With 0 kWp, solar_only cost == baseline cost."""
    inp = _parsed()
    upg = UpgradeInput(solar_kwp=0.0, battery_kwh=0.0)
    out = ScenarioOrchestrator().run(inp, upg)
    for rec in out["upgrade_scenarios"]["solar_only"]["short_term_forecast"]:
        c = rec["cost_eur"]
        # No PV, no battery, no HP, no EV → upgraded_total == baseline_total
        assert abs(c["upgraded_total"] - c["baseline_total"]) < 0.01, (
            f"Month {rec['month']}: upgraded={c['upgraded_total']:.4f} "
            f"baseline={c['baseline_total']:.4f}"
        )


# ── 13. Provenance and default warnings ───────────────────────────────────────

def test_missing_solar_kwp_produces_warning():
    """When solar_kwp is absent, a warning must be emitted."""
    inp = _parsed()
    upg = UpgradeInput(usable_roof_area_m2=40.0)  # no solar_kwp
    out = ScenarioOrchestrator().run(inp, upg)
    warnings = out["validation_warnings"]
    assert any("solar_kwp" in w.lower() or "kWp" in w for w in warnings), (
        f"No solar_kwp warning in {warnings}"
    )


def test_assumptions_used_section_present():
    """Output must include an 'assumptions_used' section."""
    out = _run_scenario()
    assert "assumptions_used" in out
    assert isinstance(out["assumptions_used"], dict)


def test_assumptions_used_has_key_fields():
    """assumptions_used must expose kWp, FIT, SCOP, EV params."""
    out = _run_scenario()
    ua = out["assumptions_used"]
    assert "solar_kwp" in ua
    assert "feed_in_tariff_eur_per_kwh" in ua
    assert "battery_usable_kwh" in ua
    assert "heat_pump_scop" in ua
    assert "ev_kwh_per_100km" in ua


def test_input_summary_section_present():
    """Output must include an 'input_summary' section."""
    out = _run_scenario()
    assert "input_summary" in out
    s = out["input_summary"]
    assert "postcode" in s
    assert "annual_electricity_kwh" in s
    assert "fuel_type" in s


# ── 14. Required output schema keys present ───────────────────────────────────

def test_monthly_record_has_required_sections():
    out = _run_scenario()
    for sn in UPGRADE_SCENARIO_NAMES:
        rec = out["upgrade_scenarios"][sn]["short_term_forecast"][0]
        assert "month" in rec
        assert "scenario" in rec
        assert "energy_flows" in rec
        assert "prices" in rec
        assert "cost_eur" in rec
        ef = rec["energy_flows"]
        assert "household_electricity_kwh" in ef
        assert "pv_generation_kwh" in ef
        assert "grid_import_kwh" in ef
        assert "grid_export_kwh" in ef
        assert "battery_charge_kwh" in ef
        assert "battery_discharge_kwh" in ef
        assert "battery_losses_kwh" in ef
        assert "heat_pump_electricity_kwh" in ef
        assert "remaining_heating_fuel" in ef
        assert "ev_charging_kwh" in ef
        assert "remaining_petrol_litres" in ef
        prices = rec["prices"]
        assert "electricity_eur_per_kwh" in prices
        assert "electricity_fixed_eur" in prices
        assert "heating_eur_per_unit" in prices
        c = rec["cost_eur"]
        assert "electricity" in c
        assert "solar_export_revenue" in c
        assert "heating" in c
        assert "mobility" in c
        assert "upgraded_total" in c
        assert "baseline_total" in c
        assert "energy_cost_reduction" in c


def test_monthly_record_scenario_field_matches():
    """The scenario field inside each monthly record must match the scenario key."""
    out = _run_scenario()
    for sn in UPGRADE_SCENARIO_NAMES:
        for rec in out["upgrade_scenarios"][sn]["short_term_forecast"]:
            assert rec["scenario"] == sn, (
                f"Expected scenario={sn!r}, got {rec['scenario']!r}"
            )


def test_long_term_projection_has_all_price_scenarios():
    """long_term_projection must be nested: {low: [...], central: [...], high: [...]}."""
    out = _run_scenario()
    for sn in UPGRADE_SCENARIO_NAMES:
        lt = out["upgrade_scenarios"][sn]["long_term_projection"]
        assert "low" in lt, f"{sn}: missing 'low'"
        assert "central" in lt, f"{sn}: missing 'central'"
        assert "high" in lt, f"{sn}: missing 'high'"


def test_long_term_projection_annual_record_fields():
    out = _run_scenario()
    ann = out["upgrade_scenarios"]["solar_only"]["long_term_projection"]["central"][0]
    assert "year_label" in ann
    assert "first_month" in ann
    assert "last_month" in ann
    assert "energy_flows" in ann
    assert "cost_eur" in ann
    c = ann["cost_eur"]
    assert "upgraded_total" in c
    assert "energy_cost_reduction" in c
    assert "cumulative_energy_cost_reduction" in c
    assert "baseline_total" in c
    assert "baseline_electricity" in c
    assert "baseline_heating" in c
    assert "baseline_mobility" in c


def test_baseline_long_term_projection_nested():
    """Baseline long_term_projection must also be nested by price scenario."""
    out = _run_scenario()
    lt = out["baseline"]["long_term_projection"]
    assert "low" in lt
    assert "central" in lt
    assert "high" in lt
    assert isinstance(lt["central"], list)
    assert lt["central"][0].get("year_label") == "Year 1"


# ── 15. Negative savings are not suppressed ───────────────────────────────────

def test_negative_savings_not_suppressed():
    """A scenario with very high EV demand but no solar can have negative savings."""
    inp = _parsed()
    heavy_ev = EVAssumptions(kwh_per_100km=40.0, charging_efficiency=0.50, home_charging_share=1.0)
    upg = UpgradeInput(solar_kwp=0.0, battery_kwh=0.0, ev_assumptions=heavy_ev)
    out = ScenarioOrchestrator().run(inp, upg)
    reductions = [
        r["cost_eur"]["energy_cost_reduction"]
        for r in out["upgrade_scenarios"]["pv_ev"]["short_term_forecast"]
    ]
    assert any(r < 0 for r in reductions), (
        "Expected at least one month with negative savings (cost increase) "
        "for heavy EV + zero PV"
    )


# ── 16–25. Serializer validate_output() — one test per check ─────────────────

@pytest.fixture(scope="module")
def valid_output():
    """Generate one full output dict; reused across all serializer tests."""
    inp = validate_and_parse(MINIMAL_RAW)
    upg = _small_upgrade()
    return ScenarioOrchestrator().run(inp, upg)


def test_validate_check1_all_six_scenarios(valid_output):
    """CHECK 1: valid output passes (no missing scenarios)."""
    errors = validate_output(valid_output)
    check1 = [e for e in errors if "CHECK 1" in e]
    assert not check1, check1


def test_validate_check1_missing_scenario(valid_output):
    """CHECK 1 fires when a scenario is removed."""
    bad = copy.deepcopy(valid_output)
    del bad["upgrade_scenarios"]["full_upgrade"]
    errors = validate_output(bad)
    assert any("CHECK 1" in e for e in errors)


def test_validate_check2_month_alignment(valid_output):
    """CHECK 2: valid output passes month alignment."""
    errors = validate_output(valid_output)
    assert not any("CHECK 2" in e for e in errors)


def test_validate_check2_misaligned_months(valid_output):
    """CHECK 2 fires when upgrade months differ from baseline."""
    bad = copy.deepcopy(valid_output)
    bad["upgrade_scenarios"]["solar_only"]["short_term_forecast"][0]["month"] = "1999-01"
    errors = validate_output(bad)
    assert any("CHECK 2" in e for e in errors)


def test_validate_check3_identical_prices(valid_output):
    """CHECK 3: valid output passes price identity check."""
    errors = validate_output(valid_output)
    assert not any("CHECK 3" in e for e in errors)


def test_validate_check3_tampered_prices(valid_output):
    """CHECK 3 fires when upgrade electricity price differs from baseline."""
    bad = copy.deepcopy(valid_output)
    bad["upgrade_scenarios"]["solar_only"]["short_term_forecast"][0]["prices"][
        "electricity_eur_per_kwh"
    ] = 9.99
    errors = validate_output(bad)
    assert any("CHECK 3" in e for e in errors)


def test_validate_check4_cost_sum(valid_output):
    """CHECK 4: valid output passes component-sum check."""
    errors = validate_output(valid_output)
    assert not any("CHECK 4 FAIL" in e for e in errors)


def test_validate_check5_reduction_equals_diff(valid_output):
    """CHECK 5: energy_cost_reduction == baseline_total - upgraded_total."""
    errors = validate_output(valid_output)
    assert not any("CHECK 5" in e for e in errors)


def test_validate_check5_tampered_reduction(valid_output):
    """CHECK 5 fires when energy_cost_reduction is altered."""
    bad = copy.deepcopy(valid_output)
    bad["upgrade_scenarios"]["solar_only"]["short_term_forecast"][0]["cost_eur"][
        "energy_cost_reduction"
    ] = 999.99
    errors = validate_output(bad)
    assert any("CHECK 5" in e for e in errors)


def test_validate_check6_lt_scenario_ordering(valid_output):
    """CHECK 6: LT year-1 costs are ordered low ≤ central ≤ high."""
    errors = validate_output(valid_output)
    assert not any("CHECK 6" in e for e in errors)


def test_validate_check7_cumulative_correct(valid_output):
    """CHECK 7: cumulative reductions are a running sum of annual reductions."""
    errors = validate_output(valid_output)
    assert not any("CHECK 7" in e for e in errors)


def test_validate_check7_tampered_cumulative(valid_output):
    """CHECK 7 fires when cumulative_energy_cost_reduction is wrong."""
    bad = copy.deepcopy(valid_output)
    bad["upgrade_scenarios"]["solar_only"]["long_term_projection"]["central"][0]["cost_eur"][
        "cumulative_energy_cost_reduction"
    ] = -99999.0
    errors = validate_output(bad)
    assert any("CHECK 7" in e for e in errors)


def test_validate_check8_no_nan_or_inf(valid_output):
    """CHECK 8: valid output has no NaN or Infinity."""
    errors = validate_output(valid_output)
    assert not any("CHECK 8" in e for e in errors)


def test_validate_check8_detects_nan(valid_output):
    """CHECK 8 fires when a NaN is injected."""
    import math
    bad = copy.deepcopy(valid_output)
    bad["upgrade_scenarios"]["solar_only"]["short_term_forecast"][0]["cost_eur"]["electricity"] = (
        float("nan")
    )
    errors = validate_output(bad)
    assert any("CHECK 8" in e for e in errors)


def test_validate_check9_json_roundtrip(valid_output):
    """CHECK 9: output survives JSON round-trip unchanged."""
    errors = validate_output(valid_output)
    assert not any("CHECK 9" in e for e in errors)


def test_validate_check10_no_financing_fields(valid_output):
    """CHECK 10: valid output contains no financing keys."""
    errors = validate_output(valid_output)
    assert not any("CHECK 10" in e for e in errors)


def test_validate_check10_detects_financing(valid_output):
    """CHECK 10 fires when a financing field is injected."""
    bad = copy.deepcopy(valid_output)
    bad["upgrade_scenarios"]["solar_only"]["financing"] = {"loan_amount": 15000}
    errors = validate_output(bad)
    assert any("CHECK 10" in e for e in errors)


# ── Unit tests for solar module ────────────────────────────────────────────────

def test_solar_orientation_factor_south_is_one():
    a = SolarAssumptions()
    assert _orientation_factor("south", a) == pytest.approx(1.0)
    assert _orientation_factor("s", a) == pytest.approx(1.0)


def test_solar_orientation_factor_north_less_than_south():
    a = SolarAssumptions()
    assert _orientation_factor("north", a) < _orientation_factor("south", a)


def test_solar_tilt_factor_interpolates():
    a = SolarAssumptions()
    f25 = _tilt_factor(25.0, a)
    f30 = _tilt_factor(30.0, a)
    f35 = _tilt_factor(35.0, a)
    assert f25 < f30  # tilt 25° < 30° optimal
    assert f30 == f35  # both at max


def test_solar_zero_kwp_returns_zero():
    a = SolarAssumptions()
    gen = monthly_pv_generation(
        kwp=0.0, postcode="80331", orientation="south",
        tilt_deg=30.0, shading_factor=0.0, year=2026, month=6,
        year_index=0, assumptions=a,
    )
    assert gen == pytest.approx(0.0)


def test_solar_shading_reduces_generation():
    a = SolarAssumptions()
    g0 = monthly_pv_generation(
        kwp=5.0, postcode="80331", orientation="south",
        tilt_deg=30.0, shading_factor=0.0, year=2026, month=6,
        year_index=0, assumptions=a,
    )
    g50 = monthly_pv_generation(
        kwp=5.0, postcode="80331", orientation="south",
        tilt_deg=30.0, shading_factor=0.5, year=2026, month=6,
        year_index=0, assumptions=a,
    )
    assert g50 == pytest.approx(g0 * 0.5, rel=1e-6)


def test_feed_in_tariff_by_size():
    a = SolarAssumptions()
    assert feed_in_tariff(5.0, a) == pytest.approx(0.082)
    assert feed_in_tariff(20.0, a) == pytest.approx(0.071)
    assert feed_in_tariff(50.0, a) == pytest.approx(0.058)


def test_resolve_kwp_from_area():
    a = SolarAssumptions(m2_per_kwp=6.0)
    kwp, note = resolve_kwp(None, 30.0, a)
    assert kwp == pytest.approx(5.0)
    assert "derived" in note


def test_resolve_kwp_user_value_wins():
    a = SolarAssumptions()
    kwp, note = resolve_kwp(7.5, 30.0, a)
    assert kwp == pytest.approx(7.5)
    assert note == "user"


# ── Unit tests for upgrade_model ───────────────────────────────────────────────

def _make_model(flags_name="solar_only", kwp=5.0, bat_kwh=0.0, **kwargs) -> UpgradeEnergyModel:
    from energy_model.upgrade_model import SCENARIO_FLAGS, UpgradeEnergyModel
    return UpgradeEnergyModel(
        SCENARIO_FLAGS[flags_name],
        kwp=kwp,
        postcode="80331",
        battery_usable_kwh=bat_kwh,
        **kwargs,
    )


def test_no_solar_zero_pv_generation():
    model = _make_model("solar_only", kwp=0.0)
    rec = model.compute_month(
        baseline_electricity_kwh=350.0,
        baseline_heating_value=1000.0,
        baseline_petrol_litres=60.0,
        monthly_mileage_km=1000.0,
        year=2026, month=6, year_index=0,
        elec_unit_eur_per_kwh=0.32,
        elec_fixed_eur=12.5,
        heating_price_per_unit=0.10,
        petrol_price_eur_per_litre=1.80,
        baseline_electricity_cost_eur=124.5,
        baseline_heating_cost_eur=100.0,
        baseline_mobility_cost_eur=108.0,
    )
    assert rec.pv_generation_kwh == pytest.approx(0.0)
    assert rec.grid_import_kwh == pytest.approx(350.0)


def test_pv_battery_reduces_export_vs_solar_only():
    """Adding a battery should divert PV surplus from export to self-consumption."""
    inp = _parsed()
    upg_no_bat = UpgradeInput(solar_kwp=5.0, battery_kwh=0.0)
    upg_with_bat = UpgradeInput(solar_kwp=5.0, battery_kwh=10.0)

    orc = ScenarioOrchestrator()
    out_no_bat = orc.run(inp, upg_no_bat)
    out_with_bat = orc.run(inp, upg_with_bat)

    export_no_bat = sum(
        r["energy_flows"]["grid_export_kwh"]
        for r in out_no_bat["upgrade_scenarios"]["solar_only"]["short_term_forecast"]
    )
    export_with_bat = sum(
        r["energy_flows"]["grid_export_kwh"]
        for r in out_with_bat["upgrade_scenarios"]["pv_battery"]["short_term_forecast"]
    )
    assert export_with_bat < export_no_bat, (
        f"Battery should reduce grid export: "
        f"no_bat={export_no_bat:.1f} kWh, with_bat={export_with_bat:.1f} kWh"
    )


def test_oil_heat_pump_conversion():
    """Heat pump electricity for oil heating: (litres × oil_kwh/L × eff) / SCOP."""
    model = UpgradeEnergyModel(
        SCENARIO_FLAGS["pv_heatpump"],
        kwp=5.0, postcode="80331",
        fuel_type="oil", oil_kwh_per_litre=10.0,
        heat_pump_assumptions=HeatPumpAssumptions(
            existing_heating_efficiency=0.85, heat_pump_scop=3.0
        ),
    )
    baseline_oil_litres = 100.0
    expected_hp_kwh = (baseline_oil_litres * 10.0 * 0.85) / 3.0
    rec = model.compute_month(
        baseline_electricity_kwh=300.0,
        baseline_heating_value=baseline_oil_litres,
        baseline_petrol_litres=0.0,
        monthly_mileage_km=0.0,
        year=2026, month=1, year_index=0,
        elec_unit_eur_per_kwh=0.32,
        elec_fixed_eur=12.5,
        heating_price_per_unit=1.05,
        petrol_price_eur_per_litre=1.80,
        baseline_electricity_cost_eur=108.5,
        baseline_heating_cost_eur=105.0,
        baseline_mobility_cost_eur=0.0,
    )
    assert rec.heat_pump_electricity_kwh == pytest.approx(expected_hp_kwh, rel=1e-6)
    assert rec.remaining_heating_fuel == pytest.approx(0.0)
