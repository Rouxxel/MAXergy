# energy_model — Production Modelling Package

German residential energy cost forecasting and home upgrade comparison.

---

## Purpose

Given a household's current energy use and property details, this package produces:

- **Baseline forecast** — what you pay doing nothing (short-term constant prices, long-term trend scenarios)
- **Upgrade scenarios** — how much each combination of PV / battery / heat pump / EV saves over time
- **Financing analysis** — monthly loan instalments, payback period, cumulative net savings

Net savings formula:  
`net_monthly_savings = energy_cost_reduction − financing_instalment`

where `energy_cost_reduction = baseline_total_cost − upgraded_total_cost`.

---

## Upgrade Scenarios

| Scenario | Technologies |
|---|---|
| `solar_only` | Rooftop PV |
| `pv_battery` | PV + home battery |
| `pv_heatpump` | PV + heat pump (replaces gas/oil) |
| `pv_ev` | PV + EV charging (replaces petrol/diesel) |
| `pv_battery_heatpump` | PV + battery + heat pump |
| `full_upgrade` | PV + battery + heat pump + EV |

All six scenarios are computed in every call.

---

## Usage

### Python — compute_model

```python
from scripts.energy_model import compute_model

result = compute_model({
    "location": {"postcode": "10115", "country": "DE"},
    "household": {
        "occupants": 3,
        "electricity": {
            "annual_kwh": 4200,
            "arbeitspreis_eur_per_kwh": 0.32,
            "grundpreis_eur_per_month": 12.50,
            "contract_end_date": "2026-12-31"
        },
        "roof": {
            "usable_area_m2": 40,
            "orientation": "south",
            "tilt_deg": 30,
            "shading_factor": 0.1
        }
    },
    "heating": {"fuel_type": "gas", "annual_consumption": 14000, "annual_spend_eur": 1450},
    "mobility": {
        "vehicle_type": "petrol",
        "annual_mileage_km": 12000,
        "fuel_consumption_l_per_100km": 6.5
    },
    "financing": {"loan_term_years": 15, "loan_rate_pct": 4.5},
    "forecast_horizon": {"short_term_months": 12, "long_term_years": 20}
})
```

### Python — run_model (file I/O)

```python
from scripts.energy_model import run_model

result = run_model("data/input.json", "data/output.json")
```

### CLI

```bash
python scripts/run_model.py --input documentation/data/model_input1.json
python scripts/run_model.py --input data/in.json --output data/out.json
```

Exits `0` on success, `1` on validation error or I/O failure.

---

## Input Format

All fields are at the top level of a JSON object.

### Required

| Section | Field | Type | Description |
|---|---|---|---|
| `location` | `postcode` | string | German postcode (e.g. `"10115"`) |
| `heating` | `annual_consumption` or `annual_spend_eur` | number | Gas kWh or oil litres consumed per year; or annual spend in EUR |
| `mobility` | `annual_mileage_km` | number | Annual vehicle kilometres |
| `mobility` | `fuel_consumption_l_per_100km` | number | Litres per 100 km |

### Optional — with defaults

| Section | Field | Default | Notes |
|---|---|---|---|
| `location` | `country` | `"DE"` | Only `"DE"` supported |
| `household` | `occupants` | `2` | Used to estimate electricity if not provided |
| `household.electricity` | `annual_kwh` | `occupants × 1400` | |
| `household.electricity` | `arbeitspreis_eur_per_kwh` | `0.32` | Working price |
| `household.electricity` | `grundpreis_eur_per_month` | `12.50` | Standing charge |
| `household.electricity` | `contract_end_date` | `null` | ISO date; constant price applied through this date |
| `household.roof` | `usable_area_m2` | `30` | Determines max PV size |
| `household.roof` | `orientation` | `"south"` | `"south"` / `"east"` / `"west"` / `"north"` |
| `household.roof` | `tilt_deg` | `30` | |
| `household.roof` | `shading_factor` | `0.0` | 0 = no shading, 1 = full shade |
| `heating` | `fuel_type` | `"gas"` | `"gas"` or `"oil"` |
| `mobility` | `vehicle_type` | `"petrol"` | `"petrol"` / `"diesel"` / `"electric"` / `"phev"` / `"hybrid"` |
| `mobility` | `annual_fuel_spend_eur` | `null` | Used to derive effective fuel price if provided |
| `financing` | `loan_term_years` | `15` | Loan duration |
| `financing` | `loan_rate_pct` | `4.5` | Annual nominal interest rate |
| `financing` | `known_subsidy_eur` | `null` | Reduces financed principal |
| `financing` | `upfront_contribution_eur` | `null` | Reduces financed principal |
| `forecast_horizon` | `short_term_months` | `12` | Monthly records; must be ≥ 1 |
| `forecast_horizon` | `long_term_years` | `20` | Annual aggregates; must be ≥ 1 |

