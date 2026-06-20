"""
#############################################################################
### Assessment router
###
### @file assessment_router.py
### @date 2026
#############################################################################

POST /assessment endpoint for submitting household assessments.
"""

import uuid
from typing import Dict

from fastapi import APIRouter, Request

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import (
    HouseholdAssessment,
    AssessmentResponse,
)

# In-memory store for demo purposes; replace with database in production
_assessments_store: Dict[str, HouseholdAssessment] = {}

router = APIRouter(
    prefix="/assessment",
    tags=["assessment"],
)


@router.post("")
@SlowLimiter.limit("10/m")
async def submit_assessment(request: Request, assessment: HouseholdAssessment) -> AssessmentResponse:
    """
    Submit a household assessment for energy forecasting.
    
    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        assessment (HouseholdAssessment): Household assessment data.
    
    Returns:
        AssessmentResponse: Assessment ID and status.
    """
    assessment_id = str(uuid.uuid4())
    
    # Store assessment (in-memory for demo)
    _assessments_store[assessment_id] = assessment
    
    log_handler.info(
        "Assessment submitted: %s for location %s, %s",
        assessment_id,
        assessment.location.postcode,
        assessment.location.country,
    )
    
    return AssessmentResponse(
        assessment_id=assessment_id,
        status="submitted",
        message="Assessment submitted successfully. Use the assessment_id to request forecasts.",
    )
