"""
compare_models.py — Merge M1–M5 result JSONs into a comparison table, pick winners,
and render comparison + forest plots.

Inputs : results/m{1..5}_results.json  (one per model, each with 3 outcomes)
Outputs:
  results/comparison_table.csv       (15 rows = 5 models × 3 outcomes)
  results/winner_summary.md          (winner per outcome + dc_active interpretation)
  results/cv_mse_comparison.png      (grouped bars: outcome × model, y=CV-MSE)
  results/dc_active_forest_plot.png  (subplot per outcome: β ± 95% CI per model)

NOTE on comparability: M1–M5 are fit on DIFFERENT sample frames because of listwise
deletion on different predictor sets (M1 ~3.7–4.0k rows, M2 3259, M3/M4/M5 2757 after
the poverty-rate 2010–2011 drop). CV-MSE is therefore a within-outcome model-selection
metric, not a strictly cross-comparable number across models. This is surfaced in
winner_summary.md.
"""

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

ROOT = Path(__file__).parent.parent
RES = ROOT / "results"

MODELS = ["m1", "m2", "m3", "m4", "m5"]
OUTCOMES = ["elec_rate_cents_kwh", "unemployment_rate", "per_capita_income"]

OUTCOME_LABELS = {
    "elec_rate_cents_kwh": "Electricity rate (¢/kWh)",
    "unemployment_rate": "Unemployment rate (pp)",
    "per_capita_income": "Per-capita income ($)",
}

# ── Load all results ────────────────────────────────────────────────────────────
rows = []
for m in MODELS:
    d = json.load(open(RES / f"{m}_results.json"))
    model_name = d["model"]
    for oc in OUTCOMES:
        v = d["outcomes"][oc]
        rows.append({
            "model": model_name,
            "outcome": oc,
            "n_obs": v.get("n_obs"),
            "cv_mse_mean": v["cv_mse_mean"],
            "cv_mse_std": v["cv_mse_std"],
            "cv_rmse": v["cv_rmse"],
            "train_mse": v["train_mse"],
            "overfitting_gap": v["train_mse"] - v["cv_mse_mean"],
            "dc_active_coef": v["dc_active_coef"],
            "dc_active_se": v["dc_active_se"],
            "dc_active_ci_lo": v["dc_active_ci_lo"],
            "dc_active_ci_hi": v["dc_active_ci_hi"],
        })

df = pd.DataFrame(rows)

# ── Winner per outcome = min CV-MSE ───────────────────────────────────────────────
df["is_winner"] = False
for oc in OUTCOMES:
    sub = df[df["outcome"] == oc]
    win_idx = sub["cv_mse_mean"].idxmin()
    df.loc[win_idx, "is_winner"] = True

# ── Validation ────────────────────────────────────────────────────────────────────
assert len(df) == 15, f"Expected 15 rows, got {len(df)}"
bad = df[df[["cv_mse_mean", "dc_active_coef"]].isna().any(axis=1)]
assert bad.empty, f"NaN in cv_mse or dc_active_coef:\n{bad}"

# ── Save comparison table ──────────────────────────────────────────────────────────
col_order = [
    "model", "outcome", "n_obs", "cv_mse_mean", "cv_mse_std", "cv_rmse",
    "train_mse", "overfitting_gap", "dc_active_coef", "dc_active_se",
    "dc_active_ci_lo", "dc_active_ci_hi", "is_winner",
]
df[col_order].to_csv(RES / "comparison_table.csv", index=False)
print(f"Saved comparison_table.csv ({len(df)} rows)")


# ── Winner summary ─────────────────────────────────────────────────────────────────
def ci_excludes_zero(lo, hi):
    return (lo > 0 and hi > 0) or (lo < 0 and hi < 0)


lines = ["# Model Comparison — Winner Summary\n"]
lines.append(
    "CV-MSE is computed via 10-fold `GroupKFold` grouped on `fips`. Because there are "
    "only 3 treated counties (~10 post-treatment county-years after dropping contaminated "
    "controls), most CV test folds contain **zero** treated units — so the cross-validated "
    "MSE measures overall **predictive/model-selection fit** (dominated by control counties), "
    "**not** a test of the treatment effect. The causal `dc_active` estimate comes from the "
    "**full-data fit with cluster-robust standard errors (clustered on `fips`)**, reported below.\n"
)
lines.append(
    "\n**Comparability caveat:** M1–M5 are fit on different sample frames due to listwise "
    "deletion on different predictor sets (M1 ≈3.7–4.0k rows; M2 = 3,259; M3/M4/M5 = 2,757 "
    "after dropping 2010–2011 for `poverty_rate`). CV-MSE is best read as a within-outcome "
    "model-selection metric, and absolute MSE values shift with the sample frame.\n")

