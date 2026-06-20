"""
#############################################################################
### Recommendation router
###
### @file recommendation_router.py
### @date 2026
#############################################################################

POST /recommendation endpoint for generating upgrade recommendations.
"""

from fastapi import APIRouter, HTTPException, Request

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import (
    HouseholdAssessment,
    ForecastResult,
    Recommendation,
)

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_recommendation"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_recommendation"]["endpoint_tag"]],
)


@router.post(config_loader["endpoints"]["maxergy_recommendation"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['maxergy_recommendation']['request_limit']}/"
    f"{config_loader['endpoints']['maxergy_recommendation']['unit_of_time_for_limit']}"
)
async def generate_recommendation(
    request: Request, 
    assessment: HouseholdAssessment
) -> Recommendation:
    """
    Generate upgrade recommendation based on household assessment.
    
    This endpoint analyzes forecast scenarios and recommends the best
    upgrade option based on monthly savings and other factors.
    
    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        assessment (HouseholdAssessment): Household assessment data.
    
    Returns:
        Recommendation: Recommended scenario with rationale.
    
    Raises:
        HTTPException: If recommendation generation fails.
    """
    try:
        # Import forecast router to reuse forecast generation
        from src.api_endpoints.routers.maxergy.forecast_router import generate_forecast
        
        log_handler.info(
            "Generating recommendation for location %s, %s",
            assessment.location.postcode,
            assessment.location.country,
        )
        
        # Generate forecast first
        forecast = await generate_forecast(request, assessment)
        
        # Rank scenarios by monthly savings
        ranked_scenarios = sorted(
            [(s.id, s.monthly_saving_eur) for s in forecast.scenarios],
            key=lambda x: x[1],
            reverse=True,
        )
        
        # Select top recommendation
        if not ranked_scenarios:
            raise HTTPException(status_code=400, detail="No scenarios available for recommendation")
        
        top_scenario_id, top_savings = ranked_scenarios[0]
        selected_scenario = next(s for s in forecast.scenarios if s.id == top_scenario_id)
        
        # Generate rationale
        if top_savings > 0:
            rationale = (
                f"Based on your household profile, the {top_scenario_id} scenario offers "
                f"the highest monthly savings of €{top_savings:.2f}. "
                f"This configuration includes {', '.join([k for k, v in selected_scenario.components.model_dump().items() if v])}. "
                f"Expected payback period: {selected_scenario.payback_month} months if applicable."
            )
        else:
            rationale = (
                f"Based on your household profile, all scenarios show negative short-term savings "
                f"due to financing costs. However, the {top_scenario_id} scenario offers the best "
                f"long-term value with post-payoff savings of "
                f"€{selected_scenario.monthly_saving_post_payoff_eur:.2f}/month."
            )
        
        log_handler.info(
            "Recommendation generated: %s with €%.2f/month savings",
            top_scenario_id,
            top_savings,
        )
        
        return Recommendation(
            selected_scenario_id=top_scenario_id,
            selected_scenario=selected_scenario,
            ranked_scenarios=ranked_scenarios,
            rationale=rationale,
        )
        
    except Exception as e:
        log_handler.error("Recommendation generation failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {str(e)}")
