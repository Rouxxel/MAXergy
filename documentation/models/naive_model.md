# Naive Model (Baseline Energy-Savings Forecast)

**Script:** `scripts/run_baseline_model.py`
**Input:** `documentation/data/model_input1.json`
**Output:** `documentation/data/model_output_1.json`

## Purpose

Produces a deterministic, non-hourly estimate of monthly and annual energy costs for a household's current setup (baseline) and up to 6 solar-led upgrade scenarios. Designed as a fast, always-runnable first pass; every constant is a clearly marked placeholder so the model can be upgraded incrementally without touching the output schema.

## Method

### Baseline

Monthly cost = electricity (annual kWh × tariff + Grundpreis) + heating (annual spend ÷ 12) + mobility (annual fuel spend ÷ 12). Fallback fuel prices are used if spend fields are absent.

### Scenario generation

Scenarios are generated for every combination present in `upgrade_candidates` that includes solar PV. Six combos are covered: `solar_only`, `pv_battery`, `pv_heatpump`, `pv_ev`, `pv_battery_heatpump`, `full_upgrade`.

### Solar generation

```
solar_pv_kwp  = min(usable_area_m2 / 7, 10)   # auto-sized if not overridden
annual_gen    = solar_pv_kwp × 1000 kWh/kWp   # Germany-average specific yield
```

### Self-consumption (lookup table — core simplification)

| Combo | Ratio |
|---|---|
| Solar only | 0.30 |
| Solar + battery | 0.65 |
| Solar + heat pump | 0.45 |
| Solar + EV | 0.40 |
| Solar + battery + heat pump | 0.75 |
| Solar + battery + heat pump + EV | 0.80 |

### Electricity cost under a scenario

```
grid_import  = max(household_load + hp_load + ev_load − self_consumed, 0)
elec_cost    = grid_import × arbeitspreis + grundpreis × 12
             − exported × 0.082 €/kWh (feed-in)
```

### Heat pump load

```
heating_demand_kwh / COP (3.3)   →  HP load in kWh; heating cost = 0
```

### EV load

```
annual_mileage / 100 × 18 kWh/100 km × arbeitspreis × 0.7 (off-peak discount)
```

### Financing

Standard amortizing loan on `(system_cost − subsidy)` at the input rate and term. Subsidy defaults to 30 % of system cost if not provided. Equipment cost placeholders: solar 1 400 €/kWp, battery 700 €/kWh, heat pump 12 000 €, EV charger 1 200 €.

### Forecasts

**Short-term (12 months):** Flat electricity and mobility; heating multiplied by normalized seasonal weights (Jan 1.45 → Jul 0.62 → Dec 1.45).

**Long-term (20 years):** Annual escalation applied to each cost bucket — electricity 3 %, gas/oil 4 %, fuel 3 %. Financing installment stays flat for the loan term, then drops to 0.

## Output schema (top-level keys)

```
{
  "baseline": {
    "monthly_cost_eur": { electricity, heating, mobility, total },
    "short_term_forecast": [ { month, total_eur } × 12 ],
    "long_term_forecast":  [ { year, annual_total_eur } × 20 ]
  },
  "scenarios": [
    {
      "id", "components", "sizing",
      "monthly_cost_eur": { electricity, heating, mobility, financing_installment, total },
      "monthly_saving_eur",
      "monthly_saving_post_payoff_eur",   // only present when monthly_saving_eur < 0
      "self_consumption_ratio",
      "short_term_forecast": [ { month, total_eur, saving_eur } × 12 ],
      "long_term_forecast":  [ { year, annual_total_eur, annual_saving_eur } × 20 ],
      "payback_month"                     // null if not within loan term
    }
  ]
}
```

## Limitations & upgrade path

All constants at the top of the script are marked `# placeholder`. Priority replacements:

| Constant | Replace with |
|---|---|
| `SPECIFIC_YIELD_KWH_PER_KWP` | Postcode-based yield API (e.g. PVGIS) |
| `SELF_CONSUMPTION_RATIOS` | Hourly dispatch simulation |
| `COP` | Building-specific heat load model |
| `FEED_IN_TARIFF_EUR_PER_KWH` | Real EEG tariff by registration date |
| Escalation rates | Macro energy price model |
