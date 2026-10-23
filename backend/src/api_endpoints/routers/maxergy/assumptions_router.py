"""
#############################################################################
### Assumptions router
###
### @file assumptions_router.py
### @date 2026
#############################################################################

GET /assumptions endpoint: the production engine's default assumptions.
"""

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse

from src.utils.limiter import endpoint_limit, limiter as SlowLimiter
from src.utils.service_auth import verify_service_token
from src.core_specs.configuration.config_loader import config_loader
from src.services.forecasting.assumptions_service import get_assumptions

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_assumptions"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_assumptions"]["endpoint_tag"]],
    dependencies=[Depends(verify_service_token)],
)


@router.get(config_loader["endpoints"]["maxergy_assumptions"]["endpoint_route"])
@SlowLimiter.limit(endpoint_limit("maxergy_assumptions"))
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
