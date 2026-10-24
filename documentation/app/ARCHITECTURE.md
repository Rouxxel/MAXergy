# ARCHITECTURE.md

# System Architecture

## High-Level Overview

```text
   Web app (TanStack) / Mobile (Expo)          LLM clients (claude.ai, Claude Code)
                  |                                        |
                HTTPS                                    HTTPS (OAuth / bearer)
                  |                                        |
        FastAPI backend (maxergy-api)  <--- POST /plan ---  MCP service (maxergy-mcp)
                  |                    <- GET /assumptions   |  Google Geocoding / Solar,
                  |  --- /location/enrich: geocode, roof, PVGIS --->  |
     +------------+-------------+                            |  PVGIS, onboarding script
     |            |             |
 Forecasting  Recommendation  Gemini Advisor
  Service       Service
     |            |
     +-----+------+
           |
  Production energy model (scripts/energy_model, compute_model)
```

The MCP service is a separate deployable that supports the app: it never computes savings,
it calls the backend. The backend calls the MCP's enrichment tools (geocode, roof, PVGIS) for
`POST /location/enrich` (assessment pre-fill). Both run on Railway in one project and talk over
private networking with service tokens (`documentation/app/DEPLOYMENT.md`).

## Frontend

### Stack

- React Native
- Expo
- TypeScript
- NativeWind
- Zustand
- TanStack Query

### Screens

- Onboarding
- Loading
- Results
- Scenario Comparison
- AI Advisor Chat

## Backend

### Modules

```text
app/
├── api/
├── services/
├── forecasting/
├── recommendation/
├── llm/
├── schemas/
├── models/
└── core/
```

## Core Services

### Forecast Service

Responsibilities:

- Energy modeling
- Solar generation estimation
- Battery optimization
- Heat pump savings
- EV charging savings

### Recommendation Service

Responsibilities:

- Compare scenarios
- Calculate monthly savings
- Rank configurations

### LLM Service (AI advisor, `backend/src/services/llm/`)

Responsibilities:

- Explain the user's plan, grounded only in the plan's numbers (same three-number wording as the
  app and the MCP)
- Chat onboarding when no plan exists: shared onboarding script from the MCP prompt
  `maxergy_advisor`, MCP lookup tools, and the in-process `run_plan` tool (forecasting +
  recommendation services) — the result equals `POST /plan` for the collected assessment

Provider:

- Gemini (`google-genai`, function calling); 503 when not configured in production

### MCP Service (`backend/mcp`)

Responsibilities:

- Onboarding script for LLM clients (single source: `instructions.py`)
- Roof geometry (Google Solar), geocoding, site PV yield (PVGIS)
- Savings tools (`energy_savings_overview`, `compare_scenarios`, `project_savings`,
  `next_best_upgrade`) that return views of the backend's `POST /plan` response
- Tool input schema generated from the backend Pydantic models (`contract.py`)

## API Endpoints

Full contract: `documentation/app/API_CONTRACT.md`.

- POST /assessment
- POST /forecast
- POST /recommendation
- POST /plan
- GET /assumptions
- POST /location/enrich
- GET /benchmark
- POST /advisor/chat

## Database

PostgreSQL on Railway (`maxergy-db`, attached to `maxergy-api` via `DATABASE_URL`); SQLite file
locally when `DATABASE_URL` is unset. SQLAlchemy Core + Alembic migrations (`backend/migrations`),
applied when the API starts.

Tables:

- `assessments` — id, created_at, JSON payload (the `HouseholdAssessment`); used by
  `POST /plan?assessment_id=` and as advisor context

Not stored (yet): users, plans/forecasts (recomputed from the assessment; the forecast cache is in
memory), MCP OAuth clients (file on the `maxergy-mcp-oauth` volume).

## Forecast Pipeline

1. Receive household profile
2. Generate candidate scenarios
3. Run forecast models
4. Calculate costs
5. Calculate financing
6. Compute savings
7. Rank scenarios
8. Generate explanation
9. Return response

## Scalability

- Stateless FastAPI services
- Horizontal scaling
- PostgreSQL
- Redis cache (optional)
- Gemini API integration
