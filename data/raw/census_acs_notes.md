# Census ACS Panel — Data Notes

**File:** `data/raw/census_acs_panel.csv`
**Generated:** 2025-05-23
**Coverage:** Ohio (FIPS 39), Virginia (FIPS 51), Nebraska (FIPS 31), 2010–2022
**Source:** Census Bureau ACS 5-Year Estimates via API

---

## Variable schema (verified against live API endpoints)

| Column | ACS Variable(s) | Notes |
|---|---|---|
| `median_income` | `B19013_001E` | Base endpoint. Nominal dollars (vintage-year inflation-adjusted). |
| `poverty_rate` | `S1701_C03_001E` | Subject endpoint. **NaN for 2010–2011** (variable not in API for those years). |
| `pct_bachelors` | `S1501_C01_015E` (2010–2014), `S1501_C02_015E` (2015–2022) | See schema-change note below. |
| `pop_density` | `B01003_001E` / Gazetteer `ALAND_SQMI` | Land area from 2020 Census Gazetteer (county). |
| `unemployment_acs` | `S2301_C04_001E` | Subject endpoint. Available all years 2010–2022. |
| `median_age` | `B01002_001E` | Base endpoint. |

---

## Schema change: pct_bachelors (S1501)

The S1501 table was restructured between 2014 and 2015, and again between 2016 and 2017. The column numbering changed meaning:

- **2010–2014:** `S1501_C01_015E` = "Total!!Estimate!!Percent bachelor's degree or higher" (all persons 25+). `S1501_C02_015E` in these years = male-only percentage — **not used**.
- **2015–2022:** `S1501_C02_015E` = "Percent!!Estimate!!... Population 25 years and over!!Bachelor's degree or higher" (all persons). `S1501_C01_015E` returns -888888888 (suppressed) in 2015+.

The switch point was confirmed by comparing actual county values across years. Both variables measure the same concept (% population 25+ with bachelor's or higher) and produce a continuous series.

---

## Missing data

| Condition | Affected rows | Count |
|---|---|---|
| `poverty_rate` = NaN | 2010 and 2011, all counties in OH/VA/NE | 630 rows (315 per year) |
| `pop_density` = NaN | FIPS 51515 (Bedford city, VA), 2010–2013 | 4 rows |

**Bedford city, VA (FIPS 51515):** This independent city was merged into Bedford County (FIPS 51019) in 2013 and no longer appears in the 2020 Census Gazetteer, so land area cannot be computed for the 4 years it was in the ACS county universe (2010–2013). Rows are retained with NaN pop_density per the data specification.

---

## Endpoints used

- B-series: `https://api.census.gov/data/{year}/acs/acs5?get=...&for=county:*&in=state:{fips}&key=...`
- S-series: `https://api.census.gov/data/{year}/acs/acs5/subject?get=...&for=county:*&in=state:{fips}&key=...`

## Land area

- Source: 2020 Census Gazetteer (counties): `https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_counties_national.zip`
- Field used: `ALAND_SQMI` (land area in square miles)
- Merged on 5-digit zero-padded FIPS code

## API responses cached

All Census API responses cached to `data/cache/census_acs/` as MD5-hashed JSON files. Gazetteer zip cached at `data/cache/census_acs/2020_Gaz_counties_national.zip`.

## Census sentinel values treated as NaN

Values -888888888, -666666666, -999999999, -222222222, -333333333 are converted to NaN.
