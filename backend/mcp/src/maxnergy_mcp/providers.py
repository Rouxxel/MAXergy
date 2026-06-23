"""External data sources: geocoding, Google Solar API, PVGIS.

PVGIS is keyless and EU-wide. Google Solar + Geocoding need GOOGLE_MAPS_API_KEY.
Each function degrades gracefully and raises a clear error the LLM can relay.
"""

from __future__ import annotations

import logging
import os
import time

import httpx

from .models import RoofGeometry, RoofSegment

log = logging.getLogger("maxnergy.google")

GOOGLE_KEY_ENV = "GOOGLE_MAPS_API_KEY"
# ~0.19 kWp per m2 of modern roof-mounted modules (≈ 1.7 m²/panel @ ~330 Wp usable).
KWP_PER_M2 = 0.19
_TIMEOUT = httpx.Timeout(20.0)

# Approx Google list price per call (USD), for a rough cost line in the logs.
_COST_USD = {"geocode": 0.005, "solar": 0.010}


def _google_key() -> str:
    key = os.environ.get(GOOGLE_KEY_ENV, "").strip()
    if not key:
        raise RuntimeError(
            f"{GOOGLE_KEY_ENV} is not set. Add a Google Cloud key with the Solar API + "
            "Geocoding API enabled, or call estimate_pv_production directly with known tilt/azimuth."
        )
    return key


def geocode(address: str) -> tuple[float, float]:
    """Address -> (lat, lon) via Google Geocoding API."""
    t0 = time.perf_counter()
    resp = httpx.get(
        "https://maps.googleapis.com/maps/api/geocode/json",
        params={"address": address, "key": _google_key()},  # key never logged
        timeout=_TIMEOUT,
    )
    dur = (time.perf_counter() - t0) * 1000
    data = resp.json() if resp.content else {}
    status = data.get("status")
    n = len(data.get("results", []))
    log.info(
        "geocode http=%s %.0fms status=%s results=%d ~$%.3f addr=%r",
        resp.status_code, dur, status, n, _COST_USD["geocode"], address[:120],
    )
    resp.raise_for_status()
    if status != "OK" or not data.get("results"):
        log.warning("geocode FAILED status=%s addr=%r", status, address[:120])
        raise RuntimeError(f"Geocoding failed for {address!r}: {status}")
    loc = data["results"][0]["geometry"]["location"]
    return float(loc["lat"]), float(loc["lng"])


