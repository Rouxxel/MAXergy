"""
#############################################################################
### Visualization router
###
### @file visualization_router.py
### @date 2026
#############################################################################

POST /visualization/forecast-chart endpoint for generating forecast charts.
"""

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import Response

from src.utils.custom_logger import log_handler
from src.utils.limiter import limiter as SlowLimiter
from src.models.forecast_schemas import ForecastResult
from src.services.visualization.visualization_service import get_visualization_service

router = APIRouter(
    prefix="/visualization",
    tags=["visualization"],
)


@router.post("/forecast-chart")
@SlowLimiter.limit("10/m")
async def generate_forecast_chart(
    request: Request,
    forecast: ForecastResult,
    format: str = "png"
) -> Response:
    """
    Generate forecast comparison chart.
    
    This endpoint generates a visual comparison of baseline vs scenario forecasts
    with short-term (12 months) and long-term (20 years) projections.
    
    Parameters:
        request (Request): Incoming HTTP request (required by rate limiter).
        forecast (ForecastResult): Forecast result to visualize.
        format (str): Output format (png or svg). Default: png.
    
    Returns:
        Response: Chart image with appropriate content type.
    
    Raises:
        HTTPException: If chart generation fails or format is invalid.
    """
    try:
        if format not in ["png", "svg"]:
            raise HTTPException(status_code=400, detail="Format must be 'png' or 'svg'")
        
        visualization_service = get_visualization_service()
        
        log_handler.info(
            "Generating %s forecast chart with %d scenarios",
            format,
            len(forecast.scenarios),
        )
        
        chart_data = visualization_service.generate_forecast_chart(forecast, format=format)
        
        content_type = "image/png" if format == "png" else "image/svg+xml"
        
        return Response(
            content=chart_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=forecast_comparison.{format}"
            }
        )
        
    except Exception as e:
        log_handler.error("Chart generation failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Chart generation failed: {str(e)}")
