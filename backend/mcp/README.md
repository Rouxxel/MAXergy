# MAXergy MCP service (`maxergy-mcp`)

An MCP server that supports the MAXergy app. It gives LLM clients (claude.ai, Claude Code,
and later the MAXergy web advisor) the tools to run the household onboarding conversation and
present a **credible monthly-saving figure** for a full home-energy upgrade
(solar · battery · heat pump · EV).

> **Status: being integrated into MAXergy.**
> - Done: renamed from "MAXnergy" to MAXergy (package `maxergy_mcp`, command `maxergy-mcp`,
>   env prefix `MAXERGY_`).
> - **Today the savings numbers are NOT from the production engine.** `energy_savings_overview`
>   runs `model_engine.py`, a copy of the legacy `scripts/run_baseline_model.py`, which
>   overstates savings. The other savings tools use a separate heuristic engine (`savings.py`).
> - Planned: savings tools become thin clients of the backend `POST /plan` (production
>   `scripts/energy_model`), the schema is generated from the backend OpenAPI, and all
>   instructions come from one module.
> - Planned: deployed as its own Railway service and wired to the backend (`maxergy-api`).

## Role in the MAXergy architecture

- Runs as a **standalone service** (separate process and Railway deploy), not inside FastAPI.
- Provides what the backend cannot: Google Geocoding, Google Solar roof geometry, PVGIS yield,
  and the conversational onboarding script.
- Target: it never computes savings itself; it calls the backend.
- Target: the backend calls its enrichment tools (geocode, roof, PVGIS) for the web
  assessment pre-fill and the advisor.

## Tools (current)

| Tool | Source | What it gives |
|------|--------|---------------|
| `start_advisor` | local | onboarding script; call first |
| `geocode_address` | Google Geocoding | address → lat/lon |
| `get_roof_geometry` | Google Solar API | roof planes (tilt, azimuth, area), `max_array_kwp`, `low_confidence` |
| `estimate_roof_capacity_from_area` | local heuristic | roof ceiling from floor area when the Solar API result is low-confidence |
| `estimate_pv_production` | PVGIS (keyless, EU) | annual + monthly kWh for a given system |
| `estimate_heating_spend`, `suggest_battery_kwh`, `suggest_electricity_price` | local benchmarks | values to propose to the user for confirmation |
| `model_savings`, `compare_scenarios`, `project_savings`, `recommend_upsell` | `savings.py` heuristic engine | per-scenario savings, ranking, chart series, next step (to be replaced by `POST /plan`) |
| `energy_savings_overview` | `model_engine.py` (legacy-engine copy) | baseline + 6-scenario ladder + forecasts (to move to `POST /plan`) |

The prompt `maxergy_advisor` returns the same onboarding script as `start_advisor`.

## Run locally

```bash
cd backend/mcp
uv sync
cp .env.example .env        # optional: GOOGLE_MAPS_API_KEY (Solar + Geocoding enabled)
uv run maxergy-mcp          # stdio MCP server
uv run python overview_smoke.py   # offline smoke test (parity with scripts/run_baseline_model.py)
```

PVGIS and the local engines need **no key**; only `geocode_address` and `get_roof_geometry`
use Google. Without a key, pass tilt/azimuth to `estimate_pv_production` directly.

## Transport & auth

`main()` runs **stdio** locally and switches to **streamable HTTP** (stateless, JSON responses)
when `PORT` is set (Railway); override with `MCP_TRANSPORT=stdio|http`.

Auth mode via `MAXERGY_AUTH_MODE` (switchable on redeploy):

| Mode | Provider | Use it for |
|------|----------|-----------|
| `bearer` (default) | shared-secret token (`MAXERGY_API_TOKEN`); empty = no auth | Claude Code, Anthropic API connector, local |
| `fastmcp` | `InMemoryOAuthProvider` — FastMCP is its own OAuth server (DCR + authorize + token), no external IdP | claude.ai connector, zero setup; simulated consent = effectively open |
| `passphrase` | self-hosted OAuth like `fastmcp`, but authorization is gated by `MAXERGY_AUTH_PASSPHRASE`; state persisted to `MAXERGY_OAUTH_STATE_PATH` | claude.ai connector with a shared secret |
| `google` | `GoogleProvider` (OAuth proxy, real Google login); `GOOGLE_OAUTH_CLIENT_ID/SECRET`, optional `MAXERGY_JWT_SIGNING_KEY` | claude.ai connector with per-user access control |