def get_roof_geometry(lat: float, lon: float) -> RoofGeometry:
    """Roof planes (tilt, azimuth, area) + installable ceiling via Google Solar API."""
    t0 = time.perf_counter()
    resp = httpx.get(
        "https://solar.googleapis.com/v1/buildingInsights:findClosest",
        params={
            "location.latitude": lat,
            "location.longitude": lon,
            "requiredQuality": "LOW",
            "key": _google_key(),  # key never logged
        },
        timeout=_TIMEOUT,
    )
    dur = (time.perf_counter() - t0) * 1000
    if resp.status_code == 404:
        log.warning(
            "solar http=404 %.0fms lat=%.5f lon=%.5f COVERAGE_GAP ~$%.3f",
            dur, lat, lon, _COST_USD["solar"],
        )
        raise RuntimeError(
            "No Solar API building data at this location (coverage gap). "
            "Fall back to asking the user for roof tilt/orientation."
        )
    resp.raise_for_status()
    data = resp.json()
    sp = data.get("solarPotential", {})

    segments: list[RoofSegment] = []
    for seg in sp.get("roofSegmentStats", []):
        stats = seg.get("stats", {})
        segments.append(
            RoofSegment(
                tilt_degrees=float(seg.get("pitchDegrees", 0.0)),
                azimuth_degrees=float(seg.get("azimuthDegrees", 180.0)),
                area_m2=float(stats.get("areaMeters2", 0.0)),
                sunshine_hours_per_year=seg.get("stats", {}).get("sunshineQuantiles", [None])[-1],
            )
        )
    segments.sort(key=lambda s: s.area_m2, reverse=True)

    max_area = sp.get("maxArrayAreaMeters2")
    max_kwp = None
    # Prefer the API's own panel-based ceiling when present.
    panel_w = sp.get("panelCapacityWatts")
    max_panels = sp.get("maxArrayPanelsCount")
    if panel_w and max_panels:
        max_kwp = round(panel_w * max_panels / 1000.0, 2)
    elif max_area:
        max_kwp = round(float(max_area) * KWP_PER_M2, 2)

    # Anchor for the advisor's "how big is your existing system?" question. No API knows
    # what's actually installed, so suggest a plausible size: most rooftop arrays fill
    # ~70% of the usable roof. The advisor presents this as a guess to confirm/correct.
    suggested_kwp = round(max_kwp * 0.7, 1) if max_kwp else None

    # The Solar API returns the building NEAREST the geocoded point — for large/industrial
    # sites it often locks onto a small annex and reports a tiny roof. Flag that so the
    # advisor cross-checks against floor area instead of trusting an implausible ceiling.
    low_confidence = bool(max_kwp is not None and max_kwp < 10.0)

    log.info(
        "solar http=%s %.0fms lat=%.5f lon=%.5f segments=%d max_area=%sm² max_kwp=%s low_conf=%s ~$%.3f%s",
        resp.status_code, dur, lat, lon, len(segments),
        round(max_area) if max_area else None, max_kwp, low_confidence,
        _COST_USD["solar"],
        " FALLBACK→area-estimate" if low_confidence else "",
    )

    return RoofGeometry(
        lat=lat,
        lon=lon,
        segments=segments,
        max_array_area_m2=float(max_area) if max_area else None,
        max_array_kwp=max_kwp,
        suggested_system_kwp=suggested_kwp,
        low_confidence=low_confidence,
    )


def google_azimuth_to_pvgis_aspect(azimuth_degrees: float) -> float:
    """Google (0=N,180=S) -> PVGIS aspect (0=S, -90=E, 90=W)."""
    return azimuth_degrees - 180.0


def estimate_pv_production(
    lat: float,
    lon: float,
    kwp: float,
    tilt_degrees: float,
    azimuth_degrees: float,
    system_loss_pct: float = 14.0,
) -> dict:
    """Annual + monthly PV yield via PVGIS (keyless, EU). azimuth in Google convention."""
    if kwp <= 0:
        return {"annual_kwh": 0.0, "monthly_kwh": [0.0] * 12, "specific_yield_kwh_per_kwp": 0.0}

    aspect = google_azimuth_to_pvgis_aspect(azimuth_degrees)
    t0 = time.perf_counter()
    resp = httpx.get(
        "https://re.jrc.ec.europa.eu/api/v5_2/PVcalc",
        params={
            "lat": lat,
            "lon": lon,
            "peakpower": kwp,
            "loss": system_loss_pct,
            "angle": max(0.0, min(90.0, tilt_degrees)),
            "aspect": aspect,
            "outputformat": "json",
            "mountingplace": "building",
        },
        timeout=_TIMEOUT,
    )
    dur = (time.perf_counter() - t0) * 1000
    resp.raise_for_status()
    data = resp.json()
    monthly = [round(m["E_m"], 1) for m in data["outputs"]["monthly"]["fixed"]]
    annual = round(data["outputs"]["totals"]["fixed"]["E_y"], 1)
    log.info(
        "pvgis http=%s %.0fms kwp=%.1f tilt=%.0f az=%.0f -> annual=%.0fkWh yield=%.0f (keyless)",
        resp.status_code, dur, kwp, tilt_degrees, azimuth_degrees, annual, annual / kwp,
    )
    return {
        "annual_kwh": annual,
        "monthly_kwh": monthly,
        "specific_yield_kwh_per_kwp": round(annual / kwp, 1),
        "tilt_degrees": tilt_degrees,
        "azimuth_degrees": azimuth_degrees,
        "source": "pvgis_v5_2",
    }