### Input validation errors

The following raise `ValueError` with a field-specific message:

- Missing `location.postcode`
- Negative `household.electricity.annual_kwh`
- Negative `household.electricity.arbeitspreis_eur_per_kwh`
- Negative `household.electricity.grundpreis_eur_per_month`
- Malformed `household.electricity.contract_end_date` (must be ISO-8601)
- Unsupported `heating.fuel_type` (must be `"gas"` or `"oil"`)
- Unsupported `mobility.vehicle_type`
- `financing.loan_term_years < 1`
- Negative `financing.annual_rate_pct`
- `forecast_horizon.short_term_months < 1`
- `forecast_horizon.long_term_years < 1`

---

## Output Format

All monetary values are in EUR. Energy in kWh. See `documentation/data/model_output.json` for a full example.

```json
{
  "model": {
    "name": "energy_cost_comparison",
    "version": "4.0",
    "price_scenarios": ["low", "central", "high"]
  },
  "price_models": {
    "short_term": { "name": "constant_index", "selection_basis": "Destatis rolling-origin backtest", ... },
    "long_term":  { "name": "scenario_trend", "assumptions": { "central_pct_per_year": 3.0, ... }, ... }
  },
  "input_summary": { "postcode": "...", "annual_electricity_kwh": 4200, ... },
  "assumptions_used": { "solar_kwp": 6.6, "battery_usable_kwh": 10.0, ... },
  "validation_warnings": [],
  "baseline": {
    "short_term_forecast": [
      {
        "month": "2026-01",
        "consumption": { "electricity_kwh": ..., "heating_kwh": ..., "mobility_litres": ... },
        "prices": { "electricity_eur_per_kwh": ..., "gas_eur_per_kwh": ..., "petrol_eur_per_litre": ... },
        "cost_eur": { "electricity": ..., "heating": ..., "mobility": ..., "total": ... }
      }
    ],
    "long_term_projection": {
      "low": [ { "year_label": "2026", "cost_eur": { "total": ... }, ... } ],
      "central": [ ... ],
      "high": [ ... ]
    }
  },
  "upgrade_scenarios": {
    "solar_only": {
      "investment": {
        "components": { "pv_eur": ..., "battery_eur": 0.0, "heat_pump_eur": 0.0, "ev_charger_eur": 0.0 },
        "gross_investment_eur": ...,
        "subsidy_eur": ...,
        "financed_principal_eur": ...
      },
      "financing": {
        "monthly_instalment_eur": ...,
        "loan_term_months": 180,
        "annual_rate_pct": 4.5
      },
      "short_term_forecast": [
        {
          "month": "2026-01",
          "energy_flows": { "pv_gen_kwh": ..., "direct_sc_kwh": ..., "battery_charge_kwh": ..., "grid_export_kwh": ..., "grid_import_kwh": ... },
          "cost_eur": {
            "upgraded_total": ...,
            "baseline_total": ...,
            "energy_cost_reduction": ...
          },
          "financial_result": {
            "energy_cost_reduction_eur": ...,
            "financing_instalment_eur": ...,
            "net_monthly_savings_eur": ...,
            "cumulative_net_savings_eur": ...
          }
        }
      ],
      "long_term_projection": {
        "low": [
          {
            "year_label": "2026",
            "cost_eur": { "upgraded_total": ..., "baseline_total": ..., "energy_cost_reduction": ... },
            "financial_result": {
              "annual_energy_cost_reduction_eur": ...,
              "annual_financing_payments_eur": ...,
              "annual_net_savings_eur": ...,
              "cumulative_net_savings_eur": ...,
              "remaining_loan_balance_eur": ...
            }
          }
        ],
        "central": [ ... ],
        "high": [ ... ]
      }
    }
  }
}
```

