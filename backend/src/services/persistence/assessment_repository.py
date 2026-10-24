"""Stored household assessments (replaces the former in-memory dict in the assessment router)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import insert, select

from src.models.forecast_schemas import HouseholdAssessment
from src.services.persistence.database import assessments, get_engine


def save_assessment(assessment: HouseholdAssessment) -> str:
    """Persist an assessment; returns its new id."""
    assessment_id = str(uuid.uuid4())
    with get_engine().begin() as conn:
        conn.execute(insert(assessments).values(
            id=assessment_id,
            created_at=datetime.now(timezone.utc),
            payload=assessment.model_dump(mode="json"),
        ))
    return assessment_id


def get_assessment(assessment_id: str) -> HouseholdAssessment | None:
    """The stored assessment, or None for unknown ids."""
    with get_engine().connect() as conn:
        payload = conn.execute(
            select(assessments.c.payload).where(assessments.c.id == assessment_id)
        ).scalar_one_or_none()
    return HouseholdAssessment.model_validate(payload) if payload is not None else None
