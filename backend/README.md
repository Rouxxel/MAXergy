# MAXergy Backend

FastAPI backend for the MAXergy energy forecasting and recommendation system.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Production Forecasting**: Runs the repo's energy model (`scripts/energy_model`, `compute_model`) for 6 upgrade scenarios
- **Recommendation Engine**: Shared ranking service (default: cumulative net savings, central prices) with a rationale built from forecast numbers; exposed via `/recommendation` and `/plan`
- **AI Advisor Integration**: Gemini LLM for personalized energy advice
- **Docker Support**: Multi-stage Dockerfile and docker-compose for easy deployment
- **Rate Limiting**: Built-in request rate limiting with SlowAPI
- **Logging**: Comprehensive logging system with file and console output
- **Configuration**: JSON-based configuration management via `config_loader`
- **Health Checks**: Built-in health check endpoints

## Project Structure

```
backend/
├── src/
│   ├── api_endpoints/              # API route definitions
│   │   ├── routers/
│   │   │   └── maxergy/            # MAXergy-specific routers
│   │   │       ├── assessment_router.py
│   │   │       ├── forecast_router.py
│   │   │       ├── recommendation_router.py
│   │   │       ├── plan_router.py
│   │   │       ├── assumptions_router.py
│   │   │       ├── advisor_router.py
│   │   │       ├── benchmark_router.py
│   │   │       └── visualization_router.py
│   │   └── root_endpoint.py        # Root / health-check endpoint
│   ├── core_specs/                 # Core configuration and static data
│   │   ├── configuration/
│   │   │   ├── config_file.json    # Endpoint, network, logging settings
│   │   │   └── config_loader.py    # Loads config_file.json → config_loader
│   │   └── data/
│   │       ├── general_data.json   # Static reference data
│   │       └── data_loader.py      # Loads general_data.json → data_loader
│   ├── models/                     # Pydantic models
│   │   ├── forecast_schemas.py     # Forecast and assessment schemas
│   │   └── models_example.py       # Example model patterns
│   ├── services/                   # Business logic
│   │   ├── recommendation/
│   │   │   └── recommendation_service.py # Shared ranking + rationale
│   │   ├── forecasting/
│   │   │   ├── baseline_service.py # Forecasting service (normalizer → engine → adapter, cache)
│   │   │   ├── engine.py           # Single import point for scripts/energy_model
│   │   │   ├── assumptions_service.py # Engine defaults for GET /assumptions
│   │   │   ├── input_normalizer.py # HouseholdAssessment → engine input (fuels, upgrade candidates)
│   │   │   └── model_adapter.py    # Engine output → ForecastResult
│   │   └── llm/
│   │       ├── gemini_service.py    # Gemini AI advisor service
│   │       └── __init__.py
│   └── utils/
│       ├── custom_logger.py        # Logging configuration (log_handler)
│       ├── limiter.py              # Shared SlowAPI limiter instance
│       ├── request_limiter.py      # 429 handler for rate-limit exceeded
│       └── validators.py           # Email, password, phone, token, UUID validators
├── mcp/                            # Standalone MCP service (maxergy-mcp), calls /plan and /assumptions — see mcp/README.md
├── tests/                          # Backend tests (fixtures/ holds model_input1.json)
├── logs/                           # Log files (created automatically)
├── main.py                         # Application entry point
├── requirements.txt                # Python dependencies
├── start.sh / start.bat            # Dev setup and launch scripts
├── DOCKERFILE                      # Docker build configuration
├── docker-compose.yml              # Docker compose configuration
├── .env / .env.example             # Environment variables
├── .dockerignore
├── .gitignore
├── .pylintrc
├── API_DOCUMENTATION.md            # API endpoint documentation
└── README.md
```

## Quick Start

### Option 1: Run with Python (Development)

1. **Clone and setup**:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate          # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env — set GEMINI_API_KEY if using AI advisor
   ```

3. **Run the application**:
   ```bash
   python main.py
   # or: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Access the API**:
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Option 2: Run with Docker (Production)

```bash
cd backend
docker-compose up --build
```

Or manually:

```bash
docker build -t maxergy-backend .
docker run -p 8000:8000 --env-file .env maxergy-backend
```

## Configuration

### Environment Variables (.env)

```bash
# Server
SERVER_PORT=8000
HOST=0.0.0.0
RELOAD=false
WORKERS=1

# AI Advisor
GEMINI_API_KEY=your_gemini_api_key_here

# Logging
LOG_LEVEL=info

# API metadata
API_TITLE=MAXergy API
API_VERSION=1.0.0
API_DESCRIPTION=Energy forecasting and recommendation API
```

### JSON Configuration (`config_file.json` + `config_loader`)

