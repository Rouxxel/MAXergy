# MAXergy MCP service (`maxergy-mcp`)

An MCP server that supports the MAXergy app. It gives LLM clients (claude.ai, Claude Code,
and later the MAXergy web advisor) the tools to run the household onboarding conversation and
present a **credible monthly-saving figure** for a full home-energy upgrade
(solar · battery · heat pump · EV).

**Every savings number comes from the MAXergy backend** (`POST /plan`, production engine
`scripts/energy_model`). The MCP never computes savings itself, so claude.ai users and app users
see exactly the same figures and the same recommendation.

> **Status:** savings tools run on the backend's production engine; the tool input schema is
> generated from the backend; all instructions come from one module. Deployed as the Railway
> service `maxergy-mcp` next to `maxergy-api` ([`.railway/railway.ts`](../../.railway/railway.ts),
> [`DEPLOYMENT.md`](../../documentation/app/DEPLOYMENT.md)); the two call each other over
> private networking with service tokens.

## Role in the MAXergy architecture

- Runs as a **standalone service** (separate process and Railway deploy), not inside FastAPI.
- Provides what the backend cannot: Google Geocoding, Google Solar roof geometry, PVGIS yield,
  and the conversational onboarding script.
- Calls the backend for savings (`POST /plan`) and engine defaults (`GET /assumptions`, cached
  for an hour).
- The backend calls the enrichment tools (geocode, roof, PVGIS) for `POST /location/enrich`
  (web assessment pre-fill), authenticated with a token from `MAXERGY_INTERNAL_TOKENS`. It can only
  call enrichment tools (allow-list on the backend side), never the savings tools.

## Tools

| Tool | Source | What it gives |
|------|--------|---------------|
| `start_advisor` | `instructions.py` | onboarding script; call first |
| `geocode_address` | Google Geocoding | address → lat/lon |
| `get_roof_geometry` | Google Solar API | roof planes (tilt, azimuth, area), `max_array_area_m2`, `max_array_kwp`, `low_confidence` |
| `estimate_roof_capacity_from_area` | heuristic + engine `m2_per_kwp` | usable roof area and PV ceiling from floor area (fallback) |
| `estimate_pv_production` | PVGIS (keyless, EU) | annual + monthly kWh; with `kwp=1` the site `specific_yield_kwh_per_kwp` for `household.roof` |
| `default_assumptions` | backend `GET /assumptions` | engine defaults (tariff, solar, battery, heat pump, EV, capex, financing, supported inputs) |
| `suggest_electricity_price` | backend defaults | default tariff and implied annual kWh from a monthly bill |
| `estimate_heating_spend` | heating-demand benchmark + backend fuel prices | gas/oil consumption and spend from living area |
| `suggest_battery_kwh` | heuristic + engine default | battery size to propose |
| **`energy_savings_overview`** | backend `POST /plan` | **the headline**: `{forecast, recommendation}` verbatim from the backend |
| `compare_scenarios` | backend `POST /plan` | all options with monthly figures and headline, in the backend's ranking order |
| `project_savings` | backend `POST /plan` | cumulative net savings per option per year, for a line chart |
| `next_best_upgrade` | backend `POST /plan` | what each extra component adds (or the best step from `current_scenario_id`) |

**Presentation:** results are presented with the same three numbers and wording as the MAXergy app
— year-1 monthly net with the loan ("During financing: −€X/month" when negative), "After payoff:
+€Y/month", and "N-year net: €Z" with the low/high range (`instructions.py`; each summary in
`compare_scenarios` / `next_best_upgrade` carries a ready `headline`, e.g. "Costs €39/month more
during the 15-year loan, then saves €179/month; 20-year net +€21,960.").

