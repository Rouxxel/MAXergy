"""Recorded API responses used by the MCP tests and the web/mobile mock modes must match the API.

Values that depend on the run date (the engine starts in the month after today) are not compared;
the structure (every key path) is. Copies of the same recording must be byte-identical.
Re-record with the commands in documentation/data/README.md when these fail.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.services.benchmark import benchmark_service

REPO = Path(__file__).resolve().parents[2]
MCP_FIXTURES = REPO / "backend/mcp/tests/fixtures"
COPIES = {
    "plan_model_input1.json": [
        MCP_FIXTURES / "plan_model_input1.json",
        REPO / "frontend/src/services/fixtures/plan_model_input1.json",
        REPO / "frontend-mobile/services/fixtures/plan_model_input1.json",
    ],
    "benchmark.json": [
        REPO / "frontend/src/services/fixtures/benchmark.json",
        REPO / "frontend-mobile/services/fixtures/benchmark.json",
    ],
}


def _paths(value, prefix="") -> set[str]:
    """Key paths of a JSON document; list items collapse to [] (lengths may differ)."""
    if isinstance(value, dict):
        out = {prefix} if prefix else set()
        for k, v in value.items():
            out |= _paths(v, f"{prefix}.{k}")
        return out
    if isinstance(value, list):
        out = {f"{prefix}[]"}
        for v in value:
            out |= _paths(v, f"{prefix}[]")
        return out
    return {prefix}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def client():
    from main import app

    benchmark_service.clear_cache()
    return TestClient(app, base_url="http://localhost")


@pytest.mark.parametrize("name", sorted(COPIES))
def test_copies_are_identical(name):
    first, *rest = COPIES[name]
    for other in rest:
        assert _load(other) == _load(first), f"{other} differs from {first}"


def test_recorded_plan_has_the_live_structure(client):
    live = client.post("/plan", json=_load(REPO / "backend/tests/fixtures/model_input1.json")).json()
    recorded = _load(MCP_FIXTURES / "plan_model_input1.json")
    assert _paths(recorded) == _paths(live)
    assert recorded["recommendation"]["selected_scenario_id"] == live["recommendation"]["selected_scenario_id"]


def test_recorded_benchmark_has_the_live_structure(client):
    live = client.get("/benchmark").json()
    recorded = _load(COPIES["benchmark.json"][0])
    assert _paths(recorded) == _paths(live)
    assert recorded["recommendation"]["scenario"] == live["recommendation"]["scenario"]
    assert recorded["recommendation"]["monthly_instalment_eur"] == live["recommendation"]["monthly_instalment_eur"]


def test_recorded_assumptions_equal_live(client):
    assert _load(MCP_FIXTURES / "assumptions.json") == client.get("/assumptions").json()
