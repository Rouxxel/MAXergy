# MAXergy API Documentation

This document describes the API endpoints for the MAXergy energy forecasting and recommendation system.

## Base URL

```
http://localhost:8000
```

Routes are mounted at the root (no `/api/v1` prefix). The canonical contract, including the
target v2 shapes and endpoint status, is
[`documentation/app/API_CONTRACT.md`](../documentation/app/API_CONTRACT.md).

## Authentication

Public clients (web, mobile) need no credentials. Internal services (the MAXergy MCP) send
`Authorization: Bearer $MAXERGY_SERVICE_TOKEN` on `/plan`, `/forecast`, `/recommendation` and
`/assumptions`: a valid token uses the separate service rate limit, a wrong token returns 401.

## Endpoints

All request/response shapes are defined in
[`documentation/app/API_CONTRACT.md`](../documentation/app/API_CONTRACT.md); the examples below
are trimmed.

### POST /assessment

Submit a household assessment (stored in memory; returns an id).

**Request Body** (`HouseholdAssessment`, see `documentation/data/model_input1.json`):
```json
{
  "location": { "postcode": "10115", "country": "DE" },
  "household": {
    "occupants": 2,
    "electricity": {
      "annual_kwh": 3500,
      "current_tariff_type": "fixed",
      "arbeitspreis_eur_per_kwh": 0.35,
      "grundpreis_eur_per_month": 10.0,
      "contract_end_date": null
    },
    "roof": {
      "available": true,
      "usable_area_m2": 50,
      "orientation": "south",
      "tilt_deg": 35,
      "shading_factor": 0.1,
      "specific_yield_kwh_per_kwp": null
    }
  },
  "heating": {
    "fuel_type": "gas",
    "annual_consumption": 15000,
    "annual_spend_eur": 1800,
    "building": { "floor_area_m2": 120, "insulation_class": "average" }
  },
  "mobility": {
    "vehicle_count": 1,
    "vehicles": [
      { "vehicle_type": "petrol", "annual_mileage_km": 12000, "fuel_consumption_l_per_100km": 6.5, "annual_fuel_spend_eur": 1100 }
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

**Response:**
```json
{
  "assessment_id": "uuid",
  "status": "submitted",
  "message": "Assessment submitted successfully. Use the assessment_id to request forecasts."
}
```

### POST /forecast

Run the production energy model (`scripts/energy_model`) for an assessment.

**Request Body:** `HouseholdAssessment` (as above).

**Response** (`ForecastResult`, trimmed; full example `documentation/data/model_output_v2.json`):
```json
{
  "model": { "name": "energy_cost_comparison", "version": "4.0", "engine": "energy_model" },
  "assumptions_used": { "solar_kwp": 6.667, "pv_yield_source": "regional_table", "...": "..." },
  "validation_warnings": ["battery_kwh not specified; using default 10.0 kWh"],
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
      "monthly_cost_eur": { "electricity": 157.81, "heating": 0.0, "mobility": 0.0, "financing_installment": 218.28, "total": 376.09 },
      "monthly_saving_eur": -39.18,
      "monthly_saving_post_payoff_eur": 179.1,
      "self_consumption_ratio": 0.744,
      "payback_month": 138,
      "financials": { "gross_investment_eur": 28533.33, "cumulative_net_savings_central_eur": 21959.78, "break_even_year": 12, "...": "..." },
      "short_term_forecast": [ "..." ],
      "long_term_forecast": [ "..." ],
      "long_term_band": { "low": [ "..." ], "high": [ "..." ] }
    }
  ]
}
```

Monthly figures are 12-month averages; `monthly_saving_eur` is net of the loan instalment.

### POST /recommendation

Rank the forecast's scenarios and explain the best one.

**Request Body:** `HouseholdAssessment`. **Query:** `metric` = `cumulative_central` (default,
from `config_file.json` → `recommendation.default_metric`) or `monthly_net`.

**Response** (`Recommendation`):
```json
{
  "selected_scenario_id": "full_upgrade",
  "selected_scenario": { "...": "Scenario" },
  "ranked_scenarios": [
    { "id": "full_upgrade", "score_eur": 21959.78, "metric": "cumulative_central" },
    { "id": "pv_ev", "score_eur": 21697.42, "metric": "cumulative_central" }
  ],
  "metric_used": "cumulative_central",
  "rationale": "Solar panels, battery storage, a heat pump and an EV charger (full_upgrade) ranks best by long-term net savings. During the 15-year loan it costs about €39/month more than today (loan instalment €218/month). Once the loan is repaid it saves about €179/month at today's prices. Over 20 years the cumulative net saving is about €21,960 ..."
}
```

When no scenario is available (e.g. `roof.available` is false), `selected_scenario_id` and
`selected_scenario` are `null`, `ranked_scenarios` is empty and the rationale says so.

### POST /plan

Forecast and recommendation from **one** engine run (preferred by the frontends and the MCP).

**Request Body / Query:** as `/recommendation`.

**Response** (`PlanResponse`):
```json
{ "forecast": { "...": "ForecastResult" }, "recommendation": { "...": "Recommendation" } }
```

### GET /assumptions

The production engine's default assumptions (tariff, consumption, solar incl. regional yields and
feed-in tiers, battery, heat pump, EV, investment costs, financing, long-term price growth, and
the supported inputs). Cacheable for one hour; used by the MCP suggestion tools. Shape:
`documentation/app/API_CONTRACT.md` §10.

```json
{ "tariff": { "arbeitspreis_eur_per_kwh": 0.32, "grundpreis_eur_per_month": 12.5, "...": "..." }, "solar": { "m2_per_kwp": 6.0, "...": "..." }, "supported": { "heating_fuels": ["gas", "oil"], "...": "..." } }
```

### GET /benchmark

The average German household (`documentation/data/test_profiles/average_german_household.json`)
run through the same forecasting and recommendation services as `POST /plan`, cached for an hour.
Returns the household summary, the recommended plan with year-1 monthly net (incl. instalment),
after-payoff saving, cumulative net savings (central/low/high), break-even year, rationale, a
per-year cumulative series, the model version and `forecast_start`. Shape:
`documentation/app/API_CONTRACT.md` §8.

### POST /location/enrich

Coordinates, a roof proposal and the site PV yield for a German postcode or address, looked up
through the MCP service (Google Geocoding, Google Solar, PVGIS). Used to pre-fill
`household.roof`. 503 when the MCP is disabled or unreachable; 422 when the location cannot be
geocoded. Shape: `documentation/app/API_CONTRACT.md` §9.

```bash
curl -X POST http://localhost:8000/location/enrich -H "Content-Type: application/json" \
  -d '{"postcode": "50667"}'
