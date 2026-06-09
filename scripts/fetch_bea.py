"""
Fetch BEA CAINC1 (per capita personal income) and CAGDP1 (county real GDP)
for OH (39), VA (51), NE (31) counties, 2010-2022.

Verified parameters:
  CAINC1 LineCode=3 -> "Per capita personal income" (Dollars)
  CAGDP1 LineCode=1 -> "Real Gross Domestic Product (GDP)" (Thousands of chained 2017 dollars)
  GeoFips=COUNTY   -> all US counties; filter to state FIPS prefixes
  CAGDP1 starts from 2010 (confirmed by test query)
"""

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# --- Config ---
load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ["BEA_API_KEY"]
BASE_URL = "https://apps.bea.gov/api/data"
CACHE_DIR = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109/data/cache/bea")
OUT_CSV = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109/data/raw/bea_panel.csv")
NOTES_FILE = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109/data/raw/bea_notes.md")

# State FIPS prefixes to keep
STATE_FIPS = {"39": "OH", "51": "VA", "31": "NE"}

YEARS = list(range(2010, 2023))  # 2010-2022 inclusive
YEAR_STR = ",".join(str(y) for y in YEARS)

CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_bea(table, linecode, year_str, cache_key):
    cache_path = CACHE_DIR / f"{cache_key}.json"
    if cache_path.exists():
        print(f"  [cache] {cache_key}")
        with open(cache_path) as f:
            return json.load(f)

    params = {
        "UserID": API_KEY,
        "method": "GetData",
        "datasetname": "Regional",
        "TableName": table,
        "LineCode": linecode,
        "GeoFips": "COUNTY",
        "Year": year_str,
        "ResultFormat": "JSON",
    }
    print(f"  [fetch] {cache_key}")
    r = requests.get(BASE_URL, params=params, timeout=120)
    r.raise_for_status()
    data = r.json()

    # Check for API error
    results = data.get("BEAAPI", {}).get("Results", {})
    if "Error" in results:
        raise RuntimeError(f"BEA API error for {cache_key}: {results['Error']}")

    with open(cache_path, "w") as f:
        json.dump(data, f)

    time.sleep(0.5)  # be polite
    return data


def parse_records(raw, state_prefixes, value_col):
    """Extract records for target states, return list of dicts."""
    results = raw["BEAAPI"]["Results"]
    rows = []
    for rec in results["Data"]:
        fips = rec["GeoFips"].strip()
        # Keep only 5-digit county FIPS in our states
        if len(fips) != 5:
            continue
        if fips[:2] not in state_prefixes:
            continue

        raw_val = rec["DataValue"].strip()
        # "(D)" = suppressed/not disclosed -> NaN
        if raw_val in ("(D)", "(NA)", "(L)", ""):
            val = float("nan")
        else:
            # Remove commas from numbers like "1,234,567"
            try:
                val = float(raw_val.replace(",", ""))
            except ValueError:
                val = float("nan")

        rows.append({
            "fips": fips.zfill(5),
            "year": int(rec["TimePeriod"]),
            value_col: val,
        })
    return rows


# --- Fetch CAINC1 (per capita personal income) ---
print("Fetching CAINC1 (per capita personal income, LineCode=3)...")
cainc1_raw = fetch_bea("CAINC1", "3", YEAR_STR, "cainc1_county_2010_2022")
cainc1_rows = parse_records(cainc1_raw, STATE_FIPS, "per_capita_income")
df_income = pd.DataFrame(cainc1_rows)
print(f"  CAINC1 rows for OH/VA/NE: {len(df_income)}")

# --- Fetch CAGDP1 (real GDP, thousands of chained 2017 dollars) ---
print("Fetching CAGDP1 (real GDP, LineCode=1)...")
cagdp1_raw = fetch_bea("CAGDP1", "1", YEAR_STR, "cagdp1_county_2010_2022")
cagdp1_rows = parse_records(cagdp1_raw, STATE_FIPS, "gdp_thousands")
df_gdp = pd.DataFrame(cagdp1_rows)
print(f"  CAGDP1 rows for OH/VA/NE: {len(df_gdp)}")

# --- Merge on (fips, year) ---
print("Merging on (fips, year)...")
df = pd.merge(df_income, df_gdp, on=["fips", "year"], how="outer")
df = df.sort_values(["fips", "year"]).reset_index(drop=True)

# Ensure fips is zero-padded 5-char string
df["fips"] = df["fips"].str.zfill(5)

print(f"  Panel rows: {len(df)}")
print(f"  Unique counties: {df['fips'].nunique()}")
print(f"  Year range: {df['year'].min()} - {df['year'].max()}")
print(f"  NaN per_capita_income: {df['per_capita_income'].isna().sum()}")
print(f"  NaN gdp_thousands: {df['gdp_thousands'].isna().sum()}")

# --- Save ---
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
df[["fips", "year", "per_capita_income", "gdp_thousands"]].to_csv(OUT_CSV, index=False, encoding="utf-8")
print(f"\nSaved: {OUT_CSV}")

# --- Coverage summary by state ---
df["state"] = df["fips"].str[:2].map(STATE_FIPS)
print("\nCounty counts by state:")
print(df.groupby("state")["fips"].nunique())

# --- Print notes ---
cainc1_notes = cainc1_raw["BEAAPI"]["Results"].get("Notes", [])
cagdp1_notes = cagdp1_raw["BEAAPI"]["Results"].get("Notes", [])
cainc1_unit = cainc1_raw["BEAAPI"]["Results"].get("UnitOfMeasure", "")
cagdp1_unit = cagdp1_raw["BEAAPI"]["Results"].get("UnitOfMeasure", "")
cainc1_stat = cainc1_raw["BEAAPI"]["Results"].get("Statistic", "")
cagdp1_stat = cagdp1_raw["BEAAPI"]["Results"].get("Statistic", "")
cainc1_updated = next((n["NoteText"] for n in cainc1_notes if "Last updated" in n.get("NoteText", "")), "")
cagdp1_updated = next((n["NoteText"] for n in cagdp1_notes if "Last updated" in n.get("NoteText", "")), "")

notes_md = f"""# BEA Data Pull Notes

## Parameters Verified

### CAINC1 — Per Capita Personal Income
- Table: CAINC1
- LineCode: 3
- Statistic: {cainc1_stat}
- Unit: {cainc1_unit}
- GeoFips: COUNTY (filtered to OH=39, VA=51, NE=31)
- Years: 2010–2022
- {cainc1_updated}

### CAGDP1 — County Real GDP
- Table: CAGDP1
- LineCode: 1
- Statistic: {cagdp1_stat}
- Unit: {cagdp1_unit}
- GeoFips: COUNTY (filtered to OH=39, VA=51, NE=31)
- Years: 2010–2022 (data starts from 2010, confirmed by test query)
- {cagdp1_updated}

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
- Unique counties: {df['fips'].nunique()}
- Year range: {df['year'].min()}–{df['year'].max()}
- NaN per_capita_income: {df['per_capita_income'].isna().sum()}
- NaN gdp_thousands: {df['gdp_thousands'].isna().sum()}

### Counties per state
{df.groupby("state")["fips"].nunique().to_string()}
"""

NOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
NOTES_FILE.write_text(notes_md, encoding="utf-8")
print(f"Notes saved: {NOTES_FILE}")
