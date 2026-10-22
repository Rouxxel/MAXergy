"""
Map the production engine output (energy_model.compute_model) to the API ForecastResult.

Definitions (documented in documentation/app/API_CONTRACT.md):
- Monthly figures are averages over the first 12 short-term months (constant current prices),
  so seasonal swings do not distort the headline number.
- Scenario electricity cost is net of feed-in revenue, so
  baseline.total - scenario.total == monthly_saving_eur.
- Long-term figures come from the central price scenario; low/high go to long_term_band.
"""

import math

from src.models.forecast_schemas import ForecastResult
from src.services.forecasting.engine import UPGRADE_SCENARIO_NAMES

HEADLINE_MONTHS = 12

SCENARIO_COMPONENTS: dict[str, dict[str, bool]] = {
    "solar_only":          {"solar_pv": True, "battery": False, "heat_pump": False, "ev_charger": False},
    "pv_battery":          {"solar_pv": True, "battery": True,  "heat_pump": False, "ev_charger": False},
    "pv_heatpump":         {"solar_pv": True, "battery": False, "heat_pump": True,  "ev_charger": False},
    "pv_ev":               {"solar_pv": True, "battery": False, "heat_pump": False, "ev_charger": True},
    "pv_battery_heatpump": {"solar_pv": True, "battery": True,  "heat_pump": True,  "ev_charger": False},
    "full_upgrade":        {"solar_pv": True, "battery": True,  "heat_pump": True,  "ev_charger": True},
}


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _r(value: float) -> float:
    return round(value, 2)


def _year(block: dict) -> int:
    return int(block["first_month"][:4])


def _adapt_baseline(baseline: dict) -> dict:
    st = baseline["short_term_forecast"]
    window = st[:HEADLINE_MONTHS]
    costs = {k: _r(_mean([m["cost_eur"][k] for m in window])) for k in ("electricity", "heating", "mobility")}
    costs["total"] = _r(sum(costs.values()))
    return {
        "monthly_cost_eur": costs,
        "short_term_forecast": [{"month": m["month"], "total_eur": m["cost_eur"]["total"]} for m in st],
        "long_term_forecast": [
            {"year": _year(y), "annual_total_eur": y["cost_eur"]["total"]}
            for y in baseline["long_term_projection"]["central"]
        ],
    }


def _lt_points(years: list[dict], scenario: str) -> list[dict]:
    return [
        {
            "year": _year(y),
            "annual_total_eur": _r(y["cost_eur"]["upgraded_total"] + y["financial_result"]["annual_financing_payments_eur"]),
            "annual_saving_eur": y["financial_result"]["annual_net_savings_eur"],
            "cumulative_saving_eur": y["financial_result"]["cumulative_net_savings_eur"],
            "scenario": scenario,
        }
        for y in years
    ]


def _payback(central: list[dict]) -> tuple[int | None, int | None]:
    """Return (payback_month, break_even_year) from the central annual projection.

    The month is interpolated linearly inside the first year whose cumulative net savings
    turn positive.
    """
    prev_cum = 0.0
    for idx, year in enumerate(central):
        fin = year["financial_result"]
        cum = fin["cumulative_net_savings_eur"]
        if cum > 0:
            annual = fin["annual_net_savings_eur"]
            share = -prev_cum / annual if prev_cum < 0 and annual > 0 else 0.0
            month = idx * 12 + max(1, math.ceil(12 * share))
            return month, idx + 1
        prev_cum = cum
    return None, None


