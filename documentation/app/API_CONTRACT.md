# MAXergy API Contract

Single source of documentation for every request/response exchanged between the MAXergy
frontends (web, mobile), the FastAPI backend (`maxergy-api`), and the MCP service
(`maxergy-mcp`).

- **Code source of truth:** `backend/src/models/forecast_schemas.py` (Pydantic). If this
  document and the code disagree, the code wins and this document is a bug.
- **Market:** Germany only (`country = "DE"`). Units: EUR, kWh, km, litres, m², kW/kWp.
- **Status legend:** **v1** = original legacy-engine shape. **v2** = production-engine shape.
  Endpoints and fields marked *planned* do not exist yet.

---

## 1. Base URL and paths

Routers are mounted at the **root** of the API host (decision #13):

| Method | Path | Request | Response | Status |
| ------ | ---- | ------- | -------- | ------ |
| `GET` | `/` | – | health JSON | v1 |
| `POST` | `/assessment` | `HouseholdAssessment` | `AssessmentResponse` | v1 |
| `POST` | `/forecast` | `HouseholdAssessment` | `ForecastResult` | **v2** (production engine) |
| `POST` | `/recommendation` | `HouseholdAssessment` | `Recommendation` | v1 **broken (500)** → fix planned |
| `POST` | `/plan` | `HouseholdAssessment` | `PlanResponse` | *(v2, planned)* |
| `GET` | `/benchmark` | – | `BenchmarkData` | v1 (partly hard-coded) → computed from the engine (planned) |
| `GET` | `/assumptions` | – | `Assumptions` | *(v2, planned)* |
| `POST` | `/location/enrich` | `EnrichmentRequest` | `EnrichmentResponse` | *(v2, planned)* |
| `POST` | `/advisor/chat` | `AdvisorChatRequest` | `AdvisorChatResponse` | v1 |
| `POST` | `/visualization/forecast-chart` | `HouseholdAssessment` | chart payload | v1 |

Local: `http://localhost:8000`. Production: the public domain of the Railway service
`maxergy-api` (deployment runbook `documentation/app/DEPLOYMENT.md`, planned).

---

## 2. Request — `HouseholdAssessment`

Example (identical to [`documentation/data/model_input1.json`](../data/model_input1.json)):

```json
{
  "location": { "postcode": "10115", "country": "DE" },
  "household": {
    "occupants": 3,
    "electricity": {
      "annual_kwh": 4200,
      "current_tariff_type": "fixed",
      "arbeitspreis_eur_per_kwh": 0.32,
      "grundpreis_eur_per_month": 12.5,
      "contract_end_date": "2026-12-31"
    },
    "roof": {
      "available": true,
      "usable_area_m2": 40,
      "orientation": "south",
      "tilt_deg": 30,
      "shading_factor": 0.1,
      "specific_yield_kwh_per_kwp": null
    }
  },
  "heating": {
    "fuel_type": "gas",
    "annual_consumption": 14000,
    "annual_spend_eur": 1450,
    "building": { "floor_area_m2": 120, "insulation_class": "average" }
  },
  "mobility": {
    "vehicle_count": 1,
    "vehicles": [
      {
        "vehicle_type": "petrol",
        "annual_mileage_km": 12000,
        "fuel_consumption_l_per_100km": 6.5,
        "annual_fuel_spend_eur": 1100
      }
    ]
  },
  "upgrade_candidates": {
    "solar_pv": true, "battery": true, "heat_pump": true, "ev_charger": true,
    "solar_pv_kwp": null, "battery_kwh": null, "heat_pump_kw": null
  },
  "financing": { "loan_term_years": 15, "loan_rate_pct": 4.5, "known_subsidy_eur": null },
  "forecast_horizon": { "short_term_months": 12, "long_term_years": 20 }
}
```

### Field glossary

| Field | Type / range | Notes |
| ----- | ------------ | ----- |
| `location.postcode` | string, 3–10 chars | German postcode; drives regional PV yield and degree days |
| `location.country` | `"DE"` | Other countries will be rejected (planned) |
| `household.occupants` | int 1–20 | |
| `household.electricity.annual_kwh` | 0–100 000 | |
| `household.electricity.arbeitspreis_eur_per_kwh` | 0–2 | Work price (€/kWh) |
| `household.electricity.grundpreis_eur_per_month` | 0–100 | Standing charge (€/month) |
| `household.electricity.contract_end_date` | ISO date or null | |
| `household.roof.available` | bool | `false` → solar disabled → no scenarios (baseline-only result) |
| `household.roof.usable_area_m2` | 0–500 or null | PV size derived at 6 m²/kWp by the production engine (unless `solar_pv_kwp` is set) |
| `household.roof.orientation` | `south` \| `east` \| `west` \| `north` | |
| `household.roof.tilt_deg` | 0–90 | |
| `household.roof.shading_factor` | 0–1 | 0 = no shade |
| `household.roof.specific_yield_kwh_per_kwp` | > 0 and ≤ 2000, or null | Site PV yield in kWh/kWp (e.g. PVGIS; MCP enrichment planned). Null → engine regional table (950–1150 by first postcode digit) |
| `heating.fuel_type` | `gas` \| `oil` | Only fuels supported by the production engine; anything else → 422 |
| `heating.annual_consumption` | kWh (gas) or litres (oil) | |
| `heating.annual_spend_eur` | 0–10 000 | |
| `mobility.vehicles[].vehicle_type` | `petrol` \| `diesel` \| `electric` \| `phev` \| `hybrid` | Aliases: `gas` → `petrol`, `ev` → `electric`; other values → 422 |
| `mobility.vehicles[]` aggregation | – | Combustion vehicles: mileage and spend summed, consumption mileage-weighted, type of the highest-mileage vehicle (decision #6). Electric vehicles are excluded (charging assumed in household electricity). Reported in `validation_warnings` |
| `upgrade_candidates.*` | bool | Scenarios that need a disabled component are omitted (decision #5). The EV charger is also disabled when there is no combustion vehicle |
| `upgrade_candidates.solar_pv_kwp` / `battery_kwh` | number or null | Sizing overrides used by the engine |
| `upgrade_candidates.heat_pump_kw` | number or null | Echoed in `sizing.heat_pump_kw`; the engine does not size heat pumps by power |
| `financing.loan_term_years` | 1–30 | |
| `financing.loan_rate_pct` | 0–20 | Nominal annual rate |
| `financing.known_subsidy_eur` | number or null | Reduces financed principal |
| `forecast_horizon.short_term_months` | 1–24 | |
| `forecast_horizon.long_term_years` | 1–30 | |

---

## 3. Response — `ForecastResult`

### 3.1 v2 (current)

Produced by the production engine: `compute_model` (`scripts/energy_model`) →
`backend/src/services/forecasting/model_adapter.py`. Full example for `model_input1.json`:
[`documentation/data/model_output_v2.json`](../data/model_output_v2.json). Trimmed excerpt
(one scenario, first month/year only):

```json
{
  "model": { "name": "energy_cost_comparison", "version": "4.0", "engine": "energy_model" },
  "assumptions_used": {
    "solar_kwp": 6.667, "feed_in_tariff_eur_per_kwh": 0.082, "battery_usable_kwh": 10.0,
    "heat_pump_scop": 3.0, "pv_specific_yield_kwh_per_kwp": 950.0, "pv_yield_source": "regional_table"
  },
  "validation_warnings": [
    "solar_kwp not provided; estimated 6.67 kWp from 40.0 m² roof",
    "battery_kwh not specified; using default 10.0 kWh"
  ],
  "baseline": {
    "monthly_cost_eur": { "electricity": 124.41, "heating": 120.83, "mobility": 91.67, "total": 336.91 },
    "short_term_forecast": [ { "month": "2026-11", "total_eur": 446.31 } ],
    "long_term_forecast": [ { "year": 2026, "annual_total_eur": 4085.35 } ]
  },
  "scenarios": [
    {
      "id": "full_upgrade",
      "components": { "solar_pv": true, "battery": true, "heat_pump": true, "ev_charger": true },
      "sizing": { "solar_pv_kwp": 6.67, "battery_kwh": 10.0, "heat_pump_kw": null },
      "monthly_cost_eur": {
        "electricity": 157.81, "heating": 0.0, "mobility": 0.0,
        "financing_installment": 218.28, "total": 376.09
      },
      "monthly_saving_eur": -39.18,
      "monthly_saving_post_payoff_eur": 179.1,
      "self_consumption_ratio": 0.744,
      "short_term_forecast": [ { "month": "2026-11", "total_eur": 542.27, "saving_eur": -95.97 } ],
      "long_term_forecast": [
        { "year": 2026, "annual_total_eur": 4519.35, "annual_saving_eur": -434.0, "cumulative_saving_eur": -434.0, "scenario": "central" }
      ],
      "long_term_band": {
        "low":  [ { "year": 2026, "annual_total_eur": 4515.09, "annual_saving_eur": -457.98, "cumulative_saving_eur": -457.98, "scenario": "low" } ],
        "high": [ { "year": 2026, "annual_total_eur": 4523.34, "annual_saving_eur": -410.29, "cumulative_saving_eur": -410.29, "scenario": "high" } ]
      },
      "payback_month": 138,
      "financials": {
        "gross_investment_eur": 28533.33, "subsidy_eur": 0.0, "financed_principal_eur": 28533.33,
        "loan_term_months": 180, "horizon_years": 20,
        "cumulative_net_savings_central_eur": 21959.78,
        "cumulative_net_savings_low_eur": 7243.04,
        "cumulative_net_savings_high_eur": 42854.71,
        "break_even_year": 12
      }
    }
  ]
}
```

Numbers depend on the forecast start month (the engine starts in the month after "today").

| Field | Definition |
| ----- | ---------- |
| `baseline.monthly_cost_eur.*` | Average monthly cost over the first 12 short-term months (constant current prices). |
| `scenarios[]` | Up to six scenarios in fixed order; a scenario is omitted when it needs a disabled upgrade candidate. |
| `monthly_cost_eur.electricity` | Grid electricity cost **net of feed-in revenue** (12-month average). |
| `monthly_cost_eur.financing_installment` | Average monthly loan instalment over the same 12 months. |
| `monthly_cost_eur.total` | electricity + heating + mobility + financing_installment. |
| `monthly_saving_eur` | **Average monthly net saving over the first 12 months** = `baseline.total − scenario.total` (energy cost reduction − instalment). Signed; negative means the household pays more while the loan runs. Averaging avoids seasonal distortion of a single month (e.g. a November start shows −€96 for one month vs −€39 on average). |
| `monthly_saving_post_payoff_eur` | Average monthly energy cost reduction without the instalment (what the household saves once the loan is repaid, at current prices). **Always present.** |
| `self_consumption_ratio` | (PV direct self-consumption + battery discharge) / PV generation, year 1 (central). |
| `short_term_forecast[]` | Per month: `total_eur` = upgraded energy cost + instalment; `saving_eur` = net saving. |
| `long_term_forecast[]` | Central price scenario, per projection year: `annual_total_eur` = upgraded energy cost + instalments; `annual_saving_eur` = annual net saving; `cumulative_saving_eur`. `year` is the calendar year in which the projection year starts. |
| `long_term_band.low` / `.high` | Same points for the low/high price scenarios. |
| `payback_month` | Month (counted from the forecast start) in which cumulative net savings turn positive, interpolated within the break-even year (central); null if never within the horizon. |
| `financials.*` | Investment (gross, subsidy, financed principal), loan term, horizon, cumulative net savings at the end of the horizon for central/low/high, and `break_even_year` (1-based). |
| `assumptions_used` | Engine assumptions with provenance (includes `pv_specific_yield_kwh_per_kwp`, `pv_yield_source`). |
| `validation_warnings` | Inputs the engine estimated, defaulted, or aggregated. |

Reference values for the average German household
(`documentation/data/test_outputs/model_test_summary.md`, verified by
`backend/tests/test_model_adapter.py`): full_upgrade instalment €209.35/month, year-1 net
−€297, 20-year cumulative (central) €24,828.

### 3.2 v1 (legacy, no longer served)

The original shape produced by the legacy engine (`research/legacy/run_baseline_model.py`),
example [`documentation/data/model_output_legacy.json`](../data/model_output_legacy.json). v2 is
a superset of v1, except that `monthly_saving_post_payoff_eur` was only present when
`monthly_saving_eur` was negative and `self_consumption_ratio` was a fixed preset. The legacy
engine overstates savings (e.g. `full_upgrade` +€87/month for `model_input1.json`); do not use
its numbers.

---

## 4. Response — `Recommendation`

v1 (code today; endpoint currently returns 500):

```json
{
  "selected_scenario_id": "full_upgrade",
  "selected_scenario": { "...": "Scenario" },
  "ranked_scenarios": [["full_upgrade", 87.44], ["pv_ev", 126.78]],
  "rationale": "string"
}
```

v2 (planned; scores illustrative):

```json
{
  "selected_scenario_id": "full_upgrade",
  "selected_scenario": { "...": "Scenario" },
  "ranked_scenarios": [
    { "id": "full_upgrade", "score_eur": 21959.78, "metric": "cumulative_central" },
    { "id": "pv_ev", "score_eur": 21697.42, "metric": "cumulative_central" }
  ],
  "metric_used": "cumulative_central",
  "rationale": "string built only from forecast fields"
}
```

`metric_used` enum: `monthly_net` (scenario `monthly_saving_eur`), `cumulative_central`
(`financials.cumulative_net_savings_central_eur`, end of the horizon).

## 5. Response — `PlanResponse` *(v2, planned)*

```json
{ "forecast": { "...": "ForecastResult v2" }, "recommendation": { "...": "Recommendation v2" } }
```

Computed from **one** engine run. Used by web, mobile, and every MCP savings tool.

## 6. `AssessmentResponse`

```json
{ "assessment_id": "uuid", "status": "submitted", "message": "string" }
```

Frontends must read `assessment_id` (not `id`).

## 7. Advisor

`AdvisorChatRequest`:

```json
{
  "assessment_id": "uuid or null",
  "forecast_result": { "...": "ForecastResult or null (to be deprecated in favour of plan)" },
  "plan": { "...": "PlanResponse or null (v2, planned)" },
  "user_message": "string (1–1000 chars)",
  "conversation_history": [ { "role": "user", "content": "..." } ]
}
```

`AdvisorChatResponse`:

```json
{ "advisor_message": "string", "context_used": ["user_question"], "suggestions": ["string"] }
```

Mocks must return this exact shape (not `{ "reply": ... }`).

## 8. Benchmark (`GET /benchmark`)

```json
{
  "household": {
    "location": "50667, DE", "occupants": 3, "annual_electricity_kwh": 3500,
    "heating_type": "gas", "heating_annual_kwh": 14000, "vehicle_type": "petrol",
    "annual_mileage_km": 12000, "roof_area_m2": 35, "roof_orientation": "south", "roof_tilt_deg": 32
  },
  "recommendation": {
    "scenario": "full_upgrade", "break_even_year": 8, "monthly_instalment_eur": 209,
    "cumulative_savings_eur": 24828, "description": "string"
  },
  "scenarios_count": 6,
  "projection_years": 20,
  "model_version": "4.0"
}
```

`recommendation.*` is hard-coded today; it will be computed with the same logic as `/plan` (planned).

## 9. Enrichment *(v2, planned)*

`POST /location/enrich` request: `{ "postcode": "50667", "address": null, "country": "DE" }`

Response:

```json
{
  "lat": 50.94, "lon": 6.95,
  "roof": { "usable_area_m2": 38.0, "tilt_deg": 35, "orientation": "south", "max_array_kwp": 7.6, "low_confidence": false },
  "specific_yield_kwh_per_kwp": 975.0,
  "source": { "roof": "google_solar", "yield": "pvgis" }
}
```

`source.roof`: `google_solar` | `area_estimate` | `unavailable`. `source.yield`: `pvgis` | `regional_table`.

## 10. Assumptions *(v2, planned)*

`GET /assumptions` returns the production engine defaults so no other component hard-codes
them. Current engine values: default tariff (`arbeitspreis` 0.32 €/kWh, `grundpreis`
12.50 €/month), EEG feed-in tiers (≤10 kWp 0.082, 10–40 kWp 0.071, >40 kWp 0.058 €/kWh),
heat-pump SCOP 3.0 (existing boiler efficiency 0.85), PV 6 m²/kWp, regional yield 950–1150
kWh/kWp, default battery 10 kWh, capex PV 1400 €/kWp, battery 600 €/kWh, heat pump 12 000 €,
EV charger 1200 €, long-term price growth bands.

## 11. MCP tool contract *(v2, planned)*

| Tool | Input | Output |
| ---- | ----- | ------ |
| `start_advisor` | – | onboarding script (string) |
| `geocode_address` | `address` | `{ address, lat, lon }` |
| `get_roof_geometry` | `lat, lon` | roof segments, `max_array_kwp`, `suggested_system_kwp`, `low_confidence` |
| `estimate_pv_production` | `lat, lon, kwp, tilt_degrees, azimuth_degrees` | `{ annual_kwh, monthly_kwh, specific_yield_kwh_per_kwp }` |
| `estimate_roof_capacity_from_area` | `floor_area_m2, stories` | roof ceiling estimate |
| `estimate_heating_spend`, `suggest_battery_kwh`, `suggest_electricity_price` | as today | values based on `GET /assumptions` |
| `energy_savings_overview` | `HouseholdAssessment` | `PlanResponse` (verbatim from `POST /plan`) |
| `compare_scenarios` | `HouseholdAssessment` | `recommendation.ranked_scenarios` + headline per scenario |
| `project_savings` | `HouseholdAssessment` | cumulative series from `forecast.scenarios[].long_term_forecast` |
| `next_best_upgrade` | `HouseholdAssessment` | best marginal step from `/plan` |

The MCP never computes savings itself.

## 12. Errors

| Status | Body | When |
| ------ | ---- | ---- |
| 422 | `{ "detail": [ ...field errors ] }` (development) / `{ "detail": "Invalid request." }` (production) | Schema validation failure |
| 422 | `{ "detail": "<engine message>" }` e.g. `"heating.fuel_type 'pellets' is not supported; supported fuels: gas, oil"` | Valid assessment the engine cannot model (`/forecast`) |
| 429 | rate-limit message | SlowAPI limit exceeded |
| 500 | `{ "detail": "Forecast generation failed" }` / `"Internal server error."` | Engine or unexpected failure |
| 503 | `{ "detail": "<service> unavailable" }` | *(v2)* MCP enrichment disabled/unreachable, Gemini key missing |

---

## 13. Decision log

Status: **Decided** or **Proposed** (recommendation, awaiting confirmation).

| # | Topic | Decision | Status |
| - | ----- | -------- | ------ |
| 1 | Primary ranking metric | `cumulative_central` for best plan; `monthly_net` shown prominently | Proposed |
| 2 | Number of engines | One: `compute_model` | Decided |
| 3 | Type source of truth | Backend Pydantic; frontend + MCP generated/verified from OpenAPI | Decided |
| 4 | Combined endpoint | Add `POST /plan` | Proposed |
| 5 | `upgrade_candidates` filtering | Omit scenarios needing a disabled component | Decided (implemented) |
| 6 | Multi-vehicle | Sum combustion mileage and spend, mileage-weighted consumption; EVs excluded | Decided (implemented) |
| 7 | Carbon reduction | Out of scope until emission-factor spec exists | Proposed |
| 8 | Mock default | `true` in `.env.example` for demos; `false` in CI live smoke | Proposed |
| 9 | MCP placement | Standalone Railway service `maxergy-mcp` | Decided |
| 10 | MCP → engine access | HTTP `POST /plan` | Decided |
| 11 | MCP public domain | New MAXergy domain; old domain kept during transition | Proposed |
| 12 | `monthly_saving_post_payoff_eur` | Always present in v2 | Decided (implemented) |
| 15 | Headline monthly figures | 12-month averages (not the first month) to avoid seasonal distortion | Decided (implemented) |
| 13 | API path prefix | Root paths (no `/api/v1`) — matches routers and frontend client today | Decided |
| 14 | Commercial buildings in MCP | Disabled until a commercial model exists | Proposed |
