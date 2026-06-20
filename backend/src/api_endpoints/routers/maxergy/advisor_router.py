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
from fastapi import APIRouter, HTTPException, Request

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import (
    AdvisorChatRequest,
    AdvisorChatResponse,
)
from src.services.llm.gemini_service import get_gemini_service

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_tag"]],
)


@router.post(config_loader["endpoints"]["maxergy_advisor_chat"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['maxergy_advisor_chat']['request_limit']}/"
    f"{config_loader['endpoints']['maxergy_advisor_chat']['unit_of_time_for_limit']}"
)
async def advisor_chat(request: Request, chat_request: AdvisorChatRequest) -> AdvisorChatResponse:
    """
    Chat with the AI advisor about energy upgrades.
    
    This endpoint provides AI-powered advice on energy efficiency upgrades,
    financing options, and optimization strategies.
    
    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        chat_request (AdvisorChatRequest): Chat request with context.
    
    Returns:
        AdvisorChatResponse: AI advisor response with suggestions.
    
    Raises:
        HTTPException: If advisor API is not configured or request fails.
    """
    try:
        gemini_service = get_gemini_service()
        
        log_handler.info("AI advisor chat request for assessment %s", chat_request.assessment_id)
        
        # Convert forecast_result to dict if it's a Pydantic model
        forecast_dict = None
        if chat_request.forecast_result:
            forecast_dict = chat_request.forecast_result.model_dump() if hasattr(chat_request.forecast_result, 'model_dump') else chat_request.forecast_result
        
        response = gemini_service.generate_advice(
            user_message=chat_request.user_message,
            forecast_result=forecast_dict,
            assessment_id=chat_request.assessment_id,
        )
        
        return AdvisorChatResponse(
            advisor_message=response.advisor_message,
            context_used=response.context_used,
            suggestions=response.suggestions,
        )
        
    except Exception as e:
        log_handler.error("Advisor chat failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Advisor chat failed: {str(e)}")
