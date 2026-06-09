"""
National BLS LAUS unemployment pull for the 169 counties, 2010-2024.
Adapted from data/cache/bls_laus/fetch_laus_flat.py (3 states -> 22 states).

The cached laucnty{10..22}.txt files already contain ALL US counties (the original
script only filtered to 3 states at parse time), so 2010-2022 needs no re-download —
just re-filter. 2023/2024 fetched from Wayback (BLS direct = 403). Falls back gracefully
if a year's snapshot isn't available.
"""
import urllib.request, os, csv, time
from pathlib import Path

ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
CACHE_DIR = ROOT / "data" / "cache" / "bls_laus"
OUT_CSV = ROOT / "data" / "raw" / "bls_laus_panel_national.csv"
MASTER = ROOT / "data" / "raw" / "county_master_list.csv"

# 22 target state FIPS
TARGET_STATES = {"01","04","06","13","17","18","19","29","31","32","35","37",
                 "39","40","41","45","47","48","49","51","53","56"}

# Existing cached snapshots 2010-2022 (from original run) + new attempts for 2023/2024.
# For 2023/2024 try the live BLS URL first (some envs allow it), then Wayback "latest".
NEW_YEARS = {
    23: ["https://www.bls.gov/lau/laucnty23.txt",
         "http://web.archive.org/web/2id_/https://www.bls.gov/lau/laucnty23.txt"],
    24: ["https://www.bls.gov/lau/laucnty24.txt",
         "http://web.archive.org/web/2id_/https://www.bls.gov/lau/laucnty24.txt"],
}
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}


def get_content(yr2):
    cache_path = CACHE_DIR / f"laucnty{yr2:02d}.txt"
    if cache_path.exists():
        return cache_path.read_text(encoding="latin-1")
    if yr2 not in NEW_YEARS:
        return None
    for url in NEW_YEARS[yr2]:
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                content = r.read().decode("latin-1")
            if "CN" in content and len(content) > 10000:   # sanity: looks like a real file
                cache_path.write_text(content, encoding="latin-1")
                print(f"  laucnty{yr2:02d}.txt: downloaded from {url[:50]}")
                return content
        except Exception as e:
            print(f"  laucnty{yr2:02d}.txt: {url[:50]} failed ({e})")
        time.sleep(0.5)
    return None


def parse_line(line):
    if len(line) < 132: return None
    if not line[0:15].strip().startswith("CN"): return None
    sf, cf = line[18:20].strip(), line[25:28].strip()
    if not sf.isdigit() or not cf.isdigit(): return None
    if sf not in TARGET_STATES or cf == "000": return None
    ys = line[81:85].strip()
    if not ys.isdigit(): return None
    def num(s):
        s = s.strip().replace(",", "")
        if s in ("","-","N/A","N.A."): return ""
        try: float(s); return s
        except ValueError: return ""
    return {"fips": sf.zfill(2)+cf.zfill(3), "year": int(ys),
            "unemployment_rate": num(line[123:132]), "labor_force": num(line[85:99])}


def main():
    target = set(p.zfill(5) for p in __import__("pandas").read_csv(MASTER, dtype=str)["fips"])
    all_rows, end_year = [], 0
    for yr2 in range(10, 25):
        content = get_content(yr2)
        if content is None:
            print(f"  {2000+yr2}: NOT AVAILABLE (skipped)"); continue
        rows = [r for r in (parse_line(l) for l in content.split("\n")) if r and r["fips"] in target]
        all_rows.extend(rows); end_year = max(end_year, 2000+yr2)
        print(f"  {2000+yr2}: {len(rows)} rows")
    all_rows.sort(key=lambda r: (r["fips"], r["year"]))
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fips","year","unemployment_rate","labor_force"]); w.writeheader()
        w.writerows(all_rows)
    fips_cov = len(set(r["fips"] for r in all_rows))
    print(f"\nWROTE {len(all_rows)} rows | counties {fips_cov}/169 | end year {end_year}")


if __name__ == "__main__":
    main()
