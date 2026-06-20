"""
Visualization service module.

This service wraps the visualization script from scripts/visualize_forecast.py
and provides a clean interface for generating forecast comparison charts.
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import Optional, Literal
from io import BytesIO

# Add scripts directory to path for importing the visualization script
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts"))

from src.utils.custom_logger import log_handler
from src.models.forecast_schemas import ForecastResult


class VisualizationService:
    """Service for generating forecast visualization charts."""
    
    def __init__(self):
        """Initialize the visualization service."""
        self._cache: dict[str, bytes] = {}
    
    def generate_forecast_chart(
        self,
        forecast: ForecastResult,
        format: Literal["png", "svg"] = "png",
        use_cache: bool = True,
    ) -> bytes:
        """
        Generate forecast comparison chart.
        
        Parameters:
            forecast (ForecastResult): Forecast result to visualize.
            format (str): Output format (png or svg).
            use_cache (bool): Whether to use cached results if available.
        
        Returns:
            bytes: Chart image data.
        
        Raises:
            Exception: If chart generation fails.
        """
        # Create cache key from forecast
        cache_key = self._create_cache_key(forecast, format)
        
        if use_cache and cache_key in self._cache:
            log_handler.info("Returning cached chart for key: %s", cache_key[:16])
            return self._cache[cache_key]
        
        try:
            # Import the visualization script
            from visualize_forecast import main as visualize_main
            import matplotlib.pyplot as plt
            
            log_handler.info("Generating %s forecast chart", format)
            
            # Create temporary files for forecast data
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as forecast_file:
                forecast_path = Path(forecast_file.name)
                json.dump(forecast.model_dump(), forecast_file, indent=2)
            
            # Create temporary output file
            with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{format}', delete=False) as output_file:
                output_path = Path(output_file.name)
            
            # Temporarily modify the visualization script to use our paths
            original_output = None
            try:
                # Monkey-patch the output path in the visualization script
                import visualize_forecast
                original_output = visualize_forecast.IMAGE_OUT
                visualize_forecast.IMAGE_OUT = output_path
                visualize_forecast.OUTPUT_JSON = forecast_path
                
                # Generate the chart
                visualize_main()
                
                # Read the generated image
                with output_path.open('rb') as f:
                    chart_data = f.read()
                
                # Cache the result
                if use_cache:
                    self._cache[cache_key] = chart_data
                
                log_handler.info("Chart generated successfully (%d bytes)", len(chart_data))
                
                return chart_data
                
            finally:
                # Restore original output path
                if original_output:
                    visualize_forecast.IMAGE_OUT = original_output
                
                # Clean up temporary files
                forecast_path.unlink()
                output_path.unlink()
                
        except Exception as e:
            log_handler.error("Chart generation failed: %s", str(e))
            raise
    
    def _create_cache_key(self, forecast: ForecastResult, format: str) -> str:
        """Create a cache key from forecast data."""
        import hashlib
        import json
        
        # Create a simplified representation for caching
        cache_data = {
            "format": format,
            "baseline_total": forecast.baseline.monthly_cost_eur.total,
            "scenario_count": len(forecast.scenarios),
            "scenario_ids": [s.id for s in forecast.scenarios],
        }
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.md5(cache_str.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the chart cache."""
        self._cache.clear()
        log_handler.info("Chart cache cleared")


# Singleton instance
_visualization_service = VisualizationService()


def get_visualization_service() -> VisualizationService:
    """Get the singleton visualization service instance."""
    return _visualization_service
