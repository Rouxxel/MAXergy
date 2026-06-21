# Destatis CPI Energy Price Index Backtest Report

## 1. Dataset Summary

| Property | Value |
|---|---|
| Source | Statistisches Bundesamt 61111-0004 |
| Coverage | 2019-01 to 2025-12 |
| Observations per series | 84 (no gaps, no duplicates) |
| Base year | 2020 = 100 |
| Series | electricity (CC13-0451), gas (CC13-04521), heating_oil (CC13-04530), petrol (CC13-07222) |

> **Note:** These are CPI indices, not household unit prices. Household price forecasts are derived as: `future price = current price × forecast index / latest observed index`.

## 2. Backtesting Design

| Parameter | Value |
|---|---|
| Method | Expanding-window rolling origin |
| Minimum training window | 60 months |
| Horizons | 1, 3, 6, 12 months |
| Origins (h=1) | up to 24 |
| Origins (h=3) | up to 22 |
| Origins (h=6) | up to 19 |
| Origins (h=12) | up to 13 |
| Primary metric | MAE |
| Simplicity preference | ≤10% MAE above best |
| Runtime | 514 s |

## 3. Results by Energy Type and Horizon

### Electricity

| Model | h=1 MAE | h=3 MAE | h=6 MAE | h=12 MAE | Avg MAE | Avg RMSE | Avg Bias |
|---|---:|---:|---:|---:|---:|---:|---:|
| constant | 0.32 | 0.73 | 1.27 | 2.85 | 1.09 | 1.57 | 1.05 |
| deterministic trend | 0.57 | 1.61 | 3.13 | 6.68 | 2.51 | 3.36 | 2.51 |
| ets | 0.87 | 2.02 | 3.50 | 2.51 | 2.11 | 2.98 | 0.45 |
| sarima | 1.31 | 2.96 | 4.72 | 14.30 | 4.77 | 7.75 | 4.29 |

### Gas

| Model | h=1 MAE | h=3 MAE | h=6 MAE | h=12 MAE | Avg MAE | Avg RMSE | Avg Bias |
|---|---:|---:|---:|---:|---:|---:|---:|
| constant | 0.84 | 1.00 | 2.02 | 3.88 | 1.68 | 2.52 | 1.36 |
| deterministic trend | 1.26 | 2.63 | 5.54 | 11.45 | 4.39 | 5.87 | 4.24 |
| ets | 0.84 | 1.47 | 2.41 | 3.55 | 1.85 | 2.52 | -0.59 |
| sarima | 3.96 | 7.54 | 13.76 | 26.97 | 11.19 | 15.96 | 10.57 |

### Heating Oil

| Model | h=1 MAE | h=3 MAE | h=6 MAE | h=12 MAE | Avg MAE | Avg RMSE | Avg Bias |
|---|---:|---:|---:|---:|---:|---:|---:|
| constant | 3.02 | 3.89 | 6.66 | 12.17 | 5.68 | 7.11 | 4.69 |
| deterministic trend | 3.18 | 4.87 | 9.50 | 18.63 | 7.77 | 9.98 | 7.12 |
| ets | 3.00 | 3.92 | 6.73 | 12.26 | 5.71 | 7.14 | 4.77 |
| sarima | 4.29 | 10.26 | 14.60 | 24.87 | 11.92 | 17.87 | 10.66 |

### Petrol

| Model | h=1 MAE | h=3 MAE | h=6 MAE | h=12 MAE | Avg MAE | Avg RMSE | Avg Bias |
|---|---:|---:|---:|---:|---:|---:|---:|
| constant | 2.09 | 4.02 | 4.54 | 4.28 | 3.60 | 4.86 | 1.52 |
| deterministic trend | 2.13 | 4.31 | 5.25 | 7.96 | 4.48 | 6.04 | 3.10 |
| ets | 2.09 | 4.02 | 4.54 | 4.29 | 3.60 | 4.86 | 1.52 |
| sarima | 2.85 | 6.03 | 6.61 | 9.81 | 5.83 | 7.64 | 4.43 |

## 4. Best Model per Horizon

