"""
NYT COVID-19 county data -> county-year deaths/cases per 100k for the 169 counties.
Source: https://github.com/nytimes/covid-19-data (us-counties-{year}.csv, public, no key).

Measure: ANNUAL INCREMENTAL deaths/cases (year-end cumulative minus prior year-end),
per 100k population. Cumulative-difference avoids double counting; the annual increment
is the within-year burden. Pre-2020 = 0. Population from cached ACS B01003 (county_pop_2019).
"""
import io, urllib.request
import pandas as pd
from pathlib import Path

ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
CACHE = ROOT / "data" / "cache" / "covid"
CACHE.mkdir(parents=True, exist_ok=True)
OUT_CSV = ROOT / "data" / "raw" / "covid_panel_national.csv"
MASTER = ROOT / "data" / "raw" / "county_master_list.csv"
POP = ROOT / "data" / "cache" / "county_pop_2019.csv"

# NYT split files by year (2020,2021,2022,2023 final)
URLS = {y: f"https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties-{y}.csv"
        for y in (2020, 2021, 2022, 2023)}
ALL_YEARS = list(range(2010, 2025))   # panel years; covid populated 2020+


def get_year(y):
    cp = CACHE / f"us-counties-{y}.csv"
    if cp.exists():
        return pd.read_csv(cp, dtype={"fips": str})
    print(f"  downloading NYT {y}...")
    req = urllib.request.Request(URLS[y], headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        txt = r.read().decode()
    cp.write_text(txt)
    return pd.read_csv(io.StringIO(txt), dtype={"fips": str})


def main():
    master = pd.read_csv(MASTER, dtype={"fips": str})
    target = set(master["fips"].str.zfill(5))
    pop = pd.read_csv(POP, dtype={"fips": str}).set_index("fips")["population"].to_dict()

    # year-end cumulative per county (last observation each year)
    yearend = {}   # (fips, year) -> cumulative deaths/cases
    for y in (2020, 2021, 2022, 2023):
        df = get_year(y)
        df["fips"] = df["fips"].str.zfill(5)
        df = df[df["fips"].isin(target)].copy()
        df["date"] = pd.to_datetime(df["date"])
        # last record per county in the year = year-end cumulative
        last = df.sort_values("date").groupby("fips").tail(1)
        for _, r in last.iterrows():
            yearend[(r["fips"], y)] = (r.get("deaths"), r.get("cases"))
        print(f"  {y}: {last['fips'].nunique()} counties with data")

    rows = []
    for fips in sorted(target):
        P = pop.get(fips)
        prev_d = prev_c = 0.0
        for y in ALL_YEARS:
            if y < 2020:
                rows.append({"fips": fips, "year": y, "covid_deaths_per_100k": 0.0,
                             "covid_cases_per_100k": 0.0})
                continue
            cum_d, cum_c = yearend.get((fips, y), (None, None))
            cum_d = float(cum_d) if pd.notna(cum_d) else prev_d
            cum_c = float(cum_c) if pd.notna(cum_c) else prev_c
            inc_d = max(0.0, cum_d - prev_d)
            inc_c = max(0.0, cum_c - prev_c)
            prev_d, prev_c = cum_d, cum_c
            if P and P > 0:
                rows.append({"fips": fips, "year": y,
                             "covid_deaths_per_100k": round(1e5 * inc_d / P, 3),
                             "covid_cases_per_100k": round(1e5 * inc_c / P, 3)})
            else:
                rows.append({"fips": fips, "year": y,
                             "covid_deaths_per_100k": float("nan"),
                             "covid_cases_per_100k": float("nan")})

    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False)
    print(f"\nWROTE {len(out)} rows | counties {out['fips'].nunique()}/169 | years {out['year'].min()}-{out['year'].max()}")
    chk = out.groupby("year")[["covid_deaths_per_100k", "covid_cases_per_100k"]].mean()
    print("mean by year (0 pre-2020 expected):\n", chk.round(2).to_string())


if __name__ == "__main__":
    main()
