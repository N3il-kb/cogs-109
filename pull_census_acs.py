"""
Pull ACS 5-year estimates for Ohio (39), Virginia (51), Nebraska (31) counties, 2010-2022.

Schema notes (verified against live API 2025-05-23):
- S1701_C03_001E (poverty rate): available 2012+, NaN for 2010-2011
- S1501_C02_015E (pct bachelor's):
    * 2010-2014: variable exists but C02 = Male%; use C01_015E (Total%) instead
    * 2015-2022: C02_015E = all-persons % bachelor's 25+; C01_015E suppressed
- S1501_C01_015E (Total % bachelor's): valid 2010-2014, suppressed (-888888888) 2015+
- B-series (B19013, B01003, B01002): available all years
- S2301_C04_001E (unemployment): available all years 2010+
"""

import os
import json
import hashlib
import time
import requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

# ── Config ──────────────────────────────────────────────────────────────────
ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
load_dotenv(ROOT / ".env")
KEY = os.environ["CENSUS_API_KEY"]

CACHE_DIR = ROOT / "data" / "cache" / "census_acs"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

OUT_CSV = ROOT / "data" / "raw" / "census_acs_panel.csv"
GAZ_URL = "https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_counties_national.zip"
GAZ_ZIP = CACHE_DIR / "2020_Gaz_counties_national.zip"

STATES = {"OH": "39", "VA": "51", "NE": "31"}
YEARS = list(range(2010, 2023))

BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"
SUBJ_URL = "https://api.census.gov/data/{year}/acs/acs5/subject"

# Census sentinel values that mean N/A
SENTINEL = {-888888888, -666666666, -999999999, -222222222, -333333333}


# ── Caching helpers ──────────────────────────────────────────────────────────
def cache_path(url: str) -> Path:
    h = hashlib.md5(url.encode()).hexdigest()
    return CACHE_DIR / f"{h}.json"


def fetch(url: str, retries: int = 3) -> list:
    """Return parsed JSON list or None on permanent error."""
    cp = cache_path(url)
    if cp.exists():
        return json.loads(cp.read_text())

    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                data = r.json()
                cp.write_text(json.dumps(data))
                return data
            elif r.status_code in (400, 404):
                # Variable not available this year — cache empty list as sentinel
                cp.write_text(json.dumps([]))
                return []
            else:
                print(f"  HTTP {r.status_code} for {url[:80]}... retrying")
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  Error: {e} — retrying")
            time.sleep(2 ** attempt)
    return None


def parse_val(v):
    """Convert Census string value to float, returning NaN for sentinels/nulls."""
    if v is None:
        return float("nan")
    try:
        f = float(v)
        if f in SENTINEL or f < -100000:
            return float("nan")
        return f
    except (ValueError, TypeError):
        return float("nan")


# ── Step 1: Gazetteer land area ──────────────────────────────────────────────
def load_gazetteer() -> pd.DataFrame:
    """Download and parse 2020 Census Gazetteer for county land area in sq mi."""
    if not GAZ_ZIP.exists():
        print("Downloading 2020 Gazetteer zip...")
        r = requests.get(GAZ_URL, timeout=60)
        r.raise_for_status()
        GAZ_ZIP.write_bytes(r.content)
        print(f"  Saved {GAZ_ZIP.stat().st_size / 1e6:.1f} MB")

    print("Parsing Gazetteer...")
    gaz = pd.read_csv(
        GAZ_ZIP,
        sep="\t",
        dtype={"GEOID": str},
        usecols=["GEOID", "ALAND_SQMI"],
        encoding="latin-1",
    )
    gaz["GEOID"] = gaz["GEOID"].str.strip().str.zfill(5)
    gaz = gaz.rename(columns={"GEOID": "fips", "ALAND_SQMI": "aland_sqmi"})
    print(f"  Gazetteer rows: {len(gaz)}")
    return gaz


# ── Step 2: ACS pulls ────────────────────────────────────────────────────────
def build_b_url(year: int, state_fips: str) -> str:
    vars_ = "NAME,B19013_001E,B01003_001E,B01002_001E"
    return (
        f"{BASE_URL.format(year=year)}?get={vars_}"
        f"&for=county:*&in=state:{state_fips}&key={KEY}"
    )


