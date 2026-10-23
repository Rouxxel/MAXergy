"""The three documented household profiles are full HouseholdAssessment documents.

They must pass API validation, run through the normalizer and the production engine without
errors, and give the best plan and loan instalment recorded in
documentation/data/test_outputs/model_test_summary.json. The cumulative totals are not compared:
the engine starts its forecast in the month after today, so year-1 seasonality (and with it the
20-year total) shifts with the run date.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.models.forecast_schemas import HouseholdAssessment
from src.services.forecasting.engine import compute_model
from src.services.forecasting.input_normalizer import normalize_assessment

REPO = Path(__file__).resolve().parents[2]
PROFILES = REPO / "documentation" / "data" / "test_profiles"
SUMMARY = {
    s["profile_name"]: s
    for s in json.loads((REPO / "documentation/data/test_outputs/model_test_summary.json").read_text(encoding="utf-8"))
}


def _profile(name: str) -> dict:
    return json.loads((PROFILES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", sorted(SUMMARY))
def test_profile_runs_through_api_path(name):
    assessment = HouseholdAssessment.model_validate(_profile(name))
    out = compute_model(normalize_assessment(assessment))
    best = out["upgrade_scenarios"][SUMMARY[name]["best_scenario"]]
    assert best["financing"]["monthly_instalment_eur"] == SUMMARY[name]["monthly_instalment_eur"]


@pytest.mark.parametrize("name", sorted(SUMMARY))
def test_profile_plan_recommends_documented_best(name):
    from main import app

    response = TestClient(app, base_url="http://localhost").post("/plan", json=_profile(name))
    assert response.status_code == 200
    assert response.json()["recommendation"]["selected_scenario_id"] == SUMMARY[name]["best_scenario"]


def test_roof_unavailable_returns_baseline_only(assessment_dict):
    from main import app

    assessment_dict["household"]["roof"] = {
        "available": False,
        "usable_area_m2": None,
        "orientation": None,
        "tilt_deg": None,
        "shading_factor": None,
    }
    response = TestClient(app, base_url="http://localhost").post("/plan", json=assessment_dict)
    assert response.status_code == 200
    body = response.json()
    assert body["forecast"]["scenarios"] == []
    assert body["forecast"]["baseline"]["monthly_cost_eur"]["total"] > 0
    assert body["recommendation"]["selected_scenario_id"] is None
    assert "no usable roof" in body["recommendation"]["rationale"]
