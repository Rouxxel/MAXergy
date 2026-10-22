# MAXnergy — household energy-transition advisor (MCP)

An MCP server that turns minimal onboarding answers into a **credible monthly-saving
figure** for a full home-energy upgrade (solar · battery · heat pump · EV), and spots
the strongest upsell. Built for the Cloover hackathon track.

> North Star: **€/month saved** — how much lower the household's total monthly outgoings
> are once the upgrade and its financing are in, vs. what they pay today. Where the
> installment outweighs savings early in the loan, it's shown honestly
> (e.g. *"near cost-neutral now, €194/mo saved once it's paid off"*).

## How it works

The **client LLM runs the onboarding conversation** and holds the household profile.
The MCP provides the calculators it can't do reliably in-context:

| Tool | Source | What it gives |
|------|--------|---------------|
| `geocode_address` | Google Geocoding | address → lat/lon |
| `get_roof_geometry` | Google Solar API | roof planes (tilt, azimuth, area) + `max_array_kwp` = the upsell ceiling |
| `estimate_pv_production` | PVGIS (keyless, EU) | annual + monthly kWh for a given system |
| `model_savings` | local engine | one scenario → per-bucket split + North Star |
| `compare_scenarios` | local engine | ranks the upgrade ladder by €/mo saved |
| `recommend_upsell` | local engine | the single strongest next step, proposal-ready |
| **`energy_savings_overview`** | local engine | **the headline**: canonical input → full structured overview (baseline + 6-scenario ladder + short/long forecasts + savings + payback) |

**Roof angle is derived, not guessed.** Roof pitch = roof-mounted panel tilt, so the
largest segment's tilt/azimuth from the Solar API is the existing array's orientation.
Existing system size is asked from the user (they know their kWp); `max_array_kwp` minus
that is the headroom for an upsell.

Savings span three buckets, kept non-overlapping (no double-counting of kWh):
- **Electricity** — PV self-consumption + battery charging cheap / discharging expensive on a dynamic tariff.
- **Heating** — oil/gas → heat pump (fuel spend swapped for partly self-generated electricity at SCOP ~3.5).
- **Mobility** — ICE → EV (petrol swapped for cheap off-peak charging).

## Onboarding questions the LLM should ask

address · heating type · cars (EV/ICE + annual km each) · existing solar kWp + its
financing installment · monthly electricity spend · feed-in tariff · battery installed?

## Run

```bash
uv venv && uv pip install -e .
cp .env.example .env        # add GOOGLE_MAPS_API_KEY (Solar + Geocoding enabled)
uv run maxnergy-mcp         # stdio MCP server
```

PVGIS and the whole savings engine need **no key** — only `geocode_address` and
`get_roof_geometry` use Google. Without a key, pass tilt/azimuth to
`estimate_pv_production` directly and the rest still works.

## Transport & auth

`main()` runs **stdio** locally and switches to **streamable HTTP** automatically when
`PORT` is set (Railway/cloud); override with `MCP_TRANSPORT=stdio|http`.

Auth has three modes via `MAXNERGY_AUTH_MODE`, switchable on redeploy:

| Mode | Provider | Use it for |
|------|----------|-----------|
| `bearer` (default) | shared-secret token (`MAXNERGY_API_TOKEN`) | Claude Code, Anthropic API connector |
| `fastmcp` | `InMemoryOAuthProvider` — FastMCP is its own OAuth server (DCR + authorize + token), **no external IdP** | the **claude.ai app + phone** connector, zero IdP setup |
| `google` | `GoogleProvider` (OAuth proxy, real Google login) | claude.ai connector with genuine per-user access control |

`fastmcp` mode is the quickest way onto the claude.ai connector — but it **simulates
consent (no real login)** and keeps clients/tokens **in memory** (re-auth after a
redeploy), so treat it as effectively open access and keep the Google Maps key
quota-capped. `google` mode adds real login at the cost of a Google OAuth client.

```
bearer: no/wrong token -> 401, correct -> 200
oauth : unauthenticated -> 401 with WWW-Authenticate pointing at
        /.well-known/oauth-protected-resource/mcp (Claude self-registers via DCR)
```

## Logging

