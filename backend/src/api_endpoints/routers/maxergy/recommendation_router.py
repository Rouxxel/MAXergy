"""
#############################################################################
### Recommendation router
###
### @file recommendation_router.py
### @date 2026
#############################################################################

POST /recommendation endpoint for generating upgrade recommendations.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import HouseholdAssessment, RecommendationMetric
from src.services.forecasting.baseline_service import get_forecasting_service
from src.services.recommendation.recommendation_service import build_recommendation
from src.utils.timeout import timeout

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_recommendation"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_recommendation"]["endpoint_tag"]],
)


@router.post(config_loader["endpoints"]["maxergy_recommendation"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['maxergy_recommendation']['request_limit']}/"
    f"{config_loader['endpoints']['maxergy_recommendation']['unit_of_time_for_limit']}"
)
@timeout(seconds=30)
async def generate_recommendation(
    request: Request,
    assessment: HouseholdAssessment,
    metric: Optional[RecommendationMetric] = None,
) -> Response:
    """
    Generate an upgrade recommendation for a household assessment.

    Runs (or reuses the cached) forecast and ranks its scenarios with the shared
    recommendation service.

    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        assessment (HouseholdAssessment): Household assessment data.
        metric (RecommendationMetric | None): Ranking metric; config default when omitted.

    Returns:
        Response: Recommendation with ranked scenarios and rationale.

    Raises:
        HTTPException: 422 if the assessment cannot be modelled, 500 on failure.
    """
    log_handler.info(
        "[recommendation_router] Generating recommendation for location %s, %s",
        assessment.location.postcode,
        assessment.location.country,
    )
    try:
        forecast = get_forecasting_service().generate_forecast(assessment)
        recommendation = build_recommendation(forecast, metric)
    except ValueError as e:
        log_handler.warning("[recommendation_router] Assessment cannot be modelled: %s", str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log_handler.error("[recommendation_router] Recommendation generation failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Recommendation generation failed")

    log_handler.info(
        "[recommendation_router] Recommendation generated: %s (metric %s)",
        recommendation.selected_scenario_id,
        recommendation.metric_used.value,
    )
    return JSONResponse(
        content=recommendation.model_dump(mode="json"),
        headers={"Cache-Control": "no-store"},
    )
