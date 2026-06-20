# ARCHITECTURE.md

# System Architecture

## High-Level Overview

```text
                React Native App
                        |
                    HTTPS
                        |
                    FastAPI
                        |
        +---------------+---------------+
        |               |               |
        |               |               |
 Scenario Engine   Recommendation   Gemini Advisor
                      Engine
        |               |
        +-------+-------+
                |
          Forecast Models
```

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

## API Endpoints

- POST /assessment
- POST /forecast
- POST /recommendation
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
