"""Unit tests for the forecasting service (engine mocked).

The engine call (`compute_model`) is replaced by the stored production output for the
average German household, so these tests cover the service logic only: normalization,
candidate filtering, error propagation and caching.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.models.forecast_schemas import ForecastResult, HouseholdAssessment
from src.services.forecasting.baseline_service import BaselineForecastingService

_ENGINE_OUTPUT = (
    Path(__file__).resolve().parents[3]
    / "documentation" / "data" / "test_outputs" / "average_german_household_output.json"
)
_COMPUTE_MODEL = "src.services.forecasting.baseline_service.compute_model"


@pytest.fixture(scope="module")
def engine_output() -> dict:
    return json.loads(_ENGINE_OUTPUT.read_text())


@pytest.fixture
def mock_assessment():
    """A two-person household without a car; only solar and battery are on the table."""
    return HouseholdAssessment(
        location={"postcode": "10115", "country": "DE"},
        household={
            "occupants": 2,
            "electricity": {
                "annual_kwh": 3500,
                "current_tariff_type": "fixed",
                "arbeitspreis_eur_per_kwh": 0.35,
                "grundpreis_eur_per_month": 10.0,
                "contract_end_date": None,
            },
            "roof": {
                "available": True,
                "usable_area_m2": 50,
                "orientation": "south",
                "tilt_deg": 35,
                "shading_factor": 0.1,
            },
        },
        heating={
            "fuel_type": "gas",
            "annual_consumption": 15000,
            "annual_spend_eur": 1800,
            "building": {"floor_area_m2": 120, "insulation_class": "average"},
        },
        mobility={"vehicle_count": 0, "vehicles": []},
        upgrade_candidates={
            "solar_pv": True,
            "battery": True,
            "heat_pump": False,
            "ev_charger": False,
            "solar_pv_kwp": 5,
            "battery_kwh": 7.5,
            "heat_pump_kw": None,
        },
        financing={
            "loan_term_years": 10,
            "loan_rate_pct": 4.5,
            "known_subsidy_eur": 3000,
        },
        forecast_horizon={"short_term_months": 12, "long_term_years": 20},
    )


@pytest.fixture
def baseline_service():
    """Create a forecasting service instance with an empty cache."""
    return BaselineForecastingService()


class TestBaselineForecastingService:
    """Test cases for BaselineForecastingService."""

    def test_service_initialization(self, baseline_service):
        """The service starts with an empty cache."""
        assert baseline_service._cache == {}

    def test_generate_forecast_success(self, baseline_service, mock_assessment, engine_output):
        """Engine output is adapted and filtered to the enabled upgrade candidates."""
        with patch(_COMPUTE_MODEL, return_value=engine_output) as mock_engine:
            result = baseline_service.generate_forecast(mock_assessment)

        assert isinstance(result, ForecastResult)
        assert [s.id for s in result.scenarios] == ["solar_only", "pv_battery"]
        engine_input = mock_engine.call_args.args[0]
        assert engine_input["upgrade_candidates"]["ev_charger"] is False
        assert engine_input["financing"]["known_subsidy_eur"] == 3000

    def test_generate_forecast_model_failure(self, baseline_service, mock_assessment):
        """Engine failures propagate to the caller (the router turns them into HTTP 500)."""
        with patch(_COMPUTE_MODEL, side_effect=RuntimeError("Model execution failed")):
            with pytest.raises(RuntimeError, match="Model execution failed"):
                baseline_service.generate_forecast(mock_assessment)

    def test_unsupported_heating_rejected_before_engine(self, baseline_service, mock_assessment):
        """Inputs the engine cannot model raise ValueError without calling the engine."""
        mock_assessment.heating.fuel_type = "district"
        with patch(_COMPUTE_MODEL) as mock_engine:
            with pytest.raises(ValueError, match="supported fuels"):
                baseline_service.generate_forecast(mock_assessment)
        mock_engine.assert_not_called()

    def test_cache_key_generation(self, baseline_service, mock_assessment):
        """Cache keys are stable for the same assessment and change with the input."""
        key1 = baseline_service._create_cache_key(mock_assessment)
        key2 = baseline_service._create_cache_key(mock_assessment)
        assert key1 == key2

        mock_assessment.household.occupants = 3
        assert baseline_service._create_cache_key(mock_assessment) != key1

    def test_cache_hit(self, baseline_service, mock_assessment, engine_output):
        """Cached results are returned without re-running the model."""
        with patch(_COMPUTE_MODEL, return_value=engine_output) as mock_engine:
            result1 = baseline_service.generate_forecast(mock_assessment)
            result2 = baseline_service.generate_forecast(mock_assessment)
            assert mock_engine.call_count == 1

            baseline_service.generate_forecast(mock_assessment, use_cache=False)
            assert mock_engine.call_count == 2

        assert result1 == result2
