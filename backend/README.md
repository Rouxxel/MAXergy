# MAXergy Backend

FastAPI backend for the MAXergy energy forecasting and recommendation system.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Baseline Forecasting Model**: Calculates energy costs for 6 upgrade scenarios
- **Recommendation Engine**: Selects optimal scenario based on monthly savings
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
│   │   │       └── advisor_router.py
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
│   │   ├── forecasting/
│   │   │   └── baseline_service.py # Baseline forecasting service
│   │   └── llm/
│   │       ├── gemini_service.py    # Gemini AI advisor service
│   │       └── __init__.py
│   └── utils/
│       ├── custom_logger.py        # Logging configuration (log_handler)
│       ├── limiter.py              # Shared SlowAPI limiter instance
│       ├── request_limiter.py      # 429 handler for rate-limit exceeded
│       └── validators.py           # Email, password, phone, token, UUID validators
├── logs/                           # Log files (created automatically)
├── main.py                         # Application entry point
├── requirements.txt                # Python dependencies
├── start.sh / start.bat            # Dev setup and launch scripts
├── DOCKERFILE                      # Docker build configuration
├── docker-compose.yml              # Docker compose configuration
├── .env / .env.example             # Environment variables template
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

The MAXergy backend provides the following endpoints:

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/maxergy/assessment` | Submit household assessment |
| `POST` | `/api/v1/maxergy/forecast` | Generate energy forecast |
| `POST` | `/api/v1/maxergy/recommendation` | Get upgrade recommendations |
| `POST` | `/api/v1/maxergy/advisor/chat` | Chat with AI advisor |

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for detailed request/response examples.

## Services

### Baseline Forecasting Service

Located in `src/services/forecasting/baseline_service.py`, this service:
- Wraps the baseline forecasting model
- Generates forecasts for 6 upgrade scenarios
- Caches results to avoid redundant computations
- Handles temporary file cleanup

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
pip install pytest
pytest src/tests/
```

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
