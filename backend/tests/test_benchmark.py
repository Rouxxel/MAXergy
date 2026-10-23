"""GET /benchmark is computed by the same services as POST /plan (nothing hard-coded)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.services.benchmark import benchmark_service

PROFILE = Path(__file__).resolve().parents[2] / "documentation/data/test_profiles/average_german_household.json"


@pytest.fixture
def client():
    from main import app

    benchmark_service.clear_cache()
    yield TestClient(app, base_url="http://localhost")
    benchmark_service.clear_cache()


def test_benchmark_matches_plan_for_the_same_household(client):
    bench = client.get("/benchmark").json()
    plan = client.post("/plan", json=json.loads(PROFILE.read_text(encoding="utf-8"))).json()
    rec = plan["recommendation"]
    best = rec["selected_scenario"]

    assert bench["recommendation"]["scenario"] == rec["selected_scenario_id"]
    assert bench["recommendation"]["rationale"] == rec["rationale"]
    assert bench["recommendation"]["monthly_instalment_eur"] == best["monthly_cost_eur"]["financing_installment"]
    assert bench["recommendation"]["monthly_saving_eur"] == best["monthly_saving_eur"]
    assert bench["recommendation"]["cumulative_savings_eur"] == best["financials"]["cumulative_net_savings_central_eur"]
    assert bench["recommendation"]["break_even_year"] == best["financials"]["break_even_year"]
    assert bench["scenarios_count"] == len(plan["forecast"]["scenarios"])
    assert bench["model_version"] == plan["forecast"]["model"]["version"]
    assert bench["forecast_start"] == plan["forecast"]["baseline"]["short_term_forecast"][0]["month"]
    series = bench["cumulative_series"]
    assert len(series) == bench["projection_years"]
    assert series[-1]["central"] == best["long_term_forecast"][-1]["cumulative_saving_eur"]
    assert series[-1]["low"] <= series[-1]["central"] <= series[-1]["high"]


def test_benchmark_household_comes_from_the_profile(client):
    household = client.get("/benchmark").json()["household"]
    assert household == {
        "location": "50667, DE",
        "occupants": 3,
        "annual_electricity_kwh": 3500.0,
        "heating_type": "gas",
        "heating_annual_kwh": 14000.0,
        "vehicle_type": "petrol",
        "annual_mileage_km": 12000.0,
        "roof_area_m2": 35.0,
        "roof_orientation": "south",
        "roof_tilt_deg": 32.0,
    }


def test_benchmark_is_cached(client, monkeypatch):
    first = client.get("/benchmark").json()
    monkeypatch.setattr(benchmark_service, "compute_benchmark", lambda: pytest.fail("recomputed within TTL"))
    assert client.get("/benchmark").json() == first


def test_benchmark_failure_is_500(client, monkeypatch):
    def boom():
        raise RuntimeError("engine down")

    monkeypatch.setattr(benchmark_service, "compute_benchmark", boom)
    assert client.get("/benchmark").status_code == 500
