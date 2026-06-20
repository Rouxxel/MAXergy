# Naive Model (Baseline Energy-Savings Forecast)

**Script:** `scripts/run_baseline_model.py`
**Input:** `documentation/data/model_input1.json`
**Output:** `documentation/data/model_output_1.json`

summary:

# Baseline Model Summary — MAXergy Modelling Layer

Non-hourly, lookup-table-based deterministic model. No simulation, no fitting —
closed-form formulas and fixed constants throughout.

## Input variables and processing

| Input variable | Used for | Formula / treatment |
|---|---|---|
| `electricity.annual_kwh`, `arbeitspreis`, `grundpreis` | Baseline electricity cost | `annual_kwh × arbeitspreis + grundpreis × 12` |
| `heating.annual_consumption`, `fuel_type`, `annual_spend_eur` | Baseline heating cost | Uses `annual_spend_eur` if given; else `consumption × fallback_price` (gas €0.10/kWh, oil €1.05/L) |
| `mobility.annual_mileage_km`, `fuel_consumption_l_per_100km`, `annual_fuel_spend_eur` | Baseline mobility cost | Uses spend if given; else `mileage/100 × L/100km × €1.75/L` |
| `roof.usable_area_m2`, `upgrade_candidates.solar_pv_kwp` | Solar sizing | `kWp = min(area / 7, 10)` unless overridden; `generation = kWp × 1000 kWh/kWp` |
| Active component combo (`solar_pv`, `battery`, `heat_pump`, `ev_charger`) | Self-consumption ratio (SCR) | **Fixed lookup table** (0.30 → 0.80) — not calculated |
| `heating.annual_consumption`, `fuel_type` | Heat pump electric load | `heating_demand_kWh / COP (3.3)` (oil converted via 10 kWh/L) |
| `mobility.annual_mileage_km` | EV electric load | `mileage / 100 × 18 kWh/100km` |
| `financing.loan_rate_pct`, `loan_term_years`, `known_subsidy_eur` | Monthly installment | Standard amortizing loan formula on `(system_cost − subsidy)`; subsidy defaults to 30% of cost if unknown |
| Escalation constants (3–4%/yr) | Long-term forecast | Compound each cost bucket annually: `cost × (1 + rate)^year_index` |
| Seasonal weight table (Jan–Dec) | Short-term forecast | Heating (and HP electricity) cost scaled by a fixed monthly multiplier, normalized to average 1.0 |

## Core formula per scenario

```
grid_import      = max(load − generation × SCR, 0)
electricity_cost = grid_import × arbeitspreis + grundpreis × 12 − export × feed_in_tariff
monthly_saving   = baseline_total − (scenario_total + financing_installment)
```

## Modeling upgrade priority

**Highest-value targets (most hand-waved today):**

1. **Self-consumption ratio** — flat lookup table (0.30/0.65/0.75/0.80). The biggest
   simplification in the model; an hourly dispatch simulation (load vs. PV generation
   vs. battery state-of-charge) would most improve this. Directly tied to the
   challenge's "savings certainty" criterion.
2. **Solar generation yield** — flat 1000 kWh/kWp regardless of postcode. Upgrade:
   PVGIS lookup by lat/long + roof orientation/tilt/shading → real generation curve.
3. **Electricity price (arbeitspreis, feed-in tariff)** — flat constants today. Upgrade:
   actual dynamic tariff (EPEX day-ahead) hourly curve — needed for battery/EV
   "charge cheap, discharge expensive" logic to mean anything beyond a flat 0.7 discount factor.
4. **Escalation rates** — flat 3–4%/yr placeholder. Upgrade: regression on historical
   price index (Destatis/BDEW) or futures curve extrapolation.

**Fine to keep deterministic (low payoff or genuinely stable facts):**

- **Heat pump COP** — fixed seasonal-average constant is industry-standard for
  first-pass estimates; diminishing returns without real building data.
- **Equipment costs** — roughly fixed market prices; keep as an updatable price
  table, possibly region-adjusted, rather than "modeled."
- **EV efficiency (kWh/100km)** — fine as a constant unless asking for specific EV model.
- **Financing/amortization formula** — already exact, nothing to improve.
- **Subsidy fraction default** — better as a postcode/program rule lookup
  (German subsidies are rule-based, not statistical) — a data-sourcing
  task, not a modeling one.

**Suggested priority if time-constrained:** self-consumption ratio (dispatch
simulation) → solar generation (PVGIS) → dynamic price curve (EPEX) → escalation
rates.



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
