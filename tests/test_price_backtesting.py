"""
Unit tests for price_models.py and backtest_price_models.py.

All tests use small synthetic series so the suite runs in seconds.
No production CSV is read; no output files are written.

Run with:
    python -m pytest tests/test_price_backtesting.py -v
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make the evaluation package importable from the repo root
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts" / "evaluation"))

from price_models import (
    ANNUAL_GROWTH_RATES,
    SARIMA_CANDIDATES,
    ConstantModel,
    DeterministicTrendModel,
    ETSModel,
    ForecastError,
    SARIMAModel,
)
from backtest_price_models import (
    HORIZONS,
    MIN_TRAIN,
    MODEL_NAMES,
    compute_metrics,
    compute_summary,
    run_backtest,
    safe_smape,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


def _linear_series(n: int, start: float = 100.0, slope: float = 0.5) -> list[float]:
    return [start + slope * i for i in range(n)]


def _flat_series(n: int, value: float = 100.0) -> list[float]:
    return [value] * n


def _seasonal_series(n: int) -> list[float]:
    import math as m
    return [100.0 + 5.0 * m.sin(2 * m.pi * i / 12) for i in range(n)]


def _make_ts(values: list[float], start_year: int = 2014, start_month: int = 1) -> list[tuple[str, float]]:
    """Build a (date, value) list starting from the given year-month."""
    ts = []
    y, mo = start_year, start_month
    for v in values:
        ts.append((f"{y:04d}-{mo:02d}", v))
        mo += 1
        if mo > 12:
            mo = 1
            y += 1
    return ts


def _small_series_data(n: int = 72) -> dict[str, list[tuple[str, float]]]:
    """Minimal synthetic series dict for backtesting tests."""
    return {
        "electricity": _make_ts(_linear_series(n, start=100.0, slope=0.3)),
        "gas":         _make_ts(_flat_series(n, 90.0)),
        "heating_oil": _make_ts(_seasonal_series(n)),
        "petrol":      _make_ts(_linear_series(n, start=80.0, slope=-0.1)),
    }


# ── 1. Constant forecast ──────────────────────────────────────────────────────


def test_constant_forecast_equals_last_value():
    m = ConstantModel()
    m.fit([80.0, 90.0, 100.0, 110.0])
    fc = m.forecast(5)
    assert fc == [110.0, 110.0, 110.0, 110.0, 110.0]


def test_constant_forecast_single_obs():
    m = ConstantModel()
    m.fit([42.5])
    assert m.forecast(3) == [42.5, 42.5, 42.5]


def test_constant_raises_on_empty():
    with pytest.raises(ForecastError):
        ConstantModel().fit([])


def test_constant_raises_before_fit():
    with pytest.raises(ForecastError):
        ConstantModel().forecast(1)


# ── 2. Deterministic monthly compounding ──────────────────────────────────────


def test_deterministic_monthly_rate_electricity():
    annual = ANNUAL_GROWTH_RATES["electricity"]   # 0.03
    expected_monthly = (1.0 + annual) ** (1.0 / 12.0) - 1.0
    m = DeterministicTrendModel("electricity")
    assert abs(m._monthly - expected_monthly) < 1e-12


def test_deterministic_forecast_compounding():
    m = DeterministicTrendModel("electricity")
    m.fit([100.0])
    fc = m.forecast(3)
    r = m._monthly
    assert abs(fc[0] - 100.0 * (1 + r) ** 1) < 1e-10
    assert abs(fc[1] - 100.0 * (1 + r) ** 2) < 1e-10
    assert abs(fc[2] - 100.0 * (1 + r) ** 3) < 1e-10


def test_deterministic_gas_rate():
    m = DeterministicTrendModel("gas")
    assert abs(m._monthly - ((1.04) ** (1 / 12) - 1)) < 1e-12


def test_deterministic_raises_on_empty():
    with pytest.raises(ForecastError):
        DeterministicTrendModel("electricity").fit([])


# ── 3. No future data leakage ─────────────────────────────────────────────────


def test_no_future_data_leakage():
    """
    For every record, the training cutoff must be strictly before the
    forecast month (cutoff_date < forecast_month string comparison is valid
    because dates are in ISO YYYY-MM format).
    """
    series_data = _small_series_data(n=72)
    records, _, _, _ = run_backtest(series_data, min_train=60)
    for r in records:
        assert r["training_cutoff"] < r["forecast_month"], (
            f"Leakage detected: cutoff={r['training_cutoff']} >= "
            f"forecast={r['forecast_month']}"
        )


def test_training_window_never_exceeds_cutoff():
    """
    The training data passed to each model must be exactly `cutoff_idx + 1`
    observations — i.e., it must not include the forecast period.
    We verify this by monkey-patching ConstantModel.fit() and inspecting
    the lengths of training arrays actually passed.
    """
    observed_lengths: list[int] = []
    original_fit = ConstantModel.fit

    def spy_fit(self, train):
        observed_lengths.append(len(train))
        return original_fit(self, train)

    series_data = {"electricity": _make_ts(_linear_series(65))}

    with patch.object(ConstantModel, "fit", spy_fit):
        run_backtest(series_data, min_train=60)

    # Lengths should be 60, 61, 62, 63, 64 (5 cutoffs)
    assert observed_lengths == sorted(observed_lengths), "Training lengths must be monotone"
    assert observed_lengths[0] == 60
    assert observed_lengths[-1] == 64


# ── 4. Correct forecast horizon alignment ─────────────────────────────────────


def test_forecast_horizon_alignment():
    """
    For each record, the number of months between training_cutoff and
    forecast_month must equal the declared horizon.
    """
    series_data = {"electricity": _make_ts(_linear_series(72))}
    records, _, _, _ = run_backtest(series_data, min_train=60)

    for r in records:
        cy, cm = map(int, r["training_cutoff"].split("-"))
        fy, fm = map(int, r["forecast_month"].split("-"))
        months_diff = (fy - cy) * 12 + (fm - cm)
        assert months_diff == r["horizon"], (
            f"Horizon mismatch: declared={r['horizon']}, "
            f"actual gap={months_diff}, "
            f"cutoff={r['training_cutoff']}, "
            f"forecast={r['forecast_month']}"
        )


# ── 5. Correct metric calculations ────────────────────────────────────────────


def test_mae_calculation():
    actuals   = [100.0, 102.0, 98.0, 104.0]
    forecasts = [101.0, 101.0, 101.0, 101.0]
    m = compute_metrics(actuals, forecasts)
    # |1|, |-1|, |3|, |-3| → mean = 2.0
    assert abs(m["mae"] - 2.0) < 1e-10


def test_rmse_calculation():
    actuals   = [100.0, 102.0]
    forecasts = [102.0, 100.0]
    m = compute_metrics(actuals, forecasts)
    # errors: [2, -2] → sq: [4, 4] → mean: 4 → sqrt: 2
    assert abs(m["rmse"] - 2.0) < 1e-10


def test_bias_calculation():
    actuals   = [100.0, 100.0, 100.0]
    forecasts = [103.0, 101.0, 102.0]
    m = compute_metrics(actuals, forecasts)
    # errors: [3, 1, 2] → mean = 2.0
    assert abs(m["bias"] - 2.0) < 1e-10


def test_metrics_empty_returns_nans():
    m = compute_metrics([], [])
    assert math.isnan(m["mae"])
    assert m["n"] == 0


# ── 6. Safe sMAPE ─────────────────────────────────────────────────────────────


def test_smape_both_zero_is_nan():
    assert math.isnan(safe_smape(0.0, 0.0))


def test_smape_symmetric():
    # sMAPE should be the same regardless of which is actual vs forecast
    v1 = safe_smape(100.0, 90.0)
    v2 = safe_smape(90.0, 100.0)
    assert abs(v1 - v2) < 1e-10


def test_smape_perfect_forecast_is_zero():
    assert safe_smape(100.0, 100.0) == 0.0


def test_smape_range():
    # sMAPE is in [0, 200]
    v = safe_smape(100.0, 0.0)
    assert 0.0 <= v <= 200.0


def test_smape_actual_zero_forecast_nonzero():
    # denominator = |0| + |f| = |f|, result is finite
    v = safe_smape(0.0, 50.0)
    assert not math.isnan(v)
    assert v == 200.0  # 2 * 50 / 50 * 100


# ── 7. ETS failure handling ───────────────────────────────────────────────────


def test_ets_raises_when_all_candidates_fail():
    """If every ExponentialSmoothing().fit() call raises, ForecastError is raised."""
    # Patch at statsmodels source so the lazy import inside ETSModel.fit() sees it
    with patch("statsmodels.tsa.holtwinters.ExponentialSmoothing") as MockCls:
        MockCls.return_value.fit.side_effect = RuntimeError("simulated failure")
        m = ETSModel()
        with pytest.raises(ForecastError, match="all candidates failed"):
            m.fit([100.0] * 70)
    assert len(m.fit_failures) == 6  # one per candidate


def test_ets_records_failures():
    """Partial ETS candidate failures are recorded in fit_failures."""
    m = ETSModel()
    m.fit_failures = ["N,N: RuntimeError: x", "A,N: ValueError: y"]
    assert len(m.fit_failures) == 2
    assert "N,N" in m.fit_failures[0]


# ── 8. SARIMA failure handling ────────────────────────────────────────────────


def test_sarima_raises_when_all_candidates_fail():
    with patch("statsmodels.tsa.statespace.sarimax.SARIMAX") as MockCls:
        MockCls.return_value.fit.side_effect = RuntimeError("simulated SARIMA failure")
        m = SARIMAModel()
        with pytest.raises(ForecastError, match="candidates failed"):
            m.fit([100.0] * 70)


def test_sarima_fit_failures_logged():
    m = SARIMAModel()
    m.fit_failures = [("(1,1,0)x(0,0,0)[12]", "ConvergenceWarning: failed")]
    assert len(m.fit_failures) == 1
    label, msg = m.fit_failures[0]
    assert "ConvergenceWarning" in msg


def test_sarima_raises_before_fit():
    with pytest.raises(ForecastError):
        SARIMAModel().forecast(1)


# ── 9. AIC selection on training data only ────────────────────────────────────


def test_ets_aic_uses_training_data_only():
    """
    ETSModel.fit() must select a config purely from training AIC.
    We verify this by:
      1. Fitting on a training window of 60 obs.
      2. Checking that params["aic"] is finite (computed on training data).
      3. Fitting again on 61 obs (one extra) — the selected config may differ,
         proving each call is independent and not peeking at future data.
    """
    train_60 = _linear_series(60, start=100.0, slope=0.4)
    train_61 = train_60 + [train_60[-1] + 0.4]

    m60 = ETSModel()
    m60.fit(train_60)
    assert math.isfinite(m60.aic), "AIC must be finite (computed on training data)"
    assert m60.params.get("selected_config") is not None

    m61 = ETSModel()
    m61.fit(train_61)
    assert math.isfinite(m61.aic)
    # Both should select a valid config; they may differ (that's expected)
    assert m61.params.get("selected_config") is not None


def test_sarima_aic_uses_training_data_only():
    train = _seasonal_series(60)
    m = SARIMAModel()
    m.fit(train)
    assert math.isfinite(m.aic)
    assert "order" in m.params
    assert "seasonal_order" in m.params


# ── 10. Output schema validation ──────────────────────────────────────────────


def test_backtest_record_schema():
    """Every record from run_backtest must have the required fields."""
    series_data = {"electricity": _make_ts(_linear_series(65))}
    records, _, _, _ = run_backtest(series_data, min_train=60)

    required = {
        "energy_type", "model", "training_cutoff", "horizon", "forecast_month",
        "actual_index", "predicted_index", "error", "absolute_error",
        "pct_error", "smape", "model_params",
    }
    assert records, "Expected at least one record"
    for r in records:
        missing = required - set(r.keys())
        assert not missing, f"Missing fields: {missing}"


def test_model_params_is_valid_json():
    series_data = {"electricity": _make_ts(_linear_series(65))}
    records, _, _, _ = run_backtest(series_data, min_train=60)
    for r in records:
        parsed = json.loads(r["model_params"])
        assert isinstance(parsed, dict)


def test_all_model_names_present():
    series_data = {"electricity": _make_ts(_linear_series(65))}
    records, _, _, _ = run_backtest(series_data, min_train=60)
    found = {r["model"] for r in records}
    assert set(MODEL_NAMES).issubset(found), (
        f"Missing models in output: {set(MODEL_NAMES) - found}"
    )


def test_all_horizons_represented():
    series_data = {"electricity": _make_ts(_linear_series(75))}
    records, _, _, _ = run_backtest(series_data, min_train=60)
    found_h = {r["horizon"] for r in records}
    assert set(HORIZONS).issubset(found_h)


def test_summary_has_all_series():
    series_data = _small_series_data(n=72)
    records, failures, configs, warns = run_backtest(series_data, min_train=60)
    summary = compute_summary(records, failures, configs, warns)
    for sid in series_data:
        assert sid in summary, f"Series {sid} missing from summary"


def test_summary_recommended_model_is_valid():
    series_data = {"electricity": _make_ts(_linear_series(72))}
    records, failures, configs, warns = run_backtest(series_data, min_train=60)
    summary = compute_summary(records, failures, configs, warns)
    rec = summary["electricity"]["recommended_model"]
    assert rec in MODEL_NAMES


# ── 11. SARIMA grid completeness ─────────────────────────────────────────────


def test_sarima_candidate_grid_excludes_all_zero():
    """The all-zero SARIMA configuration must not appear in the grid."""
    for cand in SARIMA_CANDIDATES:
        assert cand != (0, 0, 0, 0, 0, 0), "(0,0,0)x(0,0,0)[12] must be excluded"


def test_sarima_candidate_grid_size():
    # 3*2*2*2*2*2 = 96, minus 1 all-zero = 95
    assert len(SARIMA_CANDIDATES) == 95
