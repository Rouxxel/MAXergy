"""
Single import point for the production energy model (scripts/energy_model).

The engine lives outside the backend package, so its directory is added to sys.path here
and nowhere else.
"""

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[4] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from energy_model.assumptions import (  # noqa: E402
    BatteryAssumptions,
    EVAssumptions,
    HeatPumpAssumptions,
    SolarAssumptions,
)
from energy_model.consumption import CONSUMPTION_CONFIG  # noqa: E402
from energy_model.financing import FinancingInput  # noqa: E402
from energy_model.input_validator import flatten_mobility  # noqa: E402
from energy_model.investment_costs import InvestmentCostDefaults  # noqa: E402
from energy_model.pipeline import compute_model  # noqa: E402
from energy_model.price_models import PRICE_CONFIG  # noqa: E402
from energy_model.setup_models import UPGRADE_SCENARIO_NAMES  # noqa: E402

__all__ = [
    "BatteryAssumptions",
    "CONSUMPTION_CONFIG",
    "EVAssumptions",
    "FinancingInput",
    "HeatPumpAssumptions",
    "InvestmentCostDefaults",
    "PRICE_CONFIG",
    "SolarAssumptions",
    "UPGRADE_SCENARIO_NAMES",
    "compute_model",
    "flatten_mobility",
]
