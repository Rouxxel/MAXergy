"""Tests for the shared recommendation service (ranking metrics, tie-breaks, rationale)."""

import json
from pathlib import Path

import pytest

from src.models.forecast_schemas import RecommendationMetric
from src.services.forecasting.model_adapter import adapt_forecast
from src.services.recommendation.recommendation_service import (
    build_recommendation,
    default_metric,
)

_PROFILES = Path(__file__).resolve().parents[2] / "documentation" / "data" / "test_outputs"


def _forecast(name: str):
    return adapt_forecast(json.loads((_PROFILES / f"{name}_output.json").read_text()))


@pytest.fixture(scope="module")
def average():
    return _forecast("average_german_household")


@pytest.mark.parametrize(
    ("profile", "best"),
    [
        ("average_german_household", "full_upgrade"),
        ("low_benefit_household", "pv_ev"),
        ("high_benefit_household", "full_upgrade"),
    ],
)
def test_cumulative_matches_reference_best_plans(profile, best):
    """Same best plan as model_test_summary.md / select_best_scenario() for all three profiles."""
    rec = build_recommendation(_forecast(profile), RecommendationMetric.CUMULATIVE_CENTRAL)
    assert rec.selected_scenario_id == best


def test_ranking_is_sorted_and_complete(average):
    rec = build_recommendation(average, RecommendationMetric.CUMULATIVE_CENTRAL)
    scores = [item.score_eur for item in rec.ranked_scenarios]
    assert scores == sorted(scores, reverse=True)
    assert {i.id for i in rec.ranked_scenarios} == {s.id for s in average.scenarios}
    assert rec.ranked_scenarios[0].score_eur == pytest.approx(24828, abs=1)
    assert all(i.metric is RecommendationMetric.CUMULATIVE_CENTRAL for i in rec.ranked_scenarios)


def test_monthly_net_metric(average):
    rec = build_recommendation(average, RecommendationMetric.MONTHLY_NET)
    best = max(average.scenarios, key=lambda s: s.monthly_saving_eur)
    assert rec.selected_scenario_id == best.id
    assert rec.ranked_scenarios[0].score_eur == pytest.approx(best.monthly_saving_eur, abs=0.01)


def test_tie_break_prefers_lower_instalment(average):
    a, b = average.scenarios[0].model_copy(deep=True), average.scenarios[1].model_copy(deep=True)
    for s in (a, b):
        s.financials.cumulative_net_savings_central_eur = 1000.0
        s.long_term_forecast[0].annual_saving_eur = 100.0
    a.monthly_cost_eur.financing_installment, b.monthly_cost_eur.financing_installment = 200.0, 100.0
    forecast = average.model_copy(update={"scenarios": [a, b]})
    assert build_recommendation(forecast, RecommendationMetric.CUMULATIVE_CENTRAL).selected_scenario_id == b.id


def test_rationale_uses_forecast_numbers_and_explains_negative_savings(average):
    rec = build_recommendation(average, RecommendationMetric.CUMULATIVE_CENTRAL)
    s = rec.selected_scenario
    assert s.monthly_saving_eur < 0
    text = rec.rationale
    assert "full_upgrade" in text
    assert "more than today" in text
    assert f"€{abs(s.monthly_saving_eur):,.0f}/month" in text
    assert f"€{s.monthly_saving_post_payoff_eur:,.0f}/month" in text
    assert f"€{s.financials.cumulative_net_savings_central_eur:,.0f}" in text
    assert f"year {s.financials.break_even_year}" in text
    assert "an EV charger" in text


def test_no_scenarios_gives_empty_recommendation(average):
    rec = build_recommendation(average.model_copy(update={"scenarios": []}))
    assert rec.selected_scenario_id is None and rec.selected_scenario is None
    assert rec.ranked_scenarios == []
    assert "No upgrade scenario" in rec.rationale


def test_default_metric_from_config():
    assert default_metric() is RecommendationMetric.CUMULATIVE_CENTRAL
