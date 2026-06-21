"""
Expanding-window backtesting of CPI energy price index forecasting models.

Models evaluated:
  1. Constant index
  2. Deterministic trend (production growth assumptions)
  3. ETS  (AIC-selected from a predefined candidate set)
  4. SARIMA (AIC-selected from a predefined grid)

Usage:
    python scripts/evaluation/backtest_price_models.py

Outputs written to scripts/evaluation/output/:
  backtest_results.csv   — one row per forecast observation
  backtest_summary.json  — aggregated metrics and recommendations
  backtest_report.md     — narrative report
"""

from __future__ import annotations

import csv
import json
import math
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

# Allow running from repo root or from this directory
_HERE = Path(__file__).parent
sys.path.insert(0, str(_HERE))

from destatis_loader import DestatisLoader
from price_models import (
    ANNUAL_GROWTH_RATES,
    ConstantModel,
    DeterministicTrendModel,
    ETSModel,
    ForecastError,
    SARIMAModel,
)

# ── Constants ─────────────────────────────────────────────────────────────────

CSV_PATH    = _HERE / "61111-0004_de.csv"
OUTPUT_DIR  = _HERE / "output"
RESULTS_CSV = OUTPUT_DIR / "backtest_results.csv"
SUMMARY_JSON = OUTPUT_DIR / "backtest_summary.json"
REPORT_MD   = OUTPUT_DIR / "backtest_report.md"

SERIES_IDS  = ["electricity", "gas", "heating_oil", "petrol"]
HORIZONS    = [1, 3, 6, 12]
MIN_TRAIN   = 60
MAX_FORECAST_HORIZON = 12

# Models in simplicity order (simplest first) — used for tie-breaking
MODEL_NAMES = ["constant", "deterministic_trend", "ets", "sarima"]
SIMPLICITY  = {m: i for i, m in enumerate(MODEL_NAMES)}

# Prefer simpler model if its MAE is within this fraction of the best MAE
PREFERENCE_THRESHOLD = 0.10


# ── Data loading ──────────────────────────────────────────────────────────────


def load_series(csv_path: Path) -> dict[str, list[tuple[str, float]]]:
    """
    Return {series_id: [(YYYY-MM, value), ...]} sorted by date.
    Uses DestatisLoader; does not re-validate the dataset.
    """
    result = DestatisLoader(csv_path).load()
    df = result.clean_df
    if df is None:
        raise RuntimeError("pandas is required for backtesting")

    col_map = {
        "electricity_index": "electricity",
        "gas_index":         "gas",
        "heating_oil_index": "heating_oil",
        "petrol_index":      "petrol",
    }
    series: dict[str, list[tuple[str, float]]] = {}
    for col, sid in col_map.items():
        pairs = [
            (idx.strftime("%Y-%m"), float(val))
            for idx, val in df[col].items()
            if not math.isnan(float(val))
        ]
        series[sid] = sorted(pairs, key=lambda x: x[0])
    return series


# ── Metric helpers ────────────────────────────────────────────────────────────


def safe_smape(actual: float, forecast: float) -> float:
    """Symmetric MAPE for one observation; returns NaN when denom = 0."""
    denom = abs(actual) + abs(forecast)
    if denom == 0.0:
        return float("nan")
    return 2.0 * abs(actual - forecast) / denom * 100.0


def compute_metrics(actuals: list[float], forecasts: list[float]) -> dict[str, float]:
    """MAE, RMSE, sMAPE, bias for paired actual/forecast lists."""
    n = len(actuals)
    if n == 0:
        return {"mae": float("nan"), "rmse": float("nan"),
                "smape": float("nan"), "bias": float("nan"), "n": 0}

    errors    = [f - a for f, a in zip(forecasts, actuals)]
    abs_errs  = [abs(e) for e in errors]
    sq_errs   = [e * e for e in errors]
    smape_raw = [safe_smape(a, f) for a, f in zip(actuals, forecasts)]
    valid_sm  = [v for v in smape_raw if not math.isnan(v)]

    return {
        "mae":   sum(abs_errs) / n,
        "rmse":  math.sqrt(sum(sq_errs) / n),
        "smape": sum(valid_sm) / len(valid_sm) if valid_sm else float("nan"),
        "bias":  sum(errors) / n,
        "n":     n,
    }