The savings tools take a `HouseholdAssessment` (same shape as the app,
[`documentation/app/API_CONTRACT.md`](../../documentation/app/API_CONTRACT.md) §2) and optional
`metric` (`cumulative_central` default, or `monthly_net`). The prompt `maxergy_advisor` returns
the same onboarding script as `start_advisor`. Only residential German homes with gas or oil
heating are supported (the engine's scope); other inputs get a clear "not supported yet" answer.

## Single sources

| What | Source | Derived file (generated, do not edit) |
|------|--------|----------------------------------------|
| Tool input/response schema | `backend/src/models/forecast_schemas.py` | `src/maxergy_mcp/contract.py` via `scripts/gen_contract.py` |
| Server instructions + onboarding script | `src/maxergy_mcp/instructions.py` | `PROMPT.md` via `scripts/gen_prompt.py` |

```bash
uv run python scripts/gen_contract.py   # after changing the backend schemas
uv run python scripts/gen_prompt.py     # after changing instructions.py
```

Both scripts accept `--check`, and the tests fail if either file is out of date.

## Run locally

```bash
cd backend/mcp
uv sync                     # includes the dev group (pytest, datamodel-code-generator)
cp .env.example .env        # MAXERGY_API_BASE_URL, optional GOOGLE_MAPS_API_KEY
uv run maxergy-mcp          # stdio MCP server
uv run pytest tests         # offline tests (backend mocked with recorded responses)
```

The savings tools need the backend running (`MAXERGY_API_BASE_URL`, default
`http://localhost:8000`; start it with `python main.py` in `backend/`). PVGIS needs no key; only
`geocode_address` and `get_roof_geometry` use Google.

The test fixtures `tests/fixtures/plan_model_input1.json` and `tests/fixtures/assumptions.json`
are responses recorded from the backend for `model_input1.json`. Re-record them when the backend
contract changes (POST the fixture input to `/plan`, GET `/assumptions`, save the JSON).

## Configuration

| Variable | Purpose |
|----------|---------|
| `MAXERGY_API_BASE_URL` | Backend base URL (default `http://localhost:8000`) |
| `MAXERGY_SERVICE_TOKEN` | Bearer token sent to the backend (its `MAXERGY_SERVICE_TOKEN`): separate rate limit; a wrong token gets 401 |
| `MAXERGY_INTERNAL_TOKENS` | Comma-separated bearer tokens accepted from internal services (the backend's `MAXERGY_MCP_TOKEN`), in addition to the public auth mode |
| `HOST` | Bind address (default `0.0.0.0`; `::` only for legacy IPv6-only Railway environments) |
| `GOOGLE_MAPS_API_KEY` | Google Solar + Geocoding |
| `MAXERGY_AUTH_MODE` and related | Inbound auth, see below |
| `LOG_LEVEL` | `INFO` (default) or `DEBUG` |
| `MCP_TRANSPORT` | `stdio` / `http` override |

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

**Internal callers:** tokens in `MAXERGY_INTERNAL_TOKENS` are accepted in every mode (FastMCP
`MultiAuth` composes them with the public provider), so the backend never needs the OAuth flow.
With no public auth configured, the internal tokens alone are required.

**Env vars:** only the `MAXERGY_*` names are read (`src/maxergy_mcp/config.py`); the pre-rename
names are no longer supported — see `documentation/app/DEPLOYMENT.md` (Migrating from the
pre-rename variables).

```
bearer: no/wrong token -> 401, correct -> 200
oauth : unauthenticated -> 401 with WWW-Authenticate pointing at
        /.well-known/oauth-protected-resource/mcp (Claude self-registers via DCR)
```

## Logging

Plain-text logs to stdout (Railway captures them). `LOG_LEVEL=INFO` (default) or `DEBUG`.
Every line carries a per-request **trace id** (also sent to the backend as `X-Trace-Id`); API
keys are never logged and secret-looking arguments are masked to `***`.

- `maxergy.tools` — one `→` (entry, sanitized args) and one `←` (exit: ok/ERROR, duration,
  output shape) per tool call, via `ToolLoggingMiddleware`.
- `maxergy.api` — each backend call: method, path, HTTP status, latency, retries.
- `maxergy.providers` — each Google Geocoding / Solar API and PVGIS call: HTTP status, latency,
  key params (never the key), response shape, rough cost estimate, fallback decisions.

```
[INFO] ... maxergy.tools     [8cd59828] - → estimate_pv_production args={'lat': 48.137, 'kwp': 1, ...}
[INFO] ... maxergy.providers [8cd59828] - pvgis http=200 458ms kwp=1.0 tilt=35 az=180 -> annual=1075kWh yield=1075 (keyless)
[INFO] ... maxergy.tools     [8cd59828] - ← estimate_pv_production ok 460ms out=dict(keys=[annual_kwh, monthly_kwh, ...])
```

## Demo (claude.ai connector)

1. Add the connector `https://<maxergy-mcp-domain>/mcp` in claude.ai (Settings → Connectors) and
   unlock it with the passphrase (`MAXERGY_AUTH_PASSPHRASE`).
2. Say "I'd like to see what I could save with MAXergy". Claude calls `start_advisor` and asks the
   onboarding questions one at a time (same order as the web form); with an address it calls
   `geocode_address` → `get_roof_geometry` → `estimate_pv_production` for the roof and site yield.
3. Answer with the average household (postcode 50667, 3 people, 3,500 kWh, south roof 35 m² / 32°,
   gas 14,000 kWh, one petrol car 12,000 km, all four upgrades, 15 years at 4.5 %). Claude calls
   `energy_savings_overview` → `maxergy-api` `POST /plan` and presents: "During financing −€29/month
   … After payoff +€181/month … 20-year net about +€24,500".
4. "Show it as a chart" → `project_savings`; "What does the EV charger add?" → `next_best_upgrade`.
5. Cross-check with the app or `python scripts/demo_plan.py --profile average_german_household`:
   the numbers are identical (both come from `/plan`).

## Deploy to Railway

The service is defined in [`.railway/railway.ts`](../../.railway/railway.ts) as `maxergy-mcp`
(Railway Infrastructure as Code; the old `railway.toml` config-as-code file was removed because
Railway stops reading those files on 2026-12-01): source root `backend/mcp`, Railpack build,
start `uv run --no-dev maxergy-mcp`, port 8080, volume `/data` for the passphrase-mode OAuth state,
rebuilds on `backend/mcp/**`. Railway injects `PORT`, so the server comes up on HTTP at
`https://<service-domain>/mcp`.

Variables, secrets, first-time migration (rename the existing service to `maxergy-mcp`, clear its
config file path) and the smoke test are in
[`documentation/app/DEPLOYMENT.md`](../../documentation/app/DEPLOYMENT.md).

### Register with an MCP client

Local (stdio):
```json
{
  "mcpServers": {
    "maxergy": {
      "command": "uv",
      "args": ["run", "--directory", "<path-to-repo>/backend/mcp", "maxergy-mcp"],
      "env": { "MAXERGY_API_BASE_URL": "http://localhost:8000", "GOOGLE_MAPS_API_KEY": "..." }
    }
  }
}
```

Remote (Railway, bearer) in Claude Code:
```bash
claude mcp add --transport http maxergy https://<service-domain>/mcp \
  --header "Authorization: Bearer <MAXERGY_API_TOKEN>"
```
