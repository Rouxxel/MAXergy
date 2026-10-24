"""
#############################################################################
### Plan router
###
### @file plan_router.py
### @date 2026
#############################################################################

POST /plan endpoint: forecast and recommendation from one engine run.
"""

from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from src.utils.custom_logger import log_handler
from src.utils.limiter import endpoint_limit, limiter as SlowLimiter
from src.utils.service_auth import verify_service_token
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import HouseholdAssessment, PlanResponse, RecommendationMetric
from src.services.forecasting.baseline_service import get_forecasting_service
from src.services.persistence.assessment_repository import get_assessment
from src.services.recommendation.recommendation_service import build_recommendation
from src.utils.timeout import timeout

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_plan"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_plan"]["endpoint_tag"]],
    dependencies=[Depends(verify_service_token)],
)


@router.post(config_loader["endpoints"]["maxergy_plan"]["endpoint_route"])
@SlowLimiter.limit(endpoint_limit("maxergy_plan"))
@timeout(seconds=30)
async def generate_plan(
    request: Request,
    assessment: Optional[HouseholdAssessment] = Body(None),
    metric: Optional[RecommendationMetric] = None,
    assessment_id: Optional[str] = None,
) -> Response:
    """
    Generate the forecast and the recommendation for a household in one call.

    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        assessment (HouseholdAssessment | None): Household assessment data (request body).
        metric (RecommendationMetric | None): Ranking metric; config default when omitted.
        assessment_id (str | None): Use a stored assessment (from POST /assessment) instead of a body.

    Returns:
        Response: PlanResponse with `forecast` and `recommendation`.

    Raises:
        HTTPException: 404 for an unknown assessment_id, 422 if neither (or both) inputs are given
        or the assessment cannot be modelled, 500 on failure.
    """
    if (assessment is None) == (assessment_id is None):
        raise HTTPException(status_code=422, detail="Send either an assessment body or ?assessment_id=, not both")
    if assessment is None:
        assessment = get_assessment(assessment_id)
        if assessment is None:
            raise HTTPException(status_code=404, detail="Unknown assessment_id")
    log_handler.info(
        "[plan_router] Generating plan for location %s, %s",
        assessment.location.postcode,
        assessment.location.country,
    )
    try:
        forecast = get_forecasting_service().generate_forecast(assessment)
        plan = PlanResponse(forecast=forecast, recommendation=build_recommendation(forecast, metric))
    except ValueError as e:
        log_handler.warning("[plan_router] Assessment cannot be modelled: %s", str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log_handler.error("[plan_router] Plan generation failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Plan generation failed")

    log_handler.info(
        "[plan_router] Plan generated: %d scenarios, recommended %s",
        len(forecast.scenarios),
        plan.recommendation.selected_scenario_id,
    )
    return JSONResponse(
        content=plan.model_dump(mode="json"),
        headers={"Cache-Control": "no-store"},
    )
