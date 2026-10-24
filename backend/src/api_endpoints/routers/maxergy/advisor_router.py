"""
#############################################################################
### Advisor router
###
### @file advisor_router.py
### @date 2026
#############################################################################

POST /advisor/chat endpoint for AI advisor interactions.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from src.utils.custom_logger import log_handler
from src.utils.limiter import endpoint_limit, limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import AdvisorChatRequest, AdvisorChatResponse, PlanResponse
from src.services.forecasting.baseline_service import get_forecasting_service
from src.services.persistence.assessment_repository import get_assessment
from src.services.recommendation.recommendation_service import build_recommendation
from src.services.llm.gemini_service import AdvisorUnavailable, get_gemini_service
from src.utils.timeout import timeout
from src.utils.sanitize import sanitize_prompt

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_tag"]],
)


def _plan_for(chat_request: AdvisorChatRequest) -> PlanResponse | None:
    """The plan sent by the client, else the plan of the stored assessment (`assessment_id`)."""
    if chat_request.plan is not None or not chat_request.assessment_id:
        return chat_request.plan
    assessment = get_assessment(chat_request.assessment_id)
    if assessment is None:
        return None
    try:
        forecast = get_forecasting_service().generate_forecast(assessment)
    except ValueError:
        return None
    return PlanResponse(forecast=forecast, recommendation=build_recommendation(forecast))


@router.post(config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_route"])
@SlowLimiter.limit(endpoint_limit("maxergy_advisor_chat"))
@timeout(seconds=45)
async def advisor_chat(request: Request, chat_request: AdvisorChatRequest) -> JSONResponse:
    """
    Chat with the AI advisor.

    With `plan`, the advisor explains that plan (numbers only from the plan). Without a plan it
    runs the shared onboarding script and, once the answers are complete, returns the computed
    `assessment` and `plan` (same services as POST /plan).

    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        chat_request (AdvisorChatRequest): Message, optional plan and conversation history.

    Returns:
        JSONResponse: AdvisorChatResponse.

    Raises:
        HTTPException: 503 when the advisor is not configured or Gemini is unavailable; 500 otherwise.
    """
    log_handler.info("[advisor_router] AI advisor chat request for assessment %s", chat_request.assessment_id)
    message = sanitize_prompt(chat_request.user_message, max_length=1000)
    try:
        result = await run_in_threadpool(
            get_gemini_service().generate_advice,
            user_message=message,
            plan=await run_in_threadpool(_plan_for, chat_request),
            history=chat_request.conversation_history,
            assessment_id=chat_request.assessment_id,
        )
    except AdvisorUnavailable as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log_handler.error("[advisor_router] Advisor chat failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Advisor chat failed")

    body = AdvisorChatResponse(
        advisor_message=result.advisor_message,
        context_used=result.context_used,
        suggestions=result.suggestions,
        assessment=result.assessment,
        plan=result.plan,
    )
    return JSONResponse(content=body.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
