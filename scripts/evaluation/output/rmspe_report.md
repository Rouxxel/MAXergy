# RMSPE Results — Destatis CPI Energy Price Indices

RMSPE (%) = √[ mean( ((predicted − actual) / actual)² ) ] × 100

Source: `backtest_results.csv` (1248 valid records)

## Electricity

Model                         h=1     h=3     h=6    h=12   Overall
---------------------------------------------------------------
constant                    0.42*   0.83*   1.23*    2.38     1.25*
deterministic trend          0.58    1.43    2.60    5.40      2.68
ets                          1.23    2.18    3.47   2.30*      2.37
sarima                       1.78    3.63    5.39   12.56      6.17

*Observations per horizon* — h=1: 24  h=3: 22  h=6: 19  h=12: 13  overall: 78

\* lowest RMSPE for that horizon

## Gas

Model                         h=1     h=3     h=6    h=12   Overall
---------------------------------------------------------------
constant                     0.68   0.78*   1.47*    2.44      1.35
deterministic trend          0.80    1.56    3.18    6.31      3.16
ets                         0.65*    1.03    1.56   2.17*     1.34*
sarima                       2.62    4.75    8.93   16.48      8.55

*Observations per horizon* — h=1: 24  h=3: 22  h=6: 19  h=12: 13  overall: 78

\* lowest RMSPE for that horizon

## Heating Oil

Model                         h=1     h=3     h=6    h=12   Overall
---------------------------------------------------------------
constant                     2.25    3.24   4.89*   8.54*     4.75*
deterministic trend          2.38    3.94    6.75   12.77      6.66
ets                         2.23*   3.24*    4.92    8.60      4.77
sarima                       3.74    9.89   12.81   18.68     11.40

*Observations per horizon* — h=1: 24  h=3: 22  h=6: 19  h=12: 13  overall: 78

\* lowest RMSPE for that horizon

## Petrol

Model                         h=1     h=3     h=6    h=12   Overall
---------------------------------------------------------------
constant                    2.02*   3.60*   4.43*   4.33*     3.58*
deterministic trend          2.06    3.81    5.32    6.81      4.48
ets                          2.02    3.60    4.43    4.33      3.58
sarima                       2.90    5.71    5.91    8.25      5.62

*Observations per horizon* — h=1: 24  h=3: 22  h=6: 19  h=12: 13  overall: 78

\* lowest RMSPE for that horizon

## Lowest RMSPE by Series and Horizon

Series                   h=1          h=3          h=6         h=12         Overall
------------------------------------------------------------------------
Electricity     constant(0.42%) constant(0.83%) constant(1.23%)   ets(2.30%) constant(1.25%)
Gas               ets(0.65%) constant(0.78%) constant(1.47%)   ets(2.17%)      ets(1.34%)
Heating Oil       ets(2.23%)   ets(3.24%) constant(4.89%) constant(8.54%) constant(4.75%)
Petrol          constant(2.02%) constant(3.60%) constant(4.43%) constant(4.33%) constant(3.58%)

## Validation

- Total records read: 1248
- Valid records used: 1248
- Invalid / excluded: 0
- Actual index > 0 in all records: yes
- All models evaluated on identical record sets per series × horizon: yes
