"""MAXergy demo: run the documented households through POST /plan and print what the app shows.

Usage (backend running locally or on Railway):
    python scripts/demo_plan.py                                   # http://localhost:8000
    python scripts/demo_plan.py --api https://<maxergy-api-domain>
    python scripts/demo_plan.py --profile high_benefit_household

For each household it prints the recommended upgrade with the app's three numbers: monthly net in
year 1 (loan included; "During financing" when negative), the saving after payoff, and the
cumulative net over the horizon — the same wording as the results screen and the MCP.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import requests

REPO = Path(__file__).resolve().parent.parent
PROFILES = REPO / "documentation" / "data" / "test_profiles"
# Demo order: positive hero first, then the honest negative-during-financing case.
DEFAULT_PROFILES = ["high_benefit_household", "average_german_household", "low_benefit_household"]


def _eur(n: float) -> str:
    return f"€{abs(n):,.0f}"


def _signed(n: float) -> str:
    return f"{'−' if n < 0 else '+'}€{abs(n):,.0f}"


def describe(plan: dict) -> list[str]:
    rec = plan["recommendation"]
    best = rec["selected_scenario"]
    base = plan["forecast"]["baseline"]["monthly_cost_eur"]["total"]
    lines = [f"  Today: {_eur(base)}/month for electricity, heating and mobility"]
    if best is None:
        return lines + [f"  No upgrade possible: {rec['rationale']}"]
    m, after, f = best["monthly_saving_eur"], best["monthly_saving_post_payoff_eur"], best["financials"]
    first = (
        f"You could save {_eur(m)}/month from the start (loan included)"
        if m >= 0
        else f"During financing: {_signed(m)}/month (loan instalment {_eur(best['monthly_cost_eur']['financing_installment'])})"
    )
    lines += [
        f"  Recommended: {best['id']}",
        f"  {first}",
        f"  After payoff: {_signed(after)}/month",
        f"  {f['horizon_years']}-year net: {_signed(f['cumulative_net_savings_central_eur'])} "
        f"({_signed(f['cumulative_net_savings_low_eur'])} to {_signed(f['cumulative_net_savings_high_eur'])}), "
        f"break-even {'year ' + str(f['break_even_year']) if f['break_even_year'] else 'not reached'}",
    ]
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api", default="http://localhost:8000", help="MAXergy API base URL")
    parser.add_argument("--profile", action="append", choices=DEFAULT_PROFILES, help="profile(s) to run")
    args = parser.parse_args()

    for name in args.profile or DEFAULT_PROFILES:
        assessment = json.loads((PROFILES / f"{name}.json").read_text(encoding="utf-8"))
        try:
            resp = requests.post(f"{args.api.rstrip('/')}/plan", json=assessment, timeout=60)
        except requests.RequestException as e:
            print(f"Cannot reach {args.api}: {e}", file=sys.stderr)
            return 1
        if resp.status_code != 200:
            print(f"{name}: HTTP {resp.status_code} {resp.text[:200]}", file=sys.stderr)
            return 1
        print(f"\n{name.replace('_', ' ').title()}")
        print("\n".join(describe(resp.json())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