# ── Core backtest ─────────────────────────────────────────────────────────────


def run_backtest(
    series_data: dict[str, list[tuple[str, float]]],
    min_train: int = MIN_TRAIN,
) -> tuple[list[dict], dict, dict, dict]:
    """
    Expanding-window backtesting for all series and models.

    Returns:
        records       — list of per-observation dicts for CSV output
        model_failures — {model: {series: count}} model-level failures
        config_counts  — {"ets": {label: count}, "sarima": {label: count}}
        sarima_warn    — {series: [warning strings]}
    """
    records: list[dict] = []
    model_failures: dict[str, dict[str, int]] = {
        m: {s: 0 for s in series_data} for m in MODEL_NAMES
    }
    config_counts: dict[str, dict[str, int]] = {"ets": {}, "sarima": {}}
    sarima_warn: dict[str, list[str]] = {s: [] for s in series_data}

    n_series = len(series_data)
    for si, (series_id, ts) in enumerate(series_data.items(), 1):
        n = len(ts)
        dates  = [d for d, _ in ts]
        values = [v for _, v in ts]
        n_cutoffs = n - min_train  # number of valid training cutoffs

        print(
            f"  [{si}/{n_series}] {series_id}  "
            f"({n} obs, {n_cutoffs} cutoffs) ...",
            flush=True,
        )

        for cutoff_idx in range(min_train - 1, n - 1):
            train_vals  = values[: cutoff_idx + 1]
            cutoff_date = dates[cutoff_idx]
            max_h       = min(MAX_FORECAST_HORIZON, n - 1 - cutoff_idx)

            # ── Fit all models once per cutoff ─────────────────────────────
            fitted_forecasts: dict[str, list[float]] = {}
            fitted_params:    dict[str, Any]         = {}

            for name in MODEL_NAMES:
                try:
                    model: Any
                    if name == "constant":
                        model = ConstantModel()
                    elif name == "deterministic_trend":
                        model = DeterministicTrendModel(series_id)
                    elif name == "ets":
                        model = ETSModel()
                    else:
                        model = SARIMAModel()

                    model.fit(train_vals)
                    fc = model.forecast(MAX_FORECAST_HORIZON)
                    fitted_forecasts[name] = fc
                    fitted_params[name]    = model.params

                    # Track selected ETS / SARIMA configs
                    if name == "ets":
                        lbl = model.params.get("selected_config", "unknown")
                        config_counts["ets"][lbl] = (
                            config_counts["ets"].get(lbl, 0) + 1
                        )
                    elif name == "sarima":
                        lbl = model.params.get("label", "unknown")
                        config_counts["sarima"][lbl] = (
                            config_counts["sarima"].get(lbl, 0) + 1
                        )
                        if model.fit_failures:
                            sarima_warn[series_id].append(
                                f"{cutoff_date}: "
                                f"{len(model.fit_failures)} candidate(s) failed"
                            )

                except Exception:
                    model_failures[name][series_id] += 1

            # ── Record one row per model × horizon ────────────────────────
            for h in HORIZONS:
                if h > max_h:
                    continue
                forecast_idx = cutoff_idx + h
                actual_val   = values[forecast_idx]
                forecast_date = dates[forecast_idx]

                for name, fc in fitted_forecasts.items():
                    pred      = fc[h - 1]
                    error     = pred - actual_val
                    abs_error = abs(error)
                    smape_val = safe_smape(actual_val, pred)
                    pct_error = (
                        error / actual_val * 100.0
                        if actual_val != 0.0
                        else float("nan")
                    )

                    records.append({
                        "energy_type":     series_id,
                        "model":           name,
                        "training_cutoff": cutoff_date,
                        "horizon":         h,
                        "forecast_month":  forecast_date,
                        "actual_index":    round(actual_val, 4),
                        "predicted_index": round(pred, 4),
                        "error":           round(error, 4),
                        "absolute_error":  round(abs_error, 4),
                        "pct_error": (
                            round(pct_error, 4)
                            if not math.isnan(pct_error) else ""
                        ),
                        "smape": (
                            round(smape_val, 4)
                            if not math.isnan(smape_val) else ""
                        ),
                        "model_params": json.dumps(
                            fitted_params.get(name, {}), ensure_ascii=False
                        ),
                    })

    return records, model_failures, config_counts, sarima_warn


