"""
National ACS 5-year pull for the 22 states in county_master_list.csv, 2010-2023.

Adapted from pull_census_acs.py (OH/VA/NE -> 22 states). Reuses the same
caching, sentinel handling, and year-aware S1501 logic. Adds WFH rate (B08301).

Schema notes (unchanged from original):
- S1701_C03_001E (poverty rate): available 2012+, NaN for 2010-2011
- pct_bachelors: S1501_C01_015E (2010-2014, Total%) / S1501_C02_015E (2015+, all-persons%)
- B-series (B19013, B01003, B01002): all years
- S2301_C04_001E (unemployment): all years
NEW:
- wfh_rate = B08301_021E / B08301_001E * 100  (worked from home / total workers to work)
"""
import os, json, hashlib, time, requests
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
load_dotenv(ROOT / ".env")
KEY = os.environ["CENSUS_API_KEY"]

CACHE_DIR = ROOT / "data" / "cache" / "census_acs"      # reuse existing cache
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = ROOT / "data" / "raw" / "census_acs_panel_national.csv"
GAZ_ZIP = CACHE_DIR / "2020_Gaz_counties_national.zip"   # already cached

MASTER = ROOT / "data" / "raw" / "county_master_list.csv"
YEARS = list(range(2010, 2024))   # try through 2023 (5-yr ACS lag)
BASE_URL = "https://api.census.gov/data/{year}/acs/acs5"
SUBJ_URL = "https://api.census.gov/data/{year}/acs/acs5/subject"
SENTINEL = {-888888888, -666666666, -999999999, -222222222, -333333333}

# 22 state FIPS prefixes (from master list)
STATE_FIPS = {"01":"AL","04":"AZ","06":"CA","13":"GA","17":"IL","18":"IN","19":"IA",
              "29":"MO","31":"NE","32":"NV","35":"NM","37":"NC","39":"OH","40":"OK",
              "41":"OR","45":"SC","47":"TN","48":"TX","49":"UT","51":"VA","53":"WA","56":"WY"}


def cache_path(url):
    return CACHE_DIR / f"{hashlib.md5(url.encode()).hexdigest()}.json"


def fetch(url, retries=3):
    cp = cache_path(url)
    if cp.exists():
        return json.loads(cp.read_text())
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 200:
                data = r.json(); cp.write_text(json.dumps(data)); return data
            elif r.status_code in (400, 404):
                cp.write_text(json.dumps([])); return []   # var not available this year
            else:
                time.sleep(2 ** attempt)
        except Exception as e:
            print(f"  err {e} retry"); time.sleep(2 ** attempt)
    return None


def parse_val(v):
    if v is None: return float("nan")
    try:
        f = float(v)
        return float("nan") if (f in SENTINEL or f < -100000) else f
    except (ValueError, TypeError):
        return float("nan")


def load_gazetteer():
    gaz = pd.read_csv(GAZ_ZIP, sep="\t", dtype={"GEOID": str},
                      usecols=["GEOID", "ALAND_SQMI"], encoding="latin-1")
    gaz["GEOID"] = gaz["GEOID"].str.strip().str.zfill(5)
    return gaz.rename(columns={"GEOID": "fips", "ALAND_SQMI": "aland_sqmi"})


def build_b_url(year, sf):
    return (f"{BASE_URL.format(year=year)}?get=NAME,B19013_001E,B01003_001E,B01002_001E"
            f"&for=county:*&in=state:{sf}&key={KEY}")


def build_s_url(year, sf):
    bach = "S1501_C01_015E" if year <= 2014 else "S1501_C02_015E"
    vars_ = f"S2301_C04_001E,{bach}"
    if year >= 2012: vars_ += ",S1701_C03_001E"
    return (f"{SUBJ_URL.format(year=year)}?get={vars_}&for=county:*&in=state:{sf}&key={KEY}")


def build_wfh_url(year, sf):
    # B08301: Means of transportation to work. _001E total, _021E worked from home
    return (f"{BASE_URL.format(year=year)}?get=B08301_001E,B08301_021E"
            f"&for=county:*&in=state:{sf}&key={KEY}")


def pull_year_state(year, sf, sname):
    b_data = fetch(build_b_url(year, sf))
    s_data = fetch(build_s_url(year, sf))
    w_data = fetch(build_wfh_url(year, sf))
    if not b_data:
        print(f"  WARN no B-series {sname} {year}"); return []

    # index s/w by county fips for fast lookup
    def index(data):
        out = {}
        if data and len(data) > 1:
            hdr = data[0]
            for row in data[1:]:
                d = dict(zip(hdr, row))
                out[d["county"].zfill(3)] = d
        return out
    s_idx, w_idx = index(s_data), index(w_data)

    rows = []
    bh = b_data[0]
    for br in b_data[1:]:
        b = dict(zip(bh, br))
        cf = b["county"].zfill(3); sp = b["state"].zfill(2); fips = sp + cf
        row = {"fips": fips, "county_name": b.get("NAME",""), "state": sname, "year": year,
               "median_income": parse_val(b.get("B19013_001E")),
               "pop_total": parse_val(b.get("B01003_001E")),
               "median_age": parse_val(b.get("B01002_001E")),
               "poverty_rate": float("nan"), "pct_bachelors": float("nan"),
               "unemployment_acs": float("nan"), "wfh_rate": float("nan")}
        s = s_idx.get(cf)
        if s:
            row["unemployment_acs"] = parse_val(s.get("S2301_C04_001E"))
            row["pct_bachelors"] = parse_val(s.get("S1501_C01_015E" if year <= 2014 else "S1501_C02_015E"))
            if year >= 2012: row["poverty_rate"] = parse_val(s.get("S1701_C03_001E"))
        w = w_idx.get(cf)
        if w:
            tot = parse_val(w.get("B08301_001E")); home = parse_val(w.get("B08301_021E"))
            if tot and tot > 0 and not pd.isna(home):
                row["wfh_rate"] = 100.0 * home / tot
        rows.append(row)
    return rows


def main():
    master = pd.read_csv(MASTER, dtype={"fips": str})
    target = set(master["fips"].str.zfill(5))
    print(f"target counties: {len(target)} across {len(STATE_FIPS)} states")

    gaz = load_gazetteer()
    all_rows, end_year = [], {}
    for year in YEARS:
        got_any = False
        for sf, sname in STATE_FIPS.items():
            rows = pull_year_state(year, sf, sname)
            if rows: got_any = True
            all_rows.extend(rows)
        if got_any: end_year["acs"] = year
        print(f"  {year}: cumulative rows {len(all_rows)}")
        time.sleep(0.05)

    df = pd.DataFrame(all_rows)
    df = df[df["fips"].isin(target)].copy()       # filter to 169 counties
    df = df.merge(gaz[["fips","aland_sqmi"]], on="fips", how="left")
    df["pop_density"] = df["pop_total"] / df["aland_sqmi"]
    df = df[["fips","county_name","state","year","median_income","poverty_rate",
             "pct_bachelors","pop_density","unemployment_acs","median_age","wfh_rate"]]
    df = df.sort_values(["fips","year"]).reset_index(drop=True)
    df.to_csv(OUT_CSV, index=False)
    print(f"\nWROTE {len(df)} rows to {OUT_CSV}")
    print(f"end year reached: {df['year'].max()}")
    print(f"counties covered: {df['fips'].nunique()}/{len(target)}")
    print("null counts:\n", df.isnull().sum())
    # WFH sanity
    wfh = df.groupby("year")["wfh_rate"].mean()
    print("\nmean wfh_rate by year:\n", wfh.round(2).to_string())


if __name__ == "__main__":
    main()
