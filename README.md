# MAXergy

AI-powered home energy upgrade planner for German households.

## Overview

MAXergy helps homeowners understand the financial and environmental impact of energy efficiency upgrades like solar PV, battery storage, heat pumps, and EV charging. The application provides personalized recommendations based on household characteristics, current energy consumption, and German market conditions.

## Architecture

MAXergy consists of three main components:

- **Backend** ([`backend/`](backend/README.md)): FastAPI-based API with baseline forecasting model, recommendation engine, and AI advisor (Gemini)
- **Frontend** ([`frontend/`](frontend/README.md)): TanStack Start (React 19 + Vite 7) mobile-first web application
- **Energy Model** ([`scripts/energy_model/`](scripts/energy_model/README.md)): Production modelling package for German residential energy cost forecasting

### Data Flow

```
User Input (Household Assessment)
    ↓
Energy Model (scripts/energy_model/)
    ↓
Baseline Forecast + 6 Upgrade Scenarios
    ↓
Recommendation Engine (select_best_scenario)
    ↓
Frontend Display (Results, Comparison, AI Advisor)
```

## Quick Start

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Backend runs on `http://localhost:8000` with Swagger UI at `/docs`

### Frontend

```bash
cd frontend
bun install
cp .env.example .env
bun run dev
```

Frontend runs on `http://localhost:8080`

### Running the Energy Model

```bash
# CLI
python scripts/run_model.py --input documentation/data/model_input1.json

# Python API
from scripts.energy_model import compute_model
result = compute_model(input_dict)
```

## Project Structure

```
MAXergy/
├── backend/              # FastAPI backend service
│   ├── src/
│   │   ├── api_endpoints/    # API routers (assessment, forecast, recommendation, advisor)
│   │   ├── core_specs/       # Configuration and static data
│   │   ├── models/          # Pydantic schemas
│   │   ├── services/        # Business logic (forecasting, LLM)
│   │   └── utils/           # Logging, rate limiting, validators
│   └── main.py              # Application entry point
├── frontend/             # TanStack Start web application
│   ├── src/
│   │   ├── routes/         # File-based routing (index, results, compare, advisor)
│   │   ├── components/     # UI components (app-shell, metric-card, etc.)
│   │   ├── services/       # API client, endpoints, mocks
│   │   ├── stores/         # Zustand state management
│   │   └── types/          # TypeScript type definitions
│   └── router.tsx          # Router bootstrap
├── scripts/
│   └── energy_model/       # Production energy modelling package
│       ├── consumption.py      # BDEW H0 load profiles, heating degree days
│       ├── price_models.py      # Short-term constant, long-term scenario models
│       ├── upgrade_model.py     # PV, battery, heat pump, EV calculations
│       ├── financing.py         # Loan calculations
│       └── pipeline.py          # Main computation pipeline
├── research/             # Experimental work and backtesting (not production)
│   ├── price_forecasting/    # Price model backtesting against Destatis data
│   ├── evaluation_outputs/   # Backtest results and reports
│   └── legacy/               # Superseded CLI scripts
├── documentation/
│   ├── data/
│   │   ├── test_profiles/    # Benchmark household input
│   │   └── test_outputs/     # Pre-generated model outputs
│   └── figures/
│       └── design/           # Dashboard design specifications
└── data/                  # Static data files (BDEW profiles, climate data)
```

## Energy Model Details

The production energy model (`scripts/energy_model/`) computes:

- **Baseline forecast**: Energy costs without upgrades (short-term constant prices, long-term trend scenarios)
- **6 Upgrade scenarios**: Solar-only, PV+battery, PV+heat pump, PV+EV, PV+battery+heat pump, full upgrade
- **Financing analysis**: Monthly loan instalments, payback period, cumulative net savings

### Upgrade Scenarios

| Scenario | Technologies |
|----------|--------------|
| `solar_only` | Rooftop PV |
| `pv_battery` | PV + home battery |
| `pv_heatpump` | PV + heat pump (replaces gas/oil) |
| `pv_ev` | PV + EV charging (replaces petrol/diesel) |
| `pv_battery_heatpump` | PV + battery + heat pump |
| `full_upgrade` | PV + battery + heat pump + EV |

### Price Models

