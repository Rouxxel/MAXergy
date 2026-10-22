"""Tests for the assessment -> engine input normalizer."""

import pytest

from src.models.forecast_schemas import HouseholdAssessment
from src.services.forecasting.input_normalizer import UnsupportedInputError, normalize_assessment


def test_passes_through_canonical_input(assessment_dict):
    out = normalize_assessment(HouseholdAssessment(**assessment_dict))
    assert out["heating"]["fuel_type"] == "gas"
    assert out["mobility"]["vehicles"][0]["vehicle_type"] == "petrol"
    assert all(out["upgrade_candidates"][k] for k in ("solar_pv", "battery", "heat_pump", "ev_charger"))


def test_rejects_unsupported_heating(assessment_dict):
    assessment_dict["heating"]["fuel_type"] = "district"
    with pytest.raises(UnsupportedInputError, match="gas, oil"):
        normalize_assessment(HouseholdAssessment(**assessment_dict))


def test_no_roof_disables_solar(assessment_dict):
    assessment_dict["household"]["roof"]["available"] = False
    out = normalize_assessment(HouseholdAssessment(**assessment_dict))
    assert out["upgrade_candidates"]["solar_pv"] is False


def test_no_combustion_vehicle_disables_ev_charger(assessment_dict):
    assessment_dict["mobility"] = {"vehicle_count": 1, "vehicles": [{"vehicle_type": "ev", "annual_mileage_km": 9000}]}
    out = normalize_assessment(HouseholdAssessment(**assessment_dict))
    assert out["upgrade_candidates"]["ev_charger"] is False
