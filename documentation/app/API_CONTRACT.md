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
| `POST` | `/recommendation` | `HouseholdAssessment` (+ `?metric=`) | `Recommendation` | **v2** |
| `POST` | `/plan` | `HouseholdAssessment`, or none with `?assessment_id=` (+ `?metric=`) | `PlanResponse` | **v2** |
| `GET` | `/benchmark` | – | `BenchmarkData` | **v2** (computed by the engine, cached 1 h) |
| `GET` | `/assumptions` | – | `Assumptions` | **v2** |
| `POST` | `/location/enrich` | `EnrichmentRequest` | `EnrichmentResponse` | **v2** (via the MCP; 503 when disabled) |
| `POST` | `/advisor/chat` | `AdvisorChatRequest` | `AdvisorChatResponse` | **v2** (grounded in `plan`; chat onboarding via MCP script + `run_plan`) |
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
| `location.country` | `"DE"` | The web and mobile forms only offer Germany (others shown as coming soon); the API does not reject other values yet (planned) |
| `household.occupants` | int 1–20 | |
| `household.electricity.annual_kwh` | 0–100 000 | |
| `household.electricity.arbeitspreis_eur_per_kwh` | 0–2 | Work price (€/kWh) |
| `household.electricity.grundpreis_eur_per_month` | 0–100 | Standing charge (€/month) |
| `household.electricity.contract_end_date` | ISO date or null | |
| `household.roof.available` | bool | `false` → solar disabled → **baseline-only result**: `/plan` returns 200 with `forecast.scenarios: []`, the baseline costs and forecasts, and a recommendation with `selected_scenario_id: null` and a rationale explaining that no upgrade is possible. The frontends show the current costs and the rationale |
| `household.roof.usable_area_m2` | 0–500 or null | PV size derived at 6 m²/kWp by the production engine (unless `solar_pv_kwp` is set) |
| `household.roof.orientation` | `south` \| `south_east` \| `east` \| `north_east` \| `north` \| `north_west` \| `west` \| `south_west` | |
| `household.roof.tilt_deg` | 0–90 | |
| `household.roof.shading_factor` | 0–1 | 0 = no shade |
| `household.roof.specific_yield_kwh_per_kwp` | > 0 and ≤ 2000, or null | Site PV yield in kWh/kWp, set by the frontends from `POST /location/enrich` (PVGIS) when available. Null → engine regional table (950–1150 by first postcode digit) |
| `heating.fuel_type` | `gas` \| `oil` | Only fuels supported by the production engine; anything else → 422. The forms list other systems as "not modelled yet" (web) or hide them (mobile) |
| `heating.annual_consumption` | kWh (gas) or litres (oil) | |
| `heating.annual_spend_eur` | 0–10 000 | |
| `heating.building.floor_area_m2` / `insulation_class` | m² / `poor` \| `medium` \| `good` \| `excellent` | Collected for context; not used by the engine (heating demand comes from consumption or spend) |
| `mobility.vehicles[].vehicle_type` | `petrol` \| `diesel` \| `electric` \| `phev` \| `hybrid` | Aliases: `gas` → `petrol`, `ev` → `electric`; other values → 422 |
| `mobility.vehicles[].annual_mileage_km` | km/year | Required by the forms for every vehicle (the API treats null as 0 km) |
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

Built by `backend/src/services/recommendation/recommendation_service.py`
(`build_recommendation`), the single ranking function. Example for `model_input1.json`
(scores from `model_output_v2.json`):

```json
{
  "selected_scenario_id": "full_upgrade",
  "selected_scenario": { "...": "Scenario (as in ForecastResult)" },
  "ranked_scenarios": [
    { "id": "full_upgrade", "score_eur": 21959.78, "metric": "cumulative_central" },
    { "id": "pv_ev", "score_eur": 21697.42, "metric": "cumulative_central" },
    { "id": "pv_battery", "score_eur": 8145.08, "metric": "cumulative_central" }
  ],
  "metric_used": "cumulative_central",
  "rationale": "Solar panels, battery storage, a heat pump and an EV charger (full_upgrade) ranks best by long-term net savings. During the 15-year loan it costs about €39/month more than today (loan instalment €218/month). Once the loan is repaid it saves about €179/month at today's prices. Over 20 years the cumulative net saving is about €21,960 (central price scenario; €7,243 to €42,855 across low/high prices), breaking even in year 12."
}
```

