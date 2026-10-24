"""
Grounding text for the AI advisor, built only from the plan (forecast + recommendation) the user
is looking at. Uses the same three numbers and wording as the app and the MCP: year-1 monthly net
with the loan, saving after payoff, and cumulative net savings over the horizon.
"""

from src.models.forecast_schemas import PlanResponse, Scenario

_COMPONENT_NAMES = {
    "solar_pv": "solar panels",
    "battery": "battery storage",
    "heat_pump": "heat pump",
    "ev_charger": "EV charger",
}


def _eur(n: float) -> str:
    return f"€{abs(n):,.0f}"


def _signed(n: float) -> str:
    return f"{'−' if n < 0 else '+'}€{abs(n):,.0f}"


def scenario_sentence(s: Scenario) -> str:
    """Same sentence as the app (`summarizeSavings`) and the MCP tool headlines."""
    now, after, f = s.monthly_saving_eur, s.monthly_saving_post_payoff_eur, s.financials
    tail = f"; {f.horizon_years}-year net {_signed(f.cumulative_net_savings_central_eur)}" if f else ""
    if now >= 0:
        return f"Saves {_eur(now)}/month from the start (loan included), {_eur(after)}/month after payoff{tail}."
    loan = f"the {round(f.loan_term_months / 12)}-year loan" if f else "the loan"
    return f"Costs {_eur(now)}/month more during {loan}, then saves {_eur(after)}/month{tail}."


def _components(s: Scenario) -> str:
    return ", ".join(name for key, name in _COMPONENT_NAMES.items() if getattr(s.components, key)) or "none"


def build_plan_context(plan: PlanResponse) -> str:
    """Facts the advisor may quote; every number comes from the plan."""
    forecast, rec = plan.forecast, plan.recommendation
    base = forecast.baseline.monthly_cost_eur
    by_id = {s.id: s for s in forecast.scenarios}
    lines = [
        "HOUSEHOLD PLAN (computed by the MAXergy engine — quote these numbers, never invent others):",
        f"- Current monthly energy costs: electricity {_eur(base.electricity)}, heating {_eur(base.heating)}, "
        f"mobility {_eur(base.mobility)}, total {_eur(base.total)}.",
    ]
    best = rec.selected_scenario
    if best is None:
        lines.append("- No upgrade scenario is possible for this household with the selected options.")
    else:
        f = best.financials
        lines += [
            f"- Recommended scenario: {best.id} ({_components(best)}), ranked by {rec.metric_used.value}.",
            f"- {scenario_sentence(best)}",
            f"- Loan instalment {_eur(best.monthly_cost_eur.financing_installment)}/month"
            + (
                f" for {round(f.loan_term_months / 12)} years; gross investment {_eur(f.gross_investment_eur)}, "
                f"subsidy {_eur(f.subsidy_eur)}; break-even "
                + (f"year {f.break_even_year}" if f.break_even_year else "not reached")
                + f"; {f.horizon_years}-year range {_signed(f.cumulative_net_savings_low_eur)} to "
                f"{_signed(f.cumulative_net_savings_high_eur)} (low/high energy prices)."
                if f
                else "."
            ),
        ]
    ranked = [by_id[r.id] for r in rec.ranked_scenarios if r.id in by_id][:3]
    if ranked:
        lines.append("- Top ranked scenarios:")
        lines += [f"  {i}. {s.id} ({_components(s)}): {scenario_sentence(s)}" for i, s in enumerate(ranked, 1)]
    lines.append(f"- Rationale: {rec.rationale}")
    if forecast.validation_warnings:
        lines.append("- Assumptions/warnings: " + "; ".join(forecast.validation_warnings))
    return "\n".join(lines)
