"""AI advisor: grounded in the plan, onboarding via the shared MCP script, tool calls, 503 rules.

Gemini is replaced by a scripted fake client (no network); the forecasting/recommendation
services run for real.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.models.forecast_schemas import PlanResponse
from src.services.llm import advisor_tools
from src.services.llm.advisor_context import build_plan_context
from src.services.llm.gemini_service import GeminiService, set_gemini_service
from src.services.mcp.mcp_client import McpClient, McpUnavailable, set_mcp_client

FIXTURES = Path(__file__).resolve().parent / "fixtures"
PLAN = json.loads((Path(__file__).resolve().parents[1] / "mcp/tests/fixtures/plan_model_input1.json").read_text(encoding="utf-8"))


def _reply(text=None, calls=()):
    content = SimpleNamespace(role="model", parts=[])
    return SimpleNamespace(
        text=text,
        function_calls=[SimpleNamespace(name=n, args=a) for n, a in calls] or None,
        candidates=[SimpleNamespace(content=content)],
    )


class FakeGemini:
    """Returns scripted replies; records the requests."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests = []
        self.models = self

    def generate_content(self, model, contents, config):
        self.requests.append(SimpleNamespace(model=model, contents=list(contents), config=config))
        return self.replies.pop(0)


class FakeMcp(McpClient):
    def __init__(self, enabled=True, script="ONBOARDING SCRIPT FROM MCP"):
        super().__init__(base_url="http://mcp.test", enabled=enabled)
        self.script = script
        self.calls = []

    def get_prompt(self, name):
        if not self.enabled:
            raise McpUnavailable("disabled")
        self.calls.append(("prompt", name))
        return self.script

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return {"address": arguments.get("address"), "lat": 52.53, "lon": 13.38}