def _adapt_scenario(sn: str, data: dict, baseline_costs: dict, assumptions: dict, candidates: dict) -> dict:
    window = data["short_term_forecast"][:HEADLINE_MONTHS]
    lt = data["long_term_projection"]
    central = lt["central"]

    electricity = _r(_mean([m["cost_eur"]["electricity"] - m["cost_eur"]["solar_export_revenue"] for m in window]))
    heating = _r(_mean([m["cost_eur"]["heating"] for m in window]))
    mobility = _r(_mean([m["cost_eur"]["mobility"] for m in window]))
    instalment = _r(_mean([m["financial_result"]["financing_instalment_eur"] for m in window]))
    total = _r(electricity + heating + mobility + instalment)

    flows = central[0]["energy_flows"]
    pv_gen = flows["pv_generation_kwh"]
    scr = (flows["pv_direct_self_consumption_kwh"] + flows["battery_discharge_kwh"]) / pv_gen if pv_gen > 0 else 0.0

    components = SCENARIO_COMPONENTS[sn]
    sizing = {"solar_pv_kwp": round(assumptions["solar_kwp"], 2)}
    if components["battery"]:
        sizing["battery_kwh"] = round(assumptions["battery_usable_kwh"], 1)
    if components["heat_pump"] and candidates.get("heat_pump_kw") is not None:
        sizing["heat_pump_kw"] = candidates["heat_pump_kw"]

    payback_month, break_even_year = _payback(central)
    investment = data["investment"]

    return {
        "id": sn,
        "components": components,
        "sizing": sizing,
        "monthly_cost_eur": {
            "electricity": electricity,
            "heating": heating,
            "mobility": mobility,
            "financing_installment": instalment,
            "total": total,
        },
        "monthly_saving_eur": _r(baseline_costs["total"] - total),
        "monthly_saving_post_payoff_eur": _r(baseline_costs["total"] - total + instalment),
        "self_consumption_ratio": round(min(scr, 1.0), 3),
        "short_term_forecast": [
            {
                "month": m["month"],
                "total_eur": _r(m["cost_eur"]["upgraded_total"] + m["financial_result"]["financing_instalment_eur"]),
                "saving_eur": m["financial_result"]["net_monthly_savings_eur"],
            }
            for m in data["short_term_forecast"]
        ],
        "long_term_forecast": _lt_points(central, "central"),
        "long_term_band": {ps: _lt_points(lt[ps], ps) for ps in ("low", "high")},
        "payback_month": payback_month,
        "financials": {
            "gross_investment_eur": investment["gross_investment_eur"],
            "subsidy_eur": investment["subsidy_eur"],
            "financed_principal_eur": investment["financed_principal_eur"],
            "loan_term_months": data["financing"]["loan_term_months"],
            "horizon_years": len(central),
            "cumulative_net_savings_central_eur": central[-1]["financial_result"]["cumulative_net_savings_eur"],
            "cumulative_net_savings_low_eur": lt["low"][-1]["financial_result"]["cumulative_net_savings_eur"],
            "cumulative_net_savings_high_eur": lt["high"][-1]["financial_result"]["cumulative_net_savings_eur"],
            "break_even_year": break_even_year,
        },
    }


def is_scenario_enabled(sn: str, candidates: dict) -> bool:
    """A scenario is offered only if every component it needs is an enabled candidate."""
    return all(candidates.get(c, False) for c, needed in SCENARIO_COMPONENTS[sn].items() if needed)


def adapt_forecast(engine_output: dict, candidates: dict | None = None) -> ForecastResult:
    """Build a ForecastResult from compute_model output.

    `candidates` are the effective upgrade_candidates flags (see input_normalizer); when
    omitted all six scenarios are returned.
    """
    candidates = candidates or {c: True for c in ("solar_pv", "battery", "heat_pump", "ev_charger")}
    baseline = _adapt_baseline(engine_output["baseline"])
    assumptions = engine_output["assumptions_used"]
    model = engine_output["model"]

    scenarios = [
        _adapt_scenario(sn, engine_output["upgrade_scenarios"][sn], baseline["monthly_cost_eur"], assumptions, candidates)
        for sn in UPGRADE_SCENARIO_NAMES
        if is_scenario_enabled(sn, candidates)
    ]

    return ForecastResult(
        model={"name": model["name"], "version": model["version"], "engine": "energy_model"},
        assumptions_used=assumptions,
        validation_warnings=list(engine_output.get("validation_warnings", [])),
        baseline=baseline,
        scenarios=scenarios,
    )
