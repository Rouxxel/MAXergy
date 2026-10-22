# MAXergy API Contract

Single source of documentation for every request/response exchanged between the MAXergy
frontends (web, mobile), the FastAPI backend (`maxergy-api`), and the MCP service
(`maxergy-mcp`).

- **Code source of truth:** `backend/src/models/forecast_schemas.py` (Pydantic). If this
  document and the code disagree, the code wins and this document is a bug.
- **Market:** Germany only (`country = "DE"`). Units: EUR, kWh, km, litres, m², kW/kWp.
- **Status legend:** **v1** = shipped today (legacy engine shape). **v2** = planned target
  shape. Fields and endpoints marked *(v2)* or *planned* do not exist yet.

---

## 1. Base URL and paths

Routers are mounted at the **root** of the API host (decision #13):

| Method | Path | Request | Response | Status |
| ------ | ---- | ------- | -------- | ------ |
| `GET` | `/` | – | health JSON | v1 |
| `POST` | `/assessment` | `HouseholdAssessment` | `AssessmentResponse` | v1 |
| `POST` | `/forecast` | `HouseholdAssessment` | `ForecastResult` | v1 (legacy engine) → v2 |
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
| `household.roof.available` | bool | `false` → baseline-only result (planned) |
| `household.roof.usable_area_m2` | 0–500 or null | PV size derived at 0.2 kWp/m² by the production engine |
| `household.roof.orientation` | `south` \| `east` \| `west` \| `north` | |
| `household.roof.tilt_deg` | 0–90 | |
| `household.roof.shading_factor` | 0–1 | 0 = no shade |
| `household.roof.specific_yield_kwh_per_kwp` *(v2)* | number or null | Site PV yield from PVGIS (via MCP enrichment). Null → engine regional table |
| `heating.fuel_type` | `gas` \| `oil` | Only fuels supported by the production engine |
| `heating.annual_consumption` | kWh (gas) or litres (oil) | |
| `heating.annual_spend_eur` | 0–10 000 | |
| `mobility.vehicles[].vehicle_type` | `petrol` \| `diesel` \| `electric` \| `phev` \| `hybrid` | Legacy aliases accepted by the normalizer: `gas` → `petrol`, `ev` → `electric` |
| `mobility.vehicles[]` aggregation | – | Combustion vehicles: spend summed, consumption mileage-weighted (decision #6) |
| `upgrade_candidates.*` | bool | Scenarios that need a disabled component are omitted (decision #5) |
| `upgrade_candidates.solar_pv_kwp` / `battery_kwh` / `heat_pump_kw` | number or null | Sizing overrides |
| `financing.loan_term_years` | 1–30 | |
| `financing.loan_rate_pct` | 0–20 | Nominal annual rate |
| `financing.known_subsidy_eur` | number or null | Reduces financed principal |
| `forecast_horizon.short_term_months` | 1–24 | |
| `forecast_horizon.long_term_years` | 1–30 | |

---

## 3. Response — `ForecastResult`

### 3.1 v1 (shipped today, legacy engine)

Produced by `scripts/run_baseline_model.py`. Example:
[`documentation/data/model_output_1.json`](../data/model_output_1.json).

> **Legacy.** `model_output_1.json` reflects the legacy engine, which overstates savings
> (e.g. `full_upgrade` +€87/month for `model_input1.json`, while the production engine shows
> negative first-year net savings for an average household). Do not use it as a reference for
> numbers. It will be renamed `model_output_legacy.json` and replaced by a v2 example once the
> production engine serves `/forecast`.

```json
{
  "baseline": {
    "monthly_cost_eur": { "electricity": 124.5, "heating": 120.83, "mobility": 91.67, "total": 337.0 },
    "short_term_forecast": [ { "month": "2026-07", "total_eur": 291.17 } ],
    "long_term_forecast": [ { "year": 2026, "annual_total_eur": 4044.0 } ]
  },
  "scenarios": [
    {
      "id": "full_upgrade",
      "components": { "solar_pv": true, "battery": true, "heat_pump": true, "ev_charger": true },
      "sizing": { "solar_pv_kwp": 5.71, "battery_kwh": 7.5, "heat_pump_kw": 9.0 },
      "monthly_cost_eur": {
        "electricity": 0.0, "heating": 0.0, "mobility": 0.0,
        "financing_installment": 0.0, "total": 0.0
      },
      "monthly_saving_eur": 0.0,
      "monthly_saving_post_payoff_eur": null,
      "self_consumption_ratio": 0.8,
      "short_term_forecast": [ { "month": "2026-07", "total_eur": 0.0, "saving_eur": 0.0 } ],
      "long_term_forecast": [ { "year": 2026, "annual_total_eur": 0.0, "annual_saving_eur": 0.0 } ],
      "payback_month": null
    }
  ]
}
```

(Numbers in the scenario object are placeholders; see the example file for real v1 values.)

### 3.2 v2 (target, planned)

Produced by `compute_model` → `model_adapter`. Additions/changes vs v1 (values are
illustrative except the reference values below the table; zeros are placeholders):

```json
{
  "model": { "name": "energy_cost_comparison", "version": "4.0", "engine": "energy_model" },
  "assumptions_used": { "solar_kwp": 5.83, "battery_usable_kwh": 10.0, "pv_yield_source": "regional_table" },
  "validation_warnings": ["solar_kwp not provided; estimated 5.83 kWp from 35.0 m² roof"],
  "baseline": { "...": "unchanged v1 shape" },
  "scenarios": [
    {
      "id": "full_upgrade",
      "...": "v1 fields",
      "monthly_saving_eur": -24.76,
      "monthly_saving_post_payoff_eur": 184.59,
      "self_consumption_ratio": 0.62,
      "financials": {
        "gross_investment_eur": 0.0,
        "subsidy_eur": 0.0,
        "financed_principal_eur": 0.0,
        "loan_term_months": 180,
        "cumulative_net_savings_eur_20y_central": 24828,
        "break_even_year": null
      },
      "long_term_forecast": [ { "year": 2026, "annual_total_eur": 0.0, "annual_saving_eur": 0.0, "scenario": "central" } ],
      "long_term_band": { "low": [], "high": [] }
    }
  ]
}
```

| Field | Definition |
| ----- | ---------- |
| `monthly_saving_eur` | **Month-1 net**: energy cost reduction − financing instalment in the first short-term month. Signed. |
| `monthly_saving_post_payoff_eur` | Energy cost reduction for the same month without the instalment. **Always present** in v2 (was conditional in v1). |
| `monthly_cost_eur.financing_installment` | Monthly annuity instalment. |
| `self_consumption_ratio` | Σ(direct self-consumption + battery discharge) / Σ PV generation over the short-term window (v1: fixed preset). |
| `payback_month` | First month where production `cumulative_net_savings_eur` > 0 (null if never within horizon). |
| `financials.cumulative_net_savings_eur_20y_central` | Last value of `long_term_projection.central[].financial_result.cumulative_net_savings_eur`. |
| `validation_warnings` | Inputs the engine estimated or defaulted. |

Reference values (average German household, `model_test_summary.md`): full_upgrade instalment
€209.35/month, Year-1 net −€297 (≈ −€24.76/month), 20-year cumulative €24,828.

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

v2 (planned):

```json
{
  "selected_scenario_id": "full_upgrade",
  "selected_scenario": { "...": "Scenario" },
  "ranked_scenarios": [
    { "id": "full_upgrade", "score_eur": 24828, "metric": "cumulative_20y_central" },
    { "id": "pv_battery_heatpump", "score_eur": 21000, "metric": "cumulative_20y_central" }
  ],
  "metric_used": "cumulative_20y_central",
  "rationale": "string built only from forecast fields"
}
```

`metric_used` enum: `month_1_net`, `cumulative_20y_central`.

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
them: default tariff (`arbeitspreis` 0.32 €/kWh, `grundpreis` 12.50 €/month), EEG feed-in tiers
(≤10 kWp 0.082, 10–40 kWp 0.071, >40 kWp 0.058 €/kWh), heat-pump SCOP 3.5, PV 0.2 kWp/m²,
default battery 10 kWh, component capex, long-term price growth bands.

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
| 422 | `{ "detail": [ ...field errors ] }` (development) / `{ "detail": "Invalid request." }` (production) | Validation failure |
| 429 | rate-limit message | SlowAPI limit exceeded |
| 500 | `{ "detail": "Forecast generation failed" }` / `"Internal server error."` | Engine or unexpected failure |
| 503 | `{ "detail": "<service> unavailable" }` | *(v2)* MCP enrichment disabled/unreachable, Gemini key missing |

---

## 13. Decision log

Status: **Decided** or **Proposed** (recommendation, awaiting confirmation).

| # | Topic | Decision | Status |
| - | ----- | -------- | ------ |
| 1 | Primary ranking metric | `cumulative_20y_central` for best plan; month-1 net shown prominently | Proposed |
| 2 | Number of engines | One: `compute_model` | Decided |
| 3 | Type source of truth | Backend Pydantic; frontend + MCP generated/verified from OpenAPI | Decided |
| 4 | Combined endpoint | Add `POST /plan` | Proposed |
| 5 | `upgrade_candidates` filtering | Omit scenarios needing a disabled component | Proposed |
| 6 | Multi-vehicle | Sum combustion spend, mileage-weighted consumption | Proposed |
| 7 | Carbon reduction | Out of scope until emission-factor spec exists | Proposed |
| 8 | Mock default | `true` in `.env.example` for demos; `false` in CI live smoke | Proposed |
| 9 | MCP placement | Standalone Railway service `maxergy-mcp` | Decided |
| 10 | MCP → engine access | HTTP `POST /plan` | Decided |
| 11 | MCP public domain | New MAXergy domain; old domain kept during transition | Proposed |
| 12 | `monthly_saving_post_payoff_eur` | Always present in v2 | Proposed |
| 13 | API path prefix | Root paths (no `/api/v1`) — matches routers and frontend client today | Decided |
| 14 | Commercial buildings in MCP | Disabled until a commercial model exists | Proposed |