`config_loader.py` reads `config_file.json` at import time and exposes the result as `config_loader` (a dict). Every router should pull its prefix, tag, route, and rate-limit values from here rather than hard-coding them.

**Sections in `config_file.json`:**

| Section | Purpose |
|---|---|
| `defaults` | Shared paths and defaults |
| `logging` | Log level, directory, file name prefix |
| `email_validation` | Allowed email providers and TLDs (used by `validators.py`) |
| `network` | Uvicorn host, port, workers, reload |
| `endpoints` | Per-endpoint prefix, tag, route, and rate-limit settings |

**Endpoint config shape** (one entry per route):

```json
"example_endpoint": {
    "request_limit": 3,
    "unit_of_time_for_limit": "m",
    "endpoint_prefix": "/subsection",
    "endpoint_tag": "subsection",
    "endpoint_route": "/endpoint_name"
}
```

**Usage in a router:**

```python
from src.core_specs.configuration.config_loader import config_loader

cfg = config_loader["endpoints"]["example_endpoint"]

router = APIRouter(
    prefix=cfg["endpoint_prefix"],
    tags=[cfg["endpoint_tag"]],
)

@router.get(cfg["endpoint_route"])
@limiter.limit(f"{cfg['request_limit']}/{cfg['unit_of_time_for_limit']}")
async def my_endpoint(request: Request):
    ...
```

### Static Data (`general_data.json` + `data_loader`)

`data_loader.py` works the same way as `config_loader` but loads `src/core_specs/data/general_data.json`. Use it for reference data that is not environment-specific (e.g. supported languages, lookup tables).

```python
from src.core_specs.data.data_loader import data_loader

languages = data_loader["languages"]
```

## API Endpoints

Routers are mounted at the root of the host (no `/api/v1` prefix — decision #13 in
[`documentation/app/API_CONTRACT.md`](../documentation/app/API_CONTRACT.md), which is the
canonical contract). The MAXergy backend provides the following endpoints:

| Method | Path | Description | Status |
|---|---|---|---|
| `GET` | `/` | Health check | works |
| `GET` | `/benchmark` | Benchmark data for a typical German household | works; recommendation values hard-coded (engine-computed version planned) |
| `POST` | `/assessment` | Submit household assessment | works (in-memory store) |
| `POST` | `/forecast` | Generate energy forecast | works; production engine (`scripts/energy_model`); 422 for inputs the engine cannot model (e.g. heating fuel other than gas/oil) |
| `POST` | `/recommendation` | Ranked scenarios + rationale (`?metric=cumulative_central\|monthly_net`) | works; shared recommendation service, reuses the cached forecast |
| `POST` | `/plan` | Forecast + recommendation from one engine run | works; preferred by frontends and the MCP |
| `GET` | `/assumptions` | Engine default assumptions (tariff, solar, battery, heat pump, EV, capex, financing, supported inputs) | works; used by the MCP suggestion tools |
| `POST` | `/advisor/chat` | Chat with AI advisor | works (mock replies without `GEMINI_API_KEY`) |
| `POST` | `/visualization/forecast-chart` | Forecast chart payload | works |

### Benchmark Endpoint

The `/benchmark` endpoint returns pre-computed energy upgrade results for a typical German household. This data is displayed on the landing page to show users example outputs before they complete their own assessment.

**Response:**
```json
{
  "household": {
    "location": "Cologne (50667)",
    "occupants": 3,
    "annual_electricity_kwh": 3500,
    "heating_type": "gas",
    "heating_annual_kwh": 14000,
    "vehicle_type": "petrol",
    "annual_mileage_km": 12000,
    "roof_area_m2": 35,
    "roof_orientation": "south",
    "roof_tilt_deg": 32
  },
  "recommendation": {
    "scenario": "full_upgrade",
    "break_even_year": 8,
    "monthly_instalment_eur": 209,
    "cumulative_savings_eur": 24828,
    "description": "Solar panels + battery storage + heat pump + EV charger. Highest projected 20-year cumulative net savings under the central price scenario."
  }
}
```

**Features:**
- Caching with 1-hour TTL
- Rate limiting (25 requests per minute)
- Error handling with logging
- Fallback to hardcoded data if JSON file is unavailable

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed request/response examples.

## Services

### Forecasting Service

`src/services/forecasting/baseline_service.py` runs the production energy model
(`scripts/energy_model`, `compute_model`) in-process:

1. `input_normalizer.py` — `HouseholdAssessment` → engine input. Rejects heating fuels other
   than gas/oil (`ValueError` → HTTP 422) and computes the effective upgrade candidates: solar
   off when `roof.available` is false, EV charger off when there is no combustion vehicle.
   Multi-vehicle aggregation happens inside the engine (`flatten_mobility`).
