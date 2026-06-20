"""
Baseline forecasting service module.

This service wraps the baseline forecasting model from scripts/run_baseline_model.py
and provides a clean interface for the API endpoints to use.
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import Dict

# Add scripts directory to path for importing the baseline model
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts"))

from src.utils.custom_logger import log_handler
from src.models.forecast_schemas import (
    HouseholdAssessment,
    ForecastResult,
)


class BaselineForecastingService:
    """Service for running baseline energy forecasting model."""
    
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
            Exception: If forecast generation fails.
        """
        # Create cache key from assessment
        cache_key = self._create_cache_key(assessment)
        
        if use_cache and cache_key in self._cache:
            log_handler.info("[baseline_service] Returning cached forecast for key: %s", cache_key[:16])
            return self._cache[cache_key]
        
        try:
            # Import the baseline model
            from run_baseline_model import run_model
            
            log_handler.info(
                "[baseline_service] Generating forecast for location %s, %s",
                assessment.location.postcode,
                assessment.location.country,
            )
            
            # Create temporary files for model input/output
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as input_file:
                input_path = Path(input_file.name)
                json.dump(assessment.model_dump(), input_file, indent=2)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as output_file:
                output_path = Path(output_file.name)
            
            # Run the baseline model
            run_model(input_path, output_path)
            
            # Load the output
            with output_path.open() as f:
                forecast_data = json.load(f)
            
            # Clean up temporary files
            input_path.unlink()
            output_path.unlink()
            
            # Validate against schema
            forecast = ForecastResult(**forecast_data)
            
            # Cache the result
            if use_cache:
                self._cache[cache_key] = forecast
            
            log_handler.info(
                "[baseline_service] Forecast generated successfully with %d scenarios",
                len(forecast.scenarios),
            )
            
            return forecast
            
        except Exception as e:
            log_handler.error("[baseline_service] Forecast generation failed: %s", str(e))
            raise
    
    def _create_cache_key(self, assessment: HouseholdAssessment) -> str:
        """Create a cache key from assessment data."""
        import hashlib
        import json
        
        # Convert assessment to JSON string for hashing
        assessment_str = json.dumps(assessment.model_dump(), sort_keys=True)
        return hashlib.md5(assessment_str.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the forecast cache."""
        self._cache.clear()
        log_handler.info("[baseline_service] Forecast cache cleared")


# Singleton instance
_forecasting_service = BaselineForecastingService()


def get_forecasting_service() -> BaselineForecastingService:
    """Get the singleton forecasting service instance."""
    return _forecasting_service
