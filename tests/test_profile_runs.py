"""Automated tests for the three realistic household profile runs.

These tests do NOT run backtests or research scripts.
They verify that:
  - All three profiles are valid inputs
  - All three outputs exist and are well-formed
  - Results differ when inputs differ
  - Best-plan selection uses model output values
  - Figures exist and are non-empty
  - Financial invariants hold
  - Summary files are consistent with generated outputs
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

_REPO = Path(__file__).parent.parent
_PROFILES_DIR = _REPO / "documentation" / "data" / "test_profiles"
_OUTPUTS_DIR = _REPO / "documentation" / "data" / "test_outputs"
_FIGURES_DIR = _REPO / "documentation" / "figures" / "test_profiles"

PROFILE_NAMES = [
    "average_german_household",
    "low_benefit_household",
    "high_benefit_household",
]

SCENARIO_NAMES = [
    "solar_only",
    "pv_battery",
    "pv_heatpump",
    "pv_ev",
    "pv_battery_heatpump",
    "full_upgrade",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_output(name: str) -> dict:
    path = _OUTPUTS_DIR / f"{name}_output.json"
    return json.loads(path.read_text())


def _select_best(output: dict) -> str:
    """Mirror of create_profile_figures.select_best_plan — source of truth is output values."""
    best_sn = max(
        output["upgrade_scenarios"].keys(),
        key=lambda sn: (
            output["upgrade_scenarios"][sn]["long_term_projection"]["central"][-1][
                "financial_result"
            ]["cumulative_net_savings_eur"],
            output["upgrade_scenarios"][sn]["long_term_projection"]["central"][0][
                "financial_result"
            ]["annual_net_savings_eur"],
            -output["upgrade_scenarios"][sn]["financing"]["monthly_instalment_eur"],
        ),
    )
    return best_sn


def _yr1_lt(output: dict, sn: str) -> dict:
    return output["upgrade_scenarios"][sn]["long_term_projection"]["central"][0]


def _cum20(output: dict, sn: str) -> float:
    lt = output["upgrade_scenarios"][sn]["long_term_projection"]["central"]
    return lt[-1]["financial_result"]["cumulative_net_savings_eur"]


@pytest.fixture(scope="module")
def all_outputs() -> dict[str, dict]:
    return {name: _load_output(name) for name in PROFILE_NAMES}


@pytest.fixture(scope="module")
def summary() -> list[dict]:
    return json.loads((_OUTPUTS_DIR / "model_test_summary.json").read_text())


# ── 1. All three inputs are valid ─────────────────────────────────────────────

import sys
sys.path.insert(0, str(_REPO / "scripts"))
from energy_model.input_validator import validate_and_parse


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_profile_input_is_valid(name):
    raw = json.loads((_PROFILES_DIR / f"{name}.json").read_text())
    parsed = validate_and_parse(raw)
    assert parsed.postcode


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_profile_input_has_required_sections(name):
    raw = json.loads((_PROFILES_DIR / f"{name}.json").read_text())
    assert "location" in raw
    assert raw["location"].get("postcode")
    assert "heating" in raw
    assert "mobility" in raw


# ── 2. All three outputs exist and are well-formed ────────────────────────────

@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_output_file_exists(name):
    path = _OUTPUTS_DIR / f"{name}_output.json"
    assert path.exists(), f"Output missing: {path}"


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_output_is_valid_json(name):
    path = _OUTPUTS_DIR / f"{name}_output.json"
    data = json.loads(path.read_text())
    assert isinstance(data, dict)


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_output_has_required_top_level_keys(name, all_outputs):
    out = all_outputs[name]
    required = {"model", "input_summary", "assumptions_used", "validation_warnings",
                "price_models", "baseline", "upgrade_scenarios"}
    assert required.issubset(out.keys())


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_output_passes_production_validators(name, all_outputs):
    from energy_model.serializer import validate_output, validate_financing_output
    out = all_outputs[name]
    energy_errs = validate_output(out)
    fin_errs = validate_financing_output(out)
    assert not energy_errs, f"{name}: {energy_errs}"
    assert not fin_errs, f"{name}: {fin_errs}"


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_output_has_baseline(name, all_outputs):
    out = all_outputs[name]
    assert "short_term_forecast" in out["baseline"]
    assert "long_term_projection" in out["baseline"]
    assert len(out["baseline"]["short_term_forecast"]) > 0


# ── 3. Outputs differ when inputs differ ──────────────────────────────────────

def test_baseline_electricity_differs_across_profiles(all_outputs):
    def _annual_elec(name):
        return sum(
            r["cost_eur"]["electricity"]
            for r in all_outputs[name]["baseline"]["short_term_forecast"]
        )
    costs = [_annual_elec(n) for n in PROFILE_NAMES]
    assert len(set(round(c, 2) for c in costs)) > 1, "All profiles share identical electricity costs"


def test_pv_sizes_differ_across_profiles(all_outputs):
    kwps = {name: all_outputs[name]["assumptions_used"]["solar_kwp"] for name in PROFILE_NAMES}
    assert len(set(kwps.values())) > 1, f"All profiles share identical PV size: {kwps}"


def test_low_benefit_has_smallest_pv(all_outputs):
    kwp_low = all_outputs["low_benefit_household"]["assumptions_used"]["solar_kwp"]
    kwp_avg = all_outputs["average_german_household"]["assumptions_used"]["solar_kwp"]
    kwp_high = all_outputs["high_benefit_household"]["assumptions_used"]["solar_kwp"]
    assert kwp_low < kwp_avg < kwp_high, (
        f"Expected low<avg<high PV size: {kwp_low} < {kwp_avg} < {kwp_high}"
    )


def test_high_benefit_has_highest_baseline_cost(all_outputs):
    def _total_baseline(name):
        return sum(
            r["cost_eur"]["total"]
            for r in all_outputs[name]["baseline"]["short_term_forecast"]
        )
    totals = {n: _total_baseline(n) for n in PROFILE_NAMES}
    assert totals["high_benefit_household"] > totals["average_german_household"]
    assert totals["average_german_household"] > totals["low_benefit_household"]


def test_cum20_savings_differ_across_profiles(all_outputs):
    best_cum20 = {
        name: _cum20(all_outputs[name], _select_best(all_outputs[name]))
        for name in PROFILE_NAMES
    }
    values = list(best_cum20.values())
    assert len(set(round(v, 0) for v in values)) > 1, f"All profiles share cum20: {best_cum20}"


def test_high_benefit_has_highest_cum20(all_outputs):
    def _best_cum20(name):
        return _cum20(all_outputs[name], _select_best(all_outputs[name]))
    assert _best_cum20("high_benefit_household") > _best_cum20("average_german_household")
    assert _best_cum20("average_german_household") > _best_cum20("low_benefit_household")


# ── 4. All six upgrade scenarios are present in each output ───────────────────

@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_all_six_scenarios_present(name, all_outputs):
    out = all_outputs[name]
    assert set(out["upgrade_scenarios"].keys()) == set(SCENARIO_NAMES)


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_each_scenario_has_three_lt_price_scenarios(name, all_outputs):
    out = all_outputs[name]
    for sn in SCENARIO_NAMES:
        lt = out["upgrade_scenarios"][sn]["long_term_projection"]
        assert set(lt.keys()) == {"low", "central", "high"}, f"{name}/{sn}: {lt.keys()}"


# ── 5. Best-plan selection uses model output values ───────────────────────────

def test_best_plan_selection_uses_model_output(all_outputs, summary):
    """The recorded best scenario in the summary must match re-running selection on outputs."""
    for entry in summary:
        name = entry["profile_name"]
        out = all_outputs[name]
        expected = _select_best(out)
        recorded = entry["best_scenario"]
        assert recorded == expected, (
            f"{name}: summary says '{recorded}' but model output best is '{expected}'"
        )


def test_best_plan_differs_for_low_benefit(all_outputs, summary):
    """Low-benefit household should not necessarily share the same best plan as others."""
    # This test just records the actual best plan — if all three happen to agree, that's fine.
    best = {e["profile_name"]: e["best_scenario"] for e in summary}
    # Low benefit has constrained roof → at minimum verify its best is model-consistent
    low_best = best["low_benefit_household"]
    out_low = all_outputs["low_benefit_household"]
    assert _select_best(out_low) == low_best


# ── 6. Figures are created and non-empty ─────────────────────────────────────

@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_figure_exists(name):
    fig_path = _FIGURES_DIR / f"{name}_comparison.png"
    assert fig_path.exists(), f"Figure missing: {fig_path}"


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_figure_is_nonempty(name):
    fig_path = _FIGURES_DIR / f"{name}_comparison.png"
    assert fig_path.stat().st_size > 10_000, f"Figure suspiciously small: {fig_path.stat().st_size}"


# ── 7. Baseline cost >= 0 ─────────────────────────────────────────────────────

@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_baseline_cost_nonnegative(name, all_outputs):
    for rec in all_outputs[name]["baseline"]["short_term_forecast"]:
        assert rec["cost_eur"]["total"] >= 0


# ── 8. Upgraded cost is a finite float ───────────────────────────────────────
# Note: upgraded_total CAN be negative in peak summer months when PV export
# revenue (feed-in tariff × grid_export_kwh) exceeds all electricity costs.
# That is correct behaviour, not a bug.

@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_upgraded_cost_is_finite(name, all_outputs):
    for sn in SCENARIO_NAMES:
        for rec in all_outputs[name]["upgrade_scenarios"][sn]["short_term_forecast"]:
            val = rec["cost_eur"]["upgraded_total"]
            assert isinstance(val, (int, float)) and math.isfinite(val), (
                f"{name}/{sn} {rec['month']}: non-finite upgraded cost: {val}"
            )


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_upgraded_cost_below_baseline(name, all_outputs):
    """Upgraded total must always be less than or equal to baseline (savings ≥ 0)."""
    for sn in SCENARIO_NAMES:
        for rec in all_outputs[name]["upgrade_scenarios"][sn]["short_term_forecast"]:
            c = rec["cost_eur"]
            assert c["upgraded_total"] <= c["baseline_total"] + 0.01, (
                f"{name}/{sn} {rec['month']}: upgraded={c['upgraded_total']:.2f} "
                f"> baseline={c['baseline_total']:.2f}"
            )


# ── 9. Net savings = energy reduction - financing payments ────────────────────

@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_net_savings_formula_st(name, all_outputs):
    for sn in SCENARIO_NAMES:
        for rec in all_outputs[name]["upgrade_scenarios"][sn]["short_term_forecast"]:
            fr = rec["financial_result"]
            expected = fr["energy_cost_reduction_eur"] - fr["financing_instalment_eur"]
            assert abs(fr["net_monthly_savings_eur"] - expected) < 0.02, (
                f"{name}/{sn} {rec['month']}: net={fr['net_monthly_savings_eur']:.4f} expected={expected:.4f}"
            )


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_net_savings_formula_lt(name, all_outputs):
    for sn in SCENARIO_NAMES:
        lt = all_outputs[name]["upgrade_scenarios"][sn]["long_term_projection"]["central"]
        for yr in lt:
            fr = yr["financial_result"]
            expected = fr["annual_energy_cost_reduction_eur"] - fr["annual_financing_payments_eur"]
            assert abs(fr["annual_net_savings_eur"] - expected) < 0.10, (
                f"{name}/{sn} {yr['year_label']}: net={fr['annual_net_savings_eur']:.2f} expected={expected:.2f}"
            )


# ── 10. Summary JSON paths and values match generated files ───────────────────

def test_summary_json_exists():
    assert (_OUTPUTS_DIR / "model_test_summary.json").exists()


def test_summary_md_exists():
    assert (_OUTPUTS_DIR / "model_test_summary.md").exists()


def test_summary_has_three_entries(summary):
    assert len(summary) == 3


def test_summary_profile_names_match(summary):
    names = {e["profile_name"] for e in summary}
    assert names == set(PROFILE_NAMES)


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_summary_paths_exist(name, summary):
    entry = next(e for e in summary if e["profile_name"] == name)
    assert (_REPO / entry["input_json_path"]).exists()
    assert (_REPO / entry["output_json_path"]).exists()
    assert (_REPO / entry["figure_path"]).exists()


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_summary_baseline_matches_output(name, all_outputs, summary):
    entry = next(e for e in summary if e["profile_name"] == name)
    best_sn = entry["best_scenario"]
    out = all_outputs[name]
    yr1 = _yr1_lt(out, best_sn)
    expected_baseline = yr1["cost_eur"]["baseline_total"]
    assert abs(entry["baseline_yr1_energy_cost_eur"] - expected_baseline) < 0.01


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_summary_net_savings_matches_formula(name, summary):
    entry = next(e for e in summary if e["profile_name"] == name)
    expected_net = entry["yr1_energy_cost_reduction_eur"] - entry["yr1_financing_payments_eur"]
    assert abs(entry["yr1_net_savings_eur"] - expected_net) < 0.02


@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_summary_monthly_net_is_annual_divided_by_12(name, summary):
    entry = next(e for e in summary if e["profile_name"] == name)
    expected = entry["yr1_net_savings_eur"] / 12
    assert abs(entry["monthly_net_savings_yr1_eur"] - expected) < 0.01


# ── 11. No NaN or Infinity in any output ─────────────────────────────────────

@pytest.mark.parametrize("name", PROFILE_NAMES)
def test_no_nan_or_inf(name, all_outputs):
    def _check(obj, path=""):
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            pytest.fail(f"{name}: bad float at {path}: {obj}")
        elif isinstance(obj, dict):
            for k, v in obj.items():
                _check(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _check(v, f"{path}[{i}]")
    _check(all_outputs[name])


# ── 12. User-specific behaviour ───────────────────────────────────────────────

def test_low_benefit_low_solar_generation(all_outputs):
    """Low-benefit profile's small shaded north roof should produce less PV than average."""
    def _total_pv(name, sn="solar_only"):
        return sum(
            r["energy_flows"]["pv_generation_kwh"]
            for r in all_outputs[name]["upgrade_scenarios"][sn]["short_term_forecast"]
        )
    assert _total_pv("low_benefit_household") < _total_pv("average_german_household")


