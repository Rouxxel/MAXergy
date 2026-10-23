"""The MCP contract and prompt are generated from their single sources and must not drift."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from maxergy_mcp.contract import HouseholdAssessment, PlanResponse

from conftest import load

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _run_check(script: str) -> int:
    spec = importlib.util.spec_from_file_location(script, SCRIPTS / f"{script}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    argv, sys.argv = sys.argv, [script, "--check"]
    try:
        return module.main()
    finally:
        sys.argv = argv


def test_contract_matches_backend_schema():
    assert _run_check("gen_contract") == 0


def test_prompt_matches_instructions():
    assert _run_check("gen_prompt") == 0


def test_canonical_input_validates():
    a = HouseholdAssessment.model_validate(load("model_input1.json"))
    assert a.location.postcode == "10115"
    dumped = a.model_dump(mode="json")
    assert dumped["financing"]["loan_term_years"] == 15
    assert dumped["household"]["roof"]["usable_area_m2"] == 40.0


def test_recorded_plan_validates():
    plan = PlanResponse.model_validate(load("plan_model_input1.json"))
    assert plan.recommendation.selected_scenario_id == "full_upgrade"
    assert plan.forecast.model.engine == "energy_model"