| Field | Definition |
| ----- | ---------- |
| `metric_used` | `cumulative_central` (default; `config_file.json` → `recommendation.default_metric`) or `monthly_net`. Override per request with `?metric=`. |
| `ranked_scenarios[]` | All scenarios best-first; `score_eur` is the metric value: `financials.cumulative_net_savings_central_eur` for `cumulative_central`, `monthly_saving_eur` for `monthly_net`. |
| Tie-breaks | `cumulative_central`: higher first-year net saving, then lower instalment. `monthly_net`: higher cumulative net savings, then lower instalment. |
| `rationale` | Built only from forecast fields. When the monthly net saving is negative it states the extra monthly cost during the loan, the post-payoff saving, and the cumulative outcome. |
| No scenarios | `selected_scenario_id` and `selected_scenario` are `null`, `ranked_scenarios` is empty, and the rationale explains why (e.g. no usable roof). |

The v1 shape (`ranked_scenarios` as `[id, saving]` tuples, no `metric_used`) is no longer served.

## 5. Response — `PlanResponse`

```json
{ "forecast": { "...": "ForecastResult" }, "recommendation": { "...": "Recommendation" } }
```

Computed from **one** engine run (the forecast is cached, so a following `/recommendation`
for the same assessment does not re-run the engine). Preferred by web, mobile, and the MCP
savings tools.

## 6. `AssessmentResponse`

```json
{ "assessment_id": "uuid", "status": "submitted", "message": "string" }
```

Frontends must read `assessment_id` (not `id`). Assessments are stored in the database and survive
restarts: `POST /plan?assessment_id=<id>` (no body) returns the plan for a stored assessment (404
unknown id; 422 when both or neither of body and `assessment_id` are sent), and the advisor uses a
stored `assessment_id` as context when no `plan` is sent.

## 7. Advisor

`AdvisorChatRequest`:

```json
{
  "assessment_id": "uuid or null",
  "plan": { "...": "PlanResponse the user is looking at, or null → chat onboarding" },
  "user_message": "string (1–1000 chars)",
  "conversation_history": [ { "role": "user | assistant", "content": "string (≤ 4000)" } ]
}
```

`AdvisorChatResponse`:

```json
{
  "advisor_message": "string",
  "context_used": ["user_question", "plan"],
  "suggestions": ["string"],
  "assessment": "HouseholdAssessment or null — set when chat onboarding finished",
  "plan": "PlanResponse or null — set when chat onboarding finished (same services as POST /plan)"
}
```

- Without `plan` but with a stored `assessment_id`: the backend computes that assessment's plan and
  grounds the answer in it (`context_used` contains `plan`).
- With `plan`: the advisor answers grounded in that plan only (recommended scenario, the three
  numbers, instalment, break-even, top-3 ranked, rationale, warnings).
- Without a plan: the advisor runs the shared onboarding script (MCP prompt `maxergy_advisor`) and
  may call the MCP lookup tools and the in-process `run_plan`; when `run_plan` succeeds the response
  carries `assessment` and `plan`, which the frontends store as the current results.
- `context_used` lists the sources: `plan`, `onboarding_script` / `onboarding_unavailable`,
  `tool:<name>` for every tool called, `development_mock` for canned development replies.
- Errors: 503 when the advisor is not configured (`GEMINI_API_KEY` missing; production) or Gemini
  is unavailable/rate-limited (message in `detail`); 504 after 45 s.

Mocks must return this exact shape (not `{ "reply": ... }`).

## 8. Benchmark (`GET /benchmark`)

```json
{
  "household": {
    "location": "50667, DE", "occupants": 3, "annual_electricity_kwh": 3500.0,
    "heating_type": "gas", "heating_annual_kwh": 14000.0, "vehicle_type": "petrol",
    "annual_mileage_km": 12000.0, "roof_area_m2": 35.0, "roof_orientation": "south", "roof_tilt_deg": 32.0
  },
  "recommendation": {
    "scenario": "full_upgrade",
    "description": "Solar panels + battery storage + heat pump + EV charger",
    "rationale": "Solar panels, battery storage, a heat pump and an EV charger (full_upgrade) ranks best by long-term net savings. During the 15-year loan it costs about €29/month more than today (loan instalment €209/month). …",
    "metric": "cumulative_central",
    "break_even_year": 9,
    "monthly_instalment_eur": 209.35,
    "monthly_saving_eur": -28.73,
    "monthly_saving_post_payoff_eur": 180.62,
    "cumulative_savings_eur": 24499.54,
    "cumulative_savings_low_eur": 9346.57,
    "cumulative_savings_high_eur": 46082.4
  },
  "cumulative_series": [
    { "year": 2026, "central": -311.54, "low": -333.6, "high": -289.73 },
    "…",
    { "year": 2045, "central": 24499.54, "low": 9346.57, "high": 46082.4 }
  ],
  "scenarios_count": 6,
  "projection_years": 20,
  "model_version": "4.0",
  "forecast_start": "2026-11"
}
```

- Computed, not hard-coded: `documentation/data/test_profiles/average_german_household.json` (a
  full `HouseholdAssessment`; path in `config_file.json` → `benchmark.profile_path`) runs through
  the same forecasting and recommendation services as `POST /plan`, so the scenario, figures and
  rationale equal `/plan` for that household (tested in `backend/tests/test_benchmark.py`).
