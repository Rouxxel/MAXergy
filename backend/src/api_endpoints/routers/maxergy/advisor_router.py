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
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        
        if not gemini_api_key or gemini_api_key == "key_here":
            # Return mock response if API key not configured
            log_handler.warning("GEMINI_API_KEY not configured, returning mock response")
            
            mock_response = _generate_mock_response(chat_request)
            return mock_response
        
        # TODO: Implement actual Gemini API call
        # For now, return mock response
        log_handler.info("AI advisor chat request for assessment %s", chat_request.assessment_id)
        mock_response = _generate_mock_response(chat_request)
        return mock_response
        
    except Exception as e:
        log_handler.error("Advisor chat failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Advisor chat failed: {str(e)}")


def _generate_mock_response(chat_request: AdvisorChatRequest) -> AdvisorChatResponse:
    """Generate a mock advisor response for development."""
    
    # Simple keyword-based mock responses
    user_message_lower = chat_request.user_message.lower()
    
    if "solar" in user_message_lower:
        advisor_message = (
            "Solar PV is a great starting point for energy independence. "
            "Based on typical German conditions, you can expect around 1000 kWh/kWp annual yield. "
            "Consider adding battery storage to increase self-consumption from 30% to 65%."
        )
        suggestions = [
            "Start with solar PV as the foundation",
            "Add battery storage if you have high daytime consumption",
            "Check your roof orientation and shading for optimal placement",
        ]
    elif "battery" in user_message_lower:
        advisor_message = (
            "Battery storage increases your self-consumption ratio significantly. "
            "A 7.5 kWh battery is typical for a 5-6 kWp solar system. "
            "This can reduce grid dependence and protect against rising electricity prices."
        )
        suggestions = [
            "Size battery to match your evening consumption patterns",
            "Consider smart home integration for optimal charging",
            "Batteries work best with time-of-use tariffs",
        ]
    elif "heat pump" in user_message_lower:
        advisor_message = (
            "Heat pumps are highly efficient with a COP of 3.3 or higher. "
            "They replace fossil fuel heating and can be powered by your solar PV. "
            "Consider your building's insulation level for optimal performance."
        )
        suggestions = [
            "Improve insulation before installing heat pump",
            "Combine with solar PV for maximum savings",
            "Check eligibility for BAFA subsidies",
        ]
    elif "ev" in user_message_lower or "electric vehicle" in user_message_lower:
        advisor_message = (
            "EV charging at home with solar PV can significantly reduce mobility costs. "
            "Typical BEV consumption is 18 kWh/100km. "
            "Consider off-peak charging and smart charging management."
        )
        suggestions = [
            "Install home charger for convenience",
            "Time charging with solar generation peaks",
            "Consider vehicle-to-grid technology in the future",
        ]
    elif "cost" in user_message_lower or "price" in user_message_lower:
        advisor_message = (
            "The total cost depends on the combination of upgrades. "
            "Solar PV typically costs around €1,400/kWp, batteries €700/kWh, "
            "and heat pumps around €12,000 installed. "
            "Subsidies can cover up to 30% of system costs."
        )
        suggestions = [
            "Check KfW and BAFA subsidy programs",
            "Consider green loans for favorable financing",
            "Calculate ROI based on your energy savings",
        ]
    else:
        advisor_message = (
            "I can help you with questions about solar PV, battery storage, heat pumps, "
            "EV charging, costs, and financing options. "
            "Please provide more specific details about what you'd like to know."
        )
        suggestions = [
            "Ask about specific technologies (solar, battery, heat pump, EV)",
            "Inquire about costs and financing options",
            "Request information about subsidies and incentives",
        ]
    
    context_used = ["user_question"]
    if chat_request.forecast_result:
        context_used.append("forecast_result")
    
    return AdvisorChatResponse(
        advisor_message=advisor_message,
        context_used=context_used,
        suggestions=suggestions,
    )
