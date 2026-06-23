"""Smoke test for the in-repo overview model.

Proves the port in `model_engine.py` reproduces the team's canonical model
(`scripts/run_baseline_model.py` in the Rouxxel/MAXergy monorepo) byte-for-byte, then
checks the structural invariants the contract requires.

Run:  uv run python overview_smoke.py    (or: python overview_smoke.py)
Fully offline — no network, no Google key. If the canonical repo isn't present locally
the cross-check is skipped and only the structural invariants run.
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import date
from pathlib import Path

from maxnergy_mcp.model_engine import run_overview
from maxnergy_mcp.model_schema import ModelInput

CANONICAL_REPO = Path("/Users/sandbox1/MAXergy")
TEMPLATE_INPUT = CANONICAL_REPO / "documentation" / "data" / "model_input1.json"


def _canonical_output(raw_in: dict, today: date) -> dict | None:
    """Run the teammate's canonical model on the same input, into a temp file (never theirs)."""
    script_dir = CANONICAL_REPO / "scripts"
    if not (script_dir / "run_baseline_model.py").exists():
        return None
    sys.path.insert(0, str(script_dir))
    import run_baseline_model as canon

    # Pin 'today' so the forecast windows line up with our run.
    canon.date = type("D", (), {"today": staticmethod(lambda: today)})
    with tempfile.TemporaryDirectory() as d:
        ip, op = Path(d) / "in.json", Path(d) / "out.json"
        ip.write_text(json.dumps(raw_in))
        canon.run_model(ip, op)
        return json.loads(op.read_text())


def main() -> None:
    raw_in = json.loads(TEMPLATE_INPUT.read_text())
    today = date.today()

    inp = ModelInput.model_validate(raw_in)          # input round-trips through the schema
    out = run_overview(inp, today=today)             # our in-repo model

    # 1. byte-for-byte parity with the canonical model
    canon = _canonical_output(raw_in, today)
    if canon is None:
        print("canonical repo not found — skipping parity check\n")
    else:
        assert out == canon, "PORT DRIFT: output differs from the canonical model"
        print("Parity: in-repo model == canonical model (exact)\n")

    # 2. structural invariants
    b = out["baseline"]["monthly_cost_eur"]
    assert abs(b["total"] - (b["electricity"] + b["heating"] + b["mobility"])) < 0.01
    stf = out["baseline"]["short_term_forecast"]
    assert abs(sum(p["total_eur"] for p in stf) / len(stf) - b["total"]) < 0.05
    for s in out["scenarios"]:
        assert "payback_month" in s  # always present (may be null)
        if s["monthly_saving_eur"] < 0:
            assert "monthly_saving_post_payoff_eur" in s
        else:
            assert "monthly_saving_post_payoff_eur" not in s
    print("Structural invariants passed.\n")

    print(f"{'scenario':22}{'save/mo':>10}{'payback':>9}")
    for s in out["scenarios"]:
        print(f"{s['id']:22}{s['monthly_saving_eur']:>10.2f}{str(s['payback_month']):>9}")
    print(f"\nbaseline total: {b['total']} €/mo  ({len(out['scenarios'])} scenarios)")


if __name__ == "__main__":
    main()
