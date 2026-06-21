"""
#############################################################################
### Main backend file
###
### @file main.py
### @author Sebastian Russo
### @date 2025
#############################################################################

This module initializes the FastAPI backend locally for development.
It sets up routers, custom logger, rate limiter, and loads environment variables.
"""

#Native imports
import os
from contextlib import asynccontextmanager

#Third-party imports
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv
import json
load_dotenv()

#Other files imports
from src.utils.request_limiter import rate_limit_handler
from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter

#Json files
from src.core_specs.configuration.config_loader import config_loader
from src.core_specs.data.data_loader import data_loader

#Endpoints imports
from src.api_endpoints.root_endpoint import router as root_router
from src.api_endpoints.routers.maxergy.assessment_router import router as assessment_router
from src.api_endpoints.routers.maxergy.forecast_router import router as forecast_router
from src.api_endpoints.routers.maxergy.recommendation_router import router as recommendation_router
from src.api_endpoints.routers.maxergy.advisor_router import router as advisor_router
from src.api_endpoints.routers.maxergy.visualization_router import router as visualization_router
from src.api_endpoints.routers.maxergy.benchmark_router import router as benchmark_router

"""API APP-----------------------------------------------------------"""
#Lifespan event manager (startup and shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    port = config_loader["network"]["server_port"]
    log_handler.info(f"MAXnergy server starting on port {port}")
    yield
    log_handler.info("MAXnergy server shutting down")

#Create FastAPI app
app = FastAPI(
    lifespan=lifespan, 
    title=os.getenv("API_TITLE", "MAXnergy"),
    version=os.getenv("API_VERSION", "1.0.0"),
    description=os.getenv("API_DESCRIPTION", "A for building MAXnergys with FastAPI")
)

"""VARIOUS-----------------------------------------------------------"""
#Setup rate limiter
app.state.limiter = limiter

#Add global exception handler for rate limits
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

#Add global exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log_handler.error(
        "Validation error on %s %s: %s",
        request.method,
        request.url,
        json.dumps(exc.errors(), indent=2)
    )
    log_handler.error("Request body: %s", exc.body)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        }
    )

#Setup CORS for web app and future React Native app
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",  # TanStack Start dev server
        "http://127.0.0.1:8080",
        "http://localhost:3000",  # Alternative dev port
        "http://127.0.0.1:3000",
        # Add production frontend URLs when deployed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

"""Routers-----------------------------------------------------------"""
#Root
app.include_router(root_router)

#MAXergy routers
app.include_router(assessment_router)
app.include_router(forecast_router)
app.include_router(recommendation_router)
app.include_router(advisor_router)
app.include_router(visualization_router)
app.include_router(benchmark_router)

"""Start server-----------------------------------------------------------"""
if __name__ == "__main__":
    port = config_loader["network"]["server_port"]
    
    uvicorn.run(
        config_loader["network"]["uvicorn_app_reference"],
        host=config_loader["network"]["host"],
        port=config_loader["network"]["server_port"],
        reload=config_loader["network"]["reload"],
        workers=config_loader["network"]["workers"],
        proxy_headers=config_loader["network"]["proxy_headers"]
    )
    
    log_handler.info(f"Loaded configuration: \n {config_loader}")
    log_handler.info(f"Loaded data: \n {data_loader}")
    #available at: http://127.0.0.1:8000/docs
