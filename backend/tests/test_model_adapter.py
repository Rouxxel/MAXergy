"""Golden tests: adapter output vs. the stored production output for the average household.

Reference values: documentation/data/test_outputs/model_test_summary.md
"""

import json
from pathlib import Path

import pytest

from src.models.forecast_schemas import ForecastResult
from src.services.forecasting.model_adapter import adapt_forecast, is_scenario_enabled

REPO_ROOT = Path(__file__).resolve().parents[2]

_GOLDEN = REPO_ROOT / "documentation" / "data" / "test_outputs" / "average_german_household_output.json"


@pytest.fixture(scope="module")
def raw() -> dict:
    return json.loads(_GOLDEN.read_text())


@pytest.fixture(scope="module")
def forecast(raw) -> ForecastResult:
    return adapt_forecast(raw)


def _scenario(forecast: ForecastResult, sn: str):
    return next(s for s in forecast.scenarios if s.id == sn)


def test_all_six_scenarios(forecast):
    assert [s.id for s in forecast.scenarios] == [
        "solar_only", "pv_battery", "pv_heatpump", "pv_ev", "pv_battery_heatpump", "full_upgrade",
    ]
    assert forecast.model.engine == "energy_model"


def test_full_upgrade_reference_values(forecast):
    s = _scenario(forecast, "full_upgrade")
    assert s.monthly_cost_eur.financing_installment == pytest.approx(209.35, abs=0.01)
    assert s.long_term_forecast[0].annual_saving_eur == pytest.approx(-297.0, abs=1)
    assert s.financials.cumulative_net_savings_central_eur == pytest.approx(24828, abs=1)
    assert s.monthly_saving_eur < 0 < s.monthly_saving_post_payoff_eur


def test_totals_reconcile(forecast):
    b = forecast.baseline.monthly_cost_eur
    assert b.total == pytest.approx(b.electricity + b.heating + b.mobility, abs=0.011)
    for s in forecast.scenarios:
        c = s.monthly_cost_eur
        assert c.total == pytest.approx(c.electricity + c.heating + c.mobility + c.financing_installment, abs=0.011)
        assert s.monthly_saving_eur == pytest.approx(b.total - c.total, abs=0.011)
        assert s.monthly_saving_post_payoff_eur == pytest.approx(s.monthly_saving_eur + c.financing_installment, abs=0.011)


def test_month_rows_match_engine(raw, forecast):
    s = _scenario(forecast, "full_upgrade")
    engine_month = raw["upgrade_scenarios"]["full_upgrade"]["short_term_forecast"][0]
    assert s.short_term_forecast[0].saving_eur == engine_month["financial_result"]["net_monthly_savings_eur"]
    assert s.short_term_forecast[0].month == engine_month["month"]


def test_payback_consistent_with_cumulative(forecast):
    for s in forecast.scenarios:
        cums = [p.cumulative_saving_eur for p in s.long_term_forecast]
        if s.financials.break_even_year is None:
            assert s.payback_month is None
            assert all(c <= 0 for c in cums)
        else:
            idx = s.financials.break_even_year - 1
            assert cums[idx] > 0 and all(c <= 0 for c in cums[:idx])
            assert idx * 12 < s.payback_month <= (idx + 1) * 12


def test_band_and_ratios(forecast):
    for s in forecast.scenarios:
        assert set(s.long_term_band) == {"low", "high"}
        assert 0 <= s.self_consumption_ratio <= 1
        f = s.financials
        assert f.cumulative_net_savings_low_eur <= f.cumulative_net_savings_central_eur <= f.cumulative_net_savings_high_eur


def test_candidate_filtering(raw):
    candidates = {"solar_pv": True, "battery": True, "heat_pump": False, "ev_charger": False}
    forecast = adapt_forecast(raw, candidates)
    assert [s.id for s in forecast.scenarios] == ["solar_only", "pv_battery"]
    assert not is_scenario_enabled("solar_only", {"solar_pv": False})