Plain-text logs to stdout (Railway captures them in the deploy logs tab). Set
`LOG_LEVEL=INFO` (default) or `DEBUG`. Every line carries a per-request **trace id** so a
tool call and the Google/PVGIS API calls it triggers line up. API keys are never logged;
secret-looking arguments are masked to `***`.

- `maxnergy.tools` — one `→` (entry, sanitized args) and one `←` (exit: ok/ERROR,
  duration, output shape) per tool call, via a FastMCP middleware (no tool code touched).
- `maxnergy.google` — each Google Geocoding / Solar API and PVGIS call: HTTP status,
  latency, key params (never the key), response shape, a rough cost estimate, and fallback
  decisions (e.g. tiny-roof → area estimate).
- Uvicorn already logs the HTTP route layer (`POST /mcp` status, OAuth 401s, DCR).

Example (one `estimate_pv_production` call — note the shared `[8cd59828]`):

```
[INFO] ... maxnergy.tools  [8cd59828] - → estimate_pv_production args={'lat': 48.137, 'kwp': 6, ...}
[INFO] ... maxnergy.google [8cd59828] - pvgis http=200 458ms kwp=6.0 tilt=35 az=180 -> annual=6451kWh yield=1075 (keyless)
[INFO] ... maxnergy.tools  [8cd59828] - ← estimate_pv_production ok 460ms out=dict(keys=[annual_kwh, monthly_kwh, ...])
```

A geocode that hits the small-annex case logs `solar ... low_conf=True FALLBACK→area-estimate`.

## Deploy to Railway

```bash
railway init                 # in this directory, or link an existing project
railway variables --set GOOGLE_MAPS_API_KEY=... \
                  --set MAXNERGY_API_TOKEN=$(python -c "import secrets;print(secrets.token_urlsafe(32))")
railway up
```

Railway injects `PORT`, so the server comes up on HTTP at `https://<your-app>.up.railway.app/mcp`.
`railway.toml` pins the Nixpacks build + `uv run maxnergy-mcp` start command.

### Register with an MCP client

Local (stdio):
```json
{
  "mcpServers": {
    "maxnergy": {
      "command": "uv",
      "args": ["run", "--directory", "/Users/sandbox1/maxnergy-mcp", "maxnergy-mcp"],
      "env": { "GOOGLE_MAPS_API_KEY": "..." }
    }
  }
}
```

Remote (Railway, with bearer) in Claude Code:
```bash
claude mcp add --transport http maxnergy https://<your-app>.up.railway.app/mcp \
  --header "Authorization: Bearer <MAXNERGY_API_TOKEN>"
```

## Modeling notes

Heuristics are calibrated to German single-family homes and every constant is named in
`savings.py` and surfaced in each result's `assumptions`. The self-consumption curve is
the main simplification — swap it for an hourly PV+load simulation for production
accuracy; the tool interfaces stay the same.

### Canonical model (`energy_savings_overview`)

`model_schema.py` is the team's shared input/output contract (mirrors
`MAXergy/documentation/data/model_input1.json` / `model_output_1.json`). `model_engine.py`
is a **faithful in-repo port of the team's canonical baseline model**
(`scripts/run_baseline_model.py` in the Rouxxel/MAXergy monorepo) — the MCP runs it
directly, with no dependency on the teammate's backend, and produces output **identical to
the canonical model** for the same input (`overview_smoke.py` diffs the two byte-for-byte).

Inherited from the canonical model (all flagged placeholders, upgrade incrementally):
- **Tariff** — split `arbeitspreis` (€/kWh) + `grundpreis` (€/month).
- **Solar** — flat 1000 kWh/kWp, `usable_area/7` capped at 10 kWp. (PVGIS via
  `providers.estimate_pv_production` is the intended future swap for the flat yield.)
- **Capex + subsidy** — €1400/kWp solar, €700/kWh battery, €12k heat pump, €1.2k EV
  charger; 30 % subsidy when none is given, remainder amortized at the loan rate/term.
- **Escalation** — per bucket: electricity 3 %/yr, gas/oil 4 %/yr, fuel 3 %/yr; the loan
  installment drops after `loan_term_years` (the savings cliff).
- **EV load** — taken from vehicles already typed `"ev"` (so an all-combustion household
  currently sees no added EV charging load — a known quirk of the canonical model).

To re-sync after the canonical model changes, re-port `compute_overview` and re-run the
parity test: `uv run python overview_smoke.py`.
