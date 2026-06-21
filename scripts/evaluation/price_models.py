"""
Four CPI index forecasting models for expanding-window backtesting.

Each model exposes a consistent interface:
    model.fit(train: list[float]) -> self
    model.forecast(horizon: int) -> list[float]   # length == horizon

Models are intentionally stateless between fit() calls so they can be
re-instantiated cheaply inside a backtesting loop.
"""

from __future__ import annotations

import warnings
from itertools import product
from typing import Any

import numpy as np

# ── Production growth assumptions ─────────────────────────────────────────────

ANNUAL_GROWTH_RATES: dict[str, float] = {
    "electricity": 0.03,
    "gas":         0.04,
    "heating_oil": 0.04,
    "petrol":      0.03,
}

# ── ETS candidate set ─────────────────────────────────────────────────────────
# Each entry is passed directly to statsmodels ExponentialSmoothing.
# Damping is only relevant when trend is set, so damped_trend=False when
# trend=None (no-op, but harmless).

ETS_CANDIDATES: list[dict[str, Any]] = [
    {"trend": None,  "seasonal": None,  "damped_trend": False, "label": "N,N"},
    {"trend": "add", "seasonal": None,  "damped_trend": False, "label": "A,N"},
    {"trend": "add", "seasonal": None,  "damped_trend": True,  "label": "Ad,N"},
    {"trend": None,  "seasonal": "add", "damped_trend": False, "label": "N,A"},
    {"trend": "add", "seasonal": "add", "damped_trend": False, "label": "A,A"},
    {"trend": "add", "seasonal": "add", "damped_trend": True,  "label": "Ad,A"},
]

SEASONAL_PERIOD = 12

# ── SARIMA candidate grid ─────────────────────────────────────────────────────
# p ∈ {0,1,2}, d ∈ {0,1}, q ∈ {0,1}, P ∈ {0,1}, D ∈ {0,1}, Q ∈ {0,1}
# Exclude the degenerate all-zero case.

SARIMA_CANDIDATES: list[tuple[int, int, int, int, int, int]] = [
    (p, d, q, P, D, Q)
    for p, d, q, P, D, Q in product([0, 1, 2], [0, 1], [0, 1], [0, 1], [0, 1], [0, 1])
    if not (p == 0 and d == 0 and q == 0 and P == 0 and D == 0 and Q == 0)
]


# ── Exceptions ─────────────────────────────────────────────────────────────────


class ForecastError(Exception):
    """Raised when a model cannot produce a valid forecast."""


# ── Model classes ──────────────────────────────────────────────────────────────


class ConstantModel:
    """Forecast every future period as the last observed value."""

    def __init__(self) -> None:
        self._last: float | None = None
        self.params: dict[str, Any] = {}

    def fit(self, train: list[float]) -> "ConstantModel":
        if not train:
            raise ForecastError("ConstantModel: empty training series")
        self._last = float(train[-1])
        self.params = {"last_value": self._last}
        return self

    def forecast(self, horizon: int) -> list[float]:
        if self._last is None:
            raise ForecastError("ConstantModel: call fit() before forecast()")
        return [self._last] * horizon


class DeterministicTrendModel:
    """
    Compounded monthly growth derived from production annual assumptions.

    forecast[h] = last_observed × (1 + monthly_rate)^h   for h = 1, 2, …
    """

    def __init__(self, series_id: str) -> None:
        annual = ANNUAL_GROWTH_RATES.get(series_id, 0.03)
        self._monthly = (1.0 + annual) ** (1.0 / 12.0) - 1.0
        self._last: float | None = None
        self.params: dict[str, Any] = {
            "series_id": series_id,
            "annual_rate": annual,
            "monthly_rate": round(self._monthly, 10),
        }

    def fit(self, train: list[float]) -> "DeterministicTrendModel":
        if not train:
            raise ForecastError("DeterministicTrendModel: empty training series")
        self._last = float(train[-1])
        self.params["last_value"] = self._last
        return self

    def forecast(self, horizon: int) -> list[float]:
        if self._last is None:
            raise ForecastError("DeterministicTrendModel: call fit() before forecast()")
        r = self._monthly
        return [self._last * (1.0 + r) ** h for h in range(1, horizon + 1)]