# ── Aggregation ───────────────────────────────────────────────────────────────


def compute_summary(
    records: list[dict],
    model_failures: dict,
    config_counts: dict,
    sarima_warn: dict,
) -> dict:
    """Aggregate records into nested metrics dict."""

    # Bucket actuals / preds by (series, model, horizon)
    buckets: dict[tuple, tuple[list[float], list[float]]] = defaultdict(
        lambda: ([], [])
    )
    for r in records:
        key = (r["energy_type"], r["model"], r["horizon"])
        act, pred = buckets[key]
        act.append(r["actual_index"])
        pred.append(r["predicted_index"])

    summary: dict[str, Any] = {}

    # Infer series present from the records (may be a subset of SERIES_IDS in tests)
    series_present = sorted({r["energy_type"] for r in records})

    for series_id in series_present:
        det_mae_by_h: dict[int, float] = {}
        series_section: dict[str, Any] = {}

        for model_name in MODEL_NAMES:
            by_h: dict[str, Any] = {}
            all_act:  list[float] = []
            all_pred: list[float] = []

            for h in HORIZONS:
                act, pred = buckets.get((series_id, model_name, h), ([], []))
                if not act:
                    continue
                m = compute_metrics(act, pred)
                by_h[str(h)] = {
                    "mae":       round(m["mae"],   4),
                    "rmse":      round(m["rmse"],  4),
                    "smape":     round(m["smape"], 4) if not math.isnan(m["smape"]) else None,
                    "bias":      round(m["bias"],  4),
                    "n_origins": m["n"],
                }
                all_act.extend(act)
                all_pred.extend(pred)

                if model_name == "deterministic_trend":
                    det_mae_by_h[h] = m["mae"]

            if all_act:
                ov = compute_metrics(all_act, all_pred)
                overall = {
                    "mae":       round(ov["mae"],   4),
                    "rmse":      round(ov["rmse"],  4),
                    "smape":     round(ov["smape"], 4) if not math.isnan(ov["smape"]) else None,
                    "bias":      round(ov["bias"],  4),
                    "n_origins": ov["n"],
                }
            else:
                overall = {}

            series_section[model_name] = {"by_horizon": by_h, "overall": overall}

        # MAE improvement over deterministic trend
        for model_name in MODEL_NAMES:
            imp_by_h: dict[str, float | None] = {}
            model_data = series_section.get(model_name, {})
            for h in HORIZONS:
                det_mae = det_mae_by_h.get(h)
                model_mae_entry = model_data.get("by_horizon", {}).get(str(h), {})
                model_mae = model_mae_entry.get("mae")
                if det_mae and model_mae is not None and det_mae != 0:
                    imp = (det_mae - model_mae) / det_mae * 100.0
                    imp_by_h[str(h)] = round(imp, 2)
                else:
                    imp_by_h[str(h)] = None
            series_section[model_name]["mae_improvement_vs_det"] = imp_by_h

            # Overall improvement
            det_ov = series_section.get("deterministic_trend", {}).get("overall", {})
            mod_ov = series_section.get(model_name, {}).get("overall", {})
            det_mae_ov = det_ov.get("mae")
            mod_mae_ov = mod_ov.get("mae")
            if det_mae_ov and mod_mae_ov is not None and det_mae_ov != 0:
                series_section[model_name]["mae_improvement_vs_det_overall"] = round(
                    (det_mae_ov - mod_mae_ov) / det_mae_ov * 100.0, 2
                )
            else:
                series_section[model_name]["mae_improvement_vs_det_overall"] = None

        # Best model per horizon
        best_by_h: dict[str, dict] = {}
        for h in HORIZONS:
            candidates = []
            for m in MODEL_NAMES:
                mae = (
                    series_section.get(m, {})
                    .get("by_horizon", {})
                    .get(str(h), {})
                    .get("mae")
                )
                if mae is not None:
                    candidates.append((mae, SIMPLICITY[m], m))
            if candidates:
                candidates.sort()
                best_mae, _, best_m = candidates[0]
                best_by_h[str(h)] = {"model": best_m, "mae": best_mae}

        # Overall recommendation (lowest avg MAE; prefer simpler within threshold)
        overall_maes = [
            (
                series_section.get(m, {}).get("overall", {}).get("mae", float("inf")),
                SIMPLICITY[m],
                m,
            )
            for m in MODEL_NAMES
            if series_section.get(m, {}).get("overall")
        ]
        overall_maes.sort()
        best_overall_mae = overall_maes[0][0] if overall_maes else float("inf")
        recommended = overall_maes[0][2] if overall_maes else "unknown"
        # Prefer simpler if within threshold
        for mae, _, m in overall_maes:
            if mae <= best_overall_mae * (1.0 + PREFERENCE_THRESHOLD):
                recommended = m
                break

        summary[series_id] = {
            "models":               series_section,
            "best_model_by_horizon": best_by_h,
            "recommended_model":     recommended,
            "model_failures":        {m: model_failures.get(m, {}).get(series_id, 0) for m in MODEL_NAMES},
        }

    summary["ets_configs_selected"]   = config_counts.get("ets", {})
    summary["sarima_configs_selected"] = config_counts.get("sarima", {})
    summary["sarima_convergence_warnings"] = {
        k: v[:20] for k, v in sarima_warn.items()
    }

    return summary


