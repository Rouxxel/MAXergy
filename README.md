# MAXergy

AI-powered home energy upgrade planner for German households.

## Overview

MAXergy helps homeowners understand the financial and environmental impact of energy efficiency upgrades like solar PV, battery storage, heat pumps, and EV charging. The application provides personalized recommendations based on household characteristics, current energy consumption, and German market conditions.

## Architecture

- **Backend**: FastAPI with baseline forecasting model, recommendation engine, and AI advisor (Gemini)
- **Frontend**: TanStack Start (React + Vite) with mobile-first UI
- **Data Flow**: Onboarding → Forecast → Results → Comparison → AI Advisor

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

Backend runs on `http://localhost:8000`

### Frontend

```bash
cd frontend
bun install
cp .env.example .env
bun run dev
```

Frontend runs on `http://localhost:8080`

## Features

- **Household Assessment**: 9-step onboarding form collecting energy usage, building characteristics, and upgrade preferences
- **Forecast Generation**: Baseline model calculates costs for 6 upgrade scenarios
- **Recommendation Engine**: Selects optimal scenario based on monthly savings
- **Results Display**: Interactive charts showing cost breakdowns, savings, and ROI
- **Scenario Comparison**: Compare all 6 scenarios side-by-side
- **AI Advisor**: Chat with AI about energy upgrades using Gemini

## Documentation

- [Backend API Documentation](backend/API_DOCUMENTATION.md)
- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Task List](TASKS.md)

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
