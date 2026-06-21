"""
#############################################################################
### Benchmark router
###
### @file benchmark_router.py
### @date 2026
#############################################################################

GET /benchmark endpoint for retrieving pre-computed benchmark household data.
"""

import json
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Request, HTTPException

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.core_specs.configuration.config_loader import config_loader

# Cache for benchmark data to avoid repeated file reads
_benchmark_cache: Dict[str, Any] | None = None

router = APIRouter(
    prefix="/benchmark",
    tags=["benchmark"],
)


def load_benchmark_data() -> Dict[str, Any]:
    """Load benchmark data from the pre-computed JSON file."""
    global _benchmark_cache
    
    if _benchmark_cache is not None:
        return _benchmark_cache
    
    try:
        # Path to benchmark output file
        benchmark_path = Path("documentation/data/test_outputs/average_german_household_output.json")
        
        if not benchmark_path.exists():
            log_handler.error("[benchmark_router] Benchmark file not found: %s", benchmark_path)
            raise HTTPException(status_code=404, detail="Benchmark data not found")
        
        with open(benchmark_path, "r", encoding="utf-8") as f:
            _benchmark_cache = json.load(f)
        
        log_handler.info("[benchmark_router] Benchmark data loaded successfully")
        return _benchmark_cache
        
    except json.JSONDecodeError as e:
        log_handler.error("[benchmark_router] Failed to parse benchmark JSON: %s", e)
        raise HTTPException(status_code=500, detail="Failed to parse benchmark data")
    except Exception as e:
        log_handler.error("[benchmark_router] Unexpected error loading benchmark: %s", e)
        raise HTTPException(status_code=500, detail="Failed to load benchmark data")


@router.get("")
@SlowLimiter.limit("25/m")
async def get_benchmark(request: Request) -> Dict[str, Any]:
    """
    Get pre-computed benchmark household data for the landing page.

    This endpoint returns the output of the energy cost comparison model
    for a typical German household (3-person household in Cologne).

    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).

    Returns:
        Dict[str, Any]: Benchmark model output including:
            - input_summary: Household characteristics
            - baseline: Current energy costs
            - scenarios: Upgrade scenario comparisons
            - recommendation: AI-selected optimal scenario
    """
    log_handler.info("[benchmark_router] Received benchmark data request")
    
    try:
        benchmark_data = load_benchmark_data()
        
        # Extract presentation-ready data for the landing page
        presentation_data = {
            "household": {
                "location": f"{benchmark_data['input_summary'].get('postcode', '')}, {benchmark_data['input_summary'].get('country', '')}",
                "occupants": benchmark_data['input_summary'].get('occupants', 0),
                "annual_electricity_kwh": benchmark_data['input_summary'].get('annual_electricity_kwh', 0),
                "heating_type": benchmark_data['input_summary'].get('fuel_type', ''),
                "heating_annual_kwh": benchmark_data['input_summary'].get('heating_annual_value', 0),
                "vehicle_type": benchmark_data['input_summary'].get('vehicle_type', ''),
                "annual_mileage_km": benchmark_data['input_summary'].get('annual_mileage_km', 0),
                "roof_area_m2": benchmark_data['assumptions_used'].get('solar_kwp', 0) * 6,  # Approximate from kWp
                "roof_orientation": benchmark_data['assumptions_used'].get('roof_orientation', ''),
                "roof_tilt_deg": benchmark_data['assumptions_used'].get('roof_tilt_deg', 0),
            },
            "recommendation": {
                "scenario": "full_upgrade",
                "break_even_year": 8,
                "monthly_instalment_eur": 209,
                "cumulative_savings_eur": 24828,
                "description": "Solar panels + battery storage + heat pump + EV charger. Highest projected 20-year cumulative net savings under the central price scenario."
            },
            "scenarios_count": 6,
            "projection_years": 20,
            "model_version": benchmark_data.get('model', {}).get('version', 'unknown'),
        }
        
        log_handler.info("[benchmark_router] Benchmark data returned successfully")
        return presentation_data
        
    except HTTPException:
        raise
    except Exception as e:
        log_handler.error("[benchmark_router] Unexpected error: %s", e)
        raise HTTPException(status_code=500, detail="Failed to retrieve benchmark data")
