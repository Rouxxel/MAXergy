"""Service-to-service auth and the separate service rate limit."""

import pytest
from fastapi.testclient import TestClient

from src.utils.limiter import endpoint_limit, limiter
from src.utils.service_auth import SERVICE_KEY

TOKEN = "test-service-token"


@pytest.fixture
def client(monkeypatch):
    from main import app

    monkeypatch.setenv("MAXERGY_SERVICE_TOKEN", TOKEN)
    limiter.reset()
    yield TestClient(app, base_url="http://localhost")
    limiter.reset()


def test_endpoint_limit_per_identity():
    limit_for = endpoint_limit("maxergy_plan")
    assert limit_for("1.2.3.4") == "5/minute"
    assert limit_for(SERVICE_KEY) == "300/minute"


def test_anonymous_and_valid_token_are_accepted(client):
    assert client.get("/assumptions").status_code == 200
    assert client.get("/assumptions", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 200


def test_invalid_token_is_rejected(client):
    response = client.get("/assumptions", headers={"Authorization": "Bearer wrong"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_token_rejected_when_backend_has_none(client, monkeypatch):
    monkeypatch.delenv("MAXERGY_SERVICE_TOKEN")
    assert client.get("/assumptions", headers={"Authorization": f"Bearer {TOKEN}"}).status_code == 401


def test_service_token_bypasses_public_limit(client, assessment_dict):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    statuses = [client.post("/plan", json=assessment_dict, headers=headers).status_code for _ in range(7)]
    assert statuses == [200] * 7  # public limit is 5/min

    anonymous = [client.post("/plan", json=assessment_dict).status_code for _ in range(6)]
    assert anonymous[:5] == [200] * 5
    assert anonymous[5] == 429
