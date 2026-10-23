"""Endpoint tests for POST /plan and POST /recommendation (real engine)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.models.forecast_schemas import PlanResponse, Recommendation
from src.services.forecasting import baseline_service
from src.services.forecasting.baseline_service import get_forecasting_service


@pytest.fixture(scope="module")
def client():
    from main import app

    return TestClient(app, base_url="http://localhost")


def test_plan_and_recommendation_share_one_engine_run(client, assessment_dict):
    get_forecasting_service().clear_cache()
    real_compute = baseline_service.compute_model
    with patch.object(baseline_service, "compute_model", side_effect=real_compute) as engine:
        plan = client.post("/plan", json=assessment_dict)
        rec = client.post("/recommendation", json=assessment_dict)
    assert plan.status_code == 200 and rec.status_code == 200
    assert engine.call_count == 1

    plan_body = PlanResponse.model_validate(plan.json())
    rec_body = Recommendation.model_validate(rec.json())
    assert len(plan_body.forecast.scenarios) == 6
    assert plan_body.recommendation.selected_scenario_id == rec_body.selected_scenario_id
    assert plan_body.recommendation.metric_used.value == "cumulative_central"
    assert plan_body.recommendation.rationale


def test_recommendation_metric_query_param(client, assessment_dict):
    rec = client.post("/recommendation", params={"metric": "monthly_net"}, json=assessment_dict)
    assert rec.status_code == 200
    body = Recommendation.model_validate(rec.json())
    assert body.metric_used.value == "monthly_net"
    assert body.selected_scenario_id == max(
        body.ranked_scenarios, key=lambda i: i.score_eur
    ).id


def test_plan_rejects_unsupported_heating(client, assessment_dict):
    assessment_dict["heating"]["fuel_type"] = "coal"
    response = client.post("/plan", json=assessment_dict)
    assert response.status_code == 422
    assert "supported fuels" in response.json()["detail"]