- Cached for `benchmark.cache_ttl_seconds` (3600). Rate limit 25/minute (`maxergy_benchmark`).
- `forecast_start` is the first forecast month: the engine starts the month after the run date, so
  the cumulative totals move slightly from month to month (e.g. €24,828 for a July start, about
  €24,500 for November). Instalment, sizes and the recommended plan do not change.
- `monthly_saving_eur` is the year-1 monthly net including the instalment (negative during
  financing for this household); `cumulative_series` holds the recommended plan's cumulative net
  savings per year (central, low, high) for the landing chart.
- On failure: 500 (the landing pages then show the last recorded response with its `forecast_start`).

## 9. Enrichment (`POST /location/enrich`)

Looks up coordinates, a roof proposal and the site PV yield through the MCP service (Google
Geocoding, Google Solar, PVGIS at 1 kWp), to pre-fill `household.roof` and
`household.roof.specific_yield_kwh_per_kwp`.

Request (`EnrichmentRequest`; `postcode` and/or `address` required, `country` must be `"DE"`):
`{ "postcode": "50667", "address": null, "country": "DE" }`

Response (`EnrichmentResponse`):

```json
{
  "lat": 50.94, "lon": 6.96,
  "roof": { "usable_area_m2": 38.0, "tilt_deg": 35.0, "azimuth_deg": 170.0, "orientation": "south", "max_array_kwp": 7.2, "low_confidence": false },
  "specific_yield_kwh_per_kwp": 1012.0,
  "source": { "roof": "google_solar", "pv_yield": "pvgis" },
  "warnings": []
}
```

| Field | Definition |
| ----- | ---------- |
| `roof` | From the largest roof segment; `null` when the roof scan fails (`source.roof = "unavailable"`, reason in `warnings`). `orientation` uses the engine's eight names (`south`, `south_east`, …). |
| `specific_yield_kwh_per_kwp` | PVGIS yield for 1 kWp at the roof's tilt/azimuth (30°/south if no roof); `null` when PVGIS fails (`source.pv_yield = "unavailable"`; the engine then uses its regional table). |
| `low_confidence` | The roof scan probably found a small adjacent building; ask the user to confirm the size. |

Errors: 422 for an invalid request or a location that cannot be geocoded; 503 when the MCP is
disabled (`MCP_ENABLED`), unreachable, rejects the backend's token, or has no Google key.

## 10. Assumptions (`GET /assumptions`)

Returns the production engine defaults (read from `scripts/energy_model` configuration
objects) so no other component hard-codes them. Cacheable for one hour. Trimmed example:

```json
{
  "tariff": { "arbeitspreis_eur_per_kwh": 0.32, "grundpreis_eur_per_month": 12.5, "gas_eur_per_kwh": 0.1, "oil_eur_per_litre": 1.05, "petrol_eur_per_litre": 1.75 },
  "consumption": { "electricity_kwh_per_person_per_year": 1500.0, "oil_kwh_per_litre": 10.0 },
  "solar": {
    "m2_per_kwp": 6.0, "default_yield_kwh_per_kwp": 1000.0, "annual_degradation_pct": 0.5,
    "regional_yield_kwh_per_kwp": { "1": 950.0, "4": 1030.0, "8": 1150.0, "...": "..." },
    "feed_in_tariff_eur_per_kwh": { "up_to_10_kwp": 0.082, "10_to_40_kwp": 0.071, "above_40_kwp": 0.058 }
  },
  "battery": { "default_usable_kwh": 10.0, "round_trip_efficiency": 0.9025 },
  "heat_pump": { "scop": 3.0, "existing_heating_efficiency": 0.85 },
  "ev": { "kwh_per_100km": 18.0, "charging_efficiency": 0.92, "home_charging_share": 0.8 },
  "investment_costs": { "pv_eur_per_kwp": 1400.0, "battery_eur_per_kwh": 600.0, "heat_pump_eur_fixed": 12000.0, "ev_charger_eur_fixed": 1200.0 },
  "financing": { "loan_term_years": 15, "loan_rate_pct": 4.5 },
  "long_term_price_growth": { "electricity": { "low": 0.01, "central": 0.03, "high": 0.05 }, "...": "..." },
  "supported": { "country": ["DE"], "heating_fuels": ["gas", "oil"], "vehicle_types": ["petrol", "diesel", "electric", "phev", "hybrid"], "building_types": ["residential"] }
}
```

Used by the MCP suggestion tools (`default_assumptions`, `suggest_electricity_price`,
`estimate_heating_spend`, `estimate_roof_capacity_from_area`, `suggest_battery_kwh`).

## 11. MCP tool contract