2. `engine.py` — the only place that puts `scripts/` on `sys.path`.
3. `model_adapter.py` — engine output → `ForecastResult`: monthly figures are averages over
   the first 12 months, scenario electricity is net of feed-in revenue, long-term figures use
   the central price scenario (low/high in `long_term_band`), plus `financials`,
   `payback_month`, `assumptions_used` and `validation_warnings`. Scenarios that need a
   disabled component are omitted.
4. Results are cached in memory by an MD5 of the normalized engine input; engine warnings
   are logged.

Field definitions: [`documentation/app/API_CONTRACT.md`](../documentation/app/API_CONTRACT.md).

### Recommendation Service

`src/services/recommendation/recommendation_service.py` — `build_recommendation(forecast, metric)`
is the single ranking function (used by `/recommendation` and `/plan`):

- `cumulative_central` (default, `config_file.json` → `recommendation.default_metric`):
  cumulative net savings at the end of the horizon, central prices; tie-breaks: higher
  first-year net saving, then lower instalment.
- `monthly_net`: average monthly net saving in the first year; tie-breaks: higher cumulative
  net savings, then lower instalment.
- The rationale quotes only forecast fields (monthly net, instalment, post-payoff saving,
  cumulative central/low/high, break-even year) and explains negative savings during the loan.
- No scenarios (e.g. no usable roof) → `selected_scenario_id: null` with an explanatory rationale.

### Gemini AI Advisor Service

Located in `src/services/llm/gemini_service.py`, this service:
- Integrates with Google Gemini API
- Generates personalized energy advice
- Provides recommendation summaries
- Explains savings calculations
- Detects upsell opportunities
- Falls back to mock responses when API key is not configured

## Models (`src/models/`)

The MAXergy backend uses Pydantic models for request/response validation:

- `forecast_schemas.py`: Contains `HouseholdAssessment`, `ForecastResult`, `Recommendation`, and related schemas
- `models_example.py`: Example model patterns for reference

## Utilities (`src/utils/`)

| Module | When to use |
|---|---|
| `custom_logger.py` | `log_handler` — use everywhere instead of `print` |
| `limiter.py` | Shared `limiter` instance; decorate routes with `@limiter.limit(...)` |
| `request_limiter.py` | Registered in `main.py` as the global 429 handler |
| `validators.py` | Email, password, phone, token, UUID validators |

## Security Features

- **Rate Limiting**: Configurable per-endpoint rate limiting via `config_file.json`
- **Input Validation**: Pydantic models with strict type checking
- **API Key Security**: Gemini API key stored in environment variables, never logged
- **Non-root Docker**: Container runs as non-root user
- **Environment Variables**: Sensitive data via `.env`, never committed

## Logging

- **File Logging**: Timestamped log files in `logs/`
- **Console Logging**: Structured output for containers
- **Configurable Levels**: Set via `logging.logging_level` in `config_file.json`
- **Request Logging**: Rate-limit violations logged at warning level

## Docker Features

> **Known limitation:** the image is built from `backend/` only, so it does not contain
> `scripts/energy_model` and `POST /forecast` fails inside the container. Building from the
> repository root (for the Railway deployment) is planned.

### Multi-stage Build
- **Builder stage**: Installs dependencies
- **Production stage**: Minimal runtime image
- **Security**: Non-root user execution
- **Health checks**: Built-in container health monitoring

### Docker Compose
- **Production**: Optimized for deployment
- **Volumes**: Persistent log storage

## Development

### Hot Reload

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Or use `start.bat` / `start.sh` and choose development mode.

### Adding Dependencies

```bash
pip install new-package
pip freeze > requirements.txt
```

### Running Tests

```bash
pip install pytest httpx
pytest backend/tests backend/src/tests   # from the repo root
pytest tests                             # production energy model tests (repo root)
```

- `backend/tests/` — adapter golden tests, normalizer, recommendation service, assumptions, service
  and the `/forecast`, `/recommendation`, `/plan`, `/assumptions` endpoints (real engine).
- `backend/src/tests/` — service unit tests with the engine mocked.
- `backend/conftest.py` switches the working directory to `backend/` (the config loaders resolve
  paths from there) and provides the `assessment_dict` fixture from
  `backend/tests/fixtures/model_input1.json`.

## Deployment

1. Update environment variables for production.
2. Build: `docker build -t maxergy-backend:latest .`
3. Deploy: `docker-compose up -d`

Compatible with AWS ECS/Fargate, Google Cloud Run, Azure Container Instances, Heroku, DigitalOcean App Platform, and similar.

## API Documentation

Once running:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Requirements

- Python 3.12+
- Docker (optional)
- Docker Compose (optional)

## License

Proprietary - All rights reserved
