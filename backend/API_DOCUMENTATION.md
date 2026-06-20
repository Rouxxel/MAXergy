# MAXergy API Documentation

This document describes the API endpoints for the MAXergy energy forecasting and recommendation system.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. Rate limiting is applied to prevent abuse.

## Endpoints

### POST /api/v1/maxergy/assessment

Submit a household assessment for processing.

**Request Body:**
```json
{
  "location": {
    "postcode": "10115",
    "country": "Germany"
  },
  "household": {
    "occupants": {
      "count": 2
    },
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
      "shading_factor": 0.1
    }
  },
  "heating": {
    "fuel_type": "gas",
    "annual_consumption": 15000,
    "annual_spend_eur": 1800,
    "building": {
      "floor_area_m2": 120,
      "insulation_class": "moderate"
    }
  },
  "mobility": {
    "vehicle_type": "none",
    "annual_mileage_km": null,
    "fuel_consumption_l_per_100km": null,
    "annual_fuel_spend_eur": null
  },
  "upgrade_candidates": {
    "solar_pv": true,
    "battery": true,
    "heat_pump": false,
    "ev_charger": false,
    "solar_pv_kwp": 5,
    "battery_kwh": 7.5,
    "heat_pump_kw": null
  },
  "financing": {
    "loan_term_years": 10,
    "loan_rate_pct": 4.5,
    "known_subsidy_eur": 3000
  },
  "forecast_horizon": {
    "short_term_months": 12,
    "long_term_years": 20
  }
}
```

**Response:**
```json
{
  "id": "uuid",
  "status": "processing"
}
```

### POST /api/v1/maxergy/forecast

Generate a forecast based on household assessment.

**Request Body:** Same as assessment endpoint.

**Response:**
```json
{
  "baseline": {
    "monthly_cost_eur": {
      "electricity": 102.92,
      "gas_oil": 150.0,
      "fuel": 0.0,
      "total": 252.92
    },
    "short_term_forecast": [
      {
        "month": 1,
        "year": 2024,
        "cost_eur": 252.92
      }
    ],
    "long_term_forecast": [
      {
        "month": 1,
        "year": 2024,
        "cost_eur": 252.92
      }
    ]
  },
  "scenarios": [
    {
      "id": "solar_only",
      "components": {
        "solar_pv": true,
        "battery": false,
        "heat_pump": false,
        "ev_charger": false
      },
      "sizing": {
        "solar_pv_kwp": 5,
        "battery_kwh": null,
        "heat_pump_kw": null
      },
      "monthly_cost_eur": {
        "electricity": 50.0,
        "gas_oil": 150.0,
        "fuel": 0.0,
        "total": 200.0
      },
      "financing_installment_eur": 45.0,
      "monthly_saving_eur": 52.92,
      "monthly_saving_post_payoff_eur": 97.92,
      "self_consumption_ratio": 0.35,
      "payback_month": 84,
      "short_term_forecast": [],
      "long_term_forecast": []
    }
  ]
}
```

### POST /api/v1/maxergy/recommendation

Generate upgrade recommendations based on forecast.

**Request Body:** Same as assessment endpoint.

**Response:**
```json
{
  "selected_scenario": {
    "id": "pv_battery",
    "components": {
      "solar_pv": true,
      "battery": true,
      "heat_pump": false,
      "ev_charger": false
    },
    "sizing": {
      "solar_pv_kwp": 5,
      "battery_kwh": 7.5,
      "heat_pump_kw": null
    },
    "monthly_cost_eur": {
      "electricity": 30.0,
      "gas_oil": 150.0,
      "fuel": 0.0,
      "total": 180.0
    },
    "financing_installment_eur": 65.0,
    "monthly_saving_eur": 72.92,
    "monthly_saving_post_payoff_eur": 137.92,
    "self_consumption_ratio": 0.65,
    "payback_month": 96
  },
  "ranked_scenarios": [],
  "reasoning": "This scenario offers the best balance of monthly savings and self-consumption ratio."
}
```

### POST /api/v1/maxergy/advisor/chat

Chat with the AI advisor about energy upgrades.

**Request Body:**
```json
{
  "user_message": "Why is solar PV recommended?",
  "forecast_result": null,
  "assessment_id": null
}
```

**Response:**
```json
{
  "advisor_message": "Solar PV is recommended because it provides the highest return on investment for your household profile...",
  "context_used": ["user_question"],
  "suggestions": [
    "Check your roof orientation and shading",
    "Consider adding battery storage",
    "Review available subsidies"
  ]
}
```

## Rate Limiting

All endpoints are rate-limited to prevent abuse:
- Assessment: 10 requests per minute
- Forecast: 5 requests per minute
- Recommendation: 5 requests per minute
- Advisor: 20 requests per minute

## Error Responses

All endpoints return standard HTTP error codes:
- `400 Bad Request`: Invalid input data
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Example Files

- `backend/data/model_input_1.json`: Example assessment input
- `backend/data/model_output_1.json`: Example forecast output
