"""
fit_models_v2.py — M1–M5 model comparison on a COMMON SAMPLE FRAME per outcome.

WHY v2: v1 fit M1/M2/M3 on different sample sizes (3811/3259/2757) because listwise
deletion ran over each spec's own predictor set. CV-MSE was therefore not comparable
across specifications. v2 fixes this: for each outcome, ALL FIVE models are fit on the
SAME rows — the common sample defined by the union of M3's (the largest) predictor set.
Only the predictor matrix X changes between M1–M5; the rows never do.

Single auditable script (no parallel agents): with ~2.7k rows and 15 fits, parallelism
saves no wall-clock and risks inter-agent inconsistency. One script = identical sample
frames, guaranteed.

Decisions baked in (from Neil):
  - Cluster-robust SEs clustered on `fips` for the dc_active inference (full-data fit).
  - GroupKFold(10) grouped on fips for model-selection CV-MSE (caveat: with 3 treated
    counties most test folds have 0 treated units, so CV measures predictive/control fit;
    the causal estimate is the full-data cluster-robust dc_active coefficient).

Outputs (results/):
  comparison_table.csv, winner_summary.md, sample_frame_audit.md,
  cv_mse_comparison.png, dc_active_forest_plot.png,
  common_sample_{outcome}.csv, diagnostics/m{i}_{...}
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

from sklearn.linear_model import LinearRegression, LassoCV, RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error
import statsmodels.api as sm

RANDOM_STATE = 42
N_SPLITS = 10

ROOT = Path(__file__).parent.parent
RES = ROOT / "results"
DIAG = RES / "diagnostics"
DIAG.mkdir(parents=True, exist_ok=True)

OUTCOMES = ["elec_rate_cents_kwh", "unemployment_rate", "per_capita_income"]
OUTCOME_LABELS = {
    "elec_rate_cents_kwh": "Electricity rate (¢/kWh)",
    "unemployment_rate": "Unemployment rate (pp)",
    "per_capita_income": "Per-capita income ($)",
}

# Predictor groups (raw names; log_* created below)
BASE = ["dc_active"]
ECON = ["per_capita_income", "log_total_employment", "avg_annual_wage", "elec_rate_cents_kwh"]
DEMO = ["poverty_rate", "unemployment_rate", "log_pop_density", "median_age", "pct_bachelors"]


def predictors_for(model, outcome):
    """Continuous (non-FE) predictors for a (model, outcome). Outcome is removed."""
    if model == "M1":
        cont = list(BASE)
    elif model == "M2":
        cont = BASE + [p for p in ECON if p != outcome]
    else:  # M3, M4, M5 all share the M3 predictor set
        cont = BASE + [p for p in (ECON + DEMO) if p != outcome]
    return cont


def m3_union(outcome):
    """Full M3 predictor set for an outcome — defines the common sample frame."""
    return BASE + [p for p in (ECON + DEMO) if p != outcome]


# ── Load & clean ────────────────────────────────────────────────────────────────
df = pd.read_csv(ROOT / "data" / "panel_master.csv", dtype={"fips": str})
df["fips"] = df["fips"].str.zfill(5)
df = df[df["contaminated_control"] != 1].copy()
df = df.drop(columns=["residential_sales_mwh", "residential_customers"], errors="ignore")
df["state"] = df["fips"].str[:2]

for raw, log in [("pop_density", "log_pop_density"),
                 ("labor_force", "log_labor_force"),
                 ("total_employment", "log_total_employment"),
                 ("total_wages", "log_total_wages"),
                 ("gdp_thousands", "log_gdp_thousands")]:
    df[log] = np.log(df[raw])

def build_X(sample, model, outcome):
    """Design matrix for a (model, outcome) on the given common-sample rows.

    FE dummies are built ON THE SAMPLE (not the full panel) with drop_first=True, so
    the dropped reference category is guaranteed to exist in the data. Building them on
    the full panel and then removing all-zero columns silently drops a *reference* level
    that no longer appears in the subsample, leaving the remaining dummies + the constant
    rank-deficient by one — which makes the cluster-robust covariance singular and the
    dc_active SE explode. Per-sample dummies avoid this entirely.
    """
    cont = predictors_for(model, outcome)
    year_fe = pd.get_dummies(sample["year"], prefix="year", drop_first=True).astype(float)
    state_fe = pd.get_dummies(sample["state"], prefix="state", drop_first=True).astype(float)
    fe = pd.concat([year_fe, state_fe], axis=1)
    fe.index = sample.index
    X = pd.concat([sample[cont].astype(float), fe], axis=1)
    fe_cols = list(fe.columns)
    return X, cont, fe_cols


audit_lines = ["# Sample Frame Audit (v2)\n",
               "For each outcome the **common sample** is the set of rows with no NaN in the "
               "outcome or in any predictor of the M3 (largest) spec. All five models for that "
               "outcome are fit on exactly these rows; only the predictor matrix changes.\n"]

comparison_rows = []
forest_data = {}   # outcome -> list of dicts per model
cvmse_data = {}    # outcome -> {model: cv_mse_mean}
nobs_per_outcome = {}

for outcome in OUTCOMES:
    union_cols = m3_union(outcome)
    needed = [outcome] + union_cols  # log_* and dc_active included via union_cols
    before = len(df)

    # ── Build the common sample ──
    sample = df.dropna(subset=needed).copy()
    sample = sample.sort_values(["fips", "year"]).reset_index(drop=True)
    n = len(sample)
    nobs_per_outcome[outcome] = n

    # Audit: what got dropped and why
    dropped = df[~df.index.isin(df.dropna(subset=needed).index)]
    yr_drop = dropped["year"].value_counts().sort_index()
    audit_lines.append(f"\n## {OUTCOME_LABELS[outcome]} (`{outcome}`)\n")
    audit_lines.append(f"- Clean panel rows (post contamination-drop): {before}")
    audit_lines.append(f"- Common-sample rows (complete cases on M3 union): **{n}**")
    audit_lines.append(f"- Dropped: {before - n} rows")
    audit_lines.append(f"- M3 predictor union ({len(union_cols)}): `{union_cols}`")
    audit_lines.append(f"- Year range in sample: {int(sample['year'].min())}–{int(sample['year'].max())}")
    audit_lines.append("- Rows dropped by year (NaN in outcome or any union predictor):")
    for yr, cnt in yr_drop.items():
        audit_lines.append(f"    - {int(yr)}: {int(cnt)} dropped")
    # Per-column NaN contribution among union predictors (on full clean panel)
    audit_lines.append("- NaN count per union column (on clean panel, pre-deletion):")
    for c in needed:
        audit_lines.append(f"    - `{c}`: {int(df[c].isna().sum())}")

    sample.to_csv(RES / f"common_sample_{outcome}.csv", index=False)

    y = sample[outcome].values
    groups = sample["fips"].values
    gkf = GroupKFold(n_splits=N_SPLITS)

    for model in ["M1", "M2", "M3", "M4", "M5"]:
        X, cont, fe_cols = build_X(sample, model, outcome)
        Xv = X.values
        regularized = model in ("M4", "M5")

        # Guardrail: design (with intercept) must be full column rank, else the
        # cluster-robust covariance is singular and SEs are meaningless.
        Xrank = sm.add_constant(X, has_constant="add").values
        rk = np.linalg.matrix_rank(Xrank)
        assert rk == Xrank.shape[1], (
            f"{model}/{outcome}: rank-deficient design ({rk} of {Xrank.shape[1]} cols) — "
            f"cluster-robust SEs would be invalid")

        # ── CV ──
        fold_mses = []
        for tr, te in gkf.split(Xv, y, groups):
            if regularized:
                scaler = StandardScaler().fit(Xv[tr])
                Xtr, Xte = scaler.transform(Xv[tr]), scaler.transform(Xv[te])
                if model == "M4":
                    est = LassoCV(alphas=np.logspace(-4, 1, 50), cv=10,
                                  random_state=RANDOM_STATE, max_iter=100000)
                else:
                    est = RidgeCV(alphas=np.logspace(-4, 4, 50), cv=10)
                est.fit(Xtr, y[tr])
                pred = est.predict(Xte)
            else:
                est = LinearRegression().fit(Xv[tr], y[tr])
                pred = est.predict(Xv[te])
            fold_mses.append(mean_squared_error(y[te], pred))
        fold_mses = np.array(fold_mses)
        cv_mse_mean = float(fold_mses.mean())
        cv_mse_std = float(fold_mses.std(ddof=1))
        cv_rmse = float(np.sqrt(cv_mse_mean))

        # ── In-sample train MSE (full-data fit on this spec) ──
        if regularized:
            scaler_full = StandardScaler().fit(Xv)
            Xs = scaler_full.transform(Xv)
            if model == "M4":
                est_full = LassoCV(alphas=np.logspace(-4, 1, 50), cv=10,
                                   random_state=RANDOM_STATE, max_iter=100000).fit(Xs, y)
            else:
                est_full = RidgeCV(alphas=np.logspace(-4, 4, 50), cv=10).fit(Xs, y)
            train_pred = est_full.predict(Xs)
            chosen_alpha = float(est_full.alpha_)
            # regularized dc_active coef is on the standardized scale
            dc_idx = list(X.columns).index("dc_active")
            dc_reg = float(est_full.coef_[dc_idx])
        else:
            est_full = LinearRegression().fit(Xv, y)
            train_pred = est_full.predict(Xv)
            chosen_alpha = None
            dc_reg = None
        train_mse = float(mean_squared_error(y, train_pred))

        # ── Cluster-robust OLS for dc_active inference (unstandardized X) ──
        X_sm = sm.add_constant(X, has_constant="add")
        ols = sm.OLS(y, X_sm).fit(cov_type="cluster",
                                  cov_kwds={"groups": sample["fips"]})
        dc_coef = float(ols.params["dc_active"])
        dc_se = float(ols.bse["dc_active"])
        ci = ols.conf_int().loc["dc_active"]
        dc_lo, dc_hi = float(ci[0]), float(ci[1])

        comparison_rows.append({
            "outcome": outcome, "model": model, "n_obs": n,
            "n_predictors": X.shape[1],
            "cv_mse_mean": cv_mse_mean, "cv_mse_std": cv_mse_std,
            "cv_rmse": cv_rmse, "train_mse": train_mse,
            "overfitting_gap": train_mse - cv_mse_mean,
            "dc_active_coef_ols": dc_coef, "dc_active_se_ols": dc_se,
            "dc_active_ci_lo_ols": dc_lo, "dc_active_ci_hi_ols": dc_hi,
            "dc_active_coef_regularized": dc_reg,
            "regularization_alpha": chosen_alpha,
        })

        # diagnostics
        resid = y - train_pred
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.scatter(train_pred, resid, s=8, alpha=0.4)
        ax.axhline(0, color="red", lw=1)
        ax.set_xlabel("Fitted"); ax.set_ylabel("Residual")
        ax.set_title(f"{model} — {outcome}\nresiduals vs fitted (n={n})")
        plt.tight_layout()
        plt.savefig(DIAG / f"{model.lower()}_residuals_{outcome}.png", dpi=120)
        plt.close()

        coef_tbl = pd.DataFrame({
            "predictor": X_sm.columns,
            "ols_coef": ols.params.values,
            "ols_se": ols.bse.values,
            "ci_lo": ols.conf_int()[0].values,
            "ci_hi": ols.conf_int()[1].values,
        })
        coef_tbl.to_csv(DIAG / f"{model.lower()}_coef_{outcome}.csv", index=False)

    # collect for plots
    sub = [r for r in comparison_rows if r["outcome"] == outcome]
    cvmse_data[outcome] = {r["model"]: r["cv_mse_mean"] for r in sub}
    forest_data[outcome] = sub

cdf = pd.DataFrame(comparison_rows)

# ── Winner = min CV-MSE per outcome ──
cdf["is_winner"] = False
for outcome in OUTCOMES:
    idx = cdf[cdf.outcome == outcome]["cv_mse_mean"].idxmin()
    cdf.loc[idx, "is_winner"] = True

# ═══ VALIDATION ═══
assert len(cdf) == 15, f"Expected 15 rows, got {len(cdf)}"
for outcome in OUTCOMES:
    ns = cdf[cdf.outcome == outcome]["n_obs"].unique()
    assert len(ns) == 1, f"{outcome}: models have different n_obs {ns} — common frame BROKEN"
crit = ["cv_mse_mean", "dc_active_coef_ols", "dc_active_ci_lo_ols", "dc_active_ci_hi_ols"]
assert not cdf[crit].isna().any().any(), "NaN in critical column"
print(f"n_obs per outcome: elec={nobs_per_outcome['elec_rate_cents_kwh']}, "
      f"unemp={nobs_per_outcome['unemployment_rate']}, "
      f"income={nobs_per_outcome['per_capita_income']}")

# ── comparison_table.csv ──
col_order = ["outcome", "model", "n_obs", "n_predictors",
             "cv_mse_mean", "cv_mse_std", "cv_rmse", "train_mse", "overfitting_gap",
             "dc_active_coef_ols", "dc_active_se_ols",
             "dc_active_ci_lo_ols", "dc_active_ci_hi_ols",
             "dc_active_coef_regularized", "regularization_alpha", "is_winner"]
cdf[col_order].to_csv(RES / "comparison_table.csv", index=False)
print(f"Saved comparison_table.csv ({len(cdf)} rows)")


def excl0(lo, hi):
    return (lo > 0 and hi > 0) or (lo < 0 and hi < 0)


# ── winner_summary.md ──
L = ["# Model Comparison v2 — Winner Summary\n"]
L.append("**v2 fix:** all five models for a given outcome are fit on the *same rows* — the "
         "common sample defined by complete cases on the M3 (largest) predictor union. CV-MSE "
         "is now comparable across M1–M5 within an outcome (v1 fit them on 3811/3259/2757 rows "
         "and the numbers were not comparable).\n")
L.append("\n**Cross-validation note:** 10-fold `GroupKFold` grouped on `fips`. With only 3 "
         "treated counties (~10 post-treatment county-years), most CV test folds contain zero "
         "treated units, so CV-MSE measures overall predictive fit (dominated by control "
         "counties) for model selection — it is *not* a test of the treatment effect.\n")
L.append("\n**Treatment inference:** the `dc_active` coefficient, SE and 95% CI come from the "
         "**full-data fit with cluster-robust standard errors clustered on `fips`** (standard "
         "DiD practice for serially-correlated county panels). For M4/M5 the regularized "
         "(standardized) dc_active coefficient is reported alongside, but inference uses the "
         "unpenalized cluster-robust OLS on the same predictors.\n")

for outcome in OUTCOMES:
    sub = cdf[cdf.outcome == outcome].sort_values("cv_mse_mean")
    win = sub[sub.is_winner].iloc[0]
    n = int(win["n_obs"])
    smp = pd.read_csv(RES / f"common_sample_{outcome}.csv", dtype={"fips": str})
    yrs = f"{int(smp.year.min())}–{int(smp.year.max())}"
    L.append(f"\n## {OUTCOME_LABELS[outcome]}  (`{outcome}`)\n")
    L.append(f"- **Common sample:** n = {n}, years {yrs}, "
             f"{smp['fips'].nunique()} counties.")
    L.append(f"- **Winner (lowest CV-MSE): {win['model']}** "
             f"(CV-MSE = {win['cv_mse_mean']:.4g}, CV-RMSE = {win['cv_rmse']:.4g}).")
    coef, lo, hi = win["dc_active_coef_ols"], win["dc_active_ci_lo_ols"], win["dc_active_ci_hi_ols"]
    sig = excl0(lo, hi)
    sigtxt = "**distinguishable from zero**" if sig else "not distinguishable from zero (CI spans 0)"
    if outcome == "elec_rate_cents_kwh":
        L.append(f"- **dc_active (winner, OLS):** {coef:+.3f} ¢/kWh, 95% CI [{lo:.3f}, {hi:.3f}].")
        interp = (f"Data centers becoming active are associated with a {coef:+.3f} ¢/kWh change "
                  f"in residential electricity rates — {sigtxt}.")
    elif outcome == "unemployment_rate":
        L.append(f"- **dc_active (winner, OLS):** {coef:+.3f} pp, 95% CI [{lo:.3f}, {hi:.3f}].")
        interp = (f"Data centers becoming active are associated with a {coef:+.3f} percentage-point "
                  f"change in the unemployment rate — {sigtxt}.")
    else:
        L.append(f"- **dc_active (winner, OLS):** ${coef:+,.0f}, 95% CI [${lo:,.0f}, ${hi:,.0f}].")
        interp = (f"Data centers becoming active are associated with a ${coef:+,.0f} change in "
                  f"per-capita income — {sigtxt}.")
    L.append(f"- **Interpretation:** {interp}")

    L.append("\n| Model | CV-MSE | CV-RMSE | overfit gap | dc_active β (OLS) | 95% CI | sig? |")
    L.append("|---|---|---|---|---|---|---|")
    for _, r in sub.iterrows():
        s = "✓" if excl0(r.dc_active_ci_lo_ols, r.dc_active_ci_hi_ols) else ""
        if outcome == "per_capita_income":
            b = f"{r.dc_active_coef_ols:+,.0f}"
            c = f"[{r.dc_active_ci_lo_ols:,.0f}, {r.dc_active_ci_hi_ols:,.0f}]"
        else:
            b = f"{r.dc_active_coef_ols:+.3f}"
            c = f"[{r.dc_active_ci_lo_ols:.3f}, {r.dc_active_ci_hi_ols:.3f}]"
        star = " **(winner)**" if r.is_winner else ""
        L.append(f"| {r.model}{star} | {r.cv_mse_mean:.4g} | {r.cv_rmse:.4g} | "
                 f"{r.overfitting_gap:.3g} | {b} | {c} | {s} |")
    L.append("")

(RES / "winner_summary.md").write_text("\n".join(L))
print("Saved winner_summary.md")

(RES / "sample_frame_audit.md").write_text("\n".join(audit_lines) + "\n")
print("Saved sample_frame_audit.md")

# ── Plot 1: CV-MSE grouped bars (normalized within outcome) ──
fig, ax = plt.subplots(figsize=(10, 6))
order = ["M1", "M2", "M3", "M4", "M5"]
colors = plt.cm.viridis(np.linspace(0.1, 0.85, len(order)))
x = np.arange(len(OUTCOMES)); bw = 0.15
for mi, m in enumerate(order):
    h = []
    for oc in OUTCOMES:
        val = cvmse_data[oc][m]; best = min(cvmse_data[oc].values())
        h.append(val / best)
    ax.bar(x + mi * bw, h, bw, label=m, color=colors[mi])
ax.set_xticks(x + bw * (len(order) - 1) / 2)
ax.set_xticklabels([OUTCOME_LABELS[o] for o in OUTCOMES], fontsize=9)
ax.set_ylabel("CV-MSE relative to best (1.0 = winner)")
ax.set_title("Cross-validated MSE by model and outcome\n(common sample frame; normalized within outcome; lower = better)")
ax.axhline(1.0, color="gray", ls=":", lw=1)
ax.legend(title="Model", ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.12))
ax.set_ylim(0.95, max(1.05, ax.get_ylim()[1]))
plt.tight_layout()
plt.savefig(RES / "cv_mse_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved cv_mse_comparison.png")

# ── Plot 2: dc_active forest plot ──
fig, axes = plt.subplots(1, len(OUTCOMES), figsize=(15, 5))
for ax, oc in zip(axes, OUTCOMES):
    sub = cdf[cdf.outcome == oc].set_index("model").loc[order]
    yy = np.arange(len(order))[::-1]
    coefs = sub["dc_active_coef_ols"].values
    los = sub["dc_active_ci_lo_ols"].values
    his = sub["dc_active_ci_hi_ols"].values
    ax.errorbar(coefs, yy, xerr=[coefs - los, his - coefs], fmt="none",
                ecolor="black", elinewidth=1.2, capsize=4)
    for xi, yi, lo, hi in zip(coefs, yy, los, his):
        ax.plot(xi, yi, "o", ms=8, zorder=3,
                color="tab:red" if excl0(lo, hi) else "tab:gray")
    ax.axvline(0, color="steelblue", ls="--", lw=1.2)
    ax.set_yticks(yy); ax.set_yticklabels(order)
    ax.set_title(OUTCOME_LABELS[oc], fontsize=11)
    ax.set_xlabel("dc_active coefficient (cluster-robust 95% CI)")
    ax.grid(axis="x", alpha=0.3)
fig.suptitle("Treatment effect (dc_active) across models — common sample, cluster-robust 95% CIs\n"
             "red = CI excludes 0; gray = spans 0; dashed = null", fontsize=12)
plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig(RES / "dc_active_forest_plot.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved dc_active_forest_plot.png")

# ── Console ──
print("\n" + "=" * 70)
with pd.option_context("display.width", 220, "display.max_columns", 25):
    show = cdf[["outcome", "model", "n_obs", "cv_mse_mean", "cv_rmse",
                "dc_active_coef_ols", "dc_active_ci_lo_ols", "dc_active_ci_hi_ols",
                "is_winner"]]
    print(show.to_string(index=False))
print("\nWinners:")
for oc in OUTCOMES:
    w = cdf[(cdf.outcome == oc) & cdf.is_winner].iloc[0]
    print(f"  {oc:24s} -> {w['model']} (CV-MSE={w['cv_mse_mean']:.4g})")
