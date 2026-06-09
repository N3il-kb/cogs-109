"""
fit_models_national.py — M1–M5 + M3+C on the national DiD set, plus bootstrap CIs,
an event study, and two robustness runs. Reuses fit_models_v2.py methodology verbatim:
common sample frame per outcome, FE dummies built ON THE SAMPLE (rank-safe), outcome
dropped from predictors, cluster-robust SEs on fips.

NEW vs v2:
  - sample = national DiD set (analysis_diD==1), staggered dc_active
  - M3+C = M3 + covid_deaths_per_100k + wfh_rate (the COVID-defense spec)
  - cluster bootstrap (1000 resamples on fips) percentile CI for dc_active
  - event study on electricity (years_since_dc bins, -1 omitted)
  - robustness: Licking 2016 vs 2020; exclude FUTURE_DC_2023plus controls

Writes to results_national/ ONLY (originals untouched).
"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.linear_model import LinearRegression, LassoCV, RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupKFold
from sklearn.metrics import mean_squared_error
import statsmodels.api as sm

RANDOM_STATE = 42
N_SPLITS = 10
N_BOOT = 1000
rng = np.random.default_rng(RANDOM_STATE)

ROOT = Path(__file__).parent.parent.parent
RES = ROOT / "results_national"
DIAG = RES / "diagnostics"
DIAG.mkdir(parents=True, exist_ok=True)

OUTCOMES = ["elec_rate_cents_kwh", "unemployment_rate", "per_capita_income"]
LABELS = {"elec_rate_cents_kwh": "Electricity rate (¢/kWh)",
          "unemployment_rate": "Unemployment rate (pp)",
          "per_capita_income": "Per-capita income ($)"}

BASE = ["dc_active"]
ECON = ["per_capita_income", "log_total_employment", "avg_annual_wage", "elec_rate_cents_kwh"]
DEMO = ["poverty_rate", "unemployment_rate", "log_pop_density", "median_age", "pct_bachelors"]
COVID = ["covid_deaths_per_100k", "wfh_rate"]
MODELS = ["M1", "M2", "M3", "M3+C", "M4", "M5"]


def predictors_for(model, outcome):
    if model == "M1":
        return list(BASE)
    if model == "M2":
        return BASE + [p for p in ECON if p != outcome]
    if model == "M3+C":
        return BASE + [p for p in (ECON + DEMO) if p != outcome] + list(COVID)
    return BASE + [p for p in (ECON + DEMO) if p != outcome]   # M3, M4, M5


def m3_union(outcome):
    """Common sample frame = complete cases on M3 union (NOT incl. covid, so M1–M5 share
    the same rows). M3+C uses the same frame but additionally drops covid/wfh-NaN rows."""
    return BASE + [p for p in (ECON + DEMO) if p != outcome]


def add_logs(df):
    for raw, log in [("pop_density","log_pop_density"),("labor_force","log_labor_force"),
                     ("total_employment","log_total_employment"),("total_wages","log_total_wages"),
                     ("gdp_thousands","log_gdp_thousands")]:
        df[log] = np.log(df[raw].where(df[raw] > 0))
    return df


def load_did(licking_year=2016, exclude_future_dc=False):
    df = pd.read_csv(ROOT / "data" / "panel_master_national.csv", dtype={"fips": str})
    df["fips"] = df["fips"].str.zfill(5)
    df = df[df["analysis_diD"] == 1].copy()
    df["state"] = df["fips"].str[:2]
    # Licking recode option (39089): default 2016 (AWS) per Phase-2 coding; 2020 = Meta
    if licking_year != 2016:
        m = df["fips"] == "39089"
        df.loc[m, "dc_opening_year"] = licking_year
        df.loc[m, "dc_active"] = (df.loc[m, "year"] >= licking_year).astype(int)
        df.loc[m, "years_since_dc"] = np.where(df.loc[m, "dc_active"] == 1,
                                               df.loc[m, "year"] - licking_year, 0)
    if exclude_future_dc:
        df = df[~df["cohort_flags"].fillna("").str.contains("FUTURE_DC_2023plus")].copy()
    return add_logs(df)


def build_X(sample, model, outcome):
    cont = predictors_for(model, outcome)
    year_fe = pd.get_dummies(sample["year"], prefix="year", drop_first=True).astype(float)
    state_fe = pd.get_dummies(sample["state"], prefix="state", drop_first=True).astype(float)
    fe = pd.concat([year_fe, state_fe], axis=1); fe.index = sample.index
    X = pd.concat([sample[cont].astype(float), fe], axis=1)
    return X, cont, list(fe.columns)


def cluster_bootstrap_dc(sample, X, y, n_boot=N_BOOT):
    """Percentile CI for dc_active via cluster (county) bootstrap. Resample counties with
    replacement, refit OLS, collect dc_active coef. Course §4.3 inference."""
    Xc = sm.add_constant(X, has_constant="add")
    Xc = Xc.reset_index(drop=True); yv = np.asarray(y)
    fips = sample["fips"].reset_index(drop=True).values
    uniq = np.unique(fips)
    idx_by_fips = {f: np.where(fips == f)[0] for f in uniq}
    dccol = list(Xc.columns).index("dc_active")
    coefs = []
    Xc_np = Xc.values
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        rows = np.concatenate([idx_by_fips[f] for f in pick])
        Xb, yb = Xc_np[rows], yv[rows]
        try:
            beta, *_ = np.linalg.lstsq(Xb, yb, rcond=None)
            coefs.append(beta[dccol])
        except np.linalg.LinAlgError:
            continue
    coefs = np.array(coefs)
    return float(np.percentile(coefs, 2.5)), float(np.percentile(coefs, 97.5)), len(coefs)


def fit_one(sample, model, outcome, do_boot=False):
    X, cont, fe_cols = build_X(sample, model, outcome)
    Xv = X.values; y = sample[outcome].values; groups = sample["fips"].values
    regularized = model in ("M4", "M5")
    # rank guard
    Xr = sm.add_constant(X, has_constant="add").values
    rk = np.linalg.matrix_rank(Xr)
    assert rk == Xr.shape[1], f"{model}/{outcome}: rank-deficient ({rk}/{Xr.shape[1]})"
    # CV
    gkf = GroupKFold(n_splits=N_SPLITS); fold = []
    for tr, te in gkf.split(Xv, y, groups):
        if regularized:
            sc = StandardScaler().fit(Xv[tr]); Xt, Xe = sc.transform(Xv[tr]), sc.transform(Xv[te])
            est = (LassoCV(alphas=np.logspace(-4,1,50), cv=10, random_state=RANDOM_STATE, max_iter=100000)
                   if model == "M4" else RidgeCV(alphas=np.logspace(-4,4,50), cv=10))
            est.fit(Xt, y[tr]); pred = est.predict(Xe)
        else:
            pred = LinearRegression().fit(Xv[tr], y[tr]).predict(Xv[te])
        fold.append(mean_squared_error(y[te], pred))
    cv_mse = float(np.mean(fold)); cv_rmse = float(np.sqrt(cv_mse))
    # train MSE
    if regularized:
        sc = StandardScaler().fit(Xv); Xs = sc.transform(Xv)
        est = (LassoCV(alphas=np.logspace(-4,1,50), cv=10, random_state=RANDOM_STATE, max_iter=100000)
               if model == "M4" else RidgeCV(alphas=np.logspace(-4,4,50), cv=10)).fit(Xs, y)
        train_pred = est.predict(Xs); alpha = float(est.alpha_)
        dc_reg = float(est.coef_[list(X.columns).index("dc_active")])
    else:
        train_pred = LinearRegression().fit(Xv, y).predict(Xv); alpha = None; dc_reg = None
    train_mse = float(mean_squared_error(y, train_pred))
    # cluster-robust OLS inference
    Xsm = sm.add_constant(X, has_constant="add")
    ols = sm.OLS(y, Xsm).fit(cov_type="cluster", cov_kwds={"groups": sample["fips"]})
    dc = float(ols.params["dc_active"]); se = float(ols.bse["dc_active"])
    ci = ols.conf_int().loc["dc_active"]; lo, hi = float(ci[0]), float(ci[1])
    boot_lo = boot_hi = np.nan; n_boot_ok = 0
    if do_boot:
        boot_lo, boot_hi, n_boot_ok = cluster_bootstrap_dc(sample, X, y)
    return {"outcome": outcome, "model": model, "n_obs": len(sample), "n_predictors": X.shape[1],
            "cv_mse_mean": cv_mse, "cv_rmse": cv_rmse, "train_mse": train_mse,
            "overfitting_gap": train_mse - cv_mse,
            "dc_active_coef_ols": dc, "dc_active_se_ols": se,
            "dc_active_ci_lo_ols": lo, "dc_active_ci_hi_ols": hi,
            "dc_active_boot_lo": boot_lo, "dc_active_boot_hi": boot_hi, "n_boot": n_boot_ok,
            "dc_active_coef_regularized": dc_reg, "regularization_alpha": alpha}


def excl0(lo, hi):
    return (lo > 0 and hi > 0) or (lo < 0 and hi < 0)


# ══════════════════════════════════════════════════════════════════════
# MAIN: M1–M5 + M3+C on the national DiD set
# ══════════════════════════════════════════════════════════════════════
df = load_did()
rows = []
covid_compare = {}
for outcome in OUTCOMES:
    union = m3_union(outcome)
    base_sample = df.dropna(subset=[outcome] + union).sort_values(["fips","year"]).reset_index(drop=True)
    # covid-augmented frame (drops covid/wfh NaN — i.e. 2024 & pre-covid wfh-missing)
    cov_sample = df.dropna(subset=[outcome] + union + COVID).sort_values(["fips","year"]).reset_index(drop=True)
    for model in MODELS:
        sample = cov_sample if model == "M3+C" else base_sample
        r = fit_one(sample, model, outcome, do_boot=(outcome == "elec_rate_cents_kwh"
                    and model in ("M1","M2","M3","M3+C","M4","M5")) or model in ("M3","M3+C"))
        rows.append(r)
    m3 = next(r for r in rows if r["outcome"]==outcome and r["model"]=="M3")
    m3c = next(r for r in rows if r["outcome"]==outcome and r["model"]=="M3+C")
    covid_compare[outcome] = (m3, m3c)

cdf = pd.DataFrame(rows)
# Winner among the comparable common-frame models (M1,M2,M3,M4,M5) — M3+C is a separate frame
cdf["is_winner"] = False
for outcome in OUTCOMES:
    sub = cdf[(cdf.outcome==outcome) & (cdf.model.isin(["M1","M2","M3","M4","M5"]))]
    cdf.loc[sub["cv_mse_mean"].idxmin(), "is_winner"] = True

col_order = ["outcome","model","n_obs","n_predictors","cv_mse_mean","cv_rmse","train_mse",
             "overfitting_gap","dc_active_coef_ols","dc_active_se_ols","dc_active_ci_lo_ols",
             "dc_active_ci_hi_ols","dc_active_boot_lo","dc_active_boot_hi","n_boot",
             "dc_active_coef_regularized","regularization_alpha","is_winner"]
cdf[col_order].to_csv(RES / "comparison_table.csv", index=False)
print("Saved comparison_table.csv", len(cdf), "rows")

# ── forest plot (6 specs x 3 outcomes) ──
fig, axes = plt.subplots(1, 3, figsize=(16, 5.5))
order = ["M1","M2","M3","M3+C","M4","M5"]
for ax, oc in zip(axes, OUTCOMES):
    sub = cdf[cdf.outcome==oc].set_index("model").loc[order]
    yy = np.arange(len(order))[::-1]
    coefs, los, his = sub["dc_active_coef_ols"].values, sub["dc_active_ci_lo_ols"].values, sub["dc_active_ci_hi_ols"].values
    ax.errorbar(coefs, yy, xerr=[coefs-los, his-coefs], fmt="none", ecolor="black", elinewidth=1.2, capsize=4)
    for xi, yi, lo, hi, m in zip(coefs, yy, los, his, order):
        col = "tab:green" if m=="M3+C" else ("tab:red" if excl0(lo,hi) else "tab:gray")
        ax.plot(xi, yi, "o", ms=9, zorder=3, color=col)
    ax.axvline(0, color="steelblue", ls="--", lw=1.2)
    ax.set_yticks(yy); ax.set_yticklabels(order); ax.set_title(LABELS[oc], fontsize=11)
    ax.set_xlabel("dc_active coef (cluster-robust 95% CI)"); ax.grid(axis="x", alpha=0.3)
fig.suptitle("Treatment effect (dc_active) across specifications — national DiD set, cluster-robust 95% CIs\n"
             "green = M3+C (COVID-controlled); red = CI excludes 0; gray = spans 0", fontsize=12)
plt.tight_layout(rect=[0,0,1,0.92])
plt.savefig(RES / "dc_active_forest_plot.png", dpi=150, bbox_inches="tight"); plt.close()
print("Saved dc_active_forest_plot.png")

# ══════════════════════════════════════════════════════════════════════
# EVENT STUDY (electricity, M3 control set)
# ══════════════════════════════════════════════════════════════════════
def event_study():
    es_df = load_did()
    union = m3_union("elec_rate_cents_kwh")
    controls = [p for p in union if p != "dc_active"]
    s = es_df.dropna(subset=["elec_rate_cents_kwh"] + controls).copy()
    # event time bins; -1 omitted reference. Controls (never-treated) get all-zero bins.
    s["evt"] = np.where(s["is_treated"]==1, s["years_since_dc"], np.nan)
    # for treated, years_since_dc is 0 when not active; reconstruct true relative time:
    oy = s["dc_opening_year"]
    rel = (s["year"] - oy)
    s["rel"] = np.where(s["is_treated"]==1, rel, np.nan)
    bins = {"m4":(-99,-4),"m3":(-3,-3),"m2":(-2,-2),"p0":(0,0),"p1":(1,1),"p2":(2,2),"p3":(3,3),"p4":(4,99)}
    # omitted = rel == -1
    for name,(lo,hi) in bins.items():
        s[f"es_{name}"] = ((s["rel"]>=lo)&(s["rel"]<=hi)).astype(float)
    es_cols = [f"es_{n}" for n in bins]
    year_fe = pd.get_dummies(s["year"], prefix="year", drop_first=True).astype(float)
    state_fe = pd.get_dummies(s["state"], prefix="state", drop_first=True).astype(float)
    for fe in (year_fe, state_fe): fe.index = s.index
    X = pd.concat([s[es_cols + controls].astype(float), year_fe, state_fe], axis=1)
    Xsm = sm.add_constant(X, has_constant="add")
    ols = sm.OLS(s["elec_rate_cents_kwh"].values, Xsm).fit(cov_type="cluster", cov_kwds={"groups": s["fips"]})
    pts = []
    labelmap = {"m4":"≤-4","m3":"-3","m2":"-2","p0":"0","p1":"+1","p2":"+2","p3":"+3","p4":"≥+4"}
    order_es = ["m4","m3","m2","p0","p1","p2","p3","p4"]
    for n in order_es:
        c = f"es_{n}"
        pts.append({"bin": labelmap[n], "coef": ols.params[c], "lo": ols.conf_int().loc[c][0],
                    "hi": ols.conf_int().loc[c][1]})
    # insert omitted -1 = 0 in chronological position (after ≤-4,-3,-2; before 0,+1,...)
    ref = {"bin":"-1 (ref)","coef":0.0,"lo":0.0,"hi":0.0}
    pre = [p for p in pts if p["bin"] in ("≤-4","-3","-2")]
    post = [p for p in pts if p["bin"] not in ("≤-4","-3","-2")]
    pts_full = pre + [ref] + post
    return pd.DataFrame(pts_full), ols

es_pts, es_ols = event_study()
es_pts.to_csv(RES / "event_study_coefs.csv", index=False)
fig, ax = plt.subplots(figsize=(9,5.5))
xx = np.arange(len(es_pts))
ax.errorbar(xx, es_pts["coef"], yerr=[es_pts["coef"]-es_pts["lo"], es_pts["hi"]-es_pts["coef"]],
            fmt="o-", color="tab:blue", ecolor="gray", capsize=4, ms=7)
ax.axhline(0, color="black", lw=1); ax.axvline(list(es_pts["bin"]).index("-1 (ref)"), color="red", ls="--", lw=1, alpha=0.6)
ax.set_xticks(xx); ax.set_xticklabels(es_pts["bin"]); ax.set_xlabel("Years relative to data-center opening")
ax.set_ylabel("Effect on electricity rate (¢/kWh)")
ax.set_title("Event study: electricity rate around data-center opening\n(M3 controls, year+state FE, cluster-robust 95% CI; -1 = reference)")
ax.grid(alpha=0.3); plt.tight_layout()
plt.savefig(RES / "event_study_electricity.png", dpi=150, bbox_inches="tight"); plt.close()
print("Saved event_study_electricity.png")

# ══════════════════════════════════════════════════════════════════════
# ROBUSTNESS: Licking 2016 vs 2020; exclude FUTURE_DC controls (electricity, M3)
# ══════════════════════════════════════════════════════════════════════
def main_elec_coef(df_in):
    union = m3_union("elec_rate_cents_kwh")
    s = df_in.dropna(subset=["elec_rate_cents_kwh"] + union).sort_values(["fips","year"]).reset_index(drop=True)
    r = fit_one(s, "M3", "elec_rate_cents_kwh", do_boot=False)
    return r["dc_active_coef_ols"], r["dc_active_ci_lo_ols"], r["dc_active_ci_hi_ols"], r["n_obs"]

rob = {}
rob["licking_2016"] = main_elec_coef(load_did(licking_year=2016))
rob["licking_2020"] = main_elec_coef(load_did(licking_year=2020))
rob["exclude_future_dc"] = main_elec_coef(load_did(exclude_future_dc=True))
print("Robustness:", {k: (round(v[0],4), v[3]) for k,v in rob.items()})

# ── covid_robustness.md ──
CL = ["# COVID Robustness — M3 vs M3+C\n",
      "The headline COVID defense: does adding explicit COVID controls (`covid_deaths_per_100k`, "
      "`wfh_rate`) to M3 move the `dc_active` effect? If not, the effect is not a pandemic artifact.\n",
      "M3 and M3+C are fit on *slightly* different frames — M3+C additionally requires non-NaN "
      "covid/wfh, dropping 2024 (no covid data) and any wfh-missing rows. n is reported for each.\n"]
for oc in OUTCOMES:
    m3, m3c = covid_compare[oc]
    b3, b3c = m3["dc_active_coef_ols"], m3c["dc_active_coef_ols"]
    pct = 100*(b3c - b3)/abs(b3) if b3 != 0 else float("nan")
    unit = "¢/kWh" if oc=="elec_rate_cents_kwh" else ("pp" if oc=="unemployment_rate" else "$")
    fmt = (lambda v: f"{v:+,.0f}") if oc=="per_capita_income" else (lambda v: f"{v:+.3f}")
    CL.append(f"\n## {LABELS[oc]}\n")
    CL.append(f"| Spec | n | dc_active β | cluster-robust 95% CI | bootstrap 95% CI |")
    CL.append(f"|---|---|---|---|---|")
    for r in (m3, m3c):
        ci = f"[{fmt(r['dc_active_ci_lo_ols'])}, {fmt(r['dc_active_ci_hi_ols'])}]"
        bci = (f"[{fmt(r['dc_active_boot_lo'])}, {fmt(r['dc_active_boot_hi'])}]"
               if not np.isnan(r['dc_active_boot_lo']) else "—")
        CL.append(f"| {r['model']} | {r['n_obs']} | {fmt(r['dc_active_coef_ols'])} {unit} | {ci} | {bci} |")
    CL.append(f"\n- **Change in dc_active when COVID controls added: {pct:+.1f}%** "
              f"({fmt(b3)} → {fmt(b3c)} {unit}).")
    if oc == "elec_rate_cents_kwh":
        stable = abs(pct) < 25
        CL.append(f"- **Read:** the electricity effect {'barely moves' if stable else 'shifts'} "
                  f"when COVID deaths and WFH are controlled explicitly — "
                  f"{'direct evidence the rate effect is NOT a pandemic artifact.' if stable else 'COVID controls absorb part of it; interpret with care.'}")
(RES / "covid_robustness.md").write_text("\n".join(CL) + "\n")
print("Saved covid_robustness.md")

# ── winner_summary.md ──
WL = ["# National DiD — Winner Summary (Phase 4)\n",
      "Sample: national DiD set (`analysis_diD=1`), 150 counties (26 in-panel treated + 124 control), "
      "staggered `dc_active` (openings 2010–2022). Methodology identical to `fit_models_v2.py`: common "
      "sample frame per outcome, FE dummies built on the sample (rank-safe), outcome dropped from "
      "predictors, cluster-robust SEs on `fips`; winner = min GroupKFold(10) CV-MSE among M1–M5.\n",
      "Inference: cluster-robust 95% CI **and** county cluster-bootstrap percentile CI "
      f"({N_BOOT} resamples) — reported together for the key specs.\n"]
for oc in OUTCOMES:
    sub = cdf[(cdf.outcome==oc) & cdf.model.isin(["M1","M2","M3","M4","M5"])].sort_values("cv_mse_mean")
    win = sub[sub.is_winner].iloc[0]
    fmt = (lambda v: f"${v:+,.0f}") if oc=="per_capita_income" else (lambda v: f"{v:+.3f}")
    unit = "¢/kWh" if oc=="elec_rate_cents_kwh" else ("pp" if oc=="unemployment_rate" else "")
    WL.append(f"\n## {LABELS[oc]}\n")
    WL.append(f"- **Winner (min CV-MSE among M1–M5): {win['model']}** (CV-RMSE={win['cv_rmse']:.4g}, n={win['n_obs']}).")
    sig = excl0(win["dc_active_ci_lo_ols"], win["dc_active_ci_hi_ols"])
    WL.append(f"- **dc_active (winner):** {fmt(win['dc_active_coef_ols'])} {unit}, "
              f"cluster CI [{fmt(win['dc_active_ci_lo_ols'])}, {fmt(win['dc_active_ci_hi_ols'])}] — "
              f"{'distinguishable from 0' if sig else 'spans 0'}.")
    WL.append("\n| Model | CV-RMSE | dc_active β | cluster 95% CI | sig? |")
    WL.append("|---|---|---|---|---|")
    for _, r in sub.iterrows():
        s = "✓" if excl0(r.dc_active_ci_lo_ols, r.dc_active_ci_hi_ols) else ""
        star = " **(win)**" if r.is_winner else ""
        WL.append(f"| {r.model}{star} | {r.cv_rmse:.4g} | {fmt(r.dc_active_coef_ols)} | "
                  f"[{fmt(r.dc_active_ci_lo_ols)}, {fmt(r.dc_active_ci_hi_ols)}] | {s} |")

WL.append("\n## Event study (electricity)\n")
WL.append("Pre-trend coefficients (should be ~0 if parallel-trends holds):")
for _, r in es_pts.iterrows():
    WL.append(f"- t={r['bin']}: {r['coef']:+.3f} ¢/kWh" + (" (reference)" if "ref" in r['bin'] else
              f" [{r['lo']:+.3f}, {r['hi']:+.3f}]"))
pre = es_pts[es_pts["bin"].isin(["-3","-2"])]
pre_ok = (pre["coef"].abs() < 0.3).all()
WL.append(f"\n**Pre-trend read:** t=-3 and t=-2 coefficients are "
          f"{'small and near zero — parallel pre-trends are defensible.' if pre_ok else 'non-trivial — pre-trends warrant caution.'}")

WL.append("\n## Robustness (electricity, M3)\n")
WL.append("| Run | dc_active β | 95% CI | n |")
WL.append("|---|---|---|---|")
for k, lab in [("licking_2016","Licking=2016 (AWS, main)"),("licking_2020","Licking=2020 (Meta)"),
               ("exclude_future_dc","Exclude FUTURE_DC_2023plus controls")]:
    c, lo, hi, n = rob[k]
    WL.append(f"| {lab} | {c:+.3f} | [{lo:+.3f}, {hi:+.3f}] | {n} |")
d = abs(rob["licking_2016"][0] - rob["licking_2020"][0])
WL.append(f"\n- **Licking sensitivity:** pooled electricity effect changes by {d:.3f} ¢/kWh between "
          f"the 2016 and 2020 codings — {'negligible; the result does not hinge on the Licking date.' if d<0.1 else 'modest; note it.'}")
de = abs(rob["licking_2016"][0] - rob["exclude_future_dc"][0])
WL.append(f"- **Future-DC controls:** dropping the 29 FUTURE_DC_2023plus controls changes the effect "
          f"by {de:.3f} ¢/kWh — {'stable.' if de<0.15 else 'some movement; note it.'}")
(RES / "winner_summary.md").write_text("\n".join(WL) + "\n")
print("Saved winner_summary.md")

# ── console ──
print("\n" + "="*70)
print("COVID TEST (electricity): M3 vs M3+C dc_active")
m3, m3c = covid_compare["elec_rate_cents_kwh"]
print(f"  M3   : {m3['dc_active_coef_ols']:+.4f} ¢/kWh  CI[{m3['dc_active_ci_lo_ols']:.3f},{m3['dc_active_ci_hi_ols']:.3f}]  n={m3['n_obs']}")
print(f"  M3+C : {m3c['dc_active_coef_ols']:+.4f} ¢/kWh  CI[{m3c['dc_active_ci_lo_ols']:.3f},{m3c['dc_active_ci_hi_ols']:.3f}]  n={m3c['n_obs']}")
print(f"  change: {100*(m3c['dc_active_coef_ols']-m3['dc_active_coef_ols'])/abs(m3['dc_active_coef_ols']):+.1f}%")
print("\nEVENT-STUDY pre-trends:")
for _, r in es_pts[es_pts["bin"].isin(["≤-4","-3","-2","-1 (ref)"])].iterrows():
    print(f"  t={r['bin']:8s}: {r['coef']:+.3f}")
print("\nWINNERS:")
for oc in OUTCOMES:
    w = cdf[(cdf.outcome==oc)&cdf.is_winner].iloc[0]
    print(f"  {oc:24s} -> {w['model']} (CV-RMSE={w['cv_rmse']:.4g}, dc_active={w['dc_active_coef_ols']:+.4g})")
