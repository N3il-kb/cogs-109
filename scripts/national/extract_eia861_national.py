"""
National EIA Form 861 extraction for the 22 states / 169 counties, 2010-2024.
Adapted from data/cache/eia861/extract_eia861.py (3 states -> 22).

Reuses cached f861{year} dirs for 2010-2022; downloads + extracts 2023/2024 ZIPs.
Same customer-weighted county-rate construction. Per-year Excel layout detection is
fragile (EIA shifts columns); each year is wrapped in try/except and skipped + logged
on failure rather than aborting the whole pull.
"""
import os, re, io, zipfile, urllib.request
import pandas as pd, requests
from pathlib import Path

ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
BASE = ROOT / "data" / "cache" / "eia861"
OUT_CSV = ROOT / "data" / "raw" / "eia861_panel_national.csv"
MASTER = ROOT / "data" / "raw" / "county_master_list.csv"
YEARS = list(range(2010, 2025))

# 22 target states (2-letter)
STATES = {"AL","AZ","CA","GA","IL","IN","IA","MO","NE","NV","NM","NC",
          "OH","OK","OR","SC","TN","TX","UT","VA","WA","WY"}
STATE_FIPS = {"AL":"01","AZ":"04","CA":"06","GA":"13","IL":"17","IN":"18","IA":"19","MO":"29",
              "NE":"31","NV":"32","NM":"35","NC":"37","OH":"39","OK":"40","OR":"41","SC":"45",
              "TN":"47","TX":"48","UT":"49","VA":"51","WA":"53","WY":"56"}


def ensure_zip(year):
    """Return path to extracted dir for a year. Handles legacy 2-digit dir names
    (f86110, f86111), downloads/unzips 2023-2024, and rejects non-zip stub downloads."""
    # legacy 2010/2011 dirs are named f86110 / f86111 (2-digit), others f861{year}
    for cand in (BASE / f"f861{year}", BASE / f"f861{str(year)[2:]}"):
        if cand.exists() and any(cand.iterdir()):
            return cand
    d = BASE / f"f861{year}"
    zp = BASE / f"f861{year}.zip"
    if not zp.exists():
        url = f"https://www.eia.gov/electricity/data/eia861/zip/f861{year}.zip"
        print(f"  downloading {url}")
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120); r.raise_for_status()
        zp.write_bytes(r.content)
    if not zipfile.is_zipfile(zp):
        zp.unlink(missing_ok=True)   # drop stub/HTML so reruns retry cleanly
        raise ValueError(f"f861{year}.zip is not a valid zip (likely not yet released / stub)")
    d.mkdir(exist_ok=True)
    with zipfile.ZipFile(zp) as zf:
        zf.extractall(d)
    return d


def find_file(d, *patterns):
    # Prefer the plain file over the _CS_ (combined-statement) variant.
    matches = [f for f in d.rglob("*")
               if all(p.lower() in f.name.lower() for p in patterns)]
    if not matches:
        return None
    matches.sort(key=lambda f: ("_cs_" in f.name.lower(), len(f.name)))
    return matches[0]


def get_fips_lookup():
    url = "https://www2.census.gov/geo/docs/reference/codes/files/national_county.txt"
    r = requests.get(url, timeout=30); r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text), header=None,
                     names=["STATE","STATEFP","COUNTYFP","COUNTYNAME","CLASSFP"], dtype=str)
    df = df[df["STATE"].isin(STATES)].copy()
    df["fips"] = df["STATEFP"].str.zfill(2) + df["COUNTYFP"].str.zfill(3)
    df["county_clean"] = df["COUNTYNAME"].str.upper().str.replace(
        r"\s+(COUNTY|PARISH|MUNICIPALITY|BOROUGH|CENSUS AREA|CITY AND BOROUGH|CITY)$","",regex=True).str.strip()
    lookup = {(r.STATE, r.county_clean): (r.fips, r.COUNTYNAME) for r in df.itertuples()}
    return lookup, df


def normalize_county(name):
    return re.sub(r"\s+(COUNTY|PARISH|MUNICIPALITY|BOROUGH|CENSUS AREA|CITY AND BOROUGH|CITY)$","",
                  str(name).upper().strip()).strip()