Misconfigured modes fall back to `bearer` with a warning.

**Env-var migration:** the pre-rename names `MAXNERGY_*` are still read as a fallback (with a
deprecation warning on stderr) by `src/maxergy_mcp/config.py`. Set the `MAXERGY_*` names on
Railway; the fallback will be removed once all deployments use the new names.

```
bearer: no/wrong token -> 401, correct -> 200
oauth : unauthenticated -> 401 with WWW-Authenticate pointing at
        /.well-known/oauth-protected-resource/mcp (Claude self-registers via DCR)
```

## Logging

Plain-text logs to stdout (Railway captures them). `LOG_LEVEL=INFO` (default) or `DEBUG`.
Every line carries a per-request **trace id**; API keys are never logged and secret-looking
arguments are masked to `***`.

- `maxergy.tools` — one `→` (entry, sanitized args) and one `←` (exit: ok/ERROR, duration,
  output shape) per tool call, via `ToolLoggingMiddleware`.
- `maxergy.providers` — each Google Geocoding / Solar API and PVGIS call: HTTP status, latency,
  key params (never the key), response shape, rough cost estimate, fallback decisions.
- `maxergy.model` — overview computations.

```
[INFO] ... maxergy.tools     [8cd59828] - → estimate_pv_production args={'lat': 48.137, 'kwp': 6, ...}
[INFO] ... maxergy.providers [8cd59828] - pvgis http=200 458ms kwp=6.0 tilt=35 az=180 -> annual=6451kWh yield=1075 (keyless)
[INFO] ... maxergy.tools     [8cd59828] - ← estimate_pv_production ok 460ms out=dict(keys=[annual_kwh, monthly_kwh, ...])
```

## Deploy to Railway

The service deploys from this directory (`backend/mcp`) with Railpack (`railway.toml`,
start command `uv run maxergy-mcp`). Railway injects `PORT`, so the server comes up on HTTP at
`https://<service-domain>/mcp`.

```bash
cd backend/mcp
railway link                 # project "maxergy", service "maxergy-mcp"
railway variables --set GOOGLE_MAPS_API_KEY=... \
                  --set MAXERGY_API_TOKEN=$(python -c "import secrets;print(secrets.token_urlsafe(32))")
railway up
```

In the Railway dashboard set the service **root directory** to `backend/mcp`. The full
two-service layout (`maxergy-api` + `maxergy-mcp`, private networking, service tokens) is
will be documented in `documentation/app/DEPLOYMENT.md`.

### Register with an MCP client

Local (stdio):
```json
{
  "mcpServers": {
    "maxergy": {
      "command": "uv",
      "args": ["run", "--directory", "<path-to-repo>/backend/mcp", "maxergy-mcp"],
      "env": { "GOOGLE_MAPS_API_KEY": "..." }
    }
  }
}
```

Remote (Railway, bearer) in Claude Code:
```bash
claude mcp add --transport http maxergy https://<service-domain>/mcp \
  --header "Authorization: Bearer <MAXERGY_API_TOKEN>"
```

## Modeling notes (current, to be replaced)

- `model_schema.py` copies the **v1** (legacy) API shape — see
  [`documentation/app/API_CONTRACT.md`](../../documentation/app/API_CONTRACT.md) §3.1.
- `model_engine.py` reproduces `scripts/run_baseline_model.py` exactly (`overview_smoke.py`
  checks parity). For `documentation/data/model_input1.json` it reports e.g. `full_upgrade`
  +€87/month and `pv_ev` +€127/month, while the production engine shows negative first-year net
  savings for an average household (`documentation/data/test_outputs/model_test_summary.md`).
- `savings.py` / `suggestions.py` use their own constants (e.g. €0.35/kWh, feed-in €0.08/kWh,
  COP 3.3) that differ from the production engine (€0.32/kWh, EEG tiers 0.082/0.071/0.058,
  SCOP 3.5). They are planned to come from the backend `GET /assumptions`.
