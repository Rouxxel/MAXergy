"""Energy system upgrade modelling package.

Stable public API:
  compute_model(raw_input)           — dict → dict
  run_model(input_path, output_path) — file → file

Supporting types for direct use:
"""

from energy_model.assumptions import (
    BatteryAssumptions,
    EVAssumptions,
    GridAssumptions,
    HeatPumpAssumptions,
    SolarAssumptions,
)
from energy_model.financing import FinancingInput, FinancingModel, LoanSchedule
from energy_model.input_validator import ParsedInput, validate_and_parse
from energy_model.investment_costs import InvestmentCostDefaults, compute_scenario_investment
from energy_model.orchestrator import ScenarioOrchestrator
from energy_model.pipeline import compute_model, run_model
from energy_model.price_models import (
    ConstantShortTermPriceModel,
    PriceConfig,
    PriceModelProtocol,
    ScenarioPriceModel,
)
from energy_model.serializer import validate_financing_output, validate_output, write_json_output
from energy_model.setup_models import UpgradeInput

__all__ = [
    "BatteryAssumptions",
    "ConstantShortTermPriceModel",
    "EVAssumptions",
    "FinancingInput",
    "FinancingModel",
    "GridAssumptions",
    "HeatPumpAssumptions",
    "InvestmentCostDefaults",
    "LoanSchedule",
    "ParsedInput",
    "PriceConfig",
    "PriceModelProtocol",
    "ScenarioPriceModel",
    "ScenarioOrchestrator",
    "SolarAssumptions",
    "UpgradeInput",
    "compute_model",
    "compute_scenario_investment",
    "run_model",
    "validate_and_parse",
    "validate_financing_output",
    "validate_output",
    "write_json_output",
]
