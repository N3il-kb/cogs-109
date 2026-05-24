# BLS QCEW Data Notes

**Sources:**

- Years 2010-2013: ZIP files from `https://data.bls.gov/cew/data/files/{year}/csv/{year}_annual_by_area.zip`
  - File naming inside ZIP: `{year}.annual.by_area/{year}.annual {fips5} {county name}.csv`
  - Establishments column: `annual_avg_estabs_count`
- Years 2014-2022: API slice per county: `https://data.bls.gov/cew/data/api/{year}/a/area/{fips}.csv`
  - Establishments column: `annual_avg_estabs`

**States:** OH (39xxx), VA (51xxx), NE (31xxx)

**Years:** 2010-2022

**Total rows in panel:** 4125

## Suppression Policy

BLS uses `disclosure_code = 'N'` to flag suppressed cells (confidentiality). When suppressed, numeric fields are set to 0 in the raw data — **not** true zeros. All such values are treated as `NaN` in the panel.

For `data_processing_employment` (NAICS 518+519 sum): if any non-suppressed rows exist, they are summed; if all rows are suppressed or none exist, the value is NaN.

## Suppressed / Missing Cell Counts

| Column | NaN count | NaN % |
|--------|-----------|-------|
| total_employment | 0 | 0.0% |
| total_wages | 0 | 0.0% |
| avg_annual_wage | 0 | 0.0% |
| data_processing_employment | 2996 | 72.6% |
| total_establishments | 0 | 0.0% |

## Variable Definitions

| Panel column | BLS source column | Filter |
|---|---|---|
| total_employment | annual_avg_emplvl | own_code=0, industry_code=10 |
| total_wages | total_annual_wages | own_code=0, industry_code=10 |
| avg_annual_wage | avg_annual_pay | own_code=0, industry_code=10 |
| total_establishments | annual_avg_estabs_count (ZIP) or annual_avg_estabs (API) | own_code=0, industry_code=10 |
| data_processing_employment | sum(annual_avg_emplvl) | industry_code in (518, 519), any own_code |

## Notes

- County FIPS: 5-digit zero-padded strings. State totals (e.g. 39000) excluded.
- `own_code=0`: total covered (all ownerships combined).
- `industry_code=10`: total, all industries.
- NAICS 518: Data Processing, Hosting, and Related Services.
- NAICS 519: Other Information Services.
- API slice URL provides annual ('a') data; confirmed returns qtr='A' rows only.
