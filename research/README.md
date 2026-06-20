# MAXergy Research Area

This directory contains experimental work, backtesting results, and legacy scripts
that are **not part of the production pipeline**.  Nothing here is imported by the
production code in `scripts/energy_model/`.

## Directory structure

```
research/
  price_forecasting/      Backtesting of energy price models against Destatis data
  evaluation_outputs/     Results from the backtests (CSV, JSON, Markdown reports)
  datasets/               Raw Destatis price data
  legacy/                 Old CLI scripts superseded by scripts/run_model.py
  tests/                  Tests for research code (not run in production CI)
```

## Price model selection

We backtested four models against Destatis energy price indices (2019–2025):

| Model              | Description                                      |
|--------------------|--------------------------------------------------|
| ConstantModel      | Forecast = last observed value                   |
| DeterministicTrend | Constant annual growth rate per scenario         |
| ETSModel           | Exponential smoothing (statsmodels)              |
| SARIMAModel        | Seasonal ARIMA (statsmodels)                     |

**Outcome**: The `ConstantModel` achieved the lowest RMSPE across all four energy
carriers (electricity, gas, heating_oil, petrol) on a rolling-origin backtest
with a 12-month horizon.

**Production decision**: `ConstantShortTermPriceModel` in `scripts/energy_model/price_models.py`
uses zero trend for the short-term (≤24 months) forecast.  The long-term projection
continues to use `ScenarioPriceModel` (low/central/high trend bands) because the
backtesting window (6 years) is too short to validate 20-year structural assumptions.

See `evaluation_outputs/backtest_report.md` and `evaluation_outputs/rmspe_report.md`
for full results.

## Legacy scripts

| File                             | Superseded by              |
|----------------------------------|----------------------------|
| `legacy/run_energy_cost_forecast.py` | `energy_model/pipeline.py` |
| `legacy/run_upgrade_comparison.py`   | `scripts/run_model.py`     |
| `legacy/run_baseline_model.py`       | (baseline now part of full model) |
| `legacy/visualize_forecast.py`       | (not yet replaced)         |
| `legacy/visualize_forecasting_accuracy.py` | (not yet replaced)   |

## Running research tests

Research tests are not run automatically with `pytest tests/`.  To run them:

```bash
cd /path/to/MAXergy
python -m pytest research/tests/ -v
```

Note: some research tests require `statsmodels` and the Destatis CSV file at
`research/datasets/61111-0004_de.csv`.
