"""End-to-end tests: assessment -> production engine -> ForecastResult (service and router)."""

import pytest
from fastapi.testclient import TestClient

from src.models.forecast_schemas import ForecastResult, HouseholdAssessment
from src.services.forecasting.baseline_service import BaselineForecastingService


@pytest.fixture
def service() -> BaselineForecastingService:
    return BaselineForecastingService()


def test_service_uses_production_engine(service, assessment_dict):
    forecast = service.generate_forecast(HouseholdAssessment(**assessment_dict), use_cache=False)
    assert forecast.model.engine == "energy_model"
    assert forecast.baseline.monthly_cost_eur.total > 0
    assert len(forecast.scenarios) == 6
    assert len(forecast.baseline.short_term_forecast) == 12
    assert len(forecast.baseline.long_term_forecast) == 20
    full = next(s for s in forecast.scenarios if s.id == "full_upgrade")
    # Production engine: an average household pays more than it saves while the loan runs.
    assert full.monthly_saving_eur < 0 < full.monthly_saving_post_payoff_eur


def test_site_yield_increases_solar_savings(service, assessment_dict):
    base = service.generate_forecast(HouseholdAssessment(**assessment_dict), use_cache=False)
    assessment_dict["household"]["roof"]["specific_yield_kwh_per_kwp"] = 1150
    site = service.generate_forecast(HouseholdAssessment(**assessment_dict), use_cache=False)
    assert site.assumptions_used["pv_yield_source"] == "site"
    assert site.scenarios[0].monthly_saving_eur > base.scenarios[0].monthly_saving_eur


def test_cache(service, assessment_dict):
    a = HouseholdAssessment(**assessment_dict)
    assert service.generate_forecast(a) is service.generate_forecast(a)
    assessment_dict["household"]["occupants"] = 5
    assert service._create_cache_key(a) != service._create_cache_key(HouseholdAssessment(**assessment_dict))


def test_forecast_endpoint(assessment_dict):
    from main import app

    client = TestClient(app, base_url="http://localhost")
    ok = client.post("/forecast", json=assessment_dict)
    assert ok.status_code == 200
    ForecastResult.model_validate(ok.json())

    assessment_dict["heating"]["fuel_type"] = "pellets"
    bad = client.post("/forecast", json=assessment_dict)
    assert bad.status_code == 422
    assert "supported fuels" in bad.json()["detail"]
