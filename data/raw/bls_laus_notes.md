# BLS LAUS County Unemployment Panel — Notes

## Source
Bureau of Labor Statistics, Local Area Unemployment Statistics (LAUS) program.
Annual county-level flat files: `https://www.bls.gov/lau/laucnty{YY}.txt` (years 2010–2022).

**Access method:** BLS direct downloads return HTTP 403 as of May 2026 (Akamai CDN blocks programmatic access). Files retrieved via Wayback Machine (web.archive.org) using snapshots from February–March 2025. The `if_` modifier was used to obtain raw file content without the Wayback toolbar wrapper.

The prior attempt (`fetch_laus.py`) used the BLS public API, which returned empty data arrays for all series — consistent with documented rate-limiting behavior.

## File Format
Fixed-width text, 132 characters per data row. Annual averages only (each file contains only annual average rows, no monthly breakdown). Skip first 6 lines (4 header lines + 2 blank lines). Skip footer (empty line + "SOURCE: BLS, LAUS" + date line).

Column positions (0-indexed):
- `0–14`: LAUS code (starts with "CN" for county)
- `18–19`: State FIPS (2 digits)
- `25–27`: County FIPS (3 digits)
- `31–80`: County name and state abbreviation
- `81–84`: Year (4-digit)
- `85–98`: Labor force (may contain commas)
- `99–112`: Employed (may contain commas)
- `113–122`: Unemployed level (may contain commas)
- `123–131`: Unemployment rate (%)

## Filter
- State FIPS: `39` (Ohio), `51` (Virginia), `31` (Nebraska)
- County FIPS `000` excluded (state-level summary rows)

## Output Schema (`bls_laus_panel.csv`)
| Column | Type | Notes |
|---|---|---|
| `fips` | string | 5-char zero-padded (state 2 + county 3) |
| `year` | integer | 2010–2022 |
| `unemployment_rate` | float | Annual average, percent |
| `labor_force` | integer | Annual average, persons |

## Coverage
- 314 unique counties/independent cities across 13 years = 4,082 rows
  - Ohio (39): 88 counties × 13 years = 1,144 rows
  - Nebraska (31): 93 counties × 13 years = 1,209 rows
  - Virginia (51): 133 counties + independent cities × 13 years = 1,729 rows
- No missing values in this dataset (BLS reported data for all counties all years)

## Generated
2026-05-23 via `data/cache/bls_laus/fetch_laus_flat.py`