---

## Modelling Approach

### Electricity consumption

BDEW H0 residential load profile (temperature-dependent, seasonal variation). Annual total distributed across 12 months weighted by profile factors.

### Heating consumption

Monthly heating load from Degree-Day method using DWD historical heating degree days for the given postcode region. Gas: kWh directly. Oil: litres × 10.0 kWh/litre.

### PV generation

System sized from usable roof area: `kWp = area_m2 × 0.2 kWp/m²`. Monthly output uses orientation × tilt × shading correction on German irradiance profile. PV degradation: 0.5%/year.

### Battery dispatch

`daytime_demand_fraction = 0.35` — 35% of electricity demand occurs during PV generation hours (08:00–17:00). Battery reduces grid import during remaining daylight demand. Prevents the naive error of assuming PV meets all demand.

### Feed-in tariff (EEG 2024)

| System size | EUR/kWh |
|---|---|
| ≤ 10 kWp | 0.082 |
| 10–40 kWp | 0.071 |
| > 40 kWp | 0.058 |

### Heat pump

`hp_electricity_kwh = (baseline_heating_kwh × existing_efficiency) / SCOP`  
Default SCOP = 3.5. Heat pump replaces boiler; electricity demand increases, gas/oil demand falls to zero.

### EV

Additional electricity demand: `annual_mileage_km / 100 × ev_kwh_per_100km`. Petrol/diesel spend falls to zero. Some EV demand served by PV via battery.

### Short-term price model

`ConstantShortTermPriceModel`: all prices frozen at the user's current tariff for every month. Selected over trend and AR models by Destatis rolling-origin backtest on 12-month horizon across all four energy carriers (electricity, gas, heating oil, petrol). Results in `research/evaluation_outputs/`.

### Long-term price model

`ScenarioPriceModel`: three deterministic annual growth paths (low / central / high). Not a statistical forecast — represents a policy-range assumption band. Central growth rates:

| Carrier | Central %/yr | Low %/yr | High %/yr |
|---|---|---|---|
| Electricity | 3.0 | 1.0 | 6.0 |
| Gas | 2.0 | 0.5 | 5.0 |
| Heating oil | 2.0 | 0.5 | 5.0 |
| Petrol | 1.5 | 0.5 | 4.0 |

**ST and LT intentionally use different models.** Year-1 totals will differ. This is correct.

### Financing

Fixed-rate annuity loan:  
`monthly_instalment = P × r × (1+r)^n / ((1+r)^n − 1)`  
where `P` = financed principal, `r` = monthly rate, `n` = term in months.  
Zero-rate fallback: `P / n`. Instalments stop after loan term; post-payoff months have zero instalment.

---

## LLM Integration Guidance

When using this model output with an LLM agent:

1. **Do not recalculate.** Pass the entire `result` dict to the LLM. All values are pre-computed and self-consistent.
2. **Use `price_models` to explain methodology.** The `selection_basis` field explains why constant short-term prices were chosen.
3. **Use `validation_warnings` to flag inputs.** Any defaulted or estimated inputs are listed there.
4. **Prefer `long_term_projection.central`** for single-number summaries. Use `low`/`high` to characterise uncertainty.
5. **Quote `assumptions_used`** when the user asks which system size was modelled.
6. **Net savings = `financial_result.cumulative_net_savings_eur`** at the final year of the long-term projection. Positive = profitable.
7. **Payback year**: first `year_label` where `cumulative_net_savings_eur > 0` in `long_term_projection.central`.
8. **Do not sum ST monthly values against LT annual values** — they use different price models and represent different horizons.
