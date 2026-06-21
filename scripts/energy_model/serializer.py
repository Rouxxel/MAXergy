"""Output serialization and validation for the energy upgrade comparison.

validate_output() runs 10 energy-schema checks.
validate_financing_output() runs 14 financing-specific checks.
write_json_output() serializes to disk and optionally validates first.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from energy_model.setup_models import PRICE_SCENARIOS, UPGRADE_SCENARIO_NAMES

# Keys that would indicate financing was accidentally included
_FINANCING_KEYS: frozenset[str] = frozenset(
    {"loan_amount", "monthly_payment", "npv", "irr", "payback_years",
     "loan_rate", "loan_term", "subsidy"}
)


def validate_output(output: dict) -> list[str]:
    """Run all 10 validation checks.  Returns a list of error descriptions."""
    errors: list[str] = []

    scenarios = output.get("upgrade_scenarios", {})
    baseline = output.get("baseline", {})

    # 1. All six scenarios present -------------------------------------------
    missing = [s for s in UPGRADE_SCENARIO_NAMES if s not in scenarios]
    if missing:
        errors.append(f"CHECK 1 FAIL – missing scenarios: {missing}")

    # 2. Baseline and upgrade months align exactly ---------------------------
    base_st = baseline.get("short_term_forecast", [])
    base_months_list = [r.get("month") for r in base_st]
    for sn in UPGRADE_SCENARIO_NAMES:
        upg_st = scenarios.get(sn, {}).get("short_term_forecast", [])
        upg_months = [r.get("month") for r in upg_st]
        if upg_months != base_months_list:
            errors.append(f"CHECK 2 FAIL – month alignment mismatch for {sn}")

    # 3. Baseline and upgrades use identical prices (central ST) -------------
    if base_st:
        base_prices = [r.get("prices", {}).get("electricity_eur_per_kwh") for r in base_st]
        for sn in UPGRADE_SCENARIO_NAMES:
            upg_st = scenarios.get(sn, {}).get("short_term_forecast", [])
            upg_prices = [r.get("prices", {}).get("electricity_eur_per_kwh") for r in upg_st]
            if upg_prices != base_prices:
                errors.append(f"CHECK 3 FAIL – price mismatch for {sn}")

    # 4. Monthly cost components sum to their totals -------------------------
    tol = 0.02  # 2-cent rounding tolerance
    for sn in UPGRADE_SCENARIO_NAMES:
        upg_st = scenarios.get(sn, {}).get("short_term_forecast", [])
        for rec in upg_st:
            c = rec.get("cost_eur", {})
            expected = (
                c.get("electricity", 0)
                - c.get("solar_export_revenue", 0)
                + c.get("heating", 0)
                + c.get("mobility", 0)
            )
            actual = c.get("upgraded_total", 0)
            if abs(actual - expected) > tol:
                errors.append(
                    f"CHECK 4 FAIL – cost sum mismatch {sn} {rec.get('month')}: "
                    f"components={expected:.4f} total={actual:.4f}"
                )

    # 4b. Baseline monthly cost sum ------------------------------------------
    for rec in base_st:
        c = rec.get("cost_eur", {})
        expected = c.get("electricity", 0) + c.get("heating", 0) + c.get("mobility", 0)
        actual = c.get("total", 0)
        if abs(actual - expected) > tol:
            errors.append(
                f"CHECK 4b FAIL – baseline cost sum {rec.get('month')}: "
                f"components={expected:.4f} total={actual:.4f}"
            )

    # 5. Energy cost reduction = baseline − upgraded -------------------------
    for sn in UPGRADE_SCENARIO_NAMES:
        upg_st = scenarios.get(sn, {}).get("short_term_forecast", [])
        for rec in upg_st:
            c = rec.get("cost_eur", {})
            expected_red = c.get("baseline_total", 0) - c.get("upgraded_total", 0)
            actual_red = c.get("energy_cost_reduction", 0)
            if abs(actual_red - expected_red) > tol:
                errors.append(
                    f"CHECK 5 FAIL – reduction {sn} {rec.get('month')}: "
                    f"expected={expected_red:.4f} actual={actual_red:.4f}"
                )

    # 6. LT scenario ordering: low ≤ central ≤ high for year 1 ---------------
    # (ST and LT use different price models; cross-model comparison is not valid)
    for sn in UPGRADE_SCENARIO_NAMES:
        lt = scenarios.get(sn, {}).get("long_term_projection", {})
        lt_low = lt.get("low", [])
        lt_cen = lt.get("central", [])
        lt_high = lt.get("high", [])
        if lt_low and lt_cen and lt_high:
            low_yr1 = lt_low[0].get("cost_eur", {}).get("upgraded_total", 0)
            cen_yr1 = lt_cen[0].get("cost_eur", {}).get("upgraded_total", 0)
            high_yr1 = lt_high[0].get("cost_eur", {}).get("upgraded_total", 0)
            if not (low_yr1 <= cen_yr1 <= high_yr1):
                errors.append(
                    f"CHECK 6 FAIL – LT scenario ordering {sn} yr1: "
                    f"low={low_yr1:.2f} central={cen_yr1:.2f} high={high_yr1:.2f}"
                )

    # 7. Cumulative reductions calculated correctly -------------------------
    for sn in UPGRADE_SCENARIO_NAMES:
        lt_central = (
            scenarios.get(sn, {})
            .get("long_term_projection", {})
            .get("central", [])
        )
        running = 0.0
        for i, ann in enumerate(lt_central):
            annual_red = ann.get("cost_eur", {}).get("energy_cost_reduction", 0)
            cumulative = ann.get("cost_eur", {}).get("cumulative_energy_cost_reduction", 0)
            running += annual_red
            if abs(cumulative - running) > 0.10:
                errors.append(
                    f"CHECK 7 FAIL – cumulative mismatch {sn} year {i+1}: "
                    f"expected={running:.2f} actual={cumulative:.2f}"
                )
                break  # stop after first mismatch to avoid noise

    # 8. No NaN or Infinity --------------------------------------------------
    def _has_bad_float(obj: Any, path: str = "") -> str | None:
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return f"bad float at {path}: {obj}"
        elif isinstance(obj, dict):
            for k, v in obj.items():
                result = _has_bad_float(v, f"{path}.{k}")
                if result:
                    return result
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                result = _has_bad_float(v, f"{path}[{i}]")
                if result:
                    return result
        return None

    bad = _has_bad_float(output, "output")
    if bad:
        errors.append(f"CHECK 8 FAIL – {bad}")

    # 9. JSON round-trip ---------------------------------------------------
    try:
        reloaded = json.loads(json.dumps(output))
        if reloaded.get("model") != output.get("model"):
            errors.append("CHECK 9 FAIL – JSON round-trip produced different model section")
    except Exception as exc:
        errors.append(f"CHECK 9 FAIL – JSON serialization error: {exc}")

    # 10. No financing fields ---------------------------------------------
    def _has_financing(obj: Any) -> bool:
        if isinstance(obj, dict):
            if _FINANCING_KEYS.intersection(obj.keys()):
                return True
            return any(_has_financing(v) for v in obj.values())
        if isinstance(obj, list):
            return any(_has_financing(v) for v in obj)
        return False

    if _has_financing(output):
        errors.append("CHECK 10 FAIL – output contains financing fields")

    return errors


def validate_financing_output(output: dict) -> list[str]:
    """Run 14 financing-specific validation checks.

    Checks are labelled FIN-CHECK 1 through FIN-CHECK 14.
    Returns a list of error descriptions (empty = all passed).
    """
    errors: list[str] = []
    scenarios = output.get("upgrade_scenarios", {})
    tol = 0.10  # 10-cent tolerance for multi-step rounding

    for sn, scen in scenarios.items():
        inv = scen.get("investment", {})
        fin = scen.get("financing", {})
        st = scen.get("short_term_forecast", [])
        lt_central = scen.get("long_term_projection", {}).get("central", [])

        gross = inv.get("gross_investment_eur", 0.0)
        subsidy = inv.get("subsidy_eur", 0.0)
        upfront = inv.get("upfront_contribution_eur", 0.0)
        principal = inv.get("financed_principal_eur", 0.0)
        instalment = fin.get("monthly_instalment_eur", 0.0)
        total_rep = fin.get("total_repayment_eur", 0.0)
        total_int = fin.get("total_interest_eur", 0.0)
        loan_months = fin.get("loan_term_months", 0)

        # FIN-CHECK 1: principal = gross - subsidy - upfront (clamped to ≥0)
        expected_principal = max(0.0, gross - subsidy - upfront)
        if abs(principal - expected_principal) > tol:
            errors.append(
                f"FIN-CHECK 1 FAIL [{sn}] – principal mismatch: "
                f"expected={expected_principal:.2f} actual={principal:.2f}"
            )

        # FIN-CHECK 2: principal is never negative
        if principal < 0:
            errors.append(f"FIN-CHECK 2 FAIL [{sn}] – negative principal: {principal:.2f}")

        # FIN-CHECK 3: annuity formula correctness (non-zero rate)
        if principal > 0 and loan_months > 0 and instalment > 0:
            rate = fin.get("annual_interest_rate_pct", 0.0) / 100.0 / 12.0
            if rate > 0:
                factor = (1.0 + rate) ** loan_months
                expected_inst = principal * rate * factor / (factor - 1.0)
                if abs(instalment - expected_inst) > tol:
                    errors.append(
                        f"FIN-CHECK 3 FAIL [{sn}] – annuity formula: "
                        f"expected={expected_inst:.4f} actual={instalment:.4f}"
                    )

        # FIN-CHECK 4: zero-interest loan gives instalment = principal / n
        if principal > 0 and loan_months > 0:
            rate = fin.get("annual_interest_rate_pct", 0.0)
            if rate == 0.0:
                expected_zero = principal / loan_months
                if abs(instalment - expected_zero) > tol:
                    errors.append(
                        f"FIN-CHECK 4 FAIL [{sn}] – zero-rate instalment: "
                        f"expected={expected_zero:.4f} actual={instalment:.4f}"
                    )

        # FIN-CHECK 5: payments stop after loan term
        if st:
            for i, rec in enumerate(st):
                fr = rec.get("financial_result", {})
                fi = fr.get("financing_instalment_eur", 0.0)
                payment_no = i + 1
                if payment_no > loan_months and abs(fi) > tol:
                    errors.append(
                        f"FIN-CHECK 5 FAIL [{sn}] – payment at month {payment_no} "
                        f"after loan term {loan_months}: {fi:.2f}"
                    )

        # FIN-CHECK 6: total repayment ≈ sum of monthly payments.
        # Tolerance = loan_months × 0.005 because the stored instalment is
        # rounded to 2 dp; n payments can accumulate up to n × 0.005 drift.
        if loan_months > 0 and instalment > 0:
            expected_rep = instalment * loan_months
            rep_tol = max(tol, loan_months * 0.005)
            if abs(total_rep - expected_rep) > rep_tol:
                errors.append(
                    f"FIN-CHECK 6 FAIL [{sn}] – total_repayment: "
                    f"expected≈{expected_rep:.2f} actual={total_rep:.2f}"
                )

        # FIN-CHECK 7: total interest = total repayment - principal
        expected_int = total_rep - principal
        if abs(total_int - expected_int) > tol:
            errors.append(
                f"FIN-CHECK 7 FAIL [{sn}] – total_interest: "
                f"expected={expected_int:.2f} actual={total_int:.2f}"
            )

        # FIN-CHECK 8: monthly net savings = energy_reduction - instalment
        for rec in st:
            fr = rec.get("financial_result", {})
            red = fr.get("energy_cost_reduction_eur", 0.0)
            fi = fr.get("financing_instalment_eur", 0.0)
            net = fr.get("net_monthly_savings_eur", 0.0)
            expected_net = red - fi
            if abs(net - expected_net) > tol:
                errors.append(
                    f"FIN-CHECK 8 FAIL [{sn}] {rec.get('month')} – "
                    f"net_savings={net:.4f} expected={expected_net:.4f}"
                )

        # FIN-CHECK 9: LT annual net savings = annual energy reduction - annual payments
        # (ST and LT use different price models; cross-model comparison is not valid)
        for ann in lt_central:
            ann_fr = ann.get("financial_result", {})
            ann_red = ann_fr.get("annual_energy_cost_reduction_eur", 0.0)
            ann_pay = ann_fr.get("annual_financing_payments_eur", 0.0)
            ann_net = ann_fr.get("annual_net_savings_eur", 0.0)
            expected_net = ann_red - ann_pay
            if abs(ann_net - expected_net) > tol:
                errors.append(
                    f"FIN-CHECK 9 FAIL [{sn}] yr{lt_central.index(ann)+1} – "
                    f"net_savings={ann_net:.2f} expected={expected_net:.2f}"
                )

        # FIN-CHECK 10: baseline and upgraded energy costs unchanged by financing
        # (check that energy_cost_reduction matches cost_eur fields)
        for rec in st:
            c = rec.get("cost_eur", {})
            fr = rec.get("financial_result", {})
            energy_red_cost_eur = c.get("energy_cost_reduction", 0.0)
            energy_red_fr = fr.get("energy_cost_reduction_eur", 0.0)
            if abs(energy_red_cost_eur - energy_red_fr) > tol:
                errors.append(
                    f"FIN-CHECK 10 FAIL [{sn}] {rec.get('month')} – "
                    f"energy_reduction in cost_eur ({energy_red_cost_eur:.4f}) "
                    f"≠ financial_result ({energy_red_fr:.4f})"
                )

    # FIN-CHECK 11: financing calculated separately per scenario (instalments differ)
    instalments = {
        sn: scenarios[sn].get("financing", {}).get("monthly_instalment_eur", 0.0)
        for sn in scenarios
    }
    principals = {
        sn: scenarios[sn].get("investment", {}).get("financed_principal_eur", 0.0)
        for sn in scenarios
    }
    # Two scenarios with different gross investments must have different instalments
    # (unless both are zero-investment)
    grosses = {sn: scenarios[sn].get("investment", {}).get("gross_investment_eur", 0.0)
               for sn in scenarios}
    for sn_a, sn_b in [("solar_only", "pv_battery"), ("pv_battery", "pv_battery_heatpump")]:
        if sn_a in grosses and sn_b in grosses:
            if abs(grosses[sn_a] - grosses[sn_b]) > 1.0:
                if abs(instalments.get(sn_a, 0) - instalments.get(sn_b, 0)) < 0.01:
                    errors.append(
                        f"FIN-CHECK 11 FAIL – {sn_a} and {sn_b} have different "
                        f"investments ({grosses[sn_a]:.2f} vs {grosses[sn_b]:.2f}) "
                        f"but identical instalments"
                    )

    # FIN-CHECK 12: no shared-technology double-counting.
    # Components are nested under investment["components"].
    if all(sn in scenarios for sn in ["solar_only", "pv_battery", "full_upgrade"]):
        fu_inv = scenarios["full_upgrade"].get("investment", {})
        fu_comp = fu_inv.get("components", {})
        comp_sum = sum(fu_comp.values())
        fu_gross = fu_inv.get("gross_investment_eur", 0.0)
        if abs(fu_gross - comp_sum) > tol:
            errors.append(
                f"FIN-CHECK 12 FAIL – full_upgrade gross ({fu_gross:.2f}) ≠ "
                f"component sum ({comp_sum:.2f})"
            )
        # pv_battery gross must equal pv component + battery component
        so_comp = scenarios["solar_only"].get("investment", {}).get("components", {})
        pb_inv = scenarios["pv_battery"].get("investment", {})
        pb_comp = pb_inv.get("components", {})
        pv_eur = so_comp.get("pv_eur", 0.0)
        bat_eur = pb_comp.get("battery_eur", 0.0)
        pb_gross = pb_inv.get("gross_investment_eur", 0.0)
        if abs(pb_gross - (pv_eur + bat_eur)) > tol:
            errors.append(
                f"FIN-CHECK 12b FAIL – pv_battery gross ({pb_gross:.2f}) ≠ "
                f"pv ({pv_eur:.2f}) + battery ({bat_eur:.2f})"
            )

    # FIN-CHECK 13: no NaN or Infinity in financing fields
    def _bad_float_in_fin(obj: Any, path: str = "") -> str | None:
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return f"{path}: {obj}"
        if isinstance(obj, dict):
            for k, v in obj.items():
                r = _bad_float_in_fin(v, f"{path}.{k}")
                if r:
                    return r
        if isinstance(obj, list):
            for i, v in enumerate(obj):
                r = _bad_float_in_fin(v, f"{path}[{i}]")
                if r:
                    return r
        return None

    for sn, scen in scenarios.items():
        bad = _bad_float_in_fin(scen.get("investment", {}), f"{sn}.investment")
        bad = bad or _bad_float_in_fin(scen.get("financing", {}), f"{sn}.financing")
        if bad:
            errors.append(f"FIN-CHECK 13 FAIL – NaN/Inf in {bad}")

    # FIN-CHECK 14: negative monthly net savings preserved (not clamped to zero)
    # At least some scenarios should have months where instalment > energy_reduction
    # when principal > 0.  We verify values are not artificially floored.
    for sn, scen in scenarios.items():
        st = scen.get("short_term_forecast", [])
        for rec in st:
            fr = rec.get("financial_result", {})
            net = fr.get("net_monthly_savings_eur")
            red = fr.get("energy_cost_reduction_eur", 0.0)
            fi = fr.get("financing_instalment_eur", 0.0)
            if net is not None and fi > red:
                # Should be negative, not zero
                if net >= 0:
                    errors.append(
                        f"FIN-CHECK 14 FAIL [{sn}] {rec.get('month')} – "
                        f"net_savings clamped to {net:.4f} (expected < 0)"
                    )
                    break

    return errors


def write_json_output(
    output: dict,
    path: Path,
    validate: bool = True,
) -> list[str]:
    """Write the output dict to *path* as pretty-printed JSON.

    Returns the list of validation errors (empty = all checks passed).
    """
    errors: list[str] = []
    if validate:
        errors = validate_output(output)

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return errors
