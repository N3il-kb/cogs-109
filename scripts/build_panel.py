"""
build_panel.py — Merge all raw CSVs into panel_master.csv

Sources merged:
  - data/raw/bea_panel.csv
  - data/raw/census_acs_panel.csv
  - data/raw/eia861_panel.csv       (note: res_sales_mwh + res_customers are all-NaN by design)
  - data/raw/bls_qcew_panel.csv
  - data/raw/bls_laus_panel.csv
  - data/raw/treatment.csv

Treatment timing (verified from primary sources):
  - Licking County OH  (39089): Meta operational 2020
  - Henrico County VA  (51087): Meta operational 2020
  - Sarpy County NE    (31153): Meta operational 2019
  NOTE: Sarpy County also has a Google data center (groundbreaking Oct 2019) — compound treatment.

Known contaminated control counties excluded from control pool:
  - 39049 Franklin OH    (Google New Albany ~2022, borders Licking County)
  - 51107 Loudoun VA     (AWS/Google/Microsoft data center alley)
  - 51153 Prince William VA (AWS Manassas)
  - 51059 Fairfax VA     (AWS/Microsoft)
  - 51117 Mecklenburg VA (Microsoft Boydton ~2011)
  - 31055 Douglas NE     (Google announced ~2022)
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
RAW  = ROOT / "data" / "raw"
OUT  = ROOT / "data"

TREATED_FIPS = {"39089", "51087", "31153"}

CONTAMINATED_FIPS = {
    "39049",  # Franklin OH — Google New Albany ~2022
    "51107",  # Loudoun VA — AWS/Google/Microsoft alley
    "51153",  # Prince William VA — AWS Manassas
    "51059",  # Fairfax VA — AWS/Microsoft
    "51117",  # Mecklenburg VA — Microsoft Boydton ~2011
    "31055",  # Douglas NE — Google ~2022
}

# ── Load all sources ───────────────────────────────────────────────────────────
print("Loading raw CSVs...")

bea = pd.read_csv(RAW / "bea_panel.csv",         dtype={"fips": str})
acs = pd.read_csv(RAW / "census_acs_panel.csv",   dtype={"fips": str})
eia = pd.read_csv(RAW / "eia861_panel.csv",       dtype={"fips": str})
qcew= pd.read_csv(RAW / "bls_qcew_panel.csv",    dtype={"fips": str})
laus= pd.read_csv(RAW / "bls_laus_panel.csv",    dtype={"fips": str})
trt = pd.read_csv(RAW / "treatment.csv",          dtype={"fips": str})

# Normalise FIPS to 5-char zero-padded in every frame
for df in [bea, acs, eia, qcew, laus, trt]:
    df["fips"] = df["fips"].str.zfill(5)

# Rename EIA column to match spec (agent used res_sales_mwh)
eia = eia.rename(columns={
    "res_sales_mwh":   "residential_sales_mwh",
    "res_customers":   "residential_customers",
})

# ── Full outer join on (fips, year) ───────────────────────────────────────────
print("Merging on (fips, year)...")

panel = (
    bea
    .merge(acs.drop(columns=["county_name", "state"], errors="ignore"),
           on=["fips", "year"], how="outer")
    .merge(eia.drop(columns=["county_name", "state"], errors="ignore"),
           on=["fips", "year"], how="outer")
    .merge(qcew, on=["fips", "year"], how="outer")
    .merge(laus, on=["fips", "year"], how="outer")
)

# Consolidate county_name / state from whichever source has it
for col in ["county_name", "state"]:
    candidates = [c for c in panel.columns if c.startswith(col)]
    if len(candidates) > 1:
        panel[col] = panel[candidates[0]].combine_first(panel[candidates[1]])
        panel = panel.drop(columns=candidates[1:])

# ── Add treatment variables ────────────────────────────────────────────────────
print("Adding treatment columns...")

# Merge opening year from treatment table
trt_map = trt.set_index("fips")[["dc_opening_year", "dc_company"]].to_dict("index")

panel["is_treated"]    = panel["fips"].isin(TREATED_FIPS).astype(int)
panel["dc_opening_year"] = panel["fips"].map(
    lambda f: trt_map[f]["dc_opening_year"] if f in trt_map else np.nan
)
panel["dc_active"] = np.where(
    panel["is_treated"] == 1,
    (panel["year"] >= panel["dc_opening_year"]).astype(int),
    0
)
panel["years_since_dc"] = np.where(
    panel["dc_active"] == 1,
    panel["year"] - panel["dc_opening_year"],
    0
)

# ── Flag contaminated control counties ────────────────────────────────────────
panel["contaminated_control"] = (
    (~panel["fips"].isin(TREATED_FIPS)) &
    (panel["fips"].isin(CONTAMINATED_FIPS))
).astype(int)

# ── Enforce FIPS as zero-padded string ────────────────────────────────────────
panel["fips"] = panel["fips"].astype(str).str.zfill(5)

# ── Sort ───────────────────────────────────────────────────────────────────────
panel = panel.sort_values(["fips", "year"]).reset_index(drop=True)

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION CHECKS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("VALIDATION CHECKS")
print("="*60)

issues = []

# 1. All 3 treated counties present
for fips in TREATED_FIPS:
    if fips not in panel["fips"].values:
        issues.append(f"FAIL: Treated county {fips} missing from panel")
    else:
        print(f"  ✓ Treated county {fips} present")

# 2. Control county count (excluding contaminated)
control_fips = set(panel["fips"].unique()) - TREATED_FIPS - CONTAMINATED_FIPS
n_controls = len(control_fips)
if n_controls < 100:
    issues.append(f"FAIL: Only {n_controls} clean control counties (need ≥100)")
else:
    print(f"  ✓ {n_controls} clean control counties (excl. {len(CONTAMINATED_FIPS)} contaminated)")

# 3. All years 2010-2022 covered per county
years_required = set(range(2010, 2023))
missing_years = []
for fips, grp in panel.groupby("fips"):
    yrs = set(grp["year"].astype(int))
    missing = years_required - yrs
    if missing:
        missing_years.append((fips, sorted(missing)))
if missing_years:
    print(f"  ⚠ {len(missing_years)} counties missing some years:")
    for fips, yrs in missing_years[:10]:
        print(f"      {fips}: {yrs}")
    if len(missing_years) > 10:
        print(f"      ... and {len(missing_years)-10} more")
else:
    print("  ✓ All counties have all years 2010–2022")

# 4. Treatment timing check
timing = {
    "39089": 2020,  # Licking OH
    "51087": 2020,  # Henrico VA
    "31153": 2019,  # Sarpy NE
}
for fips, expected_year in timing.items():
    rows = panel[panel["fips"] == fips]
    if rows.empty:
        issues.append(f"FAIL: {fips} not found for timing check")
        continue
    actual = rows["dc_opening_year"].dropna().unique()
    if len(actual) == 0 or int(actual[0]) != expected_year:
        issues.append(f"FAIL: {fips} opening year is {actual}, expected {expected_year}")
    else:
        print(f"  ✓ {fips} treatment year = {expected_year}")

# 5. Outlier check (>5 SD from mean) on continuous variables
print("\n  Outlier check (|z| > 5):")
continuous_cols = [
    "per_capita_income", "gdp_thousands",
    "median_income", "poverty_rate", "pct_bachelors",
    "pop_density", "unemployment_acs", "median_age",
    "elec_rate_cents_kwh",
    "total_employment", "avg_annual_wage",
    "unemployment_rate", "labor_force",
]
outlier_found = False
for col in continuous_cols:
    if col not in panel.columns:
        continue
    s = panel[col].dropna()
    if len(s) < 10:
        continue
    z = (s - s.mean()) / s.std()
    n_out = (z.abs() > 5).sum()
    if n_out > 0:
        worst = z.abs().max()
        print(f"    ⚠ {col}: {n_out} values >5 SD (max |z|={worst:.1f})")
        outlier_found = True
if not outlier_found:
    print("    ✓ No outliers >5 SD in any continuous variable")

# Summary
print("\n" + "="*60)
if issues:
    print("ISSUES FOUND:")
    for issue in issues:
        print(f"  {issue}")
else:
    print("All validation checks passed.")

# ── Summary stats ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY STATISTICS")
print("="*60)
print(f"Panel shape: {panel.shape[0]} rows × {panel.shape[1]} columns")
print(f"Unique counties: {panel['fips'].nunique()}")
print(f"  Treated:             {panel[panel['is_treated']==1]['fips'].nunique()}")
print(f"  Contaminated control:{panel[panel['contaminated_control']==1]['fips'].nunique()}")
print(f"  Clean control:       {n_controls}")
print(f"Years: {panel['year'].min()} – {panel['year'].max()}")
print(f"\nMissing values per column:")
for col in panel.columns:
    n = panel[col].isna().sum()
    if n > 0:
        print(f"  {col}: {n} ({100*n/len(panel):.1f}%)")

desc = panel[continuous_cols].describe().loc[["mean","std","min","max"]]
print(f"\nContinuous variable summary:\n{desc.to_string()}")

# ── Save ───────────────────────────────────────────────────────────────────────
out_path = OUT / "panel_master.csv"
panel.to_csv(out_path, index=False, encoding="utf-8")
print(f"\nSaved: {out_path}  ({len(panel)} rows)")

# ── Data quality report ────────────────────────────────────────────────────────
report_path = OUT / "data_quality_report.md"
with open(report_path, "w") as f:
    f.write("# Data Quality Report\n\n")
    f.write(f"Generated by `scripts/build_panel.py`\n\n")
    f.write("## Panel Overview\n\n")
    f.write(f"- **Rows:** {len(panel)}\n")
    f.write(f"- **Columns:** {panel.shape[1]}\n")
    f.write(f"- **Unique counties:** {panel['fips'].nunique()}\n")
    f.write(f"  - Treated: {panel[panel['is_treated']==1]['fips'].nunique()}\n")
    f.write(f"  - Contaminated controls (excluded from regression): {panel[panel['contaminated_control']==1]['fips'].nunique()}\n")
    f.write(f"  - Clean controls: {n_controls}\n")
    f.write(f"- **Years:** {panel['year'].min()}–{panel['year'].max()}\n\n")

    f.write("## Treatment Notes\n\n")
    f.write("Opening years verified from primary sources (Meta newsroom, Baxtel, local news):\n\n")
    f.write("| FIPS | County | Opening Year | Notes |\n")
    f.write("|------|--------|-------------|-------|\n")
    f.write("| 39089 | Licking County OH | 2020 | Groundbreaking 2017, operational Feb 2020 |\n")
    f.write("| 51087 | Henrico County VA | 2020 | Operational Aug 2020 (Meta newsroom confirmed) |\n")
    f.write("| 31153 | Sarpy County NE   | 2019 | ⚠ Google also opened in Sarpy County Oct 2019 — compound treatment |\n\n")

    f.write("## Contaminated Control Counties (excluded)\n\n")
    f.write("| FIPS | County | Reason |\n")
    f.write("|------|--------|--------|\n")
    f.write("| 39049 | Franklin OH | Google New Albany ~2022; borders Licking County |\n")
    f.write("| 51107 | Loudoun VA | AWS/Google/Microsoft data center alley |\n")
    f.write("| 51153 | Prince William VA | AWS Manassas |\n")
    f.write("| 51059 | Fairfax VA | AWS/Microsoft |\n")
    f.write("| 51117 | Mecklenburg VA | Microsoft Boydton ~2011 |\n")
    f.write("| 31055 | Douglas NE | Google announced ~2022 |\n\n")

    f.write("## Missing Data by Column\n\n")
    f.write("| Column | N Missing | % Missing | Notes |\n")
    f.write("|--------|-----------|-----------|-------|\n")
    notes_map = {
        "residential_sales_mwh": "Structurally missing — utility data can't be cleanly allocated to counties",
        "residential_customers": "Structurally missing — same reason as above",
        "poverty_rate": "Missing 2010–2011 for all counties (ACS subject table variable didn't exist those years)",
        "pop_density": "4 rows: Bedford city VA (FIPS 51515) merged into Bedford County 2013",
        "elec_rate_cents_kwh": "5.3% missing in small rural NE counties 2020–2022",
        "data_processing_employment": "72.6% missing — expected; most small counties have no NAICS 518/519 establishments or suppressed cells",
    }
    for col in panel.columns:
        n = panel[col].isna().sum()
        if n > 0:
            pct = 100 * n / len(panel)
            note = notes_map.get(col, "")
            f.write(f"| {col} | {n} | {pct:.1f}% | {note} |\n")

    f.write("\n## Validation Results\n\n")
    if issues:
        f.write("### ⚠ Issues\n\n")
        for issue in issues:
            f.write(f"- {issue}\n")
    else:
        f.write("All validation checks passed.\n\n")

    f.write("\n## Summary Statistics\n\n")
    f.write("```\n")
    f.write(desc.to_string())
    f.write("\n```\n")

print(f"Saved: {report_path}")
