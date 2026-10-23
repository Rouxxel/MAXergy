"""
Location enrichment: address/postcode → coordinates, roof proposal and site PV yield.

Uses the MCP enrichment tools (Google Geocoding, Google Solar, PVGIS). The result pre-fills
`household.roof` (area, tilt, orientation) and `household.roof.specific_yield_kwh_per_kwp` of a
HouseholdAssessment. Roof and yield lookups degrade gracefully: if one fails the field is null,
its source is "unavailable" and a warning explains why; only a failed geocode is an error.
"""

from src.models.forecast_schemas import (
    EnrichmentRequest,
    EnrichmentResponse,
    EnrichmentRoof,
    EnrichmentSource,
)
from src.services.mcp.mcp_client import McpToolError, McpUnavailable, get_mcp_client

DEFAULT_TILT_DEG = 30.0
DEFAULT_AZIMUTH_DEG = 180.0
_COMPASS = ["north", "north_east", "east", "south_east", "south", "south_west", "west", "north_west"]


def orientation_from_azimuth(azimuth_deg: float) -> str:
    """Map an azimuth (0=N, 90=E, 180=S, 270=W) to the engine's eight orientation names."""
    return _COMPASS[int(((azimuth_deg % 360) + 22.5) // 45) % 8]


def enrich_location(request: EnrichmentRequest) -> EnrichmentResponse:
    """Run geocode → roof geometry → PVGIS (1 kWp).

    Raises McpUnavailable (disabled, unreachable, misconfigured) or McpToolError (geocode failed).
    """
    mcp = get_mcp_client()
    address = request.address or f"{request.postcode}, Germany"
    try:
        geo = mcp.call_tool("geocode_address", {"address": address})
    except McpToolError as e:
        # A missing Google key on the MCP is a service problem, not a bad address.
        if "GOOGLE_MAPS_API_KEY" in str(e):
            raise McpUnavailable("MCP service has no Google Maps key configured") from e
        raise
    lat, lon = geo["lat"], geo["lon"]
    warnings: list[str] = []

    roof: EnrichmentRoof | None = None
    tilt, azimuth = DEFAULT_TILT_DEG, DEFAULT_AZIMUTH_DEG
    try:
        geometry = mcp.call_tool("get_roof_geometry", {"lat": lat, "lon": lon})
        segments = geometry.get("segments") or []
        main = segments[0] if segments else None
        if main:
            tilt, azimuth = main["tilt_degrees"], main["azimuth_degrees"]
        roof = EnrichmentRoof(
            usable_area_m2=geometry.get("max_array_area_m2") or (main["area_m2"] if main else None),
            tilt_deg=tilt if main else None,
            azimuth_deg=azimuth if main else None,
            orientation=orientation_from_azimuth(azimuth) if main else None,
            max_array_kwp=geometry.get("max_array_kwp"),
            low_confidence=bool(geometry.get("low_confidence")),
        )
        if roof.low_confidence:
            warnings.append("Roof scan may have found a small adjacent building; confirm the roof size.")
    except McpToolError as e:
        warnings.append(f"Roof geometry unavailable: {e}")

    specific_yield: float | None = None
    try:
        pv = mcp.call_tool("estimate_pv_production", {
            "lat": lat, "lon": lon, "kwp": 1.0, "tilt_degrees": tilt, "azimuth_degrees": azimuth,
        })
        specific_yield = pv.get("specific_yield_kwh_per_kwp")
    except McpToolError as e:
        warnings.append(f"PV yield unavailable (the engine will use its regional table): {e}")

    return EnrichmentResponse(
        lat=lat,
        lon=lon,
        roof=roof,
        specific_yield_kwh_per_kwp=specific_yield,
        source=EnrichmentSource(
            roof="google_solar" if roof else "unavailable",
            pv_yield="pvgis" if specific_yield else "unavailable",
        ),
        warnings=warnings,
    )