def read_sales(d, year):
    f = find_file(d, "sales_ult_cust") or find_file(d, "file2")
    if f is None: raise FileNotFoundError("no sales file")
    raw = pd.read_excel(f, header=None, dtype=str)
    row2 = raw.iloc[2].tolist()
    # Residential revenue = the FIRST "Thousand(s) Dollars" header at/after col 7.
    # Robust to year-to-year left-structure shifts (State/Ownership vs BA Code vs Short Form).
    res_rev = None
    for i in range(7, min(len(row2), 14)):
        if "thousand" in str(row2[i]).lower() and "dollar" in str(row2[i]).lower():
            res_rev = i; break
    if res_rev is None:
        raise ValueError(f"could not locate residential revenue column in {f.name}; row2={row2[6:14]}")
    data = raw.iloc[3:].copy(); data.columns = range(len(data.columns))
    data = data.rename(columns={0:"data_year",1:"utility_id",3:"part",4:"service_type",6:"state",
                                res_rev:"res_revenue_k",res_rev+1:"res_sales_mwh",res_rev+2:"res_customers"})
    data = data[["data_year","utility_id","part","service_type","state",
                 "res_revenue_k","res_sales_mwh","res_customers"]]
    data = data[data["state"].isin(STATES) & (data["part"]=="A")].copy()
    for c in ["res_revenue_k","res_sales_mwh","res_customers"]:
        data[c] = pd.to_numeric(data[c], errors="coerce")
    data["utility_id"] = data["utility_id"].astype(str).str.strip(); data["year"] = year
    return data[["year","utility_id","state","res_revenue_k","res_sales_mwh","res_customers"]]


def read_territory(d):
    f = find_file(d, "service_territory") or find_file(d, "file4")
    if f is None: raise FileNotFoundError("no territory file")
    raw = pd.read_excel(f, header=0, dtype=str)
    raw.columns = [c.strip().lower().replace(" ","_") for c in raw.columns]
    rename = {}
    for c in raw.columns:
        cl = c.lower().replace(" ","_")
        if cl in ("utility_id","utility_number"): rename[c]="utility_id"
        elif cl=="state": rename[c]="state"
        elif cl=="county": rename[c]="county"
    df = raw.rename(columns=rename)
    df = df[df["state"].isin(STATES)].copy()
    for c in ["utility_id","county","state"]:
        df[c] = df[c].astype(str).str.strip()
    return df[["utility_id","state","county"]].drop_duplicates()


def process_year(d, year, lookup):
    sales = read_sales(d, year)
    svc = read_territory(d)
    m = svc.merge(sales, on=["utility_id","state"], how="left"); m["year"] = year
    m["county_clean"] = m["county"].apply(normalize_county)
    m[["fips","county_name"]] = m.apply(
        lambda r: pd.Series(lookup.get((r["state"], r["county_clean"]), (None, r["county"]))), axis=1)
    for c in ["res_revenue_k","res_sales_mwh","res_customers"]:
        m[c] = pd.to_numeric(m[c], errors="coerce")
    m["util_rate"] = (m["res_revenue_k"]*100.0/m["res_sales_mwh"]).where(m["res_sales_mwh"]>0, float("nan"))
    m["weight"] = m["res_customers"].fillna(0); m["rxw"] = m["util_rate"]*m["weight"]
    def wavg(g):
        w, rx = g["weight"], g["rxw"]
        if w.sum()>0 and rx.notna().any(): return rx.sum()/w.sum()
        if g["util_rate"].notna().any(): return g["util_rate"].mean()
        return float("nan")
    agg = m.groupby(["year","fips","county_name","state"], dropna=False).apply(
        lambda g: pd.Series({"elec_rate_cents_kwh": wavg(g)})).reset_index()
    return agg[["year","fips","county_name","state","elec_rate_cents_kwh"]]


def main():
    target = set(p.zfill(5) for p in pd.read_csv(MASTER, dtype=str)["fips"])
    lookup, fips_df = get_fips_lookup()
    all_rows, issues, end_year = [], [], 0
    for year in YEARS:
        try:
            d = ensure_zip(year)
            agg = process_year(d, year, lookup)
            all_rows.append(agg); end_year = max(end_year, year)
            n = agg["elec_rate_cents_kwh"].notna().sum()
            print(f"  {year}: {len(agg)} county rows, {n} with rate")
        except Exception as e:
            issues.append((year, str(e))); print(f"  {year}: FAILED ({e})")

    panel = pd.concat(all_rows, ignore_index=True) if all_rows else pd.DataFrame()
    # full grid: 169 counties x all years
    grid = pd.MultiIndex.from_product([sorted(target), YEARS], names=["fips","year"]).to_frame(index=False)
    panel["fips"] = panel["fips"].astype(str).str.zfill(5)
    final = grid.merge(panel[["fips","year","elec_rate_cents_kwh"]], on=["fips","year"], how="left")
    final["res_sales_mwh"] = float("nan"); final["res_customers"] = float("nan")
    final = final[final["fips"].isin(target)].sort_values(["fips","year"]).reset_index(drop=True)
    final.to_csv(OUT_CSV, index=False)
    filled = final["elec_rate_cents_kwh"].notna().sum()
    print(f"\nWROTE {len(final)} rows | rate non-null {filled}/{len(final)} ({100*filled/len(final):.1f}%)")
    print(f"counties {final['fips'].nunique()}/169 | end year {end_year}")
    if issues:
        print("YEAR ISSUES:", issues)
    print("rate non-null by year:\n", final.groupby("year")["elec_rate_cents_kwh"].apply(lambda s: s.notna().sum()).to_string())


if __name__ == "__main__":
    main()
