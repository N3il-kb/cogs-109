# BEA Data Pull Notes

## Parameters Verified

### CAINC1 — Per Capita Personal Income
- Table: CAINC1
- LineCode: 3
- Statistic: Per capita personal income
- Unit: Dollars
- GeoFips: COUNTY (filtered to OH=39, VA=51, NE=31)
- Years: 2010–2022
- Last updated: February 5, 2026-- new statistics for 2024; revised statistics for 2020-2023.

### CAGDP1 — County Real GDP
- Table: CAGDP1
- LineCode: 1
- Statistic: Real Gross Domestic Product (GDP)
- Unit: Thousands of chained 2017 dollars
- GeoFips: COUNTY (filtered to OH=39, VA=51, NE=31)
- Years: 2010–2022 (data starts from 2010, confirmed by test query)
- Last updated: February 5, 2026-- new statistics for 2024; revised statistics for 2020-2023.

## Output Schema
`bea_panel.csv` columns:
- `fips`: 5-character zero-padded county FIPS code (string)
- `year`: integer year
- `per_capita_income`: dollars (current, not inflation-adjusted)
- `gdp_thousands`: thousands of chained 2017 dollars (real GDP)

## Data Quality
- Suppressed values `(D)` converted to NaN; rows retained.
- No rows dropped for missingness.

## Panel Summary
- Unique counties: 286
- Year range: 2010–2022
- NaN per_capita_income: 0
- NaN gdp_thousands: 0

### Counties per state
state
NE     93
OH     88
VA    105
