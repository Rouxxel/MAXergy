"""
Recommendation service: rank forecast scenarios and explain the best one.

Single ranking function shared by POST /recommendation and POST /plan (and later the benchmark
and the MCP). The rationale is built only from ForecastResult fields — no other numbers.

Metrics (documented in documentation/app/API_CONTRACT.md):
- cumulative_central: cumulative net savings at the end of the horizon, central price scenario.
  Tie-breaks: higher first-year net saving, then lower monthly instalment.
- monthly_net: average monthly net saving over the first 12 months.
  Tie-breaks: higher cumulative net savings, then lower monthly instalment.
"""

from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import (
    ForecastResult,
    RankedScenarioItem,
    Recommendation,
    RecommendationMetric,
    Scenario,
)

COMPONENT_LABELS = {
    "solar_pv": "solar panels",
    "battery": "battery storage",
    "heat_pump": "a heat pump",
    "ev_charger": "an EV charger",
}

METRIC_DESCRIPTIONS = {
    RecommendationMetric.CUMULATIVE_CENTRAL: "long-term net savings",
    RecommendationMetric.MONTHLY_NET: "monthly net savings in the first year",
}


def default_metric() -> RecommendationMetric:
    """Ranking metric configured in config_file.json (`recommendation.default_metric`)."""
    value = config_loader.get("recommendation", {}).get("default_metric", RecommendationMetric.CUMULATIVE_CENTRAL.value)
    return RecommendationMetric(value)


def _cumulative(s: Scenario) -> float:
    return s.financials.cumulative_net_savings_central_eur if s.financials else float("-inf")


def _first_year_net(s: Scenario) -> float:
    return s.long_term_forecast[0].annual_saving_eur if s.long_term_forecast else s.monthly_saving_eur * 12


def _sort_key(s: Scenario, metric: RecommendationMetric) -> tuple:
    instalment = s.monthly_cost_eur.financing_installment
    if metric is RecommendationMetric.MONTHLY_NET:
        return (s.monthly_saving_eur, _cumulative(s), -instalment)
    return (_cumulative(s), _first_year_net(s), -instalment)


def _score(s: Scenario, metric: RecommendationMetric) -> float:
    return s.monthly_saving_eur if metric is RecommendationMetric.MONTHLY_NET else _cumulative(s)


def _describe(s: Scenario) -> str:
    parts = [COMPONENT_LABELS[c] for c, on in s.components.model_dump().items() if on]
    text = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]
    return text[0].upper() + text[1:]


def _euro(value: float) -> str:
    """Unsigned euro amount (the sentence carries the direction)."""
    return f"€{abs(value):,.0f}"


def _signed_euro(value: float) -> str:
    return ("-" if value < 0 else "") + _euro(value)


def build_rationale(s: Scenario, metric: RecommendationMetric) -> str:
    """Plain-language explanation of a scenario using only its forecast fields."""
    instalment = s.monthly_cost_eur.financing_installment
    sentences = [f"{_describe(s)} ({s.id}) ranks best by {METRIC_DESCRIPTIONS[metric]}."]

    if s.monthly_saving_eur >= 0:
        sentences.append(
            f"In the first year it lowers your total monthly energy outgoings by about "
            f"{_euro(s.monthly_saving_eur)}/month, already including the {_euro(instalment)}/month loan instalment."
        )
    else:
        loan_years = round(s.financials.loan_term_months / 12) if s.financials else None
        during = f"During the {loan_years}-year loan" if loan_years else "While the loan runs"
        sentences.append(
            f"{during} it costs about {_euro(s.monthly_saving_eur)}/month more than today "
            f"(loan instalment {_euro(instalment)}/month)."
        )
    if s.monthly_saving_post_payoff_eur is not None:
        sentences.append(
            f"Once the loan is repaid it saves about {_euro(s.monthly_saving_post_payoff_eur)}/month at today's prices."
        )

    f = s.financials
    if f:
        span = f"{_signed_euro(f.cumulative_net_savings_low_eur)} to {_signed_euro(f.cumulative_net_savings_high_eur)}"
        if f.cumulative_net_savings_central_eur > 0:
            sentences.append(
                f"Over {f.horizon_years} years the cumulative net saving is about "
                f"{_euro(f.cumulative_net_savings_central_eur)} (central price scenario; {span} across low/high prices)"
                + (f", breaking even in year {f.break_even_year}." if f.break_even_year else ".")
            )
        else:
            sentences.append(
                f"Over {f.horizon_years} years it does not pay back under the central price scenario "
                f"(cumulative net {_signed_euro(f.cumulative_net_savings_central_eur)})."
            )
    return " ".join(sentences)


def build_recommendation(
    forecast: ForecastResult, metric: RecommendationMetric | None = None
) -> Recommendation:
    """Rank the forecast's scenarios by `metric` (config default when None) and explain the best."""
    metric = metric or default_metric()
    ranked = sorted(forecast.scenarios, key=lambda s: _sort_key(s, metric), reverse=True)
    items = [RankedScenarioItem(id=s.id, score_eur=round(_score(s, metric), 2), metric=metric) for s in ranked]

    if not ranked:
        return Recommendation(
            selected_scenario_id=None,
            selected_scenario=None,
            ranked_scenarios=[],
            metric_used=metric,
            rationale=(
                "No upgrade scenario is available for this household with the selected options "
                "(e.g. no usable roof for solar), so only the current costs are shown."
            ),
        )

    best = ranked[0]
    return Recommendation(
        selected_scenario_id=best.id,
        selected_scenario=best,
        ranked_scenarios=items,
        metric_used=metric,
        rationale=build_rationale(best, metric),
    )
