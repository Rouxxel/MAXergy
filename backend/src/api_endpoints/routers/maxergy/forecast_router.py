"""
#############################################################################
### Forecast router
###
### @file forecast_router.py
### @date 2026
#############################################################################

POST /forecast endpoint for generating energy forecasts.
"""

from fastapi import APIRouter, HTTPException, Request, Response

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import (
    HouseholdAssessment,
    ForecastResult,
)
from src.services.forecasting.baseline_service import get_forecasting_service
from src.utils.timeout import timeout

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_forecast"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_forecast"]["endpoint_tag"]],
)


@router.post(config_loader["endpoints"]["maxergy_forecast"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['maxergy_forecast']['request_limit']}/"
    f"{config_loader['endpoints']['maxergy_forecast']['unit_of_time_for_limit']}"
)
@timeout(seconds=30)
async def generate_forecast(request: Request, assessment: HouseholdAssessment) -> Response:
    """
    Generate energy forecast for a household assessment.
    
    This endpoint calls the baseline forecasting model to generate
    cost projections for the current setup and upgrade scenarios.
    
    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        assessment (HouseholdAssessment): Household assessment data.
    
    Returns:
        Response: Complete forecast with baseline and scenarios.
    
    Raises:
        HTTPException: If forecast generation fails.
    """
    try:
        forecasting_service = get_forecasting_service()

        log_handler.info(
            "[forecast_router] Generating forecast for location %s, %s",
            assessment.location.postcode,
            assessment.location.country,
        )

        forecast = forecasting_service.generate_forecast(assessment)

        log_handler.info(
            "[forecast_router] Forecast generated successfully with %d scenarios",
            len(forecast.scenarios),
        )

        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=forecast.model_dump(),
            headers={"Cache-Control": "no-store"}
        )

    except ValueError as e:
        log_handler.warning("[forecast_router] Assessment cannot be modelled: %s", str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log_handler.error("[forecast_router] Forecast generation failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Forecast generation failed")