```

```json
{ "lat": 50.94, "lon": 6.96, "roof": { "usable_area_m2": 38.0, "tilt_deg": 35.0, "azimuth_deg": 170.0, "orientation": "south", "max_array_kwp": 7.2, "low_confidence": false }, "specific_yield_kwh_per_kwp": 1012.0, "source": { "roof": "google_solar", "pv_yield": "pvgis" }, "warnings": [] }
```

### POST /advisor/chat

Chat with the AI advisor about energy upgrades.

**Request Body:**
```json
{
  "user_message": "Why this bundle?",
  "plan": { "forecast": { "...": "ForecastResult" }, "recommendation": { "...": "Recommendation" } },
  "assessment_id": null,
  "conversation_history": []
}
```

**Response:**
```json
{
  "advisor_message": "The full upgrade ranks best by long-term net savings. During financing: −€39 per month …",
  "context_used": ["user_question", "plan"],
  "suggestions": [
    "Check your roof orientation and shading",
    "Consider adding battery storage",
    "Review available subsidies"
  ]
}
```

## Rate Limiting

Per-endpoint limits from `src/core_specs/configuration/config_file.json`:
- Assessment: 10 requests per minute
- Forecast: 5 requests per minute
- Recommendation: 5 requests per minute
- Plan: 5 requests per minute
- Assumptions: 30 requests per minute
- Location enrich: 10 requests per minute
- Advisor: 10 requests per minute
- Benchmark: 25 requests per minute

Limits apply per client IP; requests with a valid service token share a separate limit of 300
per minute (`service_request_limit`). Behind a proxy (Railway) set `FORWARDED_ALLOW_IPS=*`.

## Error Responses

- `422 Unprocessable Entity`: schema validation failure, or a valid assessment the engine cannot
  model (e.g. heating fuel other than gas/oil) with the reason in `detail`
- `429 Too Many Requests`: rate limit exceeded
- `500 Internal Server Error`: engine or server error

## Example Files

- `documentation/data/model_input1.json`: Example assessment input
- `documentation/data/model_output_v2.json`: Example forecast output (production engine)
