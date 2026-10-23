"""MCP tools: every savings number must come verbatim from the backend's POST /plan."""

from __future__ import annotations

import json

import pytest

from conftest import call_tool, load


def test_overview_returns_backend_plan_verbatim(backend, assessment):
    out = call_tool("energy_savings_overview", {"assessment": assessment})
    assert out == load("plan_model_input1.json")

    request = backend.requests[-1]
    assert request.url.path == "/plan"
    assert request.headers["authorization"] == "Bearer svc-token"
    sent = json.loads(request.content)
    assert sent["location"] == assessment["location"]
    assert sent["mobility"]["vehicles"][0]["annual_mileage_km"] == 12000


def test_overview_passes_metric(backend, assessment):
    call_tool("energy_savings_overview", {"assessment": assessment, "metric": "monthly_net"})
    assert backend.requests[-1].url.params["metric"] == "monthly_net"


def test_compare_scenarios_uses_backend_ranking(backend, assessment):
    plan = load("plan_model_input1.json")
    out = call_tool("compare_scenarios", {"assessment": assessment})
    assert out["recommended"] == plan["recommendation"]["selected_scenario_id"]
    assert [r["id"] for r in out["ranked"]] == [i["id"] for i in plan["recommendation"]["ranked_scenarios"]]
    full = next(r for r in out["ranked"] if r["id"] == "full_upgrade")
    scenario = next(s for s in plan["forecast"]["scenarios"] if s["id"] == "full_upgrade")
    assert full["monthly_saving_eur"] == scenario["monthly_saving_eur"]
    assert full["financing_installment_eur"] == scenario["monthly_cost_eur"]["financing_installment"]
    assert "more while the loan runs" in full["headline"]


def test_project_savings_series(backend, assessment):
    out = call_tool("project_savings", {"assessment": assessment})
    plan = load("plan_model_input1.json")
    assert len(out["years"]) == 20
    assert {s["scenario"] for s in out["series"]} == {s["id"] for s in plan["forecast"]["scenarios"]}
    finals = [s["cumulative_eur"][-1] for s in out["series"]]
    assert finals == sorted(finals, reverse=True)
    full = next(s for s in out["series"] if s["scenario"] == "full_upgrade")
    expected = next(s for s in plan["forecast"]["scenarios"] if s["id"] == "full_upgrade")
    assert full["cumulative_eur"][-1] == round(expected["financials"]["cumulative_net_savings_central_eur"])


def test_next_best_upgrade_steps(backend, assessment):
    out = call_tool("next_best_upgrade", {"assessment": assessment})
    assert out["next_best_upgrade"]["id"] == "full_upgrade"
    step = next(s for s in out["steps"] if s["from"] == "pv_battery_heatpump")
    assert step["adds"] == ["ev_charger"]


def test_next_best_upgrade_from_current(backend, assessment):
    out = call_tool("next_best_upgrade", {"assessment": assessment, "current_scenario_id": "solar_only"})
    assert out["current"]["id"] == "solar_only"
    assert out["next_best_upgrade"]["id"] == "full_upgrade"
    assert set(out["step"]["adds"]) == {"battery", "ev_charger", "heat_pump"}


def test_next_best_upgrade_unknown_scenario(backend, assessment):
    with pytest.raises(Exception, match="Unknown scenario"):
        call_tool("next_best_upgrade", {"assessment": assessment, "current_scenario_id": "rocket"})


def test_backend_error_is_relayed(backend, assessment):
    backend.plan_status, backend.plan_body = 422, {"detail": "heating.fuel_type 'coal' is not supported"}
    with pytest.raises(Exception, match="not supported"):
        call_tool("energy_savings_overview", {"assessment": assessment})


def test_deprecated_aliases(backend, assessment):
    assert call_tool("recommend_upsell", {"assessment": assessment})["next_best_upgrade"]["id"] == "full_upgrade"
    assert call_tool("model_savings")["use_instead"] == "energy_savings_overview"


def test_suggestions_use_engine_assumptions(backend):
    price = call_tool("suggest_electricity_price", {"monthly_spend_eur": 120})
    assert price["suggested_arbeitspreis_eur_per_kwh"] == 0.32
    assert price["implied_annual_kwh"] == round((120 - 12.5) * 12 / 0.32)

    roof = call_tool("estimate_roof_capacity_from_area", {"floor_area_m2": 100})
    assert roof["usable_area_m2"] == 60
    assert roof["estimated_max_kwp"] == 10.0  # 60 m² / 6 m²/kWp

    heat = call_tool("estimate_heating_spend", {"living_area_m2": 120, "heating_type": "gas"})
    assert heat["estimated_annual_consumption"] == 15600
    assert heat["estimated_annual_heating_spend_eur"] == 1560  # 0.10 €/kWh

    assert call_tool("suggest_battery_kwh", {"pv_kwp": 6})["engine_default_kwh"] == 10.0
    assert sum(r.url.path == "/assumptions" for r in backend.requests) == 1  # cached


def test_unsupported_inputs_are_explained(backend):
    assert call_tool("estimate_heating_spend", {"living_area_m2": 100, "heating_type": "district"})["supported"] is False
    assert call_tool("suggest_electricity_price", {"building_type": "office"})["supported"] is False


def test_onboarding_script_is_single_source():
    from maxergy_mcp.instructions import ONBOARDING_SCRIPT
    from maxergy_mcp.server import mcp

    assert call_tool("start_advisor") == {"result": ONBOARDING_SCRIPT}
    assert "energy_savings_overview" in mcp.instructions
