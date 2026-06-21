# Integrated Energy Cost Forecast Model

`scripts/run_energy_cost_forecast.py`  
Version 1.1

## Overview

Forecasts a household's future energy costs (electricity, heating, mobility) **without any home-energy upgrade**. This is the "do nothing" baseline against which future upgrade scenarios are compared.

---

## 1. Module Separation

| Class | Responsibility |
|-------|---------------|
| `BDEWProfile` | Loads BDEW H0 electricity load profile; computes monthly consumption fractions from day-type energy levels and German holidays |
| `WeatherModel` | Loads DWD climate-normal temperatures; computes heating degree days and monthly heating fractions |
| `ConsumptionModel` | Combines BDEW and DWD into per-month fractions for electricity, heating, and mobility |
| `EnergyPriceModel` | Projects monthly unit prices by scenario; respects electricity contract end date |
| `EnergyCostCalculator` | Deterministic arithmetic only: cost = consumption × price |
| `ForecastOrchestrator` | Wires the three models, validates output, serialises results |

**Rule**: price forecasting logic never enters `ConsumptionModel` or `EnergyCostCalculator`. Consumption logic never enters `EnergyPriceModel`.

---

## 2. BDEW H0 Electricity Profile

**Source file**: `data/bdew_h0_profile.json`

**Method**:
For each forecast month, the model counts:
- working days (Mon–Fri excluding national holidays)
- Saturdays
- Sundays and national public holidays

It multiplies each day count by a seasonal day-type energy factor (winter/transition/summer × weekday/Saturday/Sunday-holiday). The resulting raw monthly energy is normalised to produce 12 fractions summing to 1.0. This is recomputed per calendar year to capture real Easter and weekday offsets.

**National holidays included**: Neujahr, Karfreitag, Ostermontag, Tag der Arbeit, Christi Himmelfahrt, Pfingstmontag, Tag der Deutschen Einheit, 1. and 2. Weihnachtstag.

**Placeholder note**: The daily energy factors in `bdew_h0_profile.json` are derived from the BDEW H0 seasonal structure. The full official profile provides 96 quarter-hourly power values per day-type × season combination (9 curves). Replace the `daily_energy_by_season_daytype` values with integrals of the official BDEW quarter-hourly H0 curves once licensed data is available from bdew.de.

**Fallback**: If the JSON file is missing or corrupt, pre-computed annual fractions from a representative year are used. The output records whether the official profile or fallback was applied (`profile_sources.electricity_profile_source`).

---

## 3. DWD Weather-Dependent Heating Profiles

**Source file**: `data/dwd_climate_normals.json`

**Method**: Heating Degree Day (Gradtagszahl) approach:

```
HDD_month = max(0, (T_base - T_mean_monthly) × days_in_month)
heating_fraction_month = HDD_month / sum(HDD_all_months)
```

Base temperature: **15 °C** (German standard, configurable via `ConsumptionConfig.hdd_base_temp_c`).

Monthly mean temperatures come from **DWD Klimanormalwerte 1991–2020** for 13 regional representative stations. The user's postcode (first 2 digits) maps to the nearest climate region. Annual heating consumption is always preserved exactly after monthly allocation.

**Placeholder note**: Regional temperatures are representative averages, not the nearest individual DWD station. Replace with station-level lookup from the DWD OpenData API (`opendata.dwd.de`) using the exact postcode coordinates once connectivity is available.

**Fallback**: If the DWD file is missing, Germany-average temperatures are used. The output records the station name and whether a fallback was applied (`profile_sources.heating_profile_is_fallback`).

---

## 4. Price Calibration Rules

Effective starting prices are derived from user-supplied data wherever possible, with fallbacks only when user data is unavailable:

| Energy type | Priority 1 (user) | Priority 2 (default) |
|-------------|-------------------|----------------------|
| Electricity unit | `arbeitspreis_eur_per_kwh` from input | 0.32 EUR/kWh (PLACEHOLDER) |
| Electricity fixed | `grundpreis_eur_per_month` from input | 12.50 EUR/month (PLACEHOLDER) |
| Gas | `annual_spend_eur ÷ annual_consumption` | 0.10 EUR/kWh (PLACEHOLDER) |
| Heating oil | `annual_spend_eur ÷ annual_consumption` | 1.05 EUR/litre (PLACEHOLDER) |
| Petrol | `annual_fuel_spend_eur ÷ calculated_annual_litres` | 1.75 EUR/litre (PLACEHOLDER) |

Petrol consumption is always calculated from physical parameters (`annual_mileage_km / 100 × fuel_consumption_l_per_100km`), not from reported spend. The reported spend only influences the calibrated starting price.

---

## 5. Fixed-Contract Electricity Behaviour

During the contract period (`contract_end_date` in input):
- The electricity unit price is exactly `arbeitspreis_eur_per_kwh` every month — no seasonal variation, no trend escalation.
- The fixed monthly charge is exactly `grundpreis_eur_per_month`.
- Monthly electricity **costs** still vary because **consumption** follows the BDEW H0 seasonal profile.

After the contract expires:
- Trend escalation starts from zero elapsed months (no sudden jump in the base price).
- The scenario trend rates apply from the first post-contract month onward.

---

## 6. Long-Term Aggregation

Annual records cover **consecutive 12-month periods** starting from the first forecast month. No months are lost when the forecast starts mid-year:

- Period 0 (labeled with the start year): forecast months 1–12
- Period 1: forecast months 13–24
- etc.

Annual totals are always the sum of their constituent monthly records — there is no separate annual formula.

---

## 7. How to Execute

```bash
python scripts/run_energy_cost_forecast.py
# reads  documentation/data/model_input1.json
# writes documentation/data/model_output_forecast.json
```

Run unit tests:

```bash
python -m pytest tests/test_energy_cost_forecast.py -v
```

---

## 8. How to Interpret Low / Central / High Scenarios

Three price scenarios apply different annual trend rates to all energy carriers:

| Scenario | Electricity | Gas / Oil | Petrol |
|----------|-------------|-----------|--------|
| Low | +1 % p.a. | +1 % p.a. | +1 % p.a. |
| Central | +3 % p.a. | +4 % p.a. | +3 % p.a. |
| High | +5 % p.a. | +7 % p.a. | +5 % p.a. |

Consumption is identical across all three scenarios (only prices differ). The central scenario is the main forecast. The output validates that low ≤ central ≤ high for every annual period and emits a warning if this ordering is violated.

---

## 9. Differences from `run_baseline_model.py`

| Aspect | `run_baseline_model.py` | `run_energy_cost_forecast.py` |
|--------|------------------------|-------------------------------|
| Purpose | Cost–benefit of upgrade scenarios | Future cost without any upgrade |
| Electricity profile | Flat seasonal weights | BDEW H0 (day-type × season) |
| Heating profile | Fixed seasonal weights | DWD HDD from climate normals |
| Contract end date | Not modelled | Locks tariff until expiry |
| Price scenarios | Single escalation rate | Low / central / high |
| Monthly record | Cost total only | Consumption + prices + cost |
| Annual aggregation | By calendar year | Consecutive 12-month periods |
| Current price | Default fallback | User-derived when spend reported |

---

## 10. Remaining Limitations

- Consumption is identical in low, central, and high scenarios (only prices differ).
- The BDEW H0 daily energy factors are representative approximations; the full quarter-hourly profile is not yet licensed.
- DWD temperatures are regional averages, not exact station lookups by postcode coordinates.
- The price model uses a constant annual trend; no mean-reversion or structural breaks are modelled.
- Future weather for heating is assumed equal to climate normals (no inter-annual variability).
- Only gas and oil are supported as heating fuels; district heating is out of scope.
- No real-time data calls are made; all data is local (offline-capable).