for oc in OUTCOMES:
    sub = df[df["outcome"] == oc].sort_values("cv_mse_mean")
    win = sub[sub["is_winner"]].iloc[0]
    label = OUTCOME_LABELS[oc]
    lines.append(f"\n## {label}  (`{oc}`)\n")
    lines.append(
        f"**Winner (lowest CV-MSE): {win['model']}** — "
        f"CV-MSE = {win['cv_mse_mean']:.4g}, CV-RMSE = {win['cv_rmse']:.4g}, "
        f"n = {int(win['n_obs'])}.\n")
    coef = win["dc_active_coef"]
    lo, hi = win["dc_active_ci_lo"], win["dc_active_ci_hi"]
    sig = ci_excludes_zero(lo, hi)
    sig_txt = "**statistically distinguishable from zero**" if sig else "not distinguishable from zero (CI spans 0)"

    # Outcome-specific interpretation sentence
    if oc == "elec_rate_cents_kwh":
        interp = (f"Data centers becoming active are associated with a "
                  f"{coef:+.3f} ¢/kWh change in residential electricity rates "
                  f"(95% CI [{lo:.3f}, {hi:.3f}]) — {sig_txt}.")
    elif oc == "unemployment_rate":
        interp = (f"Data centers becoming active are associated with a "
                  f"{coef:+.3f} percentage-point change in the unemployment rate "
                  f"(95% CI [{lo:.3f}, {hi:.3f}]) — {sig_txt}.")
    else:  # per_capita_income
        interp = (f"Data centers becoming active are associated with a "
                  f"${coef:+,.0f} change in per-capita income "
                  f"(95% CI [${lo:,.0f}, ${hi:,.0f}]) — {sig_txt}.")
    lines.append(f"\n{interp}\n")

    # dc_active across all models for this outcome
    lines.append("\n| Model | CV-MSE | CV-RMSE | dc_active β | 95% CI | sig? |")
    lines.append("|---|---|---|---|---|---|")
    for _, r in sub.iterrows():
        s = "✓" if ci_excludes_zero(r["dc_active_ci_lo"], r["dc_active_ci_hi"]) else ""
        if oc == "per_capita_income":
            beta = f"{r['dc_active_coef']:+,.0f}"
            ci = f"[{r['dc_active_ci_lo']:,.0f}, {r['dc_active_ci_hi']:,.0f}]"
        else:
            beta = f"{r['dc_active_coef']:+.3f}"
            ci = f"[{r['dc_active_ci_lo']:.3f}, {r['dc_active_ci_hi']:.3f}]"
        star = " **(winner)**" if r["is_winner"] else ""
        lines.append(
            f"| {r['model']}{star} | {r['cv_mse_mean']:.4g} | {r['cv_rmse']:.4g} | {beta} | {ci} | {s} |")
    lines.append("")

(RES / "winner_summary.md").write_text("\n".join(lines))
print("Saved winner_summary.md")


# ── Plot 1: grouped bar CV-MSE ──────────────────────────────────────────────────────
# CV-MSE scales differ wildly across outcomes (income MSE ~1e8), so normalize each
# outcome's bars to the min model for that outcome → "relative CV-MSE (vs best)".
fig, ax = plt.subplots(figsize=(10, 6))
model_order = ["M1", "M2", "M3", "M4", "M5"]
colors = plt.cm.viridis(np.linspace(0.1, 0.85, len(model_order)))
n_out = len(OUTCOMES)
bar_w = 0.15
x = np.arange(n_out)

for mi, m in enumerate(model_order):
    heights = []
    for oc in OUTCOMES:
        sub = df[df["outcome"] == oc]
        val = sub[sub["model"] == m]["cv_mse_mean"].iloc[0]
        best = sub["cv_mse_mean"].min()
        heights.append(val / best)  # relative to best for that outcome
    ax.bar(x + mi * bar_w, heights, bar_w, label=m, color=colors[mi])

ax.set_xticks(x + bar_w * (len(model_order) - 1) / 2)
ax.set_xticklabels([OUTCOME_LABELS[o] for o in OUTCOMES], fontsize=9)
ax.set_ylabel("CV-MSE relative to best model (1.0 = winner)")
ax.set_title("Cross-validated MSE by model and outcome\n(normalized within outcome; lower = better)")
ax.axhline(1.0, color="gray", ls=":", lw=1)
ax.legend(title="Model", ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.12))
ax.set_ylim(0.95, max(1.05, ax.get_ylim()[1]))
plt.tight_layout()
plt.savefig(RES / "cv_mse_comparison.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved cv_mse_comparison.png")


# ── Plot 2: dc_active forest plot ────────────────────────────────────────────────────
fig, axes = plt.subplots(1, n_out, figsize=(15, 5))
for ax, oc in zip(axes, OUTCOMES):
    sub = df[df["outcome"] == oc].set_index("model").loc[model_order]
    y = np.arange(len(model_order))[::-1]  # M1 on top
    coefs = sub["dc_active_coef"].values
    los = sub["dc_active_ci_lo"].values
    his = sub["dc_active_ci_hi"].values
    err_lo = coefs - los
    err_hi = his - coefs
    pt_colors = ["tab:red" if ci_excludes_zero(lo, hi) else "tab:gray"
                 for lo, hi in zip(los, his)]
    ax.errorbar(coefs, y, xerr=[err_lo, err_hi], fmt="o", capsize=4,
                ecolor="black", elinewidth=1.2, markersize=7,
                markerfacecolor="none", markeredgewidth=0)
    # color points individually
    for xi, yi, c in zip(coefs, y, pt_colors):
        ax.plot(xi, yi, "o", color=c, markersize=8, zorder=3)
    ax.axvline(0, color="steelblue", ls="--", lw=1.2)
    ax.set_yticks(y)
    ax.set_yticklabels(model_order)
    ax.set_title(OUTCOME_LABELS[oc], fontsize=11)
    ax.set_xlabel("dc_active coefficient (95% CI)")
    ax.grid(axis="x", alpha=0.3)

fig.suptitle("Treatment effect (dc_active) across models — cluster-robust 95% CIs\n"
             "red = CI excludes 0; gray = spans 0; dashed line = null", fontsize=12)
plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig(RES / "dc_active_forest_plot.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved dc_active_forest_plot.png")

# ── Console summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("COMPARISON TABLE")
print("=" * 70)
with pd.option_context("display.width", 200, "display.max_columns", 20):
    print(df[col_order].to_string(index=False))
print("\nWinners (min CV-MSE per outcome):")
for oc in OUTCOMES:
    w = df[(df.outcome == oc) & df.is_winner].iloc[0]
    print(f"  {oc:24s} -> {w['model']}  (CV-MSE={w['cv_mse_mean']:.4g})")
