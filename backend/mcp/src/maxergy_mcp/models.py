"""Data models for the MCP's own provider outputs (roof geometry from the Google Solar API).

Household inputs and savings outputs are NOT defined here: they come from the backend
contract (`contract.py`, generated from backend/src/models/forecast_schemas.py).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RoofSegment(BaseModel):
    """One pitched plane of the roof, from the Google Solar API."""

    tilt_degrees: float = Field(description="Pitch of the plane. For roof-mounted panels this IS the panel tilt.")
    azimuth_degrees: float = Field(description="Google convention: 0=N, 90=E, 180=S, 270=W")
    area_m2: float
    sunshine_hours_per_year: Optional[float] = None


class RoofGeometry(BaseModel):
    lat: float
    lon: float
    segments: list[RoofSegment] = []
    max_array_area_m2: Optional[float] = Field(
        default=None, description="Largest installable array area on the whole roof"
    )
    max_array_kwp: Optional[float] = Field(
        default=None, description="Largest installable system size on the roof"
    )
    suggested_system_kwp: Optional[float] = Field(
        default=None,
        description="Plausible system size (~70% of roof ceiling) to suggest to the user for "
        "confirmation. NOT a detected value — no API knows what's actually installed.",
    )
    low_confidence: bool = Field(
        default=False,
        description="True when the Solar API likely locked onto a small adjacent building "
        "(tiny roof). Cross-check against floor area via estimate_roof_capacity_from_area.",
    )
    source: str = "google_solar_api"