| Series | h=1 | h=3 | h=6 | h=12 |
|---|---|---|---|---|
| Electricity | constant (0.32) | constant (0.73) | constant (1.27) | ets (2.51) |
| Gas | ets (0.84) | constant (1.00) | constant (2.02) | ets (3.55) |
| Heating Oil | ets (3.00) | constant (3.89) | constant (6.66) | constant (12.17) |
| Petrol | constant (2.09) | constant (4.02) | constant (4.54) | constant (4.28) |

## 5. Overall Recommendation per Energy Type

| Series | Recommended Model | Avg MAE |
|---|---|---:|
| Electricity | constant | 1.09 |
| Gas | constant | 1.68 |
| Heating Oil | constant | 5.68 |
| Petrol | constant | 3.60 |

## 6. MAE Improvement over Deterministic Trend

Positive = model beats the deterministic trend; negative = model is worse. Values in percent.

| Series | Model | Overall | h=1 | h=3 | h=6 | h=12 |
|---|---|---:|---:|---:|---:|---:|
| Electricity | constant | 56.53% | 43.28% | 54.69% | 59.52% | 57.30% |
| Electricity | ets | 15.83% | -53.21% | -25.33% | -11.83% | 62.40% |
| Electricity | sarima | -90.33% | -131.27% | -83.19% | -50.76% | -113.98% |
| Gas | constant | 61.80% | 33.79% | 62.01% | 63.62% | 66.15% |
| Gas | ets | 57.85% | 33.98% | 44.12% | 56.46% | 69.04% |
| Gas | sarima | -154.89% | -212.92% | -186.29% | -148.40% | -135.45% |
| Heating Oil | constant | 26.93% | 4.91% | 20.15% | 29.85% | 34.69% |
| Heating Oil | ets | 26.49% | 5.71% | 19.46% | 29.14% | 34.18% |
| Heating Oil | sarima | -53.35% | -34.89% | -110.88% | -53.66% | -33.50% |
| Petrol | constant | 19.64% | 1.89% | 6.73% | 13.42% | 46.20% |
| Petrol | ets | 19.63% | 1.88% | 6.73% | 13.42% | 46.19% |
| Petrol | sarima | -30.17% | -33.96% | -40.07% | -26.05% | -23.19% |

## 7. Did ETS or SARIMA Materially Outperform Simpler Baselines?

**Electricity:** Neither ETS nor SARIMA improved over the constant baseline by more than 10%. Simpler model preferred.

**Gas:** Neither ETS nor SARIMA improved over the constant baseline by more than 10%. Simpler model preferred.

**Heating Oil:** Neither ETS nor SARIMA improved over the constant baseline by more than 10%. Simpler model preferred.

**Petrol:** Neither ETS nor SARIMA improved over the constant baseline by more than 10%. Simpler model preferred.


## 8. Model Failures and Convergence Warnings

No model-level failures (all cutoffs produced a forecast for all models).

SARIMA candidate-level convergence warnings: 25 instances across all cutoffs. These are per-candidate failures within a grid search; a valid best model was still selected in each case.

**Most frequently selected ETS configs (across all series × cutoffs):**

- `N,N`: 48 selections
- `Ad,N`: 35 selections
- `Ad,A`: 13 selections

**Most frequently selected SARIMA configs (across all series × cutoffs):**

- `(0,1,1)x(0,1,1)[12]`: 83 selections
- `(2,1,0)x(1,1,0)[12]`: 8 selections
- `(0,1,1)x(1,1,1)[12]`: 5 selections

## 9. Limitations

1. **Short history.** The dataset spans only seven years (2019–2025). Backtesting horizons of 12 months use only 13 forecast origins, which may produce unstable MAE estimates.
2. **Exceptional energy price shock.** The 2021–2023 energy crisis caused index movements far outside the historical norm. Models that happened to track this shock well will appear overly favourable; those that did not will appear overly poor. Results may not generalise to normal market conditions.
3. **No external regressors.** ETS and SARIMA are univariate. Energy prices are affected by geopolitical events, regulatory changes, and commodity markets, none of which are captured here.
4. **Index vs price.** These are CPI sub-indices, not household unit prices. The accuracy of the resulting household price forecasts depends on the current household price remaining a stable anchor.
5. **SARIMA grid is limited.** The predefined grid covers p∈{0,1,2}, d∈{0,1}, q∈{0,1}, P∈{0,1}, D∈{0,1}, Q∈{0,1}, m=12. The true optimal SARIMA specification may lie outside this grid.
