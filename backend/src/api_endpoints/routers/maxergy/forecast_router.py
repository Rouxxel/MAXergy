"""
#############################################################################
### Forecast router
###
### @file forecast_router.py
### @date 2026
#############################################################################

POST /forecast endpoint for generating energy forecasts.
"""

import sys
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, HTTPException, Request

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.models.forecast_schemas import (
    HouseholdAssessment,
    ForecastResult,
)

# Add scripts directory to path for importing the baseline model
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts"))

# In-memory cache for demo purposes; replace with proper cache in production
_forecast_cache: Dict[str, ForecastResult] = {}

router = APIRouter(
    prefix="/forecast",
    tags=["forecast"],
)


@router.post("")
@SlowLimiter.limit("5/m")
async def generate_forecast(request: Request, assessment: HouseholdAssessment) -> ForecastResult:
    """
    Generate energy forecast for a household assessment.
    
    This endpoint calls the baseline forecasting model to generate
    cost projections for the current setup and upgrade scenarios.
    
    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        assessment (HouseholdAssessment): Household assessment data.
    
    Returns:
        ForecastResult: Complete forecast with baseline and scenarios.
    
    Raises:
        HTTPException: If forecast generation fails.
    """
    try:
        # Import the baseline model
        from run_baseline_model import run_model
        import json
        import tempfile
        
        log_handler.info(
            "Generating forecast for location %s, %s",
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
        
        log_handler.info(
            "Forecast generated successfully with %d scenarios",
            len(forecast.scenarios),
        )
        
        return forecast
        
    except Exception as e:
        log_handler.error("Forecast generation failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Forecast generation failed: {str(e)}")
