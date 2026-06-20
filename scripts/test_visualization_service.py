"""
Unit tests for the visualization service.

Tests the visualization service using example forecast data.
"""

import sys
import json
import os
from pathlib import Path

# Change to backend directory to ensure config files are found
backend_dir = Path(__file__).parent.parent / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from src.services.visualization.visualization_service import VisualizationService
from src.models.forecast_schemas import ForecastResult


def test_visualization_service():
    """Test the visualization service with example forecast data."""
    output_path = Path(__file__).parent.parent / "documentation" / "data" / "model_output_1.json"
    
    with output_path.open() as f:
        output_data = json.load(f)
    
    # Create forecast
    forecast = ForecastResult(**output_data)
    
    # Create service
    service = VisualizationService()
    
    # Generate PNG chart
    chart_data = service.generate_forecast_chart(forecast, format="png", use_cache=False)
    
    # Validate results
    assert chart_data is not None, "Chart data should not be None"
    assert len(chart_data) > 0, "Chart data should not be empty"
    assert chart_data[:8] == b'\x89PNG\r\n\x1a\n', "Should be a valid PNG file"
    
    print("✓ Visualization service test passed (PNG)")
    print(f"  Chart size: {len(chart_data)} bytes")
    return True


def test_svg_format():
    """Test SVG format generation."""
    output_path = Path(__file__).parent.parent / "documentation" / "data" / "model_output_1.json"
    
    with output_path.open() as f:
        output_data = json.load(f)
    
    forecast = ForecastResult(**output_data)
    service = VisualizationService()
    
    # Generate SVG chart
    chart_data = service.generate_forecast_chart(forecast, format="svg", use_cache=False)
    
    # Validate results
    assert chart_data is not None, "Chart data should not be None"
    assert len(chart_data) > 0, "Chart data should not be empty"
    assert b'<svg' in chart_data, "Should contain SVG tag"
    
    print("✓ SVG format test passed")
    print(f"  Chart size: {len(chart_data)} bytes")
    return True


def test_visualization_cache():
    """Test the caching functionality of the visualization service."""
    output_path = Path(__file__).parent.parent / "documentation" / "data" / "model_output_1.json"
    
    with output_path.open() as f:
        output_data = json.load(f)
    
    forecast = ForecastResult(**output_data)
    service = VisualizationService()
    
    # First call (no cache)
    chart1 = service.generate_forecast_chart(forecast, format="png", use_cache=True)
    
    # Second call (should use cache)
    chart2 = service.generate_forecast_chart(forecast, format="png", use_cache=True)
    
    # Third call (no cache)
    chart3 = service.generate_forecast_chart(forecast, format="png", use_cache=False)
    
    # Verify charts are identical
    assert chart1 == chart2, "Cached chart should be identical"
    assert chart1 == chart3, "Uncached chart should be identical for same input"
    
    print("✓ Visualization cache test passed")
    return True


def test_cache_key_generation():
    """Test that different forecasts generate different cache keys."""
    output_path = Path(__file__).parent.parent / "documentation" / "data" / "model_output_1.json"
    
    with output_path.open() as f:
        output_data = json.load(f)
    
    forecast1 = ForecastResult(**output_data)
    
    # Modify forecast
    output_data["baseline"]["monthly_cost_eur"]["total"] = 500.0
    forecast2 = ForecastResult(**output_data)
    
    service = VisualizationService()
    
    key1 = service._create_cache_key(forecast1, "png")
    key2 = service._create_cache_key(forecast2, "png")
    
    assert key1 != key2, "Different forecasts should have different cache keys"
    
    # Same forecast, different format
    key3 = service._create_cache_key(forecast1, "svg")
    assert key1 != key3, "Different formats should have different cache keys"
    
    print("✓ Cache key generation test passed")
    return True


if __name__ == "__main__":
    print("Running visualization service unit tests...\n")
    
    results = []
    results.append(test_visualization_service())
    results.append(test_svg_format())
    results.append(test_visualization_cache())
    results.append(test_cache_key_generation())
    
    print(f"\n{'='*50}")
    if all(results):
        print("All visualization service tests passed! ✓")
        sys.exit(0)
    else:
        print("Some visualization service tests failed! ✗")
        sys.exit(1)
