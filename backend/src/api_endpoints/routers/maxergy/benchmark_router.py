"""
#############################################################################
### Benchmark router
###
### @file benchmark_router.py
### @date 2026
#############################################################################

GET /benchmark endpoint: the average German household benchmark for the landing page,
computed by the production engine (same services as POST /plan).
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from src.utils.custom_logger import log_handler
from src.utils.limiter import endpoint_limit, limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.services.benchmark.benchmark_service import get_benchmark

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_benchmark"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_benchmark"]["endpoint_tag"]],
)


@router.get(config_loader["endpoints"]["maxergy_benchmark"]["endpoint_route"])
@SlowLimiter.limit(endpoint_limit("maxergy_benchmark"))
async def read_benchmark(request: Request) -> Dict[str, Any]:
    """
    Benchmark household data for the landing page.

    Runs documentation/data/test_profiles/average_german_household.json through the forecasting
    and recommendation services (cached for an hour). No values are hard-coded.

    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).

    Returns:
        Dict[str, Any]: household summary, recommended scenario with its monthly and long-term
        figures, scenario count, horizon, model version and forecast start month.
    """
    try:
        return await run_in_threadpool(get_benchmark)
    except Exception as e:
        log_handler.error("[benchmark_router] Benchmark computation failed: %s", str(e))
        raise HTTPException(status_code=500, detail="Failed to compute benchmark data")
