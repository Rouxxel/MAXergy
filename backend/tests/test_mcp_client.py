"""Backend → MCP client and POST /location/enrich (MCP replaced by a fake HTTP session)."""

import json

import pytest
from fastapi.testclient import TestClient

from src.services.mcp.enrichment_service import orientation_from_azimuth
from src.services.mcp.mcp_client import McpClient, McpToolError, McpUnavailable, set_mcp_client
from src.utils.limiter import limiter


class FakeResponse:
    def __init__(self, body: dict, status: int = 200, content_type: str = "application/json"):
        self.status_code = status
        self.headers = {"content-type": content_type}
        self._body = body
        self.text = f"event: message\ndata: {json.dumps(body)}\n\n" if content_type == "text/event-stream" else json.dumps(body)

    def json(self):
        return self._body


def tool_result(data: dict) -> dict:
    return {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": json.dumps(data)}],
                                                  "structuredContent": data, "isError": False}}


def tool_error(message: str) -> dict:
    return {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": message}], "isError": True}}


class FakeMcp:
    """Answers tools/call like the MAXergy MCP; records every request."""

    def __init__(self):
        self.calls: list[tuple[str, dict, dict]] = []
        self.responses = {
            "geocode_address": tool_result({"address": "x", "lat": 50.94, "lon": 6.96}),
            "get_roof_geometry": tool_result({
                "lat": 50.94, "lon": 6.96, "max_array_area_m2": 38.0, "max_array_kwp": 7.2,
                "low_confidence": False,
                "segments": [{"tilt_degrees": 35.0, "azimuth_degrees": 170.0, "area_m2": 40.0}],
            }),
            "estimate_pv_production": tool_result({"annual_kwh": 1012.0, "specific_yield_kwh_per_kwp": 1012.0}),
        }

    def post(self, url, json=None, headers=None, timeout=None):
        name = json["params"]["name"]
        self.calls.append((name, json["params"]["arguments"], headers))
        return self.responses[name]


@pytest.fixture
def fake():
    return FakeMcp()


def _client(fake, **kwargs) -> McpClient:
    return McpClient(base_url="http://mcp.internal:8080", token="mcp-token", enabled=True, session=fake, **kwargs)


@pytest.fixture
def api(fake):
    from main import app

    set_mcp_client(_client(fake))
    limiter.reset()
    yield TestClient(app, base_url="http://localhost")
    set_mcp_client(None)
    limiter.reset()


def test_allow_list_blocks_savings_tools(fake):
    with pytest.raises(ValueError, match="not allowed"):
        _client(fake).call_tool("energy_savings_overview", {})
    assert fake.calls == []


def test_disabled_client_is_unavailable(fake):
    client = McpClient(base_url="http://mcp.internal:8080", enabled=False, session=fake)
    with pytest.raises(McpUnavailable):
        client.call_tool("geocode_address", {"address": "x"})


def test_call_sends_jsonrpc_with_bearer(fake):
    out = _client(fake).call_tool("geocode_address", {"address": "Köln"})
    assert out["lat"] == 50.94
    name, args, headers = fake.calls[0]
    assert (name, args) == ("geocode_address", {"address": "Köln"})
    assert headers["Authorization"] == "Bearer mcp-token"


def test_url_gets_mcp_path(fake):
    assert _client(fake).url == "http://mcp.internal:8080/mcp"


def test_tool_error_and_sse(fake):
    fake.responses["geocode_address"] = FakeResponse(tool_error("Geocoding failed"))
    with pytest.raises(McpToolError, match="Geocoding failed"):
        _client(fake).call_tool("geocode_address", {"address": "x"})

    fake.responses["geocode_address"] = FakeResponse(tool_result({"lat": 1.0, "lon": 2.0}), content_type="text/event-stream")
    assert _client(fake).call_tool("geocode_address", {"address": "x"}) == {"lat": 1.0, "lon": 2.0}


def test_auth_failure_is_unavailable(fake):
    fake.responses["geocode_address"] = FakeResponse({}, status=401)
    with pytest.raises(McpUnavailable, match="credentials"):
        _client(fake).call_tool("geocode_address", {"address": "x"})


@pytest.mark.parametrize(("azimuth", "orientation"), [(180, "south"), (170, "south"), (90, "east"), (225, "south_west"), (0, "north"), (350, "north")])
def test_orientation_from_azimuth(azimuth, orientation):
    assert orientation_from_azimuth(azimuth) == orientation


@pytest.fixture(autouse=True)
def _wrap_responses(fake):
    fake.responses = {k: FakeResponse(v) for k, v in fake.responses.items()}


def test_enrich_endpoint(api, fake):
    response = api.post("/location/enrich", json={"postcode": "50667"})
    assert response.status_code == 200
    body = response.json()
    assert (body["lat"], body["lon"]) == (50.94, 6.96)
    assert body["roof"]["usable_area_m2"] == 38.0
    assert body["roof"]["tilt_deg"] == 35.0
    assert body["roof"]["orientation"] == "south"
    assert body["specific_yield_kwh_per_kwp"] == 1012.0
    assert body["source"] == {"roof": "google_solar", "pv_yield": "pvgis"}
    assert fake.calls[0][1] == {"address": "50667, Germany"}
    pv_args = fake.calls[2][1]
    assert (pv_args["kwp"], pv_args["tilt_degrees"], pv_args["azimuth_degrees"]) == (1.0, 35.0, 170.0)


def test_enrich_degrades_when_roof_unavailable(api, fake):
    fake.responses["get_roof_geometry"] = FakeResponse(tool_error("No Solar API building data at this location"))
    body = api.post("/location/enrich", json={"address": "Domkloster 4, 50667 Köln"}).json()
    assert body["roof"] is None
    assert body["source"]["roof"] == "unavailable"
    assert body["specific_yield_kwh_per_kwp"] == 1012.0
    assert any("Roof geometry unavailable" in w for w in body["warnings"])


def test_enrich_errors(api, fake):
    assert api.post("/location/enrich", json={}).status_code == 422
    assert api.post("/location/enrich", json={"postcode": "50667", "country": "FR"}).status_code == 422

    fake.responses["geocode_address"] = FakeResponse(tool_error("Geocoding failed for 'zz': ZERO_RESULTS"))
    assert api.post("/location/enrich", json={"postcode": "00000"}).status_code == 422

    fake.responses["geocode_address"] = FakeResponse(tool_error("GOOGLE_MAPS_API_KEY is not set."))
    response = api.post("/location/enrich", json={"postcode": "50667"})
    assert response.status_code == 503


def test_enrich_disabled_returns_503(api):
    set_mcp_client(McpClient(base_url="", enabled=True))
    response = api.post("/location/enrich", json={"postcode": "50667"})
    assert response.status_code == 503
    assert "disabled" in response.json()["detail"]
