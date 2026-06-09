"""
National BEA pull (CAINC1 per-capita income, CAGDP1 real GDP) for the 22 states
in county_master_list.csv, 2010-2024. Adapted from scripts/fetch_bea.py.

Uses BEA_API_KEY from .env (the original script had a hardcoded key — flagged separately).
BEA county data is national in one call; we filter by state prefix + the 169-FIPS list.
"""
import json, os, time
from pathlib import Path
import pandas as pd, requests
from dotenv import load_dotenv

ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
load_dotenv(ROOT / ".env")
API_KEY = os.environ["BEA_API_KEY"]
BASE_URL = "https://apps.bea.gov/api/data"
CACHE_DIR = ROOT / "data" / "cache" / "bea"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = ROOT / "data" / "raw" / "bea_panel_national.csv"
MASTER = ROOT / "data" / "raw" / "county_master_list.csv"

STATE_FIPS = {"01","04","06","13","17","18","19","29","31","32","35","37",
              "39","40","41","45","47","48","49","51","53","56"}
YEARS = list(range(2010, 2025))   # try through 2024
YEAR_STR = ",".join(str(y) for y in YEARS)


def fetch_bea(table, linecode, cache_key):
    cp = CACHE_DIR / f"{cache_key}.json"
    if cp.exists():
        print(f"  [cache] {cache_key}")
        return json.load(open(cp))
    params = {"UserID": API_KEY, "method": "GetData", "datasetname": "Regional",
              "TableName": table, "LineCode": linecode, "GeoFips": "COUNTY",
              "Year": YEAR_STR, "ResultFormat": "JSON"}
    print(f"  [fetch] {cache_key}")
    r = requests.get(BASE_URL, params=params, timeout=120); r.raise_for_status()
    data = r.json()
    results = data.get("BEAAPI", {}).get("Results", {})
    if "Error" in results:
        raise RuntimeError(f"BEA error {cache_key}: {results['Error']}")
    json.dump(data, open(cp, "w")); time.sleep(0.5)
    return data


def parse_records(raw, value_col):
    rows = []
    for rec in raw["BEAAPI"]["Results"]["Data"]:
        fips = rec["GeoFips"].strip()
        if len(fips) != 5 or fips[:2] not in STATE_FIPS:
            continue
        rv = rec["DataValue"].strip()
        val = float("nan") if rv in ("(D)","(NA)","(L)","") else None
        if val is None:
            try: val = float(rv.replace(",", ""))
            except ValueError: val = float("nan")
        rows.append({"fips": fips.zfill(5), "year": int(rec["TimePeriod"]), value_col: val})
    return rows


def main():
    target = set(pd.read_csv(MASTER, dtype={"fips": str})["fips"].str.zfill(5))
    print("Fetching CAINC1 (per-capita income)...")
    inc = pd.DataFrame(parse_records(fetch_bea("CAINC1","3","cainc1_county_national_2010_2024"), "per_capita_income"))
    print("Fetching CAGDP1 (real GDP)...")
    gdp = pd.DataFrame(parse_records(fetch_bea("CAGDP1","1","cagdp1_county_national_2010_2024"), "gdp_thousands"))

    df = pd.merge(inc, gdp, on=["fips","year"], how="outer")
    df["fips"] = df["fips"].str.zfill(5)
    df = df[df["fips"].isin(target)].sort_values(["fips","year"]).reset_index(drop=True)
    df[["fips","year","per_capita_income","gdp_thousands"]].to_csv(OUT_CSV, index=False)

    print(f"\nWROTE {len(df)} rows to {OUT_CSV}")
    print(f"counties: {df['fips'].nunique()}/{len(target)} | years {df['year'].min()}-{df['year'].max()}")
    print(f"NaN income {df['per_capita_income'].isna().sum()} | NaN gdp {df['gdp_thousands'].isna().sum()}")
    print("rows per year:\n", df.groupby("year").size().to_string())


if __name__ == "__main__":
    main()
