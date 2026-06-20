"""Stable public API for the production energy modelling pipeline.

Two entry points:

  compute_model(raw_input)         — accepts a dict, returns a dict.
  run_model(input_path, output_path) — reads JSON, writes JSON, returns output dict.

These are the only stable interfaces.  All internal modules may change.
This module may be called directly by an LLM agent or external API.
"""

from __future__ import annotations

import json
from pathlib import Path

from energy_model.financing import FinancingInput
from energy_model.input_validator import validate_and_parse
from energy_model.orchestrator import ScenarioOrchestrator
from energy_model.serializer import validate_financing_output, validate_output
from energy_model.setup_models import UpgradeInput


def compute_model(raw_input: dict) -> dict:
    """Compute the full energy model from a raw input dict.

    Validates input, runs all six upgrade scenarios across three price
    scenarios, computes financing, and returns the complete output dict.

    Raises ValueError for invalid input.
    """
    inp = validate_and_parse(raw_input)

    # Extract upgrade parameters (handles both canonical and legacy layout)
    upgrade = _parse_upgrade_input_from_full(raw_input)

    # Extract financing parameters
    financing_raw = raw_input.get("financing", {})
    financing = _parse_financing_input(financing_raw)

    orchestrator = ScenarioOrchestrator()
    output = orchestrator.run(inp, upgrade, financing)

    # Run validation (non-fatal — warnings collected, not raised)
    energy_warns = validate_output(output)
    fin_warns = validate_financing_output(output)
    all_warns = energy_warns + fin_warns
    if all_warns:
        existing = output.get("validation_warnings", [])
        output["validation_warnings"] = existing + all_warns

    return output


def run_model(input_path: Path | str, output_path: Path | str) -> dict:
    """Read input JSON, compute model, write output JSON.

    Creates the output directory if it does not exist.
    Returns the output dict (same as compute_model).
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    with input_path.open() as f:
        raw_input = json.load(f)

    output = compute_model(raw_input)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    return output


def _parse_upgrade_input(raw: dict) -> UpgradeInput:
    """Extract UpgradeInput from the upgrade section and/or legacy top-level keys.

    Accepts both the canonical ``upgrade`` sub-dict format and the legacy
    ``upgrade_candidates`` + ``household.roof`` layout used by model_input1.json.
    """
    kwargs: dict = {}

    def _opt_float(src: dict, src_key: str, dst_key: str | None = None) -> None:
        v = src.get(src_key)
        if v is not None:
            kwargs[dst_key or src_key] = float(v)

    def _opt_str(src: dict, src_key: str, dst_key: str | None = None) -> None:
        v = src.get(src_key)
        if v is not None:
            kwargs[dst_key or src_key] = str(v)

    _opt_float(raw, "solar_kwp")
    _opt_float(raw, "usable_roof_area_m2")
    _opt_float(raw, "battery_kwh")
    _opt_str(raw, "roof_orientation")
    _opt_float(raw, "roof_tilt_deg")
    _opt_float(raw, "shading_factor")
    _opt_float(raw, "ev_kwh_per_100km")

    return UpgradeInput(**kwargs)


def _parse_upgrade_input_from_full(raw_input: dict) -> UpgradeInput:
    """Build UpgradeInput from a complete household input dict.

    Reads from ``upgrade`` first; falls back to legacy ``upgrade_candidates``
    and ``household.roof`` sections.
    """
    upgrade_raw = dict(raw_input.get("upgrade", {}))

    # Legacy: household.roof → roof sizing parameters
    roof = raw_input.get("household", {}).get("roof", {})
    if roof.get("usable_area_m2") is not None and "usable_roof_area_m2" not in upgrade_raw:
        upgrade_raw["usable_roof_area_m2"] = roof["usable_area_m2"]
    if roof.get("orientation") and "roof_orientation" not in upgrade_raw:
        upgrade_raw["roof_orientation"] = roof["orientation"]
    if roof.get("tilt_deg") is not None and "roof_tilt_deg" not in upgrade_raw:
        upgrade_raw["roof_tilt_deg"] = roof["tilt_deg"]
    if roof.get("shading_factor") is not None and "shading_factor" not in upgrade_raw:
        upgrade_raw["shading_factor"] = roof["shading_factor"]

    # Legacy: upgrade_candidates → explicit kWp / kWh
    uc = raw_input.get("upgrade_candidates", {})
    if uc.get("solar_pv_kwp") is not None and "solar_kwp" not in upgrade_raw:
        upgrade_raw["solar_kwp"] = uc["solar_pv_kwp"]
    if uc.get("battery_kwh") is not None and "battery_kwh" not in upgrade_raw:
        upgrade_raw["battery_kwh"] = uc["battery_kwh"]

    return _parse_upgrade_input(upgrade_raw)


def _parse_financing_input(raw: dict) -> FinancingInput:
    """Extract FinancingInput from the raw financing section of the input dict."""
    kwargs: dict = {}

    def _opt_int(key: str) -> None:
        v = raw.get(key)
        if v is not None:
            kwargs[key] = int(v)

    def _opt_float(src_key: str, dst_key: str | None = None) -> None:
        v = raw.get(src_key)
        if v is not None:
            kwargs[dst_key or src_key] = float(v)

    _opt_int("loan_term_years")
    _opt_float("loan_rate_pct", "annual_rate_pct")
    _opt_float("annual_rate_pct")
    _opt_float("known_subsidy_eur")
    _opt_float("upfront_contribution_eur")
    _opt_float("pv_eur_per_kwp")
    _opt_float("battery_eur_per_kwh")
    _opt_float("heat_pump_eur_fixed")
    _opt_float("ev_charger_eur_fixed")
    _opt_float("ev_purchase_eur")

    if "loan_term_years" in kwargs and kwargs["loan_term_years"] < 1:
        raise ValueError(
            f"financing.loan_term_years must be >= 1, got {kwargs['loan_term_years']}"
        )
    if "annual_rate_pct" in kwargs and kwargs["annual_rate_pct"] < 0:
        raise ValueError(
            f"financing.annual_rate_pct must be non-negative, got {kwargs['annual_rate_pct']}"
        )

    return FinancingInput(**kwargs)
