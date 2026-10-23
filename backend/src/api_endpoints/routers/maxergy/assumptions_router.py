"""
#############################################################################
### Assumptions router
###
### @file assumptions_router.py
### @date 2026
#############################################################################

GET /assumptions endpoint: the production engine's default assumptions.
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.services.forecasting.assumptions_service import get_assumptions

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_assumptions"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_assumptions"]["endpoint_tag"]],
)


@router.get(config_loader["endpoints"]["maxergy_assumptions"]["endpoint_route"])
@SlowLimiter.limit(
    f"{config_loader['endpoints']['maxergy_assumptions']['request_limit']}/"
    f"{config_loader['endpoints']['maxergy_assumptions']['unit_of_time_for_limit']}"
)
async def read_assumptions(request: Request) -> Response:
    """
    Return the engine's default assumptions (tariff, solar, battery, heat pump, EV, capex,
    financing, price growth, supported inputs).

    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).

    Returns:
        Response: Assumptions JSON (cacheable for one hour).
    """
    return JSONResponse(content=get_assumptions(), headers={"Cache-Control": "public, max-age=3600"})
