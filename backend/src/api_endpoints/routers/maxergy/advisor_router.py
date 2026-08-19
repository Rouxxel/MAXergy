"""
#############################################################################
### Advisor router
###
### @file advisor_router.py
### @date 2026
#############################################################################

POST /advisor/chat endpoint for AI advisor interactions.
"""

import os
from fastapi import APIRouter, HTTPException, Request, Response

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import (
    AdvisorChatRequest,
    AdvisorChatResponse,
)
from src.services.llm.gemini_service import get_gemini_service
from src.utils.timeout import timeout
from src.utils.sanitize import sanitize_prompt

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_tag"]],
)


@router.post(config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['maxergy_advisor_chat']['request_limit']}/"
    f"{config_loader['endpoints']['maxergy_advisor_chat']['unit_of_time_for_limit']}"
)
@timeout(seconds=20)
async def advisor_chat(request: Request, chat_request: AdvisorChatRequest) -> Response:
    """
    Chat with the AI advisor about energy upgrades.
    
    This endpoint provides AI-powered advice on energy efficiency upgrades,
    financing options, and optimization strategies.
    
    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        chat_request (AdvisorChatRequest): Chat request with context.
    
    Returns:
        Response: AI advisor response with suggestions.

    Raises:
        HTTPException: If advisor API is not configured or request fails.
    """
    try:
        gemini_service = get_gemini_service()

        log_handler.info("[advisor_router] AI advisor chat request for assessment %s", chat_request.assessment_id)

        # Sanitize user message to prevent injection attacks
        sanitized_message = sanitize_prompt(chat_request.user_message, max_length=1000)

        # Convert forecast_result to dict if it's a Pydantic model
        forecast_dict = None
        if chat_request.forecast_result:
            forecast_dict = chat_request.forecast_result.model_dump() if hasattr(chat_request.forecast_result, 'model_dump') else chat_request.forecast_result

        response = gemini_service.generate_advice(
            user_message=sanitized_message,
            forecast_result=forecast_dict,
            assessment_id=chat_request.assessment_id,
        )

        from fastapi.responses import JSONResponse
        return JSONResponse(
            content=AdvisorChatResponse(
                advisor_message=response.advisor_message,
                context_used=response.context_used,
                suggestions=response.suggestions,
            ).model_dump(),
            headers={"Cache-Control": "no-store"}
        )

    except Exception as e:
        log_handler.error("[advisor_router] Advisor chat failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Advisor chat failed")
