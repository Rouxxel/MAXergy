"""Tests for GET /assumptions (engine defaults)."""

from fastapi.testclient import TestClient

from src.services.forecasting.assumptions_service import get_assumptions


def test_assumptions_match_engine_defaults():
    a = get_assumptions()
    assert a["tariff"]["arbeitspreis_eur_per_kwh"] == 0.32
    assert a["solar"]["m2_per_kwp"] == 6.0
    assert a["solar"]["regional_yield_kwh_per_kwp"]["1"] == 950.0
    assert a["solar"]["feed_in_tariff_eur_per_kwh"]["up_to_10_kwp"] == 0.082
    assert a["heat_pump"]["scop"] == 3.0
    assert a["battery"]["default_usable_kwh"] == 10.0
    assert a["investment_costs"]["battery_eur_per_kwh"] == 600.0
    assert a["supported"]["heating_fuels"] == ["gas", "oil"]


def test_assumptions_endpoint():
    from main import app

    response = TestClient(app, base_url="http://localhost").get("/assumptions")
    assert response.status_code == 200
    assert response.json() == get_assumptions()
    assert "max-age" in response.headers["cache-control"]
