"""
Phase 5b: extract 2010-2012 baseline features for the 400-county unmatched pool,
entirely from cached raw files (no API calls — 2010-2012 QCEW comes from nationwide ZIPs,
LAUS from flat files, ACS/BEA from cached JSON, EIA from cached Excel).

9 M3 features (same as Phase 5): per_capita_income, total_employment, avg_annual_wage,
elec_rate_cents_kwh, poverty_rate, unemployment_rate, pop_density, median_age, pct_bachelors.

Output: data/raw/unmatched_pool_baseline.csv (one row per pool county = 2010-2012 mean).
Does NOT touch panel_master_national.csv or the master list.
"""
import json, os, io, zipfile, glob, hashlib
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
CACHE = ROOT / "data" / "cache"
POOL = pd.read_csv(CACHE / "_unmatched_pool.csv", dtype={"fips": str})
POOL["fips"] = POOL["fips"].str.zfill(5)
pool_fips = set(POOL["fips"])
YEARS = [2010, 2011, 2012]
print(f"pool: {len(pool_fips)} counties")

# ── BEA per_capita_income (cached nationwide json) ──
def bea_income():
    raw = json.load(open(CACHE / "bea" / "cainc1_county_national_2010_2024.json"))
    rows = []
    # also map VA combined-area codes -> our standalone county (same crosswalk as Phase 3)
    COMBO = {"51015":"51907","51680":"51911","51035":"51913","51730":"51918",
             "51059":"51919","51095":"51931","51153":"51942"}
    inv = {v: k for k, v in COMBO.items()}
    for d in raw["BEAAPI"]["Results"]["Data"]:
        g = d["GeoFips"].strip()
        y = int(d["TimePeriod"])
        if y not in YEARS: continue
        fips = g.zfill(5)
        if fips in inv: fips = inv[fips]      # combined-area -> county
        if fips not in pool_fips: continue
        rv = d["DataValue"].strip()
        try: v = float(rv.replace(",", ""))
        except ValueError: v = np.nan
        rows.append({"fips": fips, "year": y, "per_capita_income": v})
    return pd.DataFrame(rows)

# ── ACS (cached per-state-year JSON; re-extract for 2010-2012) ──
def acs_features():
    # rebuild the exact URLs the national ACS script used, hit the cache by md5
    KEY = None
    for line in open(ROOT / ".env"):
        if line.startswith("CENSUS_API_KEY="): KEY = line.split("=",1)[1].strip()
    ST = {"01","04","06","13","17","18","19","29","31","32","35","37",
          "39","40","41","45","47","48","49","51","53","56"}
    BASE = "https://api.census.gov/data/{year}/acs/acs5"
    SUBJ = "https://api.census.gov/data/{year}/acs/acs5/subject"
    SENT = {-888888888,-666666666,-999999999,-222222222,-333333333}
    def cp(url): return CACHE / "census_acs" / f"{hashlib.md5(url.encode()).hexdigest()}.json"
    def pv(v):
        if v is None: return np.nan
        try:
            f = float(v); return np.nan if (f in SENT or f < -1e5) else f
        except: return np.nan
    # gazetteer land area for pop_density
    gaz = pd.read_csv(CACHE / "census_acs" / "2020_Gaz_counties_national.zip", sep="\t",
                      dtype={"GEOID": str}, usecols=["GEOID","ALAND_SQMI"], encoding="latin-1")
    gaz["fips"] = gaz["GEOID"].str.strip().str.zfill(5)
    land = dict(zip(gaz["fips"], gaz["ALAND_SQMI"]))
    rows = []
    for y in YEARS:
        for sf in ST:
            bu = f"{BASE.format(year=y)}?get=NAME,B19013_001E,B01003_001E,B01002_001E&for=county:*&in=state:{sf}&key={KEY}"
            su = (f"{SUBJ.format(year=y)}?get=S2301_C04_001E,"
                  f"{'S1501_C01_015E' if y<=2014 else 'S1501_C02_015E'}"
                  f"{',S1701_C03_001E' if y>=2012 else ''}&for=county:*&in=state:{sf}&key={KEY}")
            if not cp(bu).exists():  # should exist from Phase 3; skip if not
                continue
            b = json.load(open(cp(bu)))
            s = json.load(open(cp(su))) if cp(su).exists() else []
            sidx = {r[s[0].index("county")].zfill(3): dict(zip(s[0], r)) for r in s[1:]} if len(s)>1 else {}
            for r in b[1:]:
                d = dict(zip(b[0], r)); cf = d["county"].zfill(3); fips = sf + cf
                if fips not in pool_fips: continue
                srow = sidx.get(cf, {})
                pop = pv(d.get("B01003_001E")); aland = land.get(fips)
                rows.append({"fips": fips, "year": y,
                    "median_age": pv(d.get("B01002_001E")),
                    "pop_density": (pop/aland if pop and aland and aland>0 else np.nan),
                    "pct_bachelors": pv(srow.get("S1501_C01_015E" if y<=2014 else "S1501_C02_015E")),
                    "poverty_rate": pv(srow.get("S1701_C03_001E")) if y>=2012 else np.nan})
    return pd.DataFrame(rows)