- **Short-term** (≤24 months): `ConstantShortTermPriceModel` — prices frozen at current tariff. Selected via Destatis rolling-origin backtest as most accurate for 12-month horizon.
- **Long-term** (20 years): `ScenarioPriceModel` — deterministic annual growth paths (low/central/high). Not a statistical forecast, but a policy-range assumption band.

### Modelling Approach

- **Electricity**: BDEW H0 residential load profile (temperature-dependent, seasonal variation)
- **Heating**: Degree-Day method using DWD historical heating degree days
- **PV generation**: Sized from roof area with orientation/tilt/shading corrections
- **Battery dispatch**: 35% daytime demand fraction assumption
- **Heat pump**: SCOP = 3.5 default, replaces boiler
- **EV**: Additional electricity demand from annual mileage
- **Financing**: Fixed-rate annuity loan formula

## Research Area

The [`research/`](research/README.md) directory contains experimental work, backtesting results, and legacy scripts that are **not part of the production pipeline**. Key findings:

- Backtested four price models (Constant, Deterministic Trend, ETS, SARIMA) against Destatis energy price indices (2019–2025)
- `ConstantModel` achieved lowest RMSPE across all energy carriers on 12-month rolling-origin backtest
- This informed the selection of `ConstantShortTermPriceModel` for short-term forecasts

## Frontend Architecture

The frontend is a **mobile-first PWA shell** with mocked data, designed to be easily wired to the real backend and later ported to React Native:

- **Framework**: TanStack Start v1 (React 19 + Vite 7)
- **Routing**: File-based routing in `src/routes/`
- **Styling**: Tailwind CSS v4 with MAXergy design tokens
- **UI**: shadcn/ui + Radix primitives
- **State**: Zustand stores (assessment, results, UI)
- **Data fetching**: TanStack Query + typed fetch wrapper
- **Mock support**: `VITE_USE_MOCKS` environment variable for offline development

## Backend Features

- **FastAPI Framework**: Modern, fast web framework with automatic OpenAPI documentation
- **Baseline Forecasting Service**: Wraps the energy model, generates forecasts for 6 upgrade scenarios
- **Recommendation Engine**: Selects optimal scenario based on 20-year cumulative net savings
- **AI Advisor Integration**: Gemini LLM for personalized energy advice
- **Docker Support**: Multi-stage Dockerfile and docker-compose for production deployment
- **Rate Limiting**: Per-endpoint rate limiting with SlowAPI
- **Logging**: Comprehensive logging with file and console output
- **Configuration**: JSON-based configuration via `config_loader` and `data_loader`
- **Security**: Input validation, API key security, non-root Docker execution

## Features

- **Household Assessment**: 9-step onboarding form collecting energy usage, building characteristics, and upgrade preferences
- **Forecast Generation**: Baseline model calculates costs for 6 upgrade scenarios with short-term and long-term projections
- **Recommendation Engine**: Selects optimal scenario based on 20-year cumulative net savings (primary criterion)
- **Results Display**: Interactive charts showing cost breakdowns, savings, ROI, and break-even analysis
- **Scenario Comparison**: Compare all 6 scenarios side-by-side
- **AI Advisor**: Chat with AI about energy upgrades using Gemini LLM
- **Benchmark Mode**: Landing page displays results for a typical German household before personalization

## Documentation

- [Backend README](backend/README.md) — API endpoints, configuration, deployment
- [Backend API Documentation](backend/API_DOCUMENTATION.md) — Detailed request/response examples
- [Frontend README](frontend/README.md) — Tech stack, project structure, wiring backend
- [Energy Model README](scripts/energy_model/README.md) — Modelling approach, input/output format
- [Research README](research/README.md) — Price model backtesting, experimental work
- [Design README](documentation/figures/design/README.md) — Dashboard specifications, data binding
- [Task List](TASKS.md) — Development roadmap

## Development Status

- ✅ Phase 3: Household Assessment Flow
- ✅ Phase 4: Recommendation Engine
- ✅ Phase 5: Results Display
- ✅ Phase 6: AI Advisor Integration
- ✅ Phase 7: Polish and User Experience
- ✅ Phase 8: Testing and Quality Assurance
- ✅ Phase 9: Documentation and Deployment

## License

Proprietary - All rights reserved
