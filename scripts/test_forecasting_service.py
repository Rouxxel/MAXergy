"""
Unit tests for the baseline forecasting service.

Tests the forecasting service using the example input/output JSONs.
"""

import sys
import json
import os
from pathlib import Path

# Change to backend directory to ensure config files are found
backend_dir = Path(__file__).parent.parent / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from src.services.forecasting.baseline_service import BaselineForecastingService
from src.models.forecast_schemas import HouseholdAssessment


def test_forecasting_service():
    """Test the forecasting service with example input data."""
    input_path = Path(__file__).parent.parent / "documentation" / "data" / "model_input1.json"
    
    with input_path.open() as f:
        input_data = json.load(f)
    
    # Create assessment
    assessment = HouseholdAssessment(**input_data)
    
    # Create service
    service = BaselineForecastingService()
    
    # Generate forecast
    forecast = service.generate_forecast(assessment, use_cache=False)
    
    # Validate results
    assert forecast.baseline is not None, "Baseline should not be None"
    assert len(forecast.scenarios) == 6, f"Expected 6 scenarios, got {len(forecast.scenarios)}"
    
    # Check baseline costs
    baseline_total = forecast.baseline.monthly_cost_eur.total
    assert baseline_total > 0, f"Baseline total should be positive, got {baseline_total}"
    
    # Check scenarios
    scenario_ids = [s.id for s in forecast.scenarios]
    expected_ids = ["solar_only", "pv_battery", "pv_heatpump", "pv_ev", "pv_battery_heatpump", "full_upgrade"]
    for expected_id in expected_ids:
        assert expected_id in scenario_ids, f"Missing scenario: {expected_id}"
    
    # Check forecast arrays
    assert len(forecast.baseline.short_term_forecast) == 12, "Should have 12 months short-term forecast"
    assert len(forecast.baseline.long_term_forecast) == 20, "Should have 20 years long-term forecast"
    
    for scenario in forecast.scenarios:
        assert len(scenario.short_term_forecast) == 12, f"{scenario.id} should have 12 months forecast"
        assert len(scenario.long_term_forecast) == 20, f"{scenario.id} should have 20 years forecast"
    
    print("✓ Forecasting service test passed")
    print(f"  Baseline monthly total: €{baseline_total:.2f}")
    print(f"  Scenarios: {', '.join(scenario_ids)}")
    return True


def test_cache_functionality():
    """Test the caching functionality of the forecasting service."""
    input_path = Path(__file__).parent.parent / "documentation" / "data" / "model_input1.json"
    
    with input_path.open() as f:
        input_data = json.load(f)
    
    assessment = HouseholdAssessment(**input_data)
    service = BaselineForecastingService()
    
    # First call (no cache)
    forecast1 = service.generate_forecast(assessment, use_cache=True)
    
    # Second call (should use cache)
    forecast2 = service.generate_forecast(assessment, use_cache=True)
    
    # Third call (no cache)
    forecast3 = service.generate_forecast(assessment, use_cache=False)
    
    # Verify forecasts are identical
    assert forecast1.baseline.monthly_cost_eur.total == forecast2.baseline.monthly_cost_eur.total
    assert forecast1.baseline.monthly_cost_eur.total == forecast3.baseline.monthly_cost_eur.total
    
    print("✓ Cache functionality test passed")
    return True


def test_cache_key_generation():
    """Test that different assessments generate different cache keys."""
    input_path = Path(__file__).parent.parent / "documentation" / "data" / "model_input1.json"
    
    with input_path.open() as f:
        input_data = json.load(f)
    
    assessment1 = HouseholdAssessment(**input_data)
    
    # Modify assessment
    input_data["household"]["occupants"] = 5
    assessment2 = HouseholdAssessment(**input_data)
    
    service = BaselineForecastingService()
    
    key1 = service._create_cache_key(assessment1)
    key2 = service._create_cache_key(assessment2)
    
    assert key1 != key2, "Different assessments should have different cache keys"
    
    print("✓ Cache key generation test passed")
    return True


if __name__ == "__main__":
    print("Running forecasting service unit tests...\n")
    
    results = []
    results.append(test_forecasting_service())
    results.append(test_cache_functionality())
    results.append(test_cache_key_generation())
    
    print(f"\n{'='*50}")
    if all(results):
        print("All forecasting service tests passed! ✓")
        sys.exit(0)
    else:
        print("Some forecasting service tests failed! ✗")
        sys.exit(1)
