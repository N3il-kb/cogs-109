"""
Merge the 7 national sources + treatment columns into data/panel_master_national.csv.
Does NOT touch the original data/panel_master.csv.

Sources:
  bea_panel_national.csv, census_acs_panel_national.csv (incl wfh_rate),
  eia861_panel_national.csv, bls_qcew_panel_national.csv, bls_laus_panel_national.csv,
  covid_panel_national.csv
Treatment/role flags from data/raw/county_master_list.csv.
"""
import pandas as pd, numpy as np
from pathlib import Path

ROOT = Path("/Users/neilk/Desktop/School/Yr 3/Q3/COGS 109/cogs-109")
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "panel_master_national.csv"

YEARS = list(range(2010, 2025))

def load(name):
    return pd.read_csv(RAW / name, dtype={"fips": str})

bea  = load("bea_panel_national.csv")
acs  = load("census_acs_panel_national.csv")
eia  = load("eia861_panel_national.csv").rename(
        columns={"res_sales_mwh": "residential_sales_mwh", "res_customers": "residential_customers"})
qcew = load("bls_qcew_panel_national.csv")
laus = load("bls_laus_panel_national.csv")
cov  = load("covid_panel_national.csv")
master = load("county_master_list.csv")

for df in (bea, acs, eia, qcew, laus, cov, master):
    df["fips"] = df["fips"].str.zfill(5)

# Build a complete 169 x 15 grid so every county-year exists even where a source is missing
fips_all = sorted(master["fips"].unique())
grid = pd.MultiIndex.from_product([fips_all, YEARS], names=["fips", "year"]).to_frame(index=False)

panel = (grid
    .merge(bea, on=["fips","year"], how="left")
    .merge(acs.drop(columns=[c for c in ("county_name","state") if c in acs], errors="ignore"),
           on=["fips","year"], how="left")
    .merge(eia.drop(columns=[c for c in ("county_name","state") if c in eia], errors="ignore"),
           on=["fips","year"], how="left")
    .merge(qcew, on=["fips","year"], how="left")
    .merge(laus, on=["fips","year"], how="left")
    .merge(cov,  on=["fips","year"], how="left"))

# Attach county/state + role/flags from master
mcols = master[["fips","county","state","role","dc_opening_year","primary_operator",
                "all_operators","analysis_diD","classifier_dc","cohort_flags"]].copy()
panel = panel.merge(mcols, on="fips", how="left")

# Treatment variables
panel["is_treated"] = (panel["role"] == "treated").astype(int)
panel["dc_opening_year"] = pd.to_numeric(panel["dc_opening_year"], errors="coerce")
panel["dc_active"] = np.where(
    (panel["is_treated"] == 1) & panel["dc_opening_year"].notna(),
    (panel["year"] >= panel["dc_opening_year"]).astype(int), 0)
panel["years_since_dc"] = np.where(
    panel["dc_active"] == 1, panel["year"] - panel["dc_opening_year"], 0)

panel["fips"] = panel["fips"].astype(str).str.zfill(5)
panel = panel.sort_values(["fips","year"]).reset_index(drop=True)

# Column order: keys, outcomes/controls, covid/wfh, treatment/flags
col_order = ["fips","county","state","year",
    "per_capita_income","gdp_thousands","median_income","poverty_rate","pct_bachelors",
    "pop_density","unemployment_acs","median_age","elec_rate_cents_kwh",
    "residential_sales_mwh","residential_customers",
    "total_employment","total_wages","avg_annual_wage","data_processing_employment",
    "total_establishments","unemployment_rate","labor_force",
    "wfh_rate","covid_deaths_per_100k","covid_cases_per_100k",
    "role","is_treated","dc_opening_year","dc_active","years_since_dc",
    "primary_operator","all_operators","analysis_diD","classifier_dc","cohort_flags"]
panel = panel[[c for c in col_order if c in panel.columns]]
panel.to_csv(OUT, index=False)

print(f"WROTE {OUT}")
print(f"shape: {panel.shape[0]} rows x {panel.shape[1]} cols")
print(f"counties: {panel['fips'].nunique()} | years {panel['year'].min()}-{panel['year'].max()}")
print(f"treated rows {(panel['is_treated']==1).sum()} | dc_active=1 rows {(panel['dc_active']==1).sum()}")
print(f"analysis_diD=1 counties: {panel[panel['analysis_diD']==1]['fips'].nunique()}")
print(f"classifier_dc=1 counties: {panel[panel['classifier_dc']==1]['fips'].nunique()}")