# ── LAUS unemployment_rate (cached nationwide flat files) ──
def laus():
    rows = []
    for y in YEARS:
        yr2 = y - 2000
        path = CACHE / "bls_laus" / f"laucnty{yr2:02d}.txt"
        if not path.exists(): continue
        for line in path.read_text(encoding="latin-1").split("\n"):
            if len(line) < 132 or not line[0:15].strip().startswith("CN"): continue
            sf, cf = line[18:20].strip(), line[25:28].strip()
            if not (sf.isdigit() and cf.isdigit()) or cf == "000": continue
            fips = sf.zfill(2)+cf.zfill(3)
            if fips not in pool_fips: continue
            rate = line[123:132].strip().replace(",", "")
            try: v = float(rate)
            except: v = np.nan
            rows.append({"fips": fips, "year": y, "unemployment_rate": v})
    return pd.DataFrame(rows)

# ── QCEW total_employment + avg_annual_wage (2010-2012 nationwide ZIPs) ──
def qcew():
    rows = []
    for y in YEARS:
        zp = CACHE / "bls_qcew" / f"{y}_annual_by_area.zip"
        if not zp.exists(): continue
        with zipfile.ZipFile(zp) as zf:
            for fn in zf.namelist():
                base = os.path.basename(fn); pre = f"{y}.annual "
                if not base.startswith(pre): continue
                fips = base[len(pre):][:5]
                if fips not in pool_fips: continue
                with zf.open(fn) as fh:
                    try: df = pd.read_csv(fh, dtype=str, low_memory=False)
                    except: continue
                df.columns = df.columns.str.strip()
                m = (df["own_code"].str.strip()=="0") & (df["industry_code"].str.strip()=="10")
                sub = df[m]
                if sub.empty: continue
                r = sub.iloc[0]; disc = str(r.get("disclosure_code","")).strip()
                def sv(x):
                    if disc == "N": return np.nan
                    try: return float(str(x).replace(",",""))
                    except: return np.nan
                rows.append({"fips": fips, "year": y,
                    "total_employment": sv(r.get("annual_avg_emplvl")),
                    "avg_annual_wage": sv(r.get("avg_annual_pay"))})
    return pd.DataFrame(rows)

