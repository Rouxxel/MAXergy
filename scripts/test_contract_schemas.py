"""
Contract test to validate example JSONs against Pydantic schemas.

This script tests that the example input/output JSON files match the
Pydantic schemas defined in backend/src/models/forecast_schemas.py
"""

import json
import sys
from pathlib import Path

# Add backend to path to import schemas
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from src.models.forecast_schemas import (
    HouseholdAssessment,
    ForecastResult,
    Recommendation,
    AdvisorChatRequest,
    AdvisorChatResponse,
)


def test_input_schema():
    """Test that model_input1.json matches HouseholdAssessment schema."""
    input_path = Path(__file__).parent.parent / "documentation" / "data" / "model_input1.json"
    
    with input_path.open() as f:
        input_data = json.load(f)
    
    try:
        assessment = HouseholdAssessment(**input_data)
        print("✓ Input schema validation passed")
        print(f"  Location: {assessment.location.postcode}, {assessment.location.country}")
        print(f"  Occupants: {assessment.household.occupants}")
        print(f"  Annual electricity: {assessment.household.electricity.annual_kwh} kWh")
        return True
    except Exception as e:
        print(f"✗ Input schema validation failed: {e}")
        return False


def test_output_schema():
    """Test that model_output_1.json matches ForecastResult schema."""
    output_path = Path(__file__).parent.parent / "documentation" / "data" / "model_output_1.json"
    
    with output_path.open() as f:
        output_data = json.load(f)
    
    try:
        forecast = ForecastResult(**output_data)
        print("✓ Output schema validation passed")
        print(f"  Baseline monthly total: €{forecast.baseline.monthly_cost_eur.total:.2f}")
        print(f"  Number of scenarios: {len(forecast.scenarios)}")
        for scenario in forecast.scenarios:
            print(f"    - {scenario.id}: €{scenario.monthly_saving_eur:.2f}/month savings")
        return True
    except Exception as e:
        print(f"✗ Output schema validation failed: {e}")
        return False


def test_recommendation_schema():
    """Test that a sample recommendation matches Recommendation schema."""
    # Create a minimal valid recommendation
    from src.models.forecast_schemas import Scenario, Components, Sizing, ScenarioMonthlyCostEUR
    
    sample_scenario = Scenario(
        id="test_scenario",
        components=Components(solar_pv=True, battery=False, heat_pump=False, ev_charger=False),
        sizing=Sizing(solar_pv_kwp=5.0),
        monthly_cost_eur=ScenarioMonthlyCostEUR(
            electricity=50.0, heating=100.0, mobility=50.0, financing_installment=30.0, total=230.0
        ),
        monthly_saving_eur=50.0,
        self_consumption_ratio=0.3,
        short_term_forecast=[],
        long_term_forecast=[],
        payback_month=60,
    )
    
    sample_recommendation = Recommendation(
        selected_scenario_id="test_scenario",
        selected_scenario=sample_scenario,
        ranked_scenarios=[("test_scenario", 50.0)],
        rationale="Test recommendation",
    )
    
    print("✓ Recommendation schema validation passed")
    return True


def test_advisor_schemas():
    """Test that advisor request/response schemas work."""
    sample_request = AdvisorChatRequest(
        assessment_id="test_123",
        user_message="What should I upgrade first?",
    )
    
    sample_response = AdvisorChatResponse(
        advisor_message="I recommend starting with solar PV",
        context_used=["forecast_result"],
        suggestions=["Add battery for better self-consumption"],
    )
    
    print("✓ Advisor schemas validation passed")
    return True


if __name__ == "__main__":
    print("Running contract schema tests...\n")
    
    results = []
    results.append(test_input_schema())
    results.append(test_output_schema())
    results.append(test_recommendation_schema())
    results.append(test_advisor_schemas())
    
    print(f"\n{'='*50}")
    if all(results):
        print("All contract tests passed! ✓")
        sys.exit(0)
    else:
        print("Some contract tests failed! ✗")
        sys.exit(1)
