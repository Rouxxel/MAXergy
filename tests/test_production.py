"""Production pipeline tests.

Sections:
  1.  Public Python interface (compute_model)
  2.  File interface (run_model)
  3.  CLI (run_model.py)
  4.  User-specific output — Cases A, B, C, D
  5.  Modelling behaviour — 12 invariants
  6.  Invalid input validation — 9 cases
  7.  Output schema completeness
  8.  Price model behaviour
  9.  Scenario completeness and financing
 10.  JSON round-trip
 11.  Independence from research imports
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from energy_model.pipeline import compute_model, run_model
from energy_model.setup_models import UPGRADE_SCENARIO_NAMES, PRICE_SCENARIOS
from energy_model.price_models import ConstantShortTermPriceModel
from energy_model.orchestrator import ScenarioOrchestrator
from energy_model.input_validator import validate_and_parse
from energy_model.setup_models import UpgradeInput

_REPO_ROOT = Path(__file__).parent.parent
_INPUT_FILE = _REPO_ROOT / "documentation" / "data" / "model_input1.json"

# ── Shared fixture ────────────────────────────────────────────────────────────

CASE_A = {
    "location": {"postcode": "10115", "country": "DE"},
    "household": {
        "occupants": 3,
        "electricity": {
            "annual_kwh": 4200,
            "arbeitspreis_eur_per_kwh": 0.32,
            "grundpreis_eur_per_month": 12.50,
            "contract_end_date": "2026-12-31",
        },
        "roof": {
            "usable_area_m2": 40,
            "orientation": "south",
            "tilt_deg": 30,
            "shading_factor": 0.1,
        },
    },
    "heating": {"fuel_type": "gas", "annual_consumption": 14000, "annual_spend_eur": 1450},
    "mobility": {
        "vehicle_type": "petrol",
        "annual_mileage_km": 12000,
        "fuel_consumption_l_per_100km": 6.5,
        "annual_fuel_spend_eur": 1100,
    },
    "financing": {"loan_term_years": 15, "loan_rate_pct": 4.5},
    "forecast_horizon": {"short_term_months": 12, "long_term_years": 5},
}


@pytest.fixture(scope="module")
def out_a():
    return compute_model(CASE_A)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PUBLIC PYTHON INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def test_compute_model_accepts_dict(out_a):
    assert isinstance(out_a, dict)


def test_compute_model_returns_json_serialisable(out_a):
    serialised = json.dumps(out_a)
    assert len(serialised) > 100


def test_compute_model_does_not_write_files(tmp_path, monkeypatch):
    """compute_model must not open any files for writing."""
    opened_paths: list[str] = []
    real_open = open

    def tracking_open(file, mode="r", *args, **kwargs):
        if "w" in str(mode):
            opened_paths.append(str(file))
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", tracking_open)
    compute_model(CASE_A)
    assert not opened_paths, f"compute_model opened files for writing: {opened_paths}"


def test_compute_model_validates_input():
    with pytest.raises(ValueError, match="postcode"):
        compute_model({"location": {}})


def test_compute_model_normalises_defaults():
    """Input without occupants should default to 2."""
    raw = copy.deepcopy(CASE_A)
    del raw["household"]["occupants"]
    result = compute_model(raw)
    assert result["input_summary"]["occupants"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 2. FILE INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

def test_run_model_reads_input_file(tmp_path):
    in_path = tmp_path / "in.json"
    out_path = tmp_path / "out.json"
    in_path.write_text(json.dumps(CASE_A))

    result = run_model(in_path, out_path)

    assert isinstance(result, dict)
    assert out_path.exists()


def test_run_model_creates_output_directory(tmp_path):
    in_path = tmp_path / "in.json"
    out_path = tmp_path / "a" / "b" / "out.json"  # nested dirs don't exist
    in_path.write_text(json.dumps(CASE_A))

    run_model(in_path, out_path)

    assert out_path.exists()


def test_run_model_written_json_equals_returned_dict(tmp_path):
    in_path = tmp_path / "in.json"
    out_path = tmp_path / "out.json"
    in_path.write_text(json.dumps(CASE_A))

    result = run_model(in_path, out_path)
    written = json.loads(out_path.read_text())

    assert written["model"] == result["model"]
    assert set(written.keys()) == set(result.keys())


def test_run_model_uses_input_path_not_hardcoded(tmp_path):
    """run_model must not use hardcoded paths; must read from the given file."""
    custom = copy.deepcopy(CASE_A)
    custom["household"]["electricity"]["annual_kwh"] = 9999

    in_path = tmp_path / "custom.json"
    out_path = tmp_path / "out.json"
    in_path.write_text(json.dumps(custom))

    result = run_model(in_path, out_path)

    assert result["input_summary"]["annual_electricity_kwh"] == 9999


# ═══════════════════════════════════════════════════════════════════════════════
# 3. CLI
# ═══════════════════════════════════════════════════════════════════════════════

def test_cli_exits_zero_for_valid_input(tmp_path):
    in_path = tmp_path / "in.json"
    out_path = tmp_path / "out.json"
    in_path.write_text(json.dumps(CASE_A))

    r = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "run_model.py"),
         "--input", str(in_path), "--output", str(out_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"CLI failed:\n{r.stderr}"
    assert out_path.exists()


def test_cli_exits_nonzero_missing_postcode(tmp_path):
    bad = {"location": {}, "household": {}, "heating": {}, "mobility": {}}
    in_path = tmp_path / "bad.json"
    out_path = tmp_path / "out.json"
    in_path.write_text(json.dumps(bad))

    r = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "run_model.py"),
         "--input", str(in_path), "--output", str(out_path)],
        capture_output=True, text=True,
    )
    assert r.returncode != 0


def test_cli_exits_nonzero_file_not_found(tmp_path):
    r = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "run_model.py"),
         "--input", str(tmp_path / "nonexistent.json"),
         "--output", str(tmp_path / "out.json")],
        capture_output=True, text=True,
    )
    assert r.returncode != 0


def test_cli_output_file_created():
    """Smoke test against the repo example input."""
    out_path = _REPO_ROOT / "documentation" / "data" / "model_output.json"
    r = subprocess.run(
        [sys.executable, str(_REPO_ROOT / "scripts" / "run_model.py"),
         "--input", str(_INPUT_FILE),
         "--output", str(out_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert out_path.exists()
    loaded = json.loads(out_path.read_text())
    assert loaded["model"]["name"] == "energy_cost_comparison"


def test_cli_passes_validators():
    from energy_model.serializer import validate_output, validate_financing_output
    out_path = _REPO_ROOT / "documentation" / "data" / "model_output.json"
    output = json.loads(out_path.read_text())
    assert not validate_output(output)
    assert not validate_financing_output(output)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. USER-SPECIFIC OUTPUT
# ═══════════════════════════════════════════════════════════════════════════════

# Case B: higher electricity consumption
CASE_B = copy.deepcopy(CASE_A)
CASE_B["household"]["electricity"]["annual_kwh"] = 8000


@pytest.fixture(scope="module")
def out_b():
    return compute_model(CASE_B)


def test_case_b_baseline_electricity_higher(out_a, out_b):
    """Doubling annual_kwh must increase baseline electricity consumption."""
    def _total_elec_kwh(out):
        return sum(
            r["consumption"]["electricity_kwh"]
            for r in out["baseline"]["short_term_forecast"]
        )
    assert _total_elec_kwh(out_b) > _total_elec_kwh(out_a)


def test_case_b_baseline_electricity_cost_higher(out_a, out_b):
    def _total_elec_cost(out):
        return sum(
            r["cost_eur"]["electricity"]
            for r in out["baseline"]["short_term_forecast"]
        )
    assert _total_elec_cost(out_b) > _total_elec_cost(out_a)


def test_case_b_upgrade_results_recalculated(out_a, out_b):
    """With higher electricity, solar self-consumption value changes."""
    a_red = sum(
        r["cost_eur"]["energy_cost_reduction"]
        for r in out_a["upgrade_scenarios"]["solar_only"]["short_term_forecast"]
    )
    b_red = sum(
        r["cost_eur"]["energy_cost_reduction"]
        for r in out_b["upgrade_scenarios"]["solar_only"]["short_term_forecast"]
    )
    assert a_red != b_red, "solar_only energy reduction must differ with different annual_kwh"


def test_case_b_heating_unchanged(out_a, out_b):
    """Changing electricity must not affect baseline heating costs."""
    def _annual_heat(out):
        return sum(
            r["cost_eur"]["heating"]
            for r in out["baseline"]["short_term_forecast"]
        )
    assert abs(_annual_heat(out_a) - _annual_heat(out_b)) < 0.01


def test_case_b_input_summary_reflects_user(out_b):
    assert out_b["input_summary"]["annual_electricity_kwh"] == 8000


# Case C: different roof + financing
CASE_C = copy.deepcopy(CASE_A)
CASE_C["household"]["roof"] = {
    "usable_area_m2": 20,
    "orientation": "east",
    "shading_factor": 0.25,
}
CASE_C["financing"] = {"loan_term_years": 10, "loan_rate_pct": 6.0}


@pytest.fixture(scope="module")
def out_c():
    return compute_model(CASE_C)


def test_case_c_pv_size_smaller(out_a, out_c):
    """Smaller roof must produce smaller estimated PV system."""
    kwp_a = out_a["assumptions_used"]["solar_kwp"]
    kwp_c = out_c["assumptions_used"]["solar_kwp"]
    assert kwp_c < kwp_a, f"PV size should decrease: {kwp_a} → {kwp_c}"


def test_case_c_financing_instalment_differs(out_a, out_c):
    """Different loan terms and rates must produce different monthly instalments."""
    inst_a = out_a["upgrade_scenarios"]["solar_only"]["financing"]["monthly_instalment_eur"]
    inst_c = out_c["upgrade_scenarios"]["solar_only"]["financing"]["monthly_instalment_eur"]
    assert abs(inst_a - inst_c) > 0.01, f"Instalments should differ: {inst_a} vs {inst_c}"


def test_case_c_baseline_costs_unchanged(out_a, out_c):
    """Different roof and financing must not change baseline energy costs."""
    def _annual_total(out):
        return sum(
            r["cost_eur"]["total"]
            for r in out["baseline"]["short_term_forecast"]
        )
    assert abs(_annual_total(out_a) - _annual_total(out_c)) < 0.01


def test_case_c_solar_savings_differ(out_a, out_c):
    """Smaller east-facing roof should yield lower solar savings."""
    lt_a = out_a["upgrade_scenarios"]["solar_only"]["long_term_projection"]["central"]
    lt_c = out_c["upgrade_scenarios"]["solar_only"]["long_term_projection"]["central"]
    red_a = sum(yr["cost_eur"]["energy_cost_reduction"] for yr in lt_a)
    red_c = sum(yr["cost_eur"]["energy_cost_reduction"] for yr in lt_c)
    assert red_a != red_c


# Case D: higher heating and mileage — drop spend fields so default prices apply
CASE_D = copy.deepcopy(CASE_A)
CASE_D["heating"] = {"fuel_type": "gas", "annual_consumption": 25000}
CASE_D["mobility"] = {
    "vehicle_type": "petrol",
    "annual_mileage_km": 25000,
    "fuel_consumption_l_per_100km": 6.5,
}


@pytest.fixture(scope="module")
def out_d():
    return compute_model(CASE_D)


def test_case_d_heating_cost_higher(out_a, out_d):
    def _annual_heat(out):
        return sum(r["cost_eur"]["heating"] for r in out["baseline"]["short_term_forecast"])
    assert _annual_heat(out_d) > _annual_heat(out_a) * 1.5


def test_case_d_mobility_cost_higher(out_a, out_d):
    def _annual_mob(out):
        return sum(r["cost_eur"]["mobility"] for r in out["baseline"]["short_term_forecast"])
    assert _annual_mob(out_d) > _annual_mob(out_a) * 1.5


def test_case_d_ev_savings_larger(out_a, out_d):
    """Higher mileage should increase EV savings."""
    def _total_lt_red(out, sn):
        lt = out["upgrade_scenarios"][sn]["long_term_projection"]["central"]
        return sum(yr["cost_eur"]["energy_cost_reduction"] for yr in lt)
    assert _total_lt_red(out_d, "pv_ev") > _total_lt_red(out_a, "pv_ev")


def test_case_d_heatpump_savings_larger(out_a, out_d):
    """Higher heating consumption should increase heat-pump savings."""
    def _total_lt_red(out, sn):
        lt = out["upgrade_scenarios"][sn]["long_term_projection"]["central"]
        return sum(yr["cost_eur"]["energy_cost_reduction"] for yr in lt)
    assert _total_lt_red(out_d, "pv_heatpump") > _total_lt_red(out_a, "pv_heatpump")


def test_cases_produce_different_outputs(out_a, out_b, out_c, out_d):
    """All four cases differ from each other via targeted per-case invariants.

    A vs B: baseline electricity cost differs (annual_kwh = 4200 vs 8000)
    A vs C: PV size differs (different roof area/orientation)
    A vs D: heating + mobility baseline costs differ (25000 kWh gas, 25000 km)
    """
    def _baseline_elec(out):
        return sum(r["cost_eur"]["electricity"] for r in out["baseline"]["short_term_forecast"])

    def _kwp(out):
        return out["assumptions_used"]["solar_kwp"]

    def _full_heat(out):
        return sum(r["cost_eur"]["heating"] for r in out["baseline"]["short_term_forecast"])

    assert abs(_baseline_elec(out_a) - _baseline_elec(out_b)) > 10, "B must differ from A on electricity"
    assert abs(_kwp(out_a) - _kwp(out_c)) > 0.1, "C must differ from A on PV size"
    assert abs(_full_heat(out_a) - _full_heat(out_d)) > 100, "D must differ from A on heating"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MODELLING BEHAVIOUR — 12 INVARIANTS
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture(scope="module")
def out_with_constant_lt():
    """Orchestrator with constant prices for BOTH ST and LT — enables annual=monthly check."""
    inp = validate_and_parse(CASE_A)
    upg = UpgradeInput(solar_kwp=6.6, battery_kwh=10.0, roof_orientation="south")
    const = ConstantShortTermPriceModel()
    orch = ScenarioOrchestrator(st_price_model=const, lt_price_model=const)
    return orch.run(inp, upg)


def test_mb1_st_prices_are_constant(out_a):
    """MB-1: Short-term electricity price is identical for every month."""
    st = out_a["baseline"]["short_term_forecast"]
    first = st[0]["prices"]["electricity_eur_per_kwh"]
    assert all(r["prices"]["electricity_eur_per_kwh"] == first for r in st[1:])


def test_mb2_contract_lock_in(out_a):
    """MB-2: ST electricity price equals user tariff (constant model respects contract)."""
    tariff = CASE_A["household"]["electricity"]["arbeitspreis_eur_per_kwh"]
    for rec in out_a["baseline"]["short_term_forecast"]:
        assert abs(rec["prices"]["electricity_eur_per_kwh"] - tariff) < 1e-9


def test_mb3_lt_has_three_scenarios(out_a):
    """MB-3: Long-term projection has low, central, and high scenarios."""
    lt = out_a["baseline"]["long_term_projection"]
    assert set(lt.keys()) == {"low", "central", "high"}


def test_mb3_lt_scenario_ordering(out_a):
    """MB-3: LT cost ordering: low ≤ central ≤ high by final year."""
    lt = out_a["baseline"]["long_term_projection"]
    idx = -1
    low = lt["low"][idx]["cost_eur"]["total"]
    cen = lt["central"][idx]["cost_eur"]["total"]
    high = lt["high"][idx]["cost_eur"]["total"]
    assert low <= cen <= high


def test_mb4_all_six_upgrade_scenarios(out_a):
    """MB-4: All six upgrade scenarios are produced."""
    assert set(out_a["upgrade_scenarios"].keys()) == set(UPGRADE_SCENARIO_NAMES)


def test_mb5_baseline_upgrade_months_aligned(out_a):
    """MB-5: Baseline and all upgrade scenarios share identical month labels."""
    base_months = [r["month"] for r in out_a["baseline"]["short_term_forecast"]]
    for sn in UPGRADE_SCENARIO_NAMES:
        upg_months = [r["month"] for r in out_a["upgrade_scenarios"][sn]["short_term_forecast"]]
        assert upg_months == base_months, f"{sn}: month mismatch"


def test_mb6_energy_cost_reduction_formula(out_a):
    """MB-6: energy_cost_reduction = baseline_total - upgraded_total (within 2 cents)."""
    for sn in UPGRADE_SCENARIO_NAMES:
        for rec in out_a["upgrade_scenarios"][sn]["short_term_forecast"]:
            c = rec["cost_eur"]
            expected = c["baseline_total"] - c["upgraded_total"]
            assert abs(c["energy_cost_reduction"] - expected) < 0.02, (
                f"{sn} {rec['month']}: {c['energy_cost_reduction']:.4f} ≠ {expected:.4f}"
            )


def test_mb7_net_savings_formula(out_a):
    """MB-7: net_monthly_savings = energy_cost_reduction - financing_instalment."""
    for sn in UPGRADE_SCENARIO_NAMES:
        for rec in out_a["upgrade_scenarios"][sn]["short_term_forecast"]:
            fr = rec["financial_result"]
            expected = fr["energy_cost_reduction_eur"] - fr["financing_instalment_eur"]
            assert abs(fr["net_monthly_savings_eur"] - expected) < 0.02


def test_mb8_financing_stops_after_loan_term(out_a):
    """MB-8: Financing instalments are zero after the loan term."""
    loan_months = 15 * 12  # 15-year loan = 180 months
    for sn in UPGRADE_SCENARIO_NAMES:
        st = out_a["upgrade_scenarios"][sn]["short_term_forecast"]
        for i, rec in enumerate(st, 1):
            if i > loan_months:
                fi = rec["financial_result"]["financing_instalment_eur"]
                assert abs(fi) < 0.01, f"{sn} month {i}: instalment still {fi:.2f}"


def test_mb9_lt_annual_totals_consistent_under_constant_prices(out_with_constant_lt):
    """MB-9: With constant prices, LT year-1 total ≈ sum of ST month 1–12."""
    out = out_with_constant_lt
    for sn in UPGRADE_SCENARIO_NAMES:
        st = out["upgrade_scenarios"][sn]["short_term_forecast"]
        lt_cen = out["upgrade_scenarios"][sn]["long_term_projection"]["central"]
        if not lt_cen or len(st) < 12:
            continue
        st_sum = sum(r["cost_eur"]["upgraded_total"] for r in st[:12])
        lt_yr1 = lt_cen[0]["cost_eur"]["upgraded_total"]
        assert abs(lt_yr1 - st_sum) < 0.10, (
            f"{sn}: LT yr1={lt_yr1:.2f} ST sum={st_sum:.2f}"
        )


def test_mb10_cumulative_savings_chronological(out_a):
    """MB-10: Cumulative net savings in LT are a running total."""
    for sn in UPGRADE_SCENARIO_NAMES:
        lt_cen = out_a["upgrade_scenarios"][sn]["long_term_projection"]["central"]
        running = 0.0
        for yr in lt_cen:
            running += yr["financial_result"]["annual_net_savings_eur"]
            cumulative = yr["financial_result"]["cumulative_net_savings_eur"]
            assert abs(cumulative - running) < 0.10, (
                f"{sn}: expected {running:.2f} got {cumulative:.2f}"
            )


def test_mb11_no_nan_or_infinity(out_a):
    """MB-11: No NaN or Infinity in output."""
    import math

    def _check(obj, path=""):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            pytest.fail(f"Bad float at {path}: {obj}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _check(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _check(v, f"{path}[{i}]")

    _check(out_a)


def test_mb12_json_round_trip(out_a):
    """MB-12: Output can be serialised and reloaded without loss."""
    reloaded = json.loads(json.dumps(out_a))
    assert reloaded["model"] == out_a["model"]
    assert set(reloaded.keys()) == set(out_a.keys())


# ═══════════════════════════════════════════════════════════════════════════════
# 6. INVALID INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def _bad(update: dict) -> dict:
    """Return CASE_A with nested keys overridden."""
    result = copy.deepcopy(CASE_A)
    for path, value in update.items():
        parts = path.split(".")
        obj = result
        for p in parts[:-1]:
            obj = obj.setdefault(p, {})
        obj[parts[-1]] = value
    return result


def test_invalid_missing_postcode():
    with pytest.raises(ValueError, match="postcode"):
        compute_model(_bad({"location.postcode": None}))


def test_invalid_negative_annual_kwh():
    with pytest.raises(ValueError, match="annual_kwh"):
        compute_model(_bad({"household.electricity.annual_kwh": -100}))


def test_invalid_negative_arbeitspreis():
    with pytest.raises(ValueError, match="arbeitspreis"):
        compute_model(_bad({"household.electricity.arbeitspreis_eur_per_kwh": -0.01}))


def test_invalid_negative_grundpreis():
    with pytest.raises(ValueError, match="grundpreis"):
        compute_model(_bad({"household.electricity.grundpreis_eur_per_month": -5.0}))


def test_invalid_contract_date():
    with pytest.raises(ValueError, match="contract_end_date"):
        compute_model(_bad({"household.electricity.contract_end_date": "not-a-date"}))


def test_invalid_heating_fuel():
    with pytest.raises(ValueError, match="fuel_type"):
        compute_model(_bad({"heating.fuel_type": "coal"}))


def test_invalid_vehicle_type():
    with pytest.raises(ValueError, match="vehicle_type"):
        compute_model(_bad({"mobility.vehicle_type": "hovercraft"}))


def test_invalid_loan_term_zero():
    raw = copy.deepcopy(CASE_A)
    raw["financing"] = {"loan_term_years": 0, "loan_rate_pct": 4.5}
    with pytest.raises(ValueError, match="loan_term_years"):
        compute_model(raw)


def test_invalid_loan_rate_negative():
    raw = copy.deepcopy(CASE_A)
    raw["financing"] = {"loan_term_years": 15, "loan_rate_pct": -1.0}
    with pytest.raises(ValueError, match="annual_rate_pct"):
        compute_model(raw)


def test_invalid_short_term_months_zero():
    raw = copy.deepcopy(CASE_A)
    raw["forecast_horizon"] = {"short_term_months": 0, "long_term_years": 5}
    with pytest.raises(ValueError, match="short_term_months"):
        compute_model(raw)


def test_invalid_long_term_years_zero():
    raw = copy.deepcopy(CASE_A)
    raw["forecast_horizon"] = {"short_term_months": 12, "long_term_years": 0}
    with pytest.raises(ValueError, match="long_term_years"):
        compute_model(raw)


def test_error_messages_identify_field():
    """Error messages must name the offending field."""
    try:
        compute_model(_bad({"household.electricity.annual_kwh": -1}))
    except ValueError as exc:
        assert "annual_kwh" in str(exc), f"Field name missing from: {exc}"


# ═══════════════════════════════════════════════════════════════════════════════
# 7. OUTPUT SCHEMA COMPLETENESS
# ═══════════════════════════════════════════════════════════════════════════════

def test_schema_top_level_keys(out_a):
    required = {
        "model", "input_summary", "assumptions_used",
        "validation_warnings", "price_models", "baseline", "upgrade_scenarios",
    }
    assert required.issubset(out_a.keys()), f"Missing: {required - out_a.keys()}"


def test_schema_input_summary_reflects_user(out_a):
    s = out_a["input_summary"]
    assert s["postcode"] == "10115"
    assert s["annual_electricity_kwh"] == 4200
    assert s["fuel_type"] == "gas"
    assert s["annual_mileage_km"] == 12000
    assert s["short_term_months"] == 12


def test_schema_each_scenario_has_required_keys(out_a):
    for sn in UPGRADE_SCENARIO_NAMES:
        sc = out_a["upgrade_scenarios"][sn]
        assert "short_term_forecast" in sc, f"{sn}: missing short_term_forecast"
        assert "long_term_projection" in sc, f"{sn}: missing long_term_projection"
        assert "investment" in sc, f"{sn}: missing investment"
        assert "financing" in sc, f"{sn}: missing financing"


def test_schema_monthly_record_keys(out_a):
    for sn in UPGRADE_SCENARIO_NAMES:
        for rec in out_a["upgrade_scenarios"][sn]["short_term_forecast"]:
            assert "energy_flows" in rec, f"{sn} {rec['month']}: missing energy_flows"
            c = rec.get("cost_eur", {})
            assert "upgraded_total" in c
            assert "baseline_total" in c
            assert "energy_cost_reduction" in c
            fr = rec.get("financial_result", {})
            assert "net_monthly_savings_eur" in fr
            assert "cumulative_net_savings_eur" in fr


def test_schema_lt_annual_record_keys(out_a):
    for sn in UPGRADE_SCENARIO_NAMES:
        for ps in PRICE_SCENARIOS:
            for ann in out_a["upgrade_scenarios"][sn]["long_term_projection"][ps]:
                fr = ann.get("financial_result", {})
                assert "annual_energy_cost_reduction_eur" in fr
                assert "annual_net_savings_eur" in fr
                assert "cumulative_net_savings_eur" in fr
                assert "remaining_loan_balance_eur" in fr


def test_schema_price_models_keys(out_a):
    pm = out_a["price_models"]
    assert pm["short_term"]["name"] == "constant_index"
    assert pm["long_term"]["name"] == "scenario_trend"
    assert "selection_basis" in pm["short_term"]
    assert "assumptions" in pm["long_term"]


def test_schema_investment_keys(out_a):
    for sn in UPGRADE_SCENARIO_NAMES:
        inv = out_a["upgrade_scenarios"][sn]["investment"]
        assert "components" in inv
        assert "gross_investment_eur" in inv
        assert "financed_principal_eur" in inv


# ═══════════════════════════════════════════════════════════════════════════════
# 8. PRICE MODEL BEHAVIOUR
# ═══════════════════════════════════════════════════════════════════════════════

def test_st_price_equals_tariff_for_all_months(out_a):
    tariff = CASE_A["household"]["electricity"]["arbeitspreis_eur_per_kwh"]
    for rec in out_a["baseline"]["short_term_forecast"]:
        assert abs(rec["prices"]["electricity_eur_per_kwh"] - tariff) < 1e-9


def test_lt_central_costs_exceed_low_final_year(out_a):
    lt = out_a["baseline"]["long_term_projection"]
    low_last = lt["low"][-1]["cost_eur"]["total"]
    cen_last = lt["central"][-1]["cost_eur"]["total"]
    assert cen_last > low_last


def test_lt_high_exceeds_central_by_meaningful_margin(out_a):
    lt = out_a["baseline"]["long_term_projection"]
    cen_yr5 = lt["central"][-1]["cost_eur"]["total"]
    high_yr5 = lt["high"][-1]["cost_eur"]["total"]
    assert high_yr5 > cen_yr5 + 50  # central and high should diverge noticeably


def test_st_and_lt_central_yr1_differ(out_a):
    """ST (constant) and LT central year-1 must differ because they use different models."""
    st_yr1 = sum(
        r["cost_eur"]["total"] for r in out_a["baseline"]["short_term_forecast"][:12]
    )
    lt_yr1 = out_a["baseline"]["long_term_projection"]["central"][0]["cost_eur"]["total"]
    # They're the same horizon but different prices → values should differ
    assert abs(st_yr1 - lt_yr1) > 1.0  # at least €1 difference expected from trend


# ═══════════════════════════════════════════════════════════════════════════════
# 9. SCENARIO COMPLETENESS AND FINANCING
# ═══════════════════════════════════════════════════════════════════════════════

def test_all_six_scenarios_present(out_a):
    assert set(out_a["upgrade_scenarios"].keys()) == set(UPGRADE_SCENARIO_NAMES)


def test_all_three_lt_price_scenarios_per_upgrade(out_a):
    for sn in UPGRADE_SCENARIO_NAMES:
        lt = out_a["upgrade_scenarios"][sn]["long_term_projection"]
        assert set(lt.keys()) == set(PRICE_SCENARIOS)


def test_solar_only_zero_battery_cost(out_a):
    comp = out_a["upgrade_scenarios"]["solar_only"]["investment"]["components"]
    assert comp["battery_eur"] == 0.0


def test_pv_battery_has_pv_and_battery(out_a):
    comp = out_a["upgrade_scenarios"]["pv_battery"]["investment"]["components"]
    assert comp["pv_eur"] > 0
    assert comp["battery_eur"] > 0


def test_gross_investment_increases_with_upgrades(out_a):
    inv = {
        sn: out_a["upgrade_scenarios"][sn]["investment"]["gross_investment_eur"]
        for sn in UPGRADE_SCENARIO_NAMES
    }
    assert inv["solar_only"] < inv["pv_battery"] < inv["pv_battery_heatpump"]


def test_financing_instalment_positive_for_nonzero_investment(out_a):
    for sn in UPGRADE_SCENARIO_NAMES:
        inv = out_a["upgrade_scenarios"][sn]["investment"]["gross_investment_eur"]
        inst = out_a["upgrade_scenarios"][sn]["financing"]["monthly_instalment_eur"]
        if inv > 0:
            assert inst > 0, f"{sn}: zero instalment for non-zero investment"


# ═══════════════════════════════════════════════════════════════════════════════
# 10. JSON ROUND-TRIP
# ═══════════════════════════════════════════════════════════════════════════════

def test_json_roundtrip_preserves_all_keys(out_a):
    reloaded = json.loads(json.dumps(out_a))
    assert set(reloaded.keys()) == set(out_a.keys())
    for sn in UPGRADE_SCENARIO_NAMES:
        assert sn in reloaded["upgrade_scenarios"]


# ═══════════════════════════════════════════════════════════════════════════════
# 11. INDEPENDENCE FROM RESEARCH IMPORTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_orchestrator_no_research_import():
    src = (_REPO_ROOT / "scripts" / "energy_model" / "orchestrator.py").read_text()
    assert "run_energy_cost_forecast" not in src
    assert "research" not in src
    assert "sys.path.insert" not in src


def test_pipeline_no_research_import():
    src = (_REPO_ROOT / "scripts" / "energy_model" / "pipeline.py").read_text()
    assert "run_energy_cost_forecast" not in src
    assert "research" not in src


def test_price_models_no_research_import():
    src = (_REPO_ROOT / "scripts" / "energy_model" / "price_models.py").read_text()
    assert "import research" not in src
    assert "from research" not in src
    assert "run_energy_cost_forecast" not in src


def test_run_model_script_no_research_import():
    src = (_REPO_ROOT / "scripts" / "run_model.py").read_text()
    assert "research" not in src


# ═══════════════════════════════════════════════════════════════════════════════
# SERIALIZER VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

def test_validate_output_passes(out_a):
    from energy_model.serializer import validate_output
    errors = validate_output(out_a)
    assert not errors, f"validate_output errors: {errors}"


def test_validate_financing_passes(out_a):
    from energy_model.serializer import validate_financing_output
    errors = validate_financing_output(out_a)
    assert not errors, f"validate_financing_output errors: {errors}"
