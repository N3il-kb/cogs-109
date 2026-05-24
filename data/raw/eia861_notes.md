# EIA Form 861 Panel Data Notes

## Source
EIA Form 861 Annual Electric Power Industry Report, bulk ZIP files from:
https://www.eia.gov/electricity/data/eia861/

Downloaded and processed: 2026-05-23

## Coverage
- States: OH (FIPS prefix 39), VA (FIPS prefix 51), NE (FIPS prefix 31)
- Years: 2010–2022
- Unit of observation: county × year

## Output file
`data/raw/eia861_panel.csv`  
Columns: `fips, county_name, state, year, elec_rate_cents_kwh, res_sales_mwh, res_customers`

## Variable Definitions

### `elec_rate_cents_kwh`
Residential electricity rate in cents per kilowatt-hour.

**Construction:** Computed at the utility-state level as:
```
rate = (res_revenue_thousands * 100) / res_sales_mwh
```
Then aggregated to county level as a **customer-weighted average** across all utilities
listed in the EIA service territory file as serving that county. When a utility has
zero reported customers but a valid rate, a simple mean is used.

This rate is valid and represents the effective residential price in each county. Large
investor-owned utilities (e.g., Ohio Power, AEP, Dominion) report a single statewide
rate, which is correctly applied to all counties they serve.

### `res_sales_mwh` and `res_customers`
**Left as NaN (not populated).**

EIA Form 861 reports residential sales (MWh) and customer counts at the
utility-state level, not at the county level. The service territory file identifies
which counties a utility serves, but does not provide county-level allocation keys.
Summing statewide utility sales across all counties served would severely overcount
(e.g., Ohio Power's ~9M MWh statewide total would be attributed in full to each of
its 61 Ohio counties). County-level disaggregation of sales/customers would require
additional data (e.g., utility billing records or Census housing unit allocation).

If county-level customer counts are needed for the regression, consider using Census
ACS Table B25045 (housing units by tenure) or County Business Patterns as a proxy.

## File Structure by Year

| Years     | Sales file            | Service territory file    | Notes                                    |
|-----------|-----------------------|---------------------------|------------------------------------------|
| 2010      | file2_2010.xls        | file4_2010.xls            | 3-row header, res cols at positions 8–10 |
| 2011      | file2_2011.xls        | file4_2011.xls            | Same as 2010                             |
| 2012      | Sales_Ult_Cust_2012.xlsx | service_territory_2012.xls | BA_CODE added; res cols at 9–11       |
| 2013–2018 | Sales_Ult_Cust_YYYY.xls/xlsx | Service_Territory_YYYY.xls/xlsx | Same schema as 2012            |
| 2019      | Sales_Ult_Cust_2019.xlsx | Service_Territory_2019.xlsx | Short Form col added at col 9; res at 10–12 |
| 2020–2022 | Sales_Ult_Cust_YYYY.xlsx | Service_Territory_YYYY.xlsx | Short Form removed; res at 9–11      |

Sales files have a 3-row multi-level header (row 0: section, row 1: sub-section, row 2: column labels).
Data starts at row 3. Only `Part == 'A'` rows are used (aggregate per utility-state pair).

## FIPS Codes
County FIPS codes sourced from Census Bureau national county file:
https://www2.census.gov/geo/docs/reference/codes/files/national_county.txt

FIPS are 5-character zero-padded strings (e.g., "39001" for Adams County, OH).

Virginia has 133 independent cities with separate FIPS codes (e.g., 51510 = Alexandria city).
These are included as separate rows. Some Virginia cities do not appear in the EIA service
territory files (especially 2010–2011) and have NaN rates.

## Missing Data
219 county-year observations have missing rates (5.3%):
- **Nebraska (16 counties, 2020–2022):** Small rural counties (Arthur, Blaine, Garfield, etc.)
  whose serving utilities did not report residential data in the later years. Likely due to
  EIA reporting threshold changes or utility mergers not reflected in the service territory file.
- **Virginia (171 county-year obs):** Two causes:
  1. Independent cities not listed in EIA service territory in 2010–2011 (cities joined the
     territory file later as the form evolved).
  2. Several counties (Bedford, Charles City, Fairfax, Franklin, James City, Richmond, Roanoke)
     that either have unusual utility service arrangements or appear under city FIPS instead.

## Aggregation Script
`data/cache/eia861/extract_eia861.py`
