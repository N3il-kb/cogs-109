# Sample Frame Audit (v2)

For each outcome the **common sample** is the set of rows with no NaN in the outcome or in any predictor of the M3 (largest) spec. All five models for that outcome are fit on exactly these rows; only the predictor matrix changes.


## Electricity rate (¢/kWh) (`elec_rate_cents_kwh`)

- Clean panel rows (post contamination-drop): 4355
- Common-sample rows (complete cases on M3 union): **2757**
- Dropped: 1598 rows
- M3 predictor union (9): `['dc_active', 'per_capita_income', 'log_total_employment', 'avg_annual_wage', 'poverty_rate', 'unemployment_rate', 'log_pop_density', 'median_age', 'pct_bachelors']`
- Year range in sample: 2012–2022
- Rows dropped by year (NaN in outcome or any union predictor):
    - 2010: 335 dropped
    - 2011: 335 dropped
    - 2012: 80 dropped
    - 2013: 80 dropped
    - 2014: 80 dropped
    - 2015: 80 dropped
    - 2016: 80 dropped
    - 2017: 80 dropped
    - 2018: 80 dropped
    - 2019: 80 dropped
    - 2020: 96 dropped
    - 2021: 96 dropped
    - 2022: 96 dropped
- NaN count per union column (on clean panel, pre-deletion):
    - `elec_rate_cents_kwh`: 544
    - `dc_active`: 0
    - `per_capita_income`: 689
    - `log_total_employment`: 308
    - `avg_annual_wage`: 308
    - `poverty_rate`: 965
    - `unemployment_rate`: 351
    - `log_pop_density`: 351
    - `median_age`: 347
    - `pct_bachelors`: 347

## Unemployment rate (pp) (`unemployment_rate`)

- Clean panel rows (post contamination-drop): 4355
- Common-sample rows (complete cases on M3 union): **2757**
- Dropped: 1598 rows
- M3 predictor union (9): `['dc_active', 'per_capita_income', 'log_total_employment', 'avg_annual_wage', 'elec_rate_cents_kwh', 'poverty_rate', 'log_pop_density', 'median_age', 'pct_bachelors']`
- Year range in sample: 2012–2022
- Rows dropped by year (NaN in outcome or any union predictor):
    - 2010: 335 dropped
    - 2011: 335 dropped
    - 2012: 80 dropped
    - 2013: 80 dropped
    - 2014: 80 dropped
    - 2015: 80 dropped
    - 2016: 80 dropped
    - 2017: 80 dropped
    - 2018: 80 dropped
    - 2019: 80 dropped
    - 2020: 96 dropped
    - 2021: 96 dropped
    - 2022: 96 dropped
- NaN count per union column (on clean panel, pre-deletion):
    - `unemployment_rate`: 351
    - `dc_active`: 0
    - `per_capita_income`: 689
    - `log_total_employment`: 308
    - `avg_annual_wage`: 308
    - `elec_rate_cents_kwh`: 544
    - `poverty_rate`: 965
    - `log_pop_density`: 351
    - `median_age`: 347
    - `pct_bachelors`: 347

## Per-capita income ($) (`per_capita_income`)

- Clean panel rows (post contamination-drop): 4355
- Common-sample rows (complete cases on M3 union): **2757**
- Dropped: 1598 rows
- M3 predictor union (9): `['dc_active', 'log_total_employment', 'avg_annual_wage', 'elec_rate_cents_kwh', 'poverty_rate', 'unemployment_rate', 'log_pop_density', 'median_age', 'pct_bachelors']`
- Year range in sample: 2012–2022
- Rows dropped by year (NaN in outcome or any union predictor):
    - 2010: 335 dropped
    - 2011: 335 dropped
    - 2012: 80 dropped
    - 2013: 80 dropped
    - 2014: 80 dropped
    - 2015: 80 dropped
    - 2016: 80 dropped
    - 2017: 80 dropped
    - 2018: 80 dropped
    - 2019: 80 dropped
    - 2020: 96 dropped
    - 2021: 96 dropped
    - 2022: 96 dropped
- NaN count per union column (on clean panel, pre-deletion):
    - `per_capita_income`: 689
    - `dc_active`: 0
    - `log_total_employment`: 308
    - `avg_annual_wage`: 308
    - `elec_rate_cents_kwh`: 544
    - `poverty_rate`: 965
    - `unemployment_rate`: 351
    - `log_pop_density`: 351
    - `median_age`: 347
    - `pct_bachelors`: 347