def build_s_url(year: int, state_fips: str) -> str:
    """
    S-series variables with year-aware bachelor's variable selection:
    - S1501_C01_015E: Total % bachelor's, valid 2010-2014
    - S1501_C02_015E: % bachelor's (all persons 25+), valid 2015+
      (in 2010-2014, C02_015E is male-only — do not use)
    - S1701_C03_001E: poverty rate, available 2012+
    """
    bach_var = "S1501_C01_015E" if year <= 2014 else "S1501_C02_015E"
    vars_ = f"S2301_C04_001E,{bach_var}"
    if year >= 2012:
        vars_ += ",S1701_C03_001E"
    return (
        f"{SUBJ_URL.format(year=year)}?get={vars_}"
        f"&for=county:*&in=state:{state_fips}&key={KEY}"
    )


def pull_year_state(year: int, state_name: str, state_fips: str) -> list[dict]:
    """Pull B-series and S-series for one year/state, return list of row dicts."""
    # B-series
    b_url = build_b_url(year, state_fips)
    b_data = fetch(b_url)

    # S-series
    s_url = build_s_url(year, state_fips)
    s_data = fetch(s_url)

    if not b_data:
        print(f"  WARN: No B-series data for {state_name} {year}")
        return []

    b_header = b_data[0]
    rows = []

    for b_row in b_data[1:]:
        b = dict(zip(b_header, b_row))
        county_fips = b["county"].zfill(3)
        state_pad = b["state"].zfill(2)
        fips = state_pad + county_fips

        row = {
            "fips": fips,
            "county_name": b.get("NAME", ""),
            "state": state_name,
            "year": year,
            "median_income": parse_val(b.get("B19013_001E")),
            "pop_total": parse_val(b.get("B01003_001E")),
            "median_age": parse_val(b.get("B01002_001E")),
            "poverty_rate": float("nan"),
            "pct_bachelors": float("nan"),
            "unemployment_acs": float("nan"),
        }

        # Merge S-series
        if s_data and len(s_data) > 1:
            s_header = s_data[0]
            for s_row in s_data[1:]:
                s = dict(zip(s_header, s_row))
                if s.get("county", "").zfill(3) == county_fips and s.get("state", "").zfill(2) == state_pad:
                    row["unemployment_acs"] = parse_val(s.get("S2301_C04_001E"))

                    # Bachelor's: year-aware variable selection
                    if year <= 2014:
                        row["pct_bachelors"] = parse_val(s.get("S1501_C01_015E"))
                    else:
                        row["pct_bachelors"] = parse_val(s.get("S1501_C02_015E"))

                    if year >= 2012:
                        row["poverty_rate"] = parse_val(s.get("S1701_C03_001E"))
                    break

        rows.append(row)

    return rows


# ── Step 3: Main loop ────────────────────────────────────────────────────────
def main():
    gaz = load_gazetteer()

    all_rows = []
    for year in YEARS:
        for state_name, state_fips in STATES.items():
            print(f"  Pulling {state_name} {year}...")
            rows = pull_year_state(year, state_name, state_fips)
            all_rows.extend(rows)
            time.sleep(0.1)  # be polite to the API

    df = pd.DataFrame(all_rows)
    print(f"\nRaw panel shape: {df.shape}")

    # ── Step 4: Compute pop_density ──────────────────────────────────────────
    df = df.merge(gaz[["fips", "aland_sqmi"]], on="fips", how="left")
    df["pop_density"] = df["pop_total"] / df["aland_sqmi"]

    # ── Step 5: Final column selection and ordering ──────────────────────────
    final_cols = [
        "fips", "county_name", "state", "year",
        "median_income", "poverty_rate", "pct_bachelors",
        "pop_density", "unemployment_acs", "median_age",
    ]
    df = df[final_cols]

    # ── Step 6: Write output ──────────────────────────────────────────────────
    df.to_csv(OUT_CSV, index=False, encoding="utf-8")
    print(f"\nWrote {len(df)} rows to {OUT_CSV}")

    # Diagnostics
    print("\nColumn null counts:")
    print(df.isnull().sum())
    print("\nSample rows (first 3):")
    print(df.head(3).to_string())
    print("\nYear × State counts:")
    print(df.groupby(["year", "state"]).size().unstack())


if __name__ == "__main__":
    main()