class ETSModel:
    """
    Exponential Smoothing with AIC-based selection over a fixed candidate set.

    Candidate selection uses only training-data AIC; no test observations
    are seen during model selection.
    """

    def __init__(self) -> None:
        self._fitted: Any = None
        self.params: dict[str, Any] = {}
        self.aic: float = float("inf")
        self.fit_failures: list[str] = []

    def fit(self, train: list[float]) -> "ETSModel":
        from statsmodels.tsa.holtwinters import ExponentialSmoothing  # noqa: PLC0415

        arr = np.array(train, dtype=float)
        best_aic = float("inf")
        best_fitted = None
        best_label: str | None = None

        for cand in ETS_CANDIDATES:
            label = cand["label"]
            try:
                kwargs: dict[str, Any] = {
                    "endog": arr,
                    "trend": cand["trend"],
                    "seasonal": cand["seasonal"],
                    "initialization_method": "estimated",
                }
                if cand["seasonal"] is not None:
                    kwargs["seasonal_periods"] = SEASONAL_PERIOD
                if cand["trend"] is not None:
                    kwargs["damped_trend"] = cand["damped_trend"]

                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    m = ExponentialSmoothing(**kwargs).fit(optimized=True)

                if np.isfinite(m.aic) and m.aic < best_aic:
                    best_aic = m.aic
                    best_fitted = m
                    best_label = label

            except Exception as exc:
                self.fit_failures.append(
                    f"{label}: {type(exc).__name__}: {str(exc)[:100]}"
                )

        if best_fitted is None:
            raise ForecastError(
                f"ETSModel: all candidates failed — {self.fit_failures}"
            )

        self._fitted = best_fitted
        self.aic = best_aic
        self.params = {
            "selected_config": best_label,
            "aic": round(best_aic, 4),
            "n_failures": len(self.fit_failures),
        }
        return self

    def forecast(self, horizon: int) -> list[float]:
        if self._fitted is None:
            raise ForecastError("ETSModel: call fit() before forecast()")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fc = self._fitted.forecast(horizon)
        return [float(v) for v in fc]


class SARIMAModel:
    """
    SARIMA with AIC-based grid search over the predefined parameter set.

    Grid: p∈{0,1,2}, d∈{0,1}, q∈{0,1}, P∈{0,1}, D∈{0,1}, Q∈{0,1}, m=12.
    maxiter=50 with L-BFGS-B keeps individual fits fast.
    All convergence failures are caught and logged.
    """

    def __init__(self) -> None:
        self._fitted: Any = None
        self.params: dict[str, Any] = {}
        self.aic: float = float("inf")
        self.fit_failures: list[tuple[str, str]] = []

    def fit(self, train: list[float]) -> "SARIMAModel":
        from statsmodels.tsa.statespace.sarimax import SARIMAX  # noqa: PLC0415

        arr = np.array(train, dtype=float)
        best_aic = float("inf")
        best_fitted = None
        best_order: tuple[int, ...] | None = None

        # Compute plausible forecast bounds from training data.
        # Reject any model whose 12-step ahead forecast falls outside this window.
        train_min, train_max = float(arr.min()), float(arr.max())
        lo = max(0.0, train_min * 0.3)
        hi = train_max * 5.0

        for p, d, q, P, D, Q in SARIMA_CANDIDATES:
            lbl = f"({p},{d},{q})x({P},{D},{Q})[12]"
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    trend_term = "c" if (d == 0 and D == 0) else "n"
                    m = SARIMAX(
                        endog=arr,
                        order=(p, d, q),
                        seasonal_order=(P, D, Q, SEASONAL_PERIOD),
                        enforce_stationarity=False,
                        enforce_invertibility=False,
                        trend=trend_term,
                    ).fit(disp=False, maxiter=50, method="lbfgs")

                if not np.isfinite(m.aic):
                    self.fit_failures.append((lbl, "non-finite AIC"))
                    continue

                # Check 12-step forecast is in plausible range before accepting
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    test_fc = m.forecast(steps=12)
                if not all(np.isfinite(v) and lo <= v <= hi for v in test_fc):
                    self.fit_failures.append((lbl, "explosive 12-step forecast"))
                    continue

                if m.aic < best_aic:
                    best_aic = m.aic
                    best_fitted = m
                    best_order = (p, d, q, P, D, Q)

            except Exception as exc:
                self.fit_failures.append(
                    (lbl, f"{type(exc).__name__}: {str(exc)[:80]}")
                )

        if best_fitted is None:
            raise ForecastError(
                f"SARIMAModel: all {len(SARIMA_CANDIDATES)} candidates failed"
            )

        p, d, q, P, D, Q = best_order  # type: ignore[misc]
        self._fitted = best_fitted
        self.aic = best_aic
        self.params = {
            "order": [p, d, q],
            "seasonal_order": [P, D, Q, SEASONAL_PERIOD],
            "label": f"({p},{d},{q})x({P},{D},{Q})[12]",
            "aic": round(best_aic, 4),
            "n_failures": len(self.fit_failures),
        }
        return self

    def forecast(self, horizon: int) -> list[float]:
        if self._fitted is None:
            raise ForecastError("SARIMAModel: call fit() before forecast()")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            fc = self._fitted.forecast(steps=horizon)
        result = [float(v) for v in fc]
        # Final guard: catch any remaining non-finite values from multi-step extrapolation
        for v in result:
            if not np.isfinite(v):
                raise ForecastError(
                    f"SARIMAModel: non-finite forecast value from {self.params.get('label')}"
                )
        return result