@pytest.fixture(autouse=True)
def no_real_gemini(monkeypatch):
    """Tests must never reach the real Gemini API."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)


@pytest.fixture
def mcp():
    fake = FakeMcp()
    set_mcp_client(fake)
    advisor_tools.clear_script_cache()
    yield fake
    set_mcp_client(None)
    advisor_tools.clear_script_cache()


@pytest.fixture
def client():
    from main import app

    yield TestClient(app, base_url="http://localhost")
    set_gemini_service(None)


def _system(fake):
    return fake.requests[0].config.system_instruction


def test_plan_context_uses_recommendation_and_real_fields():
    ctx = build_plan_context(PlanResponse.model_validate(PLAN))
    assert "Recommended scenario: full_upgrade" in ctx
    assert "Costs €39/month more during the 15-year loan, then saves €179/month; 20-year net +€21,960." in ctx
    assert "Loan instalment €218/month" in ctx and "break-even year 12" in ctx
    assert "electricity €124, heating €121, mobility €92, total €337" in ctx  # was gas_oil/fuel → €0
    assert ctx.count("  1. ") == 1 and "  3. " in ctx  # top 3 ranked


def test_chat_with_plan_is_grounded(client, mcp):
    fake = FakeGemini(_reply("full_upgrade costs €39/month more during the loan.\n- Compare pv_ev"))
    set_gemini_service(GeminiService(client=fake, environment="production"))
    r = client.post("/advisor/chat", json={"user_message": "Why this bundle?", "plan": PLAN})
    assert r.status_code == 200
    body = r.json()
    assert body["advisor_message"].startswith("full_upgrade")
    assert body["context_used"] == ["user_question", "plan"]
    assert body["suggestions"] == ["Compare pv_ev"]
    assert body["plan"] is None
    assert "Recommended scenario: full_upgrade" in _system(fake)
    assert "=== USER ===\nWhy this bundle?" in fake.requests[0].contents[-1].parts[0].text


def test_removed_forecast_result_is_ignored(client, mcp):
    """`forecast_result` (removed alias) no longer counts as a plan: the advisor onboards instead."""
    fake = FakeGemini(_reply("ok"))
    set_gemini_service(GeminiService(client=fake, environment="production"))
    r = client.post("/advisor/chat", json={"user_message": "Why?", "forecast_result": PLAN["forecast"]})
    assert r.status_code == 200
    assert r.json()["context_used"] == ["user_question", "onboarding_script"]
    assert "Recommended scenario" not in _system(fake)


def test_history_is_passed_in_order(client, mcp):
    fake = FakeGemini(_reply("ok"))
    set_gemini_service(GeminiService(client=fake, environment="production"))
    history = [{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}]
    client.post("/advisor/chat", json={"user_message": "Next", "plan": PLAN, "conversation_history": history})
    roles = [c.role for c in fake.requests[0].contents]
    assert roles == ["user", "model", "user"]


def test_onboarding_uses_mcp_script_and_tools_and_returns_plan(client, mcp):
    assessment = json.loads((FIXTURES / "model_input1.json").read_text(encoding="utf-8"))
    fake = FakeGemini(
        _reply(calls=[("geocode_address", {"address": "10115 Berlin"})]),
        _reply(calls=[("run_plan", {"assessment": assessment})]),
        _reply("Your plan: full upgrade.\n- View your results"),
    )
    set_gemini_service(GeminiService(client=fake, environment="production"))
    r = client.post("/advisor/chat", json={"user_message": "That's everything"})
    assert r.status_code == 200
    body = r.json()

    assert "ONBOARDING SCRIPT FROM MCP" in _system(fake)
    names = [d.name for d in fake.requests[0].config.tools[0].function_declarations]
    assert "run_plan" in names and "geocode_address" in names
    assert ("geocode_address", {"address": "10115 Berlin"}) in mcp.calls
    assert body["context_used"] == ["user_question", "onboarding_script", "tool:geocode_address", "tool:run_plan"]

    web_plan = client.post("/plan", json=assessment).json()
    assert body["plan"] == web_plan  # chat onboarding gives the same plan as the web form
    assert body["assessment"]["location"] == assessment["location"]


def test_run_plan_errors_are_returned_to_the_model(mcp):
    runner = advisor_tools.ToolRunner()
    out = runner("run_plan", {"assessment": {"location": {"postcode": "10115"}}})
    assert out["error"] == "Assessment incomplete or invalid" and out["details"]
    assessment = json.loads((FIXTURES / "model_input1.json").read_text(encoding="utf-8"))
    assessment["heating"]["fuel_type"] = "district"
    assert "not supported" in runner("run_plan", {"assessment": assessment})["error"]
    assert runner.plan is None


def test_onboarding_script_is_cached_and_has_fallback(mcp):
    assert advisor_tools.get_onboarding_script() == ("ONBOARDING SCRIPT FROM MCP", True)
    advisor_tools.get_onboarding_script()
    assert mcp.calls.count(("prompt", "maxergy_advisor")) == 1
    advisor_tools.clear_script_cache()
    mcp.enabled = False
    script, from_mcp = advisor_tools.get_onboarding_script()
    assert not from_mcp and "assessment form" in script


def test_mcp_tools_not_offered_when_mcp_disabled(client, mcp):
    mcp.enabled = False
    fake = FakeGemini(_reply("Please use the form."))
    set_gemini_service(GeminiService(client=fake, environment="production"))
    body = client.post("/advisor/chat", json={"user_message": "hi"}).json()
    assert [d.name for d in fake.requests[0].config.tools[0].function_declarations] == ["run_plan"]
    assert body["context_used"] == ["user_question", "onboarding_unavailable"]


def test_missing_key_is_503_in_production(client, mcp):
    set_gemini_service(GeminiService(api_key="", environment="production"))
    r = client.post("/advisor/chat", json={"user_message": "hi", "plan": PLAN})
    assert r.status_code == 503
    assert "GEMINI_API_KEY" in r.json()["detail"]


def test_missing_key_mocks_only_in_development(client, mcp):
    set_gemini_service(GeminiService(api_key="", environment="development"))
    body = client.post("/advisor/chat", json={"user_message": "hi", "plan": PLAN}).json()
    assert "Development mode" in body["advisor_message"]
    assert "Costs €39/month more during the 15-year loan" in body["advisor_message"]


def test_gemini_failure_is_503(client, mcp):
    class Broken:
        models = None

    broken = Broken()
    broken.models = SimpleNamespace(generate_content=lambda **_: (_ for _ in ()).throw(RuntimeError("boom")))
    set_gemini_service(GeminiService(client=broken, environment="production"))
    assert client.post("/advisor/chat", json={"user_message": "hi", "plan": PLAN}).status_code == 503
