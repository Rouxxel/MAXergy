"""CLI entry point for the MAXergy production energy model.

Usage:
    python scripts/run_model.py --input documentation/data/model_input1.json
    python scripts/run_model.py --input path/to/input.json --output path/to/output.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make energy_model importable when run directly
sys.path.insert(0, str(Path(__file__).parent))

from energy_model.pipeline import run_model


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_model",
        description="MAXergy household energy upgrade model",
    )
    p.add_argument(
        "--input", "-i",
        required=True,
        type=Path,
        metavar="PATH",
        help="Path to input JSON file",
    )
    p.add_argument(
        "--output", "-o",
        type=Path,
        metavar="PATH",
        default=None,
        help="Path for output JSON (default: documentation/data/model_output.json)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    input_path: Path = args.input
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        return 1

    if args.output is not None:
        output_path: Path = args.output
    else:
        repo_root = Path(__file__).parent.parent
        output_path = repo_root / "documentation" / "data" / "model_output.json"

    try:
        output = run_model(input_path, output_path)
    except ValueError as exc:
        print(f"ERROR: Invalid input — {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: Model failed — {exc}", file=sys.stderr)
        return 1

    warnings = output.get("validation_warnings", [])
    print(f"Output written to: {output_path}")
    for w in warnings:
        print(f"  WARNING: {w}")

    scenarios = output.get("upgrade_scenarios", {})
    if scenarios:
        print("\nUpgrade scenario summary (Year 1 net savings, central scenario):")
        for sn, sc in scenarios.items():
            inv = sc.get("investment", {})
            gross = inv.get("gross_investment_eur", 0)
            fin_d = sc.get("financing", {})
            instalment = fin_d.get("monthly_instalment_eur", 0)
            lt_central = sc.get("long_term_projection", {}).get("central", [])
            yr1_net = lt_central[0]["financial_result"]["annual_net_savings_eur"] if lt_central else 0
            yr_last = lt_central[-1]["financial_result"]["cumulative_net_savings_eur"] if lt_central else 0
            lt_years = len(lt_central)
            print(
                f"  {sn:<28} €{gross:>8,.0f} gross  "
                f"€{instalment:.2f}/mo  "
                f"Yr1 net: {'+' if yr1_net >= 0 else ''}€{yr1_net:,.0f}  "
                f"{lt_years}yr: {'+' if yr_last >= 0 else ''}€{yr_last:,.0f}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