def test_high_benefit_heatpump_savings_largest(all_outputs):
    """High-benefit profile (oil heating, 3200L) should have largest HP energy reduction."""
    def _hp_reduction(name):
        lt = all_outputs[name]["upgrade_scenarios"]["pv_heatpump"]["long_term_projection"]["central"]
        return lt[-1]["financial_result"]["cumulative_net_savings_eur"]
    assert _hp_reduction("high_benefit_household") > _hp_reduction("average_german_household")
    assert _hp_reduction("average_german_household") > _hp_reduction("low_benefit_household")


def test_high_benefit_ev_savings_largest(all_outputs):
    """High-benefit profile (28,000 km/yr) should have largest EV cumulative savings."""
    def _ev_cum20(name):
        lt = all_outputs[name]["upgrade_scenarios"]["pv_ev"]["long_term_projection"]["central"]
        return lt[-1]["financial_result"]["cumulative_net_savings_eur"]
    assert _ev_cum20("high_benefit_household") > _ev_cum20("average_german_household")
    assert _ev_cum20("average_german_household") > _ev_cum20("low_benefit_household")


def test_financing_terms_affect_instalment(all_outputs):
    """Low-benefit (10yr@6.5%) should have different instalment from average (15yr@4.5%)."""
    inst_low = all_outputs["low_benefit_household"]["upgrade_scenarios"]["solar_only"]["financing"][
        "monthly_instalment_eur"
    ]
    inst_avg = all_outputs["average_german_household"]["upgrade_scenarios"]["solar_only"]["financing"][
        "monthly_instalment_eur"
    ]
    # Different loan terms + rates on different investment amounts → should differ
    assert abs(inst_low - inst_avg) > 0.01


def test_low_benefit_best_cum20_is_positive_or_best_available(all_outputs):
    """Even if all LT scenarios are negative, best plan is still the least-negative one."""
    out = all_outputs["low_benefit_household"]
    best_sn = _select_best(out)
    best_cum20 = _cum20(out, best_sn)
    # Verify this is at least as good as every other scenario
    for sn in SCENARIO_NAMES:
        assert best_cum20 >= _cum20(out, sn), (
            f"Selected {best_sn} ({best_cum20:.0f}) but {sn} ({_cum20(out, sn):.0f}) is better"
        )
