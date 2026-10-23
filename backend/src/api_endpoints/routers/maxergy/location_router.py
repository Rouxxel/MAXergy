"""
#############################################################################
### Location router
###
### @file location_router.py
### @date 2026
#############################################################################

POST /location/enrich endpoint: coordinates, roof proposal and site PV yield via the MCP.
"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from src.utils.custom_logger import log_handler
from src.utils.limiter import endpoint_limit, limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader
from src.models.forecast_schemas import EnrichmentRequest
from src.services.mcp.enrichment_service import enrich_location
from src.services.mcp.mcp_client import McpToolError, McpUnavailable
from src.utils.timeout import timeout

router = APIRouter(
    prefix=config_loader["endpoints"]["maxergy_location_enrich"]["endpoint_prefix"],
    tags=[config_loader["endpoints"]["maxergy_location_enrich"]["endpoint_tag"]],
)


@router.post(config_loader["endpoints"]["maxergy_location_enrich"]["endpoint_route"])
@SlowLimiter.limit(endpoint_limit("maxergy_location_enrich"))
@timeout(seconds=30)
async def enrich(request: Request, body: EnrichmentRequest) -> Response:
    """
    Look up coordinates, a roof proposal and the site PV yield for an address or postcode.

    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        body (EnrichmentRequest): Postcode and/or address (Germany).

    Returns:
        Response: EnrichmentResponse used to pre-fill the assessment.

    Raises:
        HTTPException: 503 when the MCP service is disabled or unreachable, 422 when the
        location cannot be geocoded.
    """
    try:
        result = await run_in_threadpool(enrich_location, body)
    except McpUnavailable as e:
        log_handler.warning("[location_router] Enrichment unavailable: %s", str(e))
        raise HTTPException(status_code=503, detail=f"Location enrichment unavailable: {e}")
    except McpToolError as e:
        log_handler.info("[location_router] Location not found: %s", str(e))
        raise HTTPException(status_code=422, detail=f"Location could not be resolved: {e}")

    return JSONResponse(content=result.model_dump(mode="json"), headers={"Cache-Control": "no-store"})
