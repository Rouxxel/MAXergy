# Model Test Summary — Three Household Profiles

All values from the production pipeline (`scripts/energy_model/`), central long-term price scenario, Year 1 annual figures.

## Results

| Profile | Best plan | Baseline cost | Upgraded cost | Yr1 net savings | 20yr cumulative |
|---|---|---|---|---|---|
| Average German Household | Full Upgrade | €3,916 | €1,701 | €-297 | €24,828 |
| Low Benefit Household | PV + EV | €1,554 | €1,163 | €-154 | €4,844 |
| High Benefit Household | Full Upgrade | €10,247 | €4,040 | €3,897 | €126,420 |

## Profile notes

### Average German Household

3-person semi-detached house in Cologne. Typical electricity use (3,500 kWh), gas heating (14,000 kWh), 12,000 km/yr petrol, 35 m² south-facing roof. Standard 15-yr loan at 4.5 %.

- **Best plan:** Full Upgrade
- **Monthly instalment:** €209.35
- **Year 1 energy reduction:** €2,215
- **Year 1 financing payments:** €2,512
- **Year 1 net savings:** €-297
- **Avg monthly net savings (Yr1):** €-24.76
- **Validation warnings:** ['solar_kwp not provided; estimated 5.83 kWp from 35.0 m² roof', 'battery_kwh not specified; using default 10.0 kWh']

### Low Benefit Household

Single-person flat in Hamburg. Low electricity use (1,500 kWh), minimal gas heating (4,500 kWh), 4,000 km/yr, small 12 m² north-facing shaded roof (40 % shading). Shorter 10-yr loan at 6.5 %.

- **Best plan:** PV + EV
- **Monthly instalment:** €45.42
- **Year 1 energy reduction:** €391
- **Year 1 financing payments:** €545
- **Year 1 net savings:** €-154
- **Avg monthly net savings (Yr1):** €-12.87
- **Validation warnings:** ['solar_kwp not provided; estimated 2.00 kWp from 12.0 m² roof', 'battery_kwh not specified; using default 10.0 kWh']

### High Benefit Household

5-person detached house in Munich. High electricity use (7,200 kWh), oil heating (3,200 litres), 28,000 km/yr petrol SUV, 60 m² south-facing roof (5 % shading). 20-yr green mortgage at 3.5 %.

- **Best plan:** Full Upgrade
- **Monthly instalment:** €192.55
- **Year 1 energy reduction:** €6,207
- **Year 1 financing payments:** €2,311
- **Year 1 net savings:** €3,897
- **Avg monthly net savings (Yr1):** €324.74
- **Validation warnings:** ['solar_kwp not provided; estimated 10.00 kWp from 60.0 m² roof', 'battery_kwh not specified; using default 10.0 kWh']

## Modelling notes

- ST forecast uses `ConstantShortTermPriceModel` (prices frozen at user tariff).
- LT projection uses `ScenarioPriceModel` (low / central / high annual trend). Central used for best-plan selection.
- Solar kWp estimated from usable roof area (0.2 kWp/m²) when not explicitly provided.
- Battery defaults to 10.0 kWh when not specified.
- Year 1 values are from `long_term_projection.central[0]`.
- 20-yr values are from `long_term_projection.central[-1].financial_result.cumulative_net_savings_eur`.
