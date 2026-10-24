"""MAXergy staging smoke test: the DEPLOYMENT.md checks against a running API (+ MCP).

    python scripts/staging_smoke.py --api https://<maxergy-api-domain> \
        [--mcp https://<maxergy-mcp-domain> --mcp-token <MAXERGY_MCP_TOKEN>] \
        [--service-token <MAXERGY_SERVICE_TOKEN>]

Locally against backend/docker-compose.staging.yml:
    python scripts/staging_smoke.py --api http://localhost:18000 --mcp http://localhost:18080 \
        --service-token staging-service-token --mcp-token staging-mcp-token

Result per check: PASS, FAIL, or SKIP/EXTERNAL when it depends on an external key (Google, Gemini)
that is missing or not working. Exit code 1 if any check FAILs.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
ASSESSMENT = json.loads((REPO / "backend/tests/fixtures/model_input1.json").read_text(encoding="utf-8"))
results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))
    print(f"[{status:8}] {name}" + (f" — {detail}" if detail else ""), flush=True)


def check(name: str, fn) -> None:
    try:
        status, detail = fn()
    except Exception as e:  # report and continue with the next check
        status, detail = "FAIL", f"{type(e).__name__}: {e}"
    record(name, status, detail)


def mcp_call(base: str, token: str | None, method: str, params: dict) -> tuple[int, dict]:
    headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = requests.post(f"{base.rstrip('/')}/mcp", json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params},
                      headers=headers, timeout=90)
    if r.status_code != 200:
        return r.status_code, {}
    text = r.text.strip()
    if r.headers.get("content-type", "").startswith("text/event-stream"):
        data = [line[5:].strip() for line in text.splitlines() if line.startswith("data:")]
        text = data[-1] if data else "{}"
    return 200, json.loads(text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--api", required=True)
    ap.add_argument("--mcp")
    ap.add_argument("--mcp-token", help="MAXERGY_MCP_TOKEN (accepted by the MCP as internal token)")
    ap.add_argument("--service-token", help="MAXERGY_SERVICE_TOKEN (to test the service rate-limit path)")
    ap.add_argument("--wait", type=int, default=120, help="seconds to wait for the API to come up")
    a = ap.parse_args()
    api = a.api.rstrip("/")

    deadline = time.time() + a.wait
    while True:
        try:
            requests.get(api + "/", timeout=5).raise_for_status()
            break
        except requests.RequestException:
            if time.time() > deadline:
                record("API health", "FAIL", f"{api} not reachable")
                return 1
            time.sleep(3)
    record("API health", "PASS", api)

    plan_holder: dict = {}

    def plan():
        r = requests.post(api + "/plan", json=ASSESSMENT, timeout=90)
        r.raise_for_status()
        plan_holder.update(r.json())
        rec = r.json()["recommendation"]
        best = rec["selected_scenario"]
        ok = rec["selected_scenario_id"] == "full_upgrade" and best["monthly_cost_eur"]["financing_installment"] > 0
        return ("PASS" if ok else "FAIL",
                f"{rec['selected_scenario_id']}, monthly net {best['monthly_saving_eur']} €, instalment "
                f"{best['monthly_cost_eur']['financing_installment']} €")

    def stored():
        aid = requests.post(api + "/assessment", json=ASSESSMENT, timeout=30).json()["assessment_id"]
        r = requests.post(f"{api}/plan?assessment_id={aid}", timeout=90)
        same = r.status_code == 200 and r.json() == plan_holder
        return ("PASS" if same else "FAIL", f"assessment {aid[:8]}… → /plan?assessment_id {r.status_code}, identical={same}")

    def benchmark():
        b = requests.get(api + "/benchmark", timeout=90).json()
        ok = b["recommendation"]["scenario"] == "full_upgrade" and len(b["cumulative_series"]) == b["projection_years"]
        return ("PASS" if ok else "FAIL", f"{b['recommendation']['scenario']}, forecast start {b['forecast_start']}")

    def assumptions():
        d = requests.get(api + "/assumptions", timeout=30).json()
        return ("PASS" if d["tariff"]["arbeitspreis_eur_per_kwh"] > 0 else "FAIL", f"€{d['tariff']['arbeitspreis_eur_per_kwh']}/kWh")

    def wrong_service_token():
        r = requests.post(api + "/plan", json=ASSESSMENT, headers={"Authorization": "Bearer wrong"}, timeout=30)
        return ("PASS" if r.status_code == 401 else "FAIL", f"HTTP {r.status_code} (expected 401)")

    def service_token():
        r = requests.post(api + "/plan", json=ASSESSMENT, headers={"Authorization": f"Bearer {a.service_token}"}, timeout=90)
        return ("PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")

    def enrich():
        r = requests.post(api + "/location/enrich", json={"postcode": "50667"}, timeout=90)
        body = r.json()
        if r.status_code == 200:
            return "PASS", f"lat/lon {body['lat']:.2f}/{body['lon']:.2f}, roof={body['source']['roof']}, yield={body['source']['pv_yield']}"
        if r.status_code in (422, 503):  # no/invalid Google key, or MCP unavailable
            return "EXTERNAL", f"HTTP {r.status_code}: {body.get('detail')}"
        return "FAIL", f"HTTP {r.status_code}: {body}"

    def advisor():
        r = requests.post(api + "/advisor/chat", json={"user_message": "Why this bundle?", "plan": plan_holder}, timeout=90)
        if r.status_code == 200:
            return "PASS", r.json()["advisor_message"][:80].replace("\n", " ")
        if r.status_code == 503:  # GEMINI_API_KEY missing, invalid or over quota — by design in production
            return "EXTERNAL", f"503: {r.json().get('detail')}"
        return "FAIL", f"HTTP {r.status_code}"

    check("POST /plan (full body)", plan)
    check("POST /assessment → /plan?assessment_id (persistence)", stored)
    check("GET /benchmark", benchmark)
    check("GET /assumptions", assumptions)
    check("Wrong service token → 401", wrong_service_token)
    if a.service_token:
        check("Service token accepted", service_token)
    check("POST /location/enrich (API → MCP → Google/PVGIS)", enrich)
    check("POST /advisor/chat (Gemini)", advisor)

    if a.mcp:
        mcp = a.mcp.rstrip("/")

        def mcp_unauthorised():
            status, _ = mcp_call(mcp, "wrong-token", "tools/list", {})
            return ("PASS" if status == 401 else "FAIL", f"HTTP {status} (expected 401)")

        def mcp_overview():
            status, msg = mcp_call(mcp, a.mcp_token, "tools/call",
                                   {"name": "energy_savings_overview", "arguments": {"assessment": ASSESSMENT}})
            if status != 200 or "error" in msg:
                return "FAIL", f"HTTP {status} {msg.get('error')}"
            result = msg["result"]
            data = result.get("structuredContent") or json.loads(result["content"][0]["text"])
            same = data == plan_holder
            return ("PASS" if same else "FAIL", f"MCP → API /plan: {data['recommendation']['selected_scenario_id']}, identical to app={same}")

        def mcp_prompt():
            status, msg = mcp_call(mcp, a.mcp_token, "prompts/get", {"name": "maxergy_advisor", "arguments": {}})
            text = (msg.get("result", {}).get("messages") or [{}])[0].get("content", {}).get("text", "")
            return ("PASS" if "HouseholdAssessment" in text else "FAIL", f"onboarding script {len(text)} chars")

        def mcp_pvgis():
            status, msg = mcp_call(mcp, a.mcp_token, "tools/call", {"name": "estimate_pv_production", "arguments": {
                "lat": 50.94, "lon": 6.96, "kwp": 1, "tilt_degrees": 30, "azimuth_degrees": 180}})
            result = msg.get("result", {})
            if status == 200 and not result.get("isError"):
                data = result.get("structuredContent") or json.loads(result["content"][0]["text"])
                return "PASS", f"PVGIS {data.get('specific_yield_kwh_per_kwp')} kWh/kWp (Cologne, 30° south)"
            return "EXTERNAL", f"PVGIS unavailable: {result.get('content', [{}])[0].get('text', status)}"

        def mcp_geocode():
            status, msg = mcp_call(mcp, a.mcp_token, "tools/call", {"name": "geocode_address", "arguments": {"address": "50667 Köln"}})
            result = msg.get("result", {})
            if status == 200 and not result.get("isError"):
                return "PASS", json.dumps(result.get("structuredContent"))[:80]
            return "EXTERNAL", f"Google geocoding: {result.get('content', [{}])[0].get('text', status)}"[:160]

        check("MCP rejects a wrong token", mcp_unauthorised)
        check("MCP energy_savings_overview (MCP → API)", mcp_overview)
        check("MCP prompt maxergy_advisor", mcp_prompt)
        check("MCP estimate_pv_production (PVGIS, no key)", mcp_pvgis)
        check("MCP geocode_address (Google key)", mcp_geocode)

    failed = [r for r in results if r[1] == "FAIL"]
    external = [r for r in results if r[1] == "EXTERNAL"]
    print(f"\n{len(results) - len(failed) - len(external)} passed, {len(external)} external/skipped, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
