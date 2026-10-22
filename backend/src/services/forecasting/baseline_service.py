"""
Forecasting service module.

Runs the production energy model (scripts/energy_model, `compute_model`) for a household
assessment: assessment -> input_normalizer -> compute_model -> model_adapter -> ForecastResult.
"""

import hashlib
import json
from typing import Dict

from src.utils.custom_logger import log_handler
from src.models.forecast_schemas import (
    HouseholdAssessment,
    ForecastResult,
)
from src.services.forecasting.engine import compute_model
from src.services.forecasting.input_normalizer import normalize_assessment
from src.services.forecasting.model_adapter import adapt_forecast


class BaselineForecastingService:
    """Service for running the production energy model."""

    def __init__(self):
        """Initialize the forecasting service."""
        self._cache: Dict[str, ForecastResult] = {}

    def generate_forecast(self, assessment: HouseholdAssessment, use_cache: bool = True) -> ForecastResult:
        """
        Generate energy forecast for a household assessment.

        Parameters:
            assessment (HouseholdAssessment): Household assessment data.
            use_cache (bool): Whether to use cached results if available.

        Returns:
            ForecastResult: Complete forecast with baseline and scenarios.

        Raises:
            ValueError: If the assessment cannot be modelled (unsupported or invalid input).
            Exception: If forecast generation fails.
        """
        engine_input = normalize_assessment(assessment)
        cache_key = self._create_cache_key(engine_input)

        if use_cache and cache_key in self._cache:
            log_handler.info("[baseline_service] Returning cached forecast for key: %s", cache_key[:16])
            return self._cache[cache_key]

        log_handler.info(
            "[baseline_service] Generating forecast for location %s, %s",
            assessment.location.postcode,
            assessment.location.country,
        )

        try:
            engine_output = compute_model(engine_input)
            forecast = adapt_forecast(engine_output, engine_input["upgrade_candidates"])
        except ValueError:
            raise
        except Exception as e:
            log_handler.error("[baseline_service] Forecast generation failed: %s", str(e))
            raise

        for warning in forecast.validation_warnings:
            log_handler.warning("[baseline_service] Model warning: %s", warning)

        if use_cache:
            self._cache[cache_key] = forecast

        log_handler.info(
            "[baseline_service] Forecast generated successfully with %d scenarios",
            len(forecast.scenarios),
        )
        return forecast

    def _create_cache_key(self, engine_input) -> str:
        """Create a cache key from the normalized engine input (or an assessment)."""
        if isinstance(engine_input, HouseholdAssessment):
            engine_input = normalize_assessment(engine_input)
        payload = json.dumps(engine_input, sort_keys=True, default=str)
        return hashlib.md5(payload.encode()).hexdigest()

    def clear_cache(self):
        """Clear the forecast cache."""
        self._cache.clear()
        log_handler.info("[baseline_service] Forecast cache cleared")


# Singleton instance
_forecasting_service = BaselineForecastingService()


def get_forecasting_service() -> BaselineForecastingService:
    """Get the singleton forecasting service instance."""
    return _forecasting_service
