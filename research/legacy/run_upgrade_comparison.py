"""CLI: baseline + upgrade scenario energy cost comparison with financing.

Reads the same input JSON as run_energy_cost_forecast.py (with optional
`roof`, `upgrade_candidates`, and `financing` sections) and writes a
comparison JSON that includes baseline costs, all six upgrade scenarios,
financing calculations, and validation results.

Usage:
    python scripts/run_upgrade_comparison.py
    python scripts/run_upgrade_comparison.py path/to/input.json path/to/output.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from run_energy_cost_forecast import _parse_input
from energy_model.financing import FinancingInput
from energy_model.orchestrator import ScenarioOrchestrator
from energy_model.serializer import validate_financing_output, write_json_output
from energy_model.setup_models import UPGRADE_SCENARIO_NAMES, UpgradeInput

_REPO_ROOT = Path(__file__).parent.parent


def _parse_upgrade_input(raw: dict) -> UpgradeInput:
    """Extract upgrade parameters from the raw JSON input."""
    roof = raw.get("household", {}).get("roof", {})
    uc = raw.get("upgrade_candidates", {})

    solar_kwp = uc.get("solar_pv_kwp")
    battery_kwh = uc.get("battery_kwh")

    return UpgradeInput(
        usable_roof_area_m2=roof.get("usable_area_m2") or roof.get("area_m2"),
        roof_orientation=roof.get("orientation", "south"),
        roof_tilt_deg=float(roof.get("tilt_deg", 30.0)),
        shading_factor=float(roof.get("shading_factor", 0.0)),
        solar_kwp=float(solar_kwp) if solar_kwp is not None else None,
        battery_kwh=float(battery_kwh) if battery_kwh is not None else None,
    )


def _parse_financing_input(raw: dict) -> FinancingInput:
    """Extract financing parameters from the raw JSON input."""
    f = raw.get("financing", {})
    return FinancingInput(
        loan_term_years=int(f.get("loan_term_years", 15)),
        annual_rate_pct=float(f.get("loan_rate_pct", 4.5)),
        known_subsidy_eur=float(f.get("known_subsidy_eur") or 0.0),
        upfront_contribution_eur=float(f.get("upfront_contribution_eur") or 0.0),
        pv_eur_per_kwp=f.get("pv_eur_per_kwp"),
        battery_eur_per_kwh=f.get("battery_eur_per_kwh"),
        heat_pump_eur_fixed=f.get("heat_pump_eur_fixed"),
        ev_charger_eur_fixed=f.get("ev_charger_eur_fixed"),
        ev_purchase_eur=float(f.get("ev_purchase_eur") or 0.0),
    )


def run_comparison(input_path: Path, output_path: Path) -> dict:
    """Run the full comparison and write output.  Returns the output dict."""
    with input_path.open() as f:
        raw = json.load(f)

    inp = _parse_input(raw)
    upgrade = _parse_upgrade_input(raw)
    financing = _parse_financing_input(raw)

    orchestrator = ScenarioOrchestrator()
    result = orchestrator.run(inp, upgrade, financing)

    # Validate (energy schema + financing)
    from energy_model.serializer import validate_output
    energy_errors = validate_output(result)
    fin_errors = validate_financing_output(result)
    all_errors = energy_errors + fin_errors

    errors = write_json_output(result, output_path, validate=False)  # already validated above

    if all_errors:
        result["validation_errors"] = all_errors
        write_json_output(result, output_path, validate=False)

    print(f"Wrote {output_path}")

    for w in result.get("validation_warnings", []):
        print(f"  WARNING: {w}")

    if all_errors:
        for e in all_errors:
            print(f"  VALIDATION ERROR: {e}")

    _print_summary(result)

    return result


def _print_summary(result: dict) -> None:
    print("\n=== Energy cost comparison + financing (central scenario, first year) ===")
    baseline_lt = result["baseline"]["long_term_projection"].get("central", [])
    if baseline_lt:
        b = baseline_lt[0]["cost_eur"]
        print(
            f"Baseline Year 1: "
            f"€{b['electricity']:.0f} elec + €{b['heating']:.0f} heat + "
            f"€{b['mobility']:.0f} mob = €{b['total']:.0f}"
        )

    print()
    print(f"  {'Scenario':<25} {'Invest':>8} {'Principal':>10} {'Instal/mo':>10} "
          f"{'Yr1 net':>10} {'20yr cum net':>14}")
    print(f"  {'-'*25} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*14}")

    for sn in UPGRADE_SCENARIO_NAMES:
        scen = result["upgrade_scenarios"][sn]
        inv = scen["investment"]["gross_investment_eur"]
        principal = scen["investment"]["financed_principal_eur"]
        instalment = scen["financing"]["monthly_instalment_eur"]

        lt = scen["long_term_projection"].get("central", [])
        yr1_net = lt[0]["financial_result"]["annual_net_savings_eur"] if lt else 0
        cum20 = lt[-1]["financial_result"]["cumulative_net_savings_eur"] if lt else 0

        print(
            f"  {sn:<25} €{inv:>7,.0f} €{principal:>9,.0f} €{instalment:>9,.2f}/mo "
            f"€{yr1_net:>+9,.0f} €{cum20:>+13,.0f}"
        )


if __name__ == "__main__":
    if len(sys.argv) == 3:
        in_path = Path(sys.argv[1])
        out_path = Path(sys.argv[2])
    else:
        in_path = _REPO_ROOT / "documentation" / "data" / "model_input1.json"
        out_path = _REPO_ROOT / "documentation" / "data" / "model_output_upgrade_comparison.json"

    run_comparison(in_path, out_path)