# ── EIA elec_rate (re-run national extractor logic for pool, 2010-2012) ──
def eia():
    import re
    BASE = CACHE / "eia861"
    url = "https://www2.census.gov/geo/docs/reference/codes/files/national_county.txt"
    import requests
    fdf = pd.read_csv(io.StringIO(requests.get(url, timeout=30).text), header=None,
            names=["STATE","STATEFP","COUNTYFP","COUNTYNAME","CLASSFP"], dtype=str)
    fdf["fips"] = fdf["STATEFP"].str.zfill(2)+fdf["COUNTYFP"].str.zfill(3)
    fdf["cc"] = fdf["COUNTYNAME"].str.upper().str.replace(
        r"\s+(COUNTY|PARISH|MUNICIPALITY|BOROUGH|CENSUS AREA|CITY AND BOROUGH|CITY)$","",regex=True).str.strip()
    look = {(r.STATE, r.cc): r.fips for r in fdf.itertuples()}
    def norm(n): return re.sub(r"\s+(COUNTY|PARISH|MUNICIPALITY|BOROUGH|CENSUS AREA|CITY AND BOROUGH|CITY)$","",str(n).upper().strip()).strip()
    STATES = set(fdf.loc[fdf["fips"].isin(pool_fips),"STATE"].unique())
    def ff(d, *pats):
        ms = [f for f in d.rglob("*") if all(p.lower() in f.name.lower() for p in pats)]
        ms.sort(key=lambda f: ("_cs_" in f.name.lower(), len(f.name)))
        return ms[0] if ms else None
    rows = []
    for y in YEARS:
        dpath = BASE / f"f861{y}"
        if not dpath.exists(): dpath = BASE / f"f861{str(y)[2:]}"
        if not dpath.exists(): continue
        sf = ff(dpath, "sales_ult_cust") or ff(dpath, "file2")
        tf = ff(dpath, "service_territory") or ff(dpath, "file4")
        if not (sf and tf): continue
        raw = pd.read_excel(sf, header=None, dtype=str); row2 = raw.iloc[2].tolist()
        rr = next((i for i in range(7, min(len(row2),14))
                   if "thousand" in str(row2[i]).lower() and "dollar" in str(row2[i]).lower()), None)
        if rr is None: continue
        dat = raw.iloc[3:].copy(); dat.columns = range(len(dat.columns))
        dat = dat.rename(columns={1:"uid",3:"part",6:"state",rr:"rev",rr+1:"mwh",rr+2:"cust"})
        dat = dat[dat["state"].isin(STATES) & (dat["part"]=="A")]
        for c in ["rev","mwh","cust"]: dat[c] = pd.to_numeric(dat[c], errors="coerce")
        dat["uid"] = dat["uid"].astype(str).str.strip()
        terr = pd.read_excel(tf, header=0, dtype=str); terr.columns=[c.strip().lower().replace(" ","_") for c in terr.columns]
        ren = {}
        for c in terr.columns:
            cl=c.lower().replace(" ","_")
            if cl in ("utility_id","utility_number"): ren[c]="uid"
            elif cl=="state": ren[c]="state"
            elif cl=="county": ren[c]="county"
        terr = terr.rename(columns=ren)
        terr = terr[terr["state"].isin(STATES)][["uid","state","county"]].drop_duplicates()
        terr["uid"]=terr["uid"].astype(str).str.strip()
        m = terr.merge(dat, on=["uid","state"], how="left")
        m["fips"] = m.apply(lambda r: look.get((r["state"], norm(r["county"]))), axis=1)
        m["rate"] = (m["rev"]*100.0/m["mwh"]).where(m["mwh"]>0, np.nan)
        m["w"] = m["cust"].fillna(0); m["rw"] = m["rate"]*m["w"]
        for fips, g in m.groupby("fips"):
            if fips not in pool_fips: continue
            w, rw = g["w"].sum(), g["rw"].sum()
            rate = (rw/w if w>0 and g["rw"].notna().any() else
                    (g["rate"].mean() if g["rate"].notna().any() else np.nan))
            rows.append({"fips": fips, "year": y, "elec_rate_cents_kwh": rate})
    return pd.DataFrame(rows)

print("extracting BEA..."); b = bea_income()
print("extracting ACS..."); a = acs_features()
print("extracting LAUS..."); l = laus()
print("extracting QCEW..."); q = qcew()
print("extracting EIA..."); e = eia()

# merge to long, then collapse to 2010-2012 mean per county
long = b
for df in (a, l, q, e):
    long = long.merge(df, on=["fips","year"], how="outer") if len(df) else long
FEATS = ["per_capita_income","total_employment","avg_annual_wage","elec_rate_cents_kwh",
         "poverty_rate","unemployment_rate","pop_density","median_age","pct_bachelors"]
for f in FEATS:
    if f not in long: long[f] = np.nan
base = long[long["fips"].isin(pool_fips)].groupby("fips")[FEATS].mean().reset_index()
# ensure all 400 present
base = POOL[["fips","state"]].merge(base, on="fips", how="left")
base.to_csv(ROOT / "data" / "raw" / "unmatched_pool_baseline.csv", index=False)

print(f"\nWROTE unmatched_pool_baseline.csv: {len(base)} counties")
print("per-feature coverage (non-NaN / 400):")
for f in FEATS:
    n = base[f].notna().sum()
    print(f"  {f:22s} {n}/400  ({100*n/len(base):.0f}%)")
