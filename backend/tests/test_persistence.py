"""Persistence: assessments survive a restart and can be used by /plan and the advisor by id.

The session-wide SQLite test database is created by the Alembic migrations (backend/conftest.py).
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from src.services.llm.gemini_service import GeminiService, set_gemini_service
from src.services.persistence import database
from src.services.persistence.assessment_repository import get_assessment, save_assessment
from src.models.forecast_schemas import HouseholdAssessment


@pytest.fixture
def client():
    from main import app

    yield TestClient(app, base_url="http://localhost")
    set_gemini_service(None)


def _restart_database_connections():
    """What a process restart does to the app: no engine, no pooled connections, no caches."""
    database.get_engine().dispose()
    database._engine_for.cache_clear()


def test_migrations_create_the_schema():
    engine = database.get_engine()
    assert "assessments" in inspect(engine).get_table_names()
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar() == "0001_assessments"


def test_database_url_normalises_railway_postgres(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@db.railway.internal:5432/railway")
    assert database.database_url() == "postgresql+psycopg://u:p@db.railway.internal:5432/railway"
    monkeypatch.setenv("DATABASE_URL", "postgres://u:p@host/db")
    assert database.database_url() == "postgresql+psycopg://u:p@host/db"
    monkeypatch.delenv("DATABASE_URL")
    assert database.database_url() == database.DEFAULT_SQLITE_URL


def test_repository_round_trip(assessment_dict):
    assessment = HouseholdAssessment.model_validate(assessment_dict)
    assessment_id = save_assessment(assessment)
    _restart_database_connections()
    assert get_assessment(assessment_id) == assessment
    assert get_assessment("00000000-0000-0000-0000-000000000000") is None


def test_plan_by_assessment_id_survives_restart(client, assessment_dict):
    assessment_id = client.post("/assessment", json=assessment_dict).json()["assessment_id"]
    _restart_database_connections()

    by_id = client.post(f"/plan?assessment_id={assessment_id}")
    by_body = client.post("/plan", json=assessment_dict)
    assert by_id.status_code == 200
    assert by_id.json() == by_body.json()


def test_plan_input_errors(client, assessment_dict):
    assert client.post("/plan?assessment_id=unknown").status_code == 404
    assert client.post("/plan").status_code == 422
    assessment_id = client.post("/assessment", json=assessment_dict).json()["assessment_id"]
    assert client.post(f"/plan?assessment_id={assessment_id}", json=assessment_dict).status_code == 422


def test_advisor_uses_the_stored_assessment_after_restart(client, assessment_dict, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assessment_id = client.post("/assessment", json=assessment_dict).json()["assessment_id"]
    _restart_database_connections()

    seen = {}

    class FakeGemini:
        models = None

        def __init__(self):
            self.models = self

        def generate_content(self, model, contents, config):
            seen["system"] = config.system_instruction
            return SimpleNamespace(text="ok", function_calls=None, candidates=[])

    set_gemini_service(GeminiService(client=FakeGemini(), environment="production"))
    body = client.post("/advisor/chat", json={"user_message": "Why?", "assessment_id": assessment_id}).json()
    assert body["context_used"] == ["user_question", "plan"]
    assert "Recommended scenario: full_upgrade" in seen["system"]