# ── Output writers ────────────────────────────────────────────────────────────

_RESULTS_COLS = [
    "energy_type", "model", "training_cutoff", "horizon", "forecast_month",
    "actual_index", "predicted_index", "error", "absolute_error",
    "pct_error", "smape", "model_params",
]


def write_results_csv(records: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_RESULTS_COLS)
        w.writeheader()
        w.writerows(records)


def write_summary_json(summary: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
        f.write("\n")


def _fmt(v: Any, decimals: int = 2) -> str:
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "—"
    if isinstance(v, float):
        return f"{v:.{decimals}f}"
    return str(v)


def write_report(summary: dict, path: Path, runtime_s: float) -> None:  # noqa: PLR0912, PLR0915
    path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    a = lines.append

    a("# Destatis CPI Energy Price Index Backtest Report")
    a("")
    a("## 1. Dataset Summary")
    a("")
    a("| Property | Value |")
    a("|---|---|")
    a("| Source | Statistisches Bundesamt 61111-0004 |")
    a("| Coverage | 2019-01 to 2025-12 |")
    a("| Observations per series | 84 (no gaps, no duplicates) |")
    a("| Base year | 2020 = 100 |")
    a("| Series | electricity (CC13-0451), gas (CC13-04521), heating_oil (CC13-04530), petrol (CC13-07222) |")
    a("")
    a(
        "> **Note:** These are CPI indices, not household unit prices. "
        "Household price forecasts are derived as: "
        "`future price = current price × forecast index / latest observed index`."
    )
    a("")

    a("## 2. Backtesting Design")
    a("")
    a("| Parameter | Value |")
    a("|---|---|")
    a(f"| Method | Expanding-window rolling origin |")
    a(f"| Minimum training window | {MIN_TRAIN} months |")
    a(f"| Horizons | 1, 3, 6, 12 months |")
    a(f"| Origins (h=1) | up to 24 |")
    a(f"| Origins (h=3) | up to 22 |")
    a(f"| Origins (h=6) | up to 19 |")
    a(f"| Origins (h=12) | up to 13 |")
    a(f"| Primary metric | MAE |")
    a(f"| Simplicity preference | ≤{int(PREFERENCE_THRESHOLD*100)}% MAE above best |")
    a(f"| Runtime | {runtime_s:.0f} s |")
    a("")

    a("## 3. Results by Energy Type and Horizon")
    a("")

    for sid in SERIES_IDS:
        s = summary.get(sid, {})
        models_s = s.get("models", {})

        a(f"### {sid.replace('_', ' ').title()}")
        a("")
        a(
            "| Model | h=1 MAE | h=3 MAE | h=6 MAE | h=12 MAE | "
            "Avg MAE | Avg RMSE | Avg Bias |"
        )
        a("|---|---:|---:|---:|---:|---:|---:|---:|")

        for m in MODEL_NAMES:
            md = models_s.get(m, {})
            bh = md.get("by_horizon", {})
            ov = md.get("overall", {})
            row = [
                m.replace("_", " "),
                _fmt(bh.get("1",  {}).get("mae")),
                _fmt(bh.get("3",  {}).get("mae")),
                _fmt(bh.get("6",  {}).get("mae")),
                _fmt(bh.get("12", {}).get("mae")),
                _fmt(ov.get("mae")),
                _fmt(ov.get("rmse")),
                _fmt(ov.get("bias")),
            ]
            a("| " + " | ".join(row) + " |")
        a("")

    a("## 4. Best Model per Horizon")
    a("")
    a("| Series | h=1 | h=3 | h=6 | h=12 |")
    a("|---|---|---|---|---|")
    for sid in SERIES_IDS:
        bbh = summary.get(sid, {}).get("best_model_by_horizon", {})
        def bm(h: str) -> str:
            entry = bbh.get(h, {})
            if not entry:
                return "—"
            return f"{entry['model'].replace('_',' ')} ({_fmt(entry['mae'])})"
        a(f"| {sid.replace('_',' ').title()} | {bm('1')} | {bm('3')} | {bm('6')} | {bm('12')} |")
    a("")

    a("## 5. Overall Recommendation per Energy Type")
    a("")
    a("| Series | Recommended Model | Avg MAE |")
    a("|---|---|---:|")
    for sid in SERIES_IDS:
        rec = summary.get(sid, {}).get("recommended_model", "—")
        mae = (
            summary.get(sid, {})
            .get("models", {})
            .get(rec, {})
            .get("overall", {})
            .get("mae")
        )
        a(f"| {sid.replace('_',' ').title()} | {rec.replace('_',' ')} | {_fmt(mae)} |")
    a("")

    a("## 6. MAE Improvement over Deterministic Trend")
    a("")
    a(
        "Positive = model beats the deterministic trend; "
        "negative = model is worse. Values in percent."
    )
    a("")
    a("| Series | Model | Overall | h=1 | h=3 | h=6 | h=12 |")
    a("|---|---|---:|---:|---:|---:|---:|")
    for sid in SERIES_IDS:
        for m in [n for n in MODEL_NAMES if n != "deterministic_trend"]:
            md = summary.get(sid, {}).get("models", {}).get(m, {})
            ov_imp = md.get("mae_improvement_vs_det_overall")
            h_imp  = md.get("mae_improvement_vs_det", {})
            a(
                f"| {sid.replace('_',' ').title()} | {m.replace('_',' ')} "
                f"| {_fmt(ov_imp)}% "
                f"| {_fmt(h_imp.get('1'))}% "
                f"| {_fmt(h_imp.get('3'))}% "
                f"| {_fmt(h_imp.get('6'))}% "
                f"| {_fmt(h_imp.get('12'))}% |"
            )
    a("")

    a("## 7. Did ETS or SARIMA Materially Outperform Simpler Baselines?")
    a("")
    for sid in SERIES_IDS:
        mods = summary.get(sid, {}).get("models", {})
        const_mae = mods.get("constant", {}).get("overall", {}).get("mae", float("inf"))
        ets_imp   = mods.get("ets",    {}).get("mae_improvement_vs_det_overall")
        sarima_imp = mods.get("sarima", {}).get("mae_improvement_vs_det_overall")
        ets_mae   = mods.get("ets",    {}).get("overall", {}).get("mae", float("inf"))
        sarima_mae = mods.get("sarima", {}).get("overall", {}).get("mae", float("inf"))

        threshold_pct = PREFERENCE_THRESHOLD * 100
        ets_beats = (
            ets_mae < const_mae * (1 - PREFERENCE_THRESHOLD)
            if const_mae < float("inf") and ets_mae < float("inf")
            else False
        )
        sarima_beats = (
            sarima_mae < const_mae * (1 - PREFERENCE_THRESHOLD)
            if const_mae < float("inf") and sarima_mae < float("inf")
            else False
        )

        label = sid.replace("_", " ").title()
        a(f"**{label}:** ", )
        lines[-1] = lines[-1].rstrip()
        if ets_beats or sarima_beats:
            parts = []
            if ets_beats:
                parts.append(f"ETS improved over constant by >{threshold_pct:.0f}% (imp={_fmt(ets_imp)}%)")
            if sarima_beats:
                parts.append(f"SARIMA improved over constant by >{threshold_pct:.0f}% (imp={_fmt(sarima_imp)}%)")
            lines[-1] += " " + "; ".join(parts) + "."
        else:
            lines[-1] += (
                f" Neither ETS nor SARIMA improved over the constant baseline by "
                f"more than {threshold_pct:.0f}%. Simpler model preferred."
            )
        a("")

    a("")
    a("## 8. Model Failures and Convergence Warnings")
    a("")

    any_fail = False
    for sid in SERIES_IDS:
        failures = summary.get(sid, {}).get("model_failures", {})
        for m, cnt in failures.items():
            if cnt > 0:
                a(f"- **{sid} / {m}**: {cnt} cutoff(s) failed to produce a forecast.")
                any_fail = True
    if not any_fail:
        a("No model-level failures (all cutoffs produced a forecast for all models).")

    a("")
    n_sarima_warn = sum(
        len(v)
        for v in summary.get("sarima_convergence_warnings", {}).values()
    )
    if n_sarima_warn:
        a(
            f"SARIMA candidate-level convergence warnings: "
            f"{n_sarima_warn} instances across all cutoffs. "
            "These are per-candidate failures within a grid search; "
            "a valid best model was still selected in each case."
        )
    else:
        a("No SARIMA convergence warnings recorded.")
    a("")

    top_ets = sorted(
        summary.get("ets_configs_selected", {}).items(),
        key=lambda x: -x[1],
    )[:5]
    top_sarima = sorted(
        summary.get("sarima_configs_selected", {}).items(),
        key=lambda x: -x[1],
    )[:5]

    a("**Most frequently selected ETS configs (across all series × cutoffs):**")
    a("")
    for lbl, cnt in top_ets:
        a(f"- `{lbl}`: {cnt} selections")
    a("")
    a("**Most frequently selected SARIMA configs (across all series × cutoffs):**")
    a("")
    for lbl, cnt in top_sarima:
        a(f"- `{lbl}`: {cnt} selections")
    a("")

    a("## 9. Limitations")
    a("")
    a(
        "1. **Short history.** The dataset spans only seven years (2019–2025). "
        "Backtesting horizons of 12 months use only 13 forecast origins, "
        "which may produce unstable MAE estimates."
    )
    a(
        "2. **Exceptional energy price shock.** The 2021–2023 energy crisis caused "
        "index movements far outside the historical norm. Models that happened to "
        "track this shock well will appear overly favourable; those that did not "
        "will appear overly poor. Results may not generalise to normal market conditions."
    )
    a(
        "3. **No external regressors.** ETS and SARIMA are univariate. "
        "Energy prices are affected by geopolitical events, regulatory changes, "
        "and commodity markets, none of which are captured here."
    )
    a(
        "4. **Index vs price.** These are CPI sub-indices, not household unit prices. "
        "The accuracy of the resulting household price forecasts depends on the "
        "current household price remaining a stable anchor."
    )
    a(
        "5. **SARIMA grid is limited.** The predefined grid covers p∈{0,1,2}, "
        "d∈{0,1}, q∈{0,1}, P∈{0,1}, D∈{0,1}, Q∈{0,1}, m=12. "
        "The true optimal SARIMA specification may lie outside this grid."
    )
    a("")

    path.write_text("\n".join(lines), encoding="utf-8")


# ── Entry point ───────────────────────────────────────────────────────────────


def main() -> None:
    print("Destatis CPI energy price index backtest", flush=True)
    print(f"  CSV: {CSV_PATH}", flush=True)
    print(f"  Min training window: {MIN_TRAIN} months", flush=True)
    print(f"  Horizons: {HORIZONS}", flush=True)
    print("", flush=True)

    t0 = time.perf_counter()

    print("Loading series data …", flush=True)
    series_data = load_series(CSV_PATH)
    for sid, ts in series_data.items():
        print(f"  {sid}: {len(ts)} observations ({ts[0][0]} – {ts[-1][0]})", flush=True)
    print("", flush=True)

    print("Running backtest …", flush=True)
    records, model_failures, config_counts, sarima_warn = run_backtest(series_data)
    print(f"  {len(records)} forecast records generated", flush=True)
    print("", flush=True)

    print("Computing summary metrics …", flush=True)
    summary = compute_summary(records, model_failures, config_counts, sarima_warn)

    runtime_s = time.perf_counter() - t0

    print("Writing outputs …", flush=True)
    write_results_csv(records, RESULTS_CSV)
    print(f"  {RESULTS_CSV}", flush=True)

    write_summary_json(summary, SUMMARY_JSON)
    print(f"  {SUMMARY_JSON}", flush=True)

    write_report(summary, REPORT_MD, runtime_s)
    print(f"  {REPORT_MD}", flush=True)

    print(f"\nDone in {runtime_s:.1f} s", flush=True)

    # ── Console summary ───────────────────────────────────────────────────────
    print("\n=== Results summary ===\n", flush=True)
    for sid in SERIES_IDS:
        s = summary.get(sid, {})
        rec = s.get("recommended_model", "?")
        print(f"{sid.replace('_',' ').title()}:")
        print(f"  Recommended: {rec}")
        bbh = s.get("best_model_by_horizon", {})
        for h in HORIZONS:
            entry = bbh.get(str(h), {})
            if entry:
                print(
                    f"  h={h:2d}: best={entry['model']:<22} MAE={entry['mae']:.3f}"
                )
        # Improvement table
        det_ov_mae = (
            s.get("models", {})
            .get("deterministic_trend", {})
            .get("overall", {})
            .get("mae")
        )
        if det_ov_mae:
            print(f"  Deterministic trend overall MAE: {det_ov_mae:.3f}")
        for m in MODEL_NAMES:
            imp = (
                s.get("models", {})
                .get(m, {})
                .get("mae_improvement_vs_det_overall")
            )
            if imp is not None:
                print(f"  {m:<25} vs det: {imp:+.1f}%")
        # Model failures
        fails = s.get("model_failures", {})
        fail_str = ", ".join(f"{m}={c}" for m, c in fails.items() if c > 0)
        if fail_str:
            print(f"  Failures: {fail_str}")
        print()


if __name__ == "__main__":
    main()
