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

### LLM Service

Responsibilities:

- Generate explanations
- Upsell suggestions
- Proposal generation

Provider:

- Gemini

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

PostgreSQL

Tables:

- users
- assessments
- households
- scenarios
- recommendations

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
