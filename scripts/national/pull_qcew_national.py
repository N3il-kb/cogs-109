"""
National BLS QCEW pull for the 169 counties, 2010-2024.
Adapted from data/cache/bls_qcew/pull_qcew.py.

Uses the per-county API slice endpoint (api/{year}/a/area/{fips}.csv) for ALL years —
no giant ZIPs needed when we know the 169 target FIPS. Caches each county-year CSV.
Preserves disclosure_code='N' -> NaN suppression and the DP (NAICS 518+519) sum logic.
"""
import io, os, time, zipfile, threading, requests
import pandas as pd
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
CACHE = ROOT / "data" / "cache" / "bls_qcew" / "national_api"
CACHE.mkdir(parents=True, exist_ok=True)
OUT_CSV = ROOT / "data" / "raw" / "bls_qcew_panel_national.csv"
MASTER = ROOT / "data" / "raw" / "county_master_list.csv"

YEARS = list(range(2010, 2025))   # through 2024
API_URL = "https://data.bls.gov/cew/data/api/{year}/a/area/{fips}.csv"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
           "Referer": "https://www.bls.gov/cew/downloadable-data-files.htm"}
_local = threading.local()


def session():
    if not hasattr(_local, "s"):
        s = requests.Session(); s.headers.update(HEADERS); _local.s = s
    return _local.s


def safe_val(val, disc):
    if isinstance(disc, str) and disc.strip() == "N": return float("nan")
    if val is None: return float("nan")
    s = str(val).strip().replace(",", "")
    if s in ("","nan"): return float("nan")
    try: return float(s)
    except ValueError: return float("nan")


def estabs_col(df):
    for c in ("annual_avg_estabs_count","annual_avg_estabs"):
        if c in df.columns: return c
    return None


def extract(df, fips5, year):
    df.columns = df.columns.str.strip()
    mt = (df["own_code"].str.strip()=="0") & (df["industry_code"].str.strip()=="10")
    sub = df[mt]
    if not sub.empty:
        r = sub.iloc[0]; disc = r.get("disclosure_code",""); ec = estabs_col(df)
        total = {"fips":fips5,"year":year,
                 "total_employment":safe_val(r.get("annual_avg_emplvl"),disc),
                 "total_wages":safe_val(r.get("total_annual_wages"),disc),
                 "avg_annual_wage":safe_val(r.get("avg_annual_pay"),disc),
                 "total_establishments":safe_val(r.get(ec),disc) if ec else float("nan")}
    else:
        total = {"fips":fips5,"year":year,"total_employment":float("nan"),"total_wages":float("nan"),
                 "avg_annual_wage":float("nan"),"total_establishments":float("nan")}
    dp = df[df["industry_code"].str.strip().isin(["518","519"])]
    dp_row = None
    if not dp.empty:
        dc = dp.get("disclosure_code", pd.Series([""]*len(dp)))
        vals = [safe_val(e,d) for e,d in zip(dp["annual_avg_emplvl"], dc)]
        present = [v for v in vals if not pd.isna(v)]
        dp_row = {"fips":fips5,"year":year,
                  "data_processing_employment": sum(present) if present else float("nan")}
    return total, dp_row


def fetch_county_year(fips5, year, retries=3):
    cp = CACHE / f"{fips5}_{year}.csv"
    if cp.exists():
        txt = cp.read_text()
        if txt.strip() == "__404__": return None, None
        try: return extract(pd.read_csv(io.StringIO(txt), dtype=str, low_memory=False), fips5, year)
        except Exception: pass
    url = API_URL.format(year=year, fips=fips5)
    for attempt in range(retries):
        try:
            r = session().get(url, timeout=60)
            if r.status_code == 404:
                cp.write_text("__404__"); return None, None
            r.raise_for_status()
            cp.write_text(r.text)
            return extract(pd.read_csv(io.StringIO(r.text), dtype=str, low_memory=False), fips5, year)
        except Exception as e:
            if attempt < retries-1: time.sleep(2**attempt)
            else:
                print(f"  ERR {fips5}/{year}: {e}")
                return {"fips":fips5,"year":year,"total_employment":float("nan"),"total_wages":float("nan"),
                        "avg_annual_wage":float("nan"),"total_establishments":float("nan")}, None


# ---- ZIP path for 2010-2013 (API slice 404s for these early years) ----
ZIP_DIR = ROOT / "data" / "cache" / "bls_qcew"

def parse_zip_year(year, fips_set):
    """Parse the nationwide {year}_annual_by_area.zip for target counties."""
    zp = ZIP_DIR / f"{year}_annual_by_area.zip"
    if not zp.exists():
        print(f"  {year}: ZIP not cached, skipping"); return [], []
    yt, yd = [], []
    with zipfile.ZipFile(zp) as zf:
        for fname in zf.namelist():
            base = os.path.basename(fname)
            prefix = f"{year}.annual "
            if not base.startswith(prefix): continue
            rest = base[len(prefix):]
            if len(rest) < 6: continue
            fips5 = rest[:5]
            if fips5 not in fips_set: continue
            with zf.open(fname) as fh:
                try: df = pd.read_csv(fh, dtype=str, low_memory=False)
                except Exception: continue
            t, dp = extract(df, fips5, year)
            yt.append(t)
            if dp: yd.append(dp)
    return yt, yd


def main():
    fips_list = sorted(set(p.zfill(5) for p in pd.read_csv(MASTER, dtype=str)["fips"]))
    fips_set = set(fips_list)
    print(f"QCEW: {len(fips_list)} counties x {len(YEARS)} years")
    totals, dps = [], []
    for year in YEARS:
        if year <= 2013:
            yt, yd = parse_zip_year(year, fips_set)   # API has no early years
        else:
            yt, yd = [], []
            with ThreadPoolExecutor(max_workers=8) as ex:
                futs = {ex.submit(fetch_county_year, f, year): f for f in fips_list}
                for fut in as_completed(futs):
                    t, dp = fut.result()
                    if t is not None: yt.append(t)
                    if dp is not None: yd.append(dp)
        totals += yt; dps += yd
        print(f"  {year}: {len(yt)} county rows")
    pt = pd.DataFrame(totals)
    pd_ = pd.DataFrame(dps) if dps else pd.DataFrame(columns=["fips","year","data_processing_employment"])
    panel = pt.merge(pd_, on=["fips","year"], how="left") if len(pd_) else pt.assign(data_processing_employment=float("nan"))
    panel["fips"] = panel["fips"].astype(str).str.zfill(5)
    panel = panel[["fips","year","total_employment","total_wages","avg_annual_wage",
                   "data_processing_employment","total_establishments"]].sort_values(["fips","year"])
    panel.to_csv(OUT_CSV, index=False)
    print(f"\nWROTE {len(panel)} rows | counties {panel['fips'].nunique()}/169 | years {panel['year'].min()}-{panel['year'].max()}")
    print("NaN counts:\n", panel.isna().sum().to_string())


if __name__ == "__main__":
    main()