The MCP savings tools take a `HouseholdAssessment` (§2; the MCP's `contract.py` is generated
from the backend schemas) and never compute savings themselves.

| Tool | Input | Output |
| ---- | ----- | ------ |
| `start_advisor` | – | onboarding script (string, from `instructions.py`) |
| `default_assumptions` | – | `GET /assumptions` (§10) |
| `geocode_address` | `address` | `{ address, lat, lon }` |
| `get_roof_geometry` | `lat, lon` | roof segments, `max_array_area_m2`, `max_array_kwp`, `suggested_system_kwp`, `low_confidence` |
| `estimate_pv_production` | `lat, lon, kwp, tilt_degrees, azimuth_degrees` | `{ annual_kwh, monthly_kwh, specific_yield_kwh_per_kwp }` |
| `estimate_roof_capacity_from_area` | `floor_area_m2, stories` | `{ usable_area_m2, estimated_max_kwp }` (engine `m2_per_kwp`) |
| `suggest_electricity_price` | `building_type, monthly_spend_eur` | default tariff + implied annual kWh (residential only) |
| `estimate_heating_spend` | `living_area_m2, heating_type, building_type` | gas/oil consumption and spend (residential gas/oil only) |
| `suggest_battery_kwh` | `pv_kwp, annual_electricity_kwh` | battery size proposal + engine default |
| `energy_savings_overview` | `assessment, metric?` | `PlanResponse` verbatim from `POST /plan` |
| `compare_scenarios` | `assessment, metric?` | backend ranking with per-scenario summary + headline |
| `project_savings` | `assessment` | years + cumulative net savings per scenario (central) |
| `next_best_upgrade` | `assessment, current_scenario_id?` | recommended scenario and what each extra component adds |

Unsupported inputs (non-residential buildings, heating other than gas/oil) return
`{ "supported": false, "note": ... }` from the suggestion tools; backend errors (e.g. 422) are
relayed as tool errors with the backend's `detail`.

## 12. Errors

| Status | Body | When |
| ------ | ---- | ---- |
| 422 | `{ "detail": [ ...field errors ] }` (development) / `{ "detail": "Invalid request." }` (production) | Schema validation failure |
| 422 | `{ "detail": "<engine message>" }` e.g. `"heating.fuel_type 'pellets' is not supported; supported fuels: gas, oil"` | Valid assessment the engine cannot model (`/forecast`) |
| 401 | `{ "detail": "Invalid service token" }` | `Authorization: Bearer` present but not the configured `MAXERGY_SERVICE_TOKEN` (`/plan`, `/forecast`, `/recommendation`, `/assumptions`) |
| 429 | rate-limit message | Per-endpoint limit exceeded (per client IP; service-token callers share a separate `service_request_limit`) |
| 500 | `{ "detail": "Forecast generation failed" }` / `"Internal server error."` | Engine or unexpected failure |
| 503 | `{ "detail": "Location enrichment unavailable: <reason>" }` | `/location/enrich` when the MCP is disabled, unreachable or misconfigured |

---

## 13. Decision log

Status: **Decided** or **Proposed** (recommendation, awaiting confirmation).

| # | Topic | Decision | Status |
| - | ----- | -------- | ------ |
| 1 | Primary ranking metric | `cumulative_central` for best plan (configurable, `?metric=monthly_net` per request); `monthly_net` shown prominently in the UI | Decided (implemented) |
| 2 | Number of engines | One: `compute_model` | Decided |
| 3 | Type source of truth | Backend Pydantic; frontend + MCP generated/verified from OpenAPI | Decided |
| 4 | Combined endpoint | Add `POST /plan` | Decided (implemented) |
| 5 | `upgrade_candidates` filtering | Omit scenarios needing a disabled component | Decided (implemented) |
| 6 | Multi-vehicle | Sum combustion mileage and spend, mileage-weighted consumption; EVs excluded | Decided (implemented) |
| 7 | Carbon reduction | Out of scope until emission-factor spec exists | Proposed |
| 8 | Mock default | `true` in `.env.example` for demos; `false` in CI live smoke | Proposed |
| 9 | MCP placement | Standalone Railway service `maxergy-mcp` | Decided |
| 10 | MCP → engine access | HTTP `POST /plan` | Decided (implemented) |
| 11 | MCP public domain | New MAXergy domain; old domain kept during transition | Proposed |
| 12 | `monthly_saving_post_payoff_eur` | Always present in v2 | Decided (implemented) |
| 15 | Headline monthly figures | 12-month averages (not the first month) to avoid seasonal distortion | Decided (implemented) |
| 13 | API path prefix | Root paths (no `/api/v1`) — matches routers and frontend client today | Decided |
| 14 | Commercial buildings in MCP | Disabled until a commercial model exists | Decided (implemented) |
