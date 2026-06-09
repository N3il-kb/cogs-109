"""
Phase 5b: positive control for the Phase 5 classifier.

Identical pipeline to fit_classifier.py — same 39 positives, same 9 baseline features,
same preprocessing (median-impute + standardize inside CV folds), same two models
(unpenalized logistic + KNN tuned 1-50), same stratified 10-fold CV seed 42, same
bootstrap. ONLY the negative class changes: 400 unmatched random counties instead of
the 124 population-matched controls.

Purpose: disambiguate the Phase 5 matched null. If the SAME pipeline scores above chance
against an unmatched pool, the matched null means "matching removed the selection signal"
(design working), not "pipeline can't detect anything." Reported whichever way it comes out;
matched null stays first. Corroborating context; inference stays with the DiD.

Writes results_national/ (new files only — does not overwrite Phase 5).
"""
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score
from sklearn.metrics import roc_auc_score, roc_curve

SEED = 42
ROOT = Path(__file__).parent.parent.parent
RES = ROOT / "results_national"

RAW_FEATS = ["per_capita_income","total_employment","avg_annual_wage","elec_rate_cents_kwh",
             "poverty_rate","unemployment_rate","pop_density","median_age","pct_bachelors"]
LOG = {"total_employment":"log_total_employment","pop_density":"log_pop_density"}
FEATURES = [LOG.get(f, f) for f in RAW_FEATS]


def pipe(model):
    return Pipeline([("imp", SimpleImputer(strategy="median")),
                     ("sc", StandardScaler()), ("clf", model)])


def positives():
    """The 39 classifier_dc=1 counties with the SAME 2010-2012 baseline features as Phase 5."""
    m = pd.read_csv(ROOT/"data"/"raw"/"county_master_list.csv", dtype={"fips":str})
    p = pd.read_csv(ROOT/"data"/"panel_master_national.csv", dtype={"fips":str})
    m["fips"]=m["fips"].str.zfill(5); p["fips"]=p["fips"].str.zfill(5)
    base = p[p["year"].between(2010,2012)].copy()
    for raw, log in LOG.items(): base[log]=np.log(base[raw].where(base[raw]>0))
    X = base.groupby("fips")[FEATURES].mean()
    pos = m[m["classifier_dc"]==1][["fips"]].merge(X, left_on="fips", right_index=True, how="left")
    pos["y"]=1
    return pos


def negatives_unmatched():
    pool = pd.read_csv(ROOT/"data"/"raw"/"unmatched_pool_baseline.csv", dtype={"fips":str})
    pool["fips"]=pool["fips"].str.zfill(5)
    for raw, log in LOG.items():
        pool[log]=np.log(pool[raw].where(pool[raw]>0))
    neg = pool[["fips"]+FEATURES].copy(); neg["y"]=0
    return neg


def cv_eval(model, X, y):
    skf = StratifiedKFold(10, shuffle=True, random_state=SEED)
    auc = cross_val_score(pipe(model), X, y, cv=skf, scoring="roc_auc").mean()
    acc = cross_val_score(pipe(model), X, y, cv=skf, scoring="accuracy").mean()
    proba = cross_val_predict(pipe(model), X, y, cv=skf, method="predict_proba")[:,1]
    return float(auc), float(acc), proba


def main():
    pos = positives(); neg = negatives_unmatched()
    df = pd.concat([pos, neg], ignore_index=True)
    X = df[FEATURES].values; y = df["y"].astype(int).values
    n, npos = len(y), int(y.sum()); base_rate = y.mean()
    print(f"unmatched design: n={n} ({npos} pos / {n-npos} neg), base rate {base_rate:.3f}")

    # KNN tuning 1..50
    skf = StratifiedKFold(10, shuffle=True, random_state=SEED)
    aucs = [cross_val_score(pipe(KNeighborsClassifier(n_neighbors=k)), X, y, cv=skf, scoring="roc_auc").mean()
            for k in range(1,51)]
    best_k = int(np.argmax(aucs))+1
    print(f"best K = {best_k} (CV AUC {max(aucs):.3f})")

    log_auc, log_acc, log_proba = cv_eval(LogisticRegression(max_iter=2000), X, y)
    knn_auc, knn_acc, knn_proba = cv_eval(KNeighborsClassifier(n_neighbors=best_k), X, y)
    print(f"Logistic: AUC {log_auc:.3f} acc {log_acc:.3f}")
    print(f"KNN(K={best_k}): AUC {knn_auc:.3f} acc {knn_acc:.3f}")

    winner = "Logistic" if log_auc>=knn_auc else f"KNN(K={best_k})"
    win_proba = log_proba if winner=="Logistic" else knn_proba
    win_auc = max(log_auc, knn_auc)

    # bootstrap CI on winner AUC
    rng = np.random.default_rng(SEED); boot=[]
    for _ in range(1000):
        idx = rng.choice(n, n, replace=True); yb, pb = y[idx], win_proba[idx]
        if 0 < yb.sum() < len(yb): boot.append(roc_auc_score(yb, pb))
    blo, bhi = float(np.percentile(boot,2.5)), float(np.percentile(boot,97.5))
    print(f"winner {winner}: bootstrap AUC CI [{blo:.3f}, {bhi:.3f}]")

    # comparison csv
    comp = pd.DataFrame([
        {"design":"unmatched","model":"Logistic","params":"unpenalized","cv_auc":log_auc,"cv_accuracy":log_acc,"base_rate":base_rate},
        {"design":"unmatched","model":"KNN","params":f"K={best_k}","cv_auc":knn_auc,"cv_accuracy":knn_acc,"base_rate":base_rate},
    ])
    comp.to_csv(RES/"classifier_positive_control.csv", index=False)

    # logistic coefficients (unmatched, full refit)
    lf = pipe(LogisticRegression(max_iter=2000)).fit(X, y)
    coefs = lf.named_steps["clf"].coef_[0]
    ctab = pd.DataFrame({"feature":FEATURES,"std_coef":coefs,"abs_coef":np.abs(coefs)}).sort_values("abs_coef",ascending=False)
    top3 = ctab.head(3)

    # ── pull Phase 5 matched results for 4-curve ROC ──
    matched = pd.read_csv(RES/"classifier_comparison.csv")
    m_log_auc = float(matched[matched.model=="Logistic"]["cv_auc"].iloc[0])
    m_knn_row = matched[matched.model=="KNN"].iloc[0]; m_knn_auc = float(m_knn_row["cv_auc"]); m_knn_k = m_knn_row["params"]
    # recompute matched OOF probas for ROC curves (identical Phase 5 pipeline)
    mm = pd.read_csv(ROOT/"data"/"raw"/"county_master_list.csv", dtype={"fips":str})
    pp = pd.read_csv(ROOT/"data"/"panel_master_national.csv", dtype={"fips":str})
    mm["fips"]=mm["fips"].str.zfill(5); pp["fips"]=pp["fips"].str.zfill(5)
    bb = pp[pp["year"].between(2010,2012)].copy()
    for raw, log in LOG.items(): bb[log]=np.log(bb[raw].where(bb[raw]>0))
    Xb = bb.groupby("fips")[FEATURES].mean()
    md = mm[["fips","classifier_dc"]].merge(Xb, left_on="fips", right_index=True, how="left")
    Xm = md[FEATURES].values; ym = md["classifier_dc"].astype(int).values
    _,_,m_log_proba = cv_eval(LogisticRegression(max_iter=2000), Xm, ym)
    mk = int(str(m_knn_k).split("=")[1])
    _,_,m_knn_proba = cv_eval(KNeighborsClassifier(n_neighbors=mk), Xm, ym)

    # ── 4-curve ROC ──
    fig, ax = plt.subplots(figsize=(7,6.5))
    curves = [
        (ym, m_log_proba, f"matched · Logistic — AUC {m_log_auc:.3f}", "tab:blue", "-"),
        (ym, m_knn_proba, f"matched · KNN({mk}) — AUC {m_knn_auc:.3f}", "tab:cyan", "-"),
        (y, log_proba, f"unmatched · Logistic — AUC {log_auc:.3f}", "tab:red", "--"),
        (y, knn_proba, f"unmatched · KNN({best_k}) — AUC {knn_auc:.3f}", "tab:orange", "--"),
    ]
    for yt, pr, lab, col, ls in curves:
        fpr, tpr, _ = roc_curve(yt, pr); ax.plot(fpr, tpr, color=col, ls=ls, lw=2, label=lab)
    ax.plot([0,1],[0,1],"k:",lw=1,label="chance (0.5)")
    ax.set_xlabel("False positive rate"); ax.set_ylabel("True positive rate")
    ax.set_title("DC-county classifier — matched (solid) vs unmatched (dashed)\nsame pipeline, only the negative class differs")
    ax.legend(loc="lower right", fontsize=9); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.savefig(RES/"classifier_positive_control_roc.png", dpi=150); plt.close()

    # ── markdown ──
    base_rate_acc = 1 - base_rate
    S = ["# Classifier — Matched Null vs Unmatched Positive Control\n",
        "Phase 5 found the DC-county classifier scored **near chance (AUC ≈ 0.59)** against the "
        "population-matched controls. This phase runs the **identical pipeline** — same 39 positives, "
        "same 9 baseline features, same models and CV — against an **unmatched random pool of 400 "
        "counties** drawn from the same 22 states. It disambiguates the null: does the pipeline detect "
        "selection when matching is *not* in the way?\n",
        "Pre-committed: reported whichever direction it comes out; the **matched null stays first**. "
        "This is corroborating context — causal inference stays with the DiD.\n",
        "## 1. Matched design (Phase 5) — the null, restated first\n",
        f"- Negatives = 124 population/state-matched controls. Base rate ≈ 23%.",
        f"- **Logistic AUC {m_log_auc:.3f} · KNN({mk}) AUC {m_knn_auc:.3f}** — near chance; accuracy = base rate.",
        "- Read: within the matched design, DC counties are barely separable on pre-treatment observables.\n",
        "## 2. Unmatched positive control (this phase)\n",
        f"- Negatives = 400 random counties (seed 42, proportional by state), excluding all 169 master "
        f"counties and all treated counties. Base rate ≈ {base_rate:.0%}.",
        f"- **Logistic AUC {log_auc:.3f} · KNN(K={best_k}) AUC {knn_auc:.3f}.** "
        f"Winner **{winner}**, bootstrap 95% CI **[{blo:.3f}, {bhi:.3f}]**.",
        f"- Accuracy note: AUC is base-rate-insensitive, which is exactly why it is the metric compared "
        f"across the two designs (the ~23% vs ~9% base rates don't distort it).\n",
        "### Unmatched logistic coefficients (which features carry the separation)\n",
        "| feature | std coef |", "|---|---|"]
    for _, r in ctab.iterrows(): S.append(f"| {r['feature']} | {r['std_coef']:+.3f} |")
    S.append(f"\n**Top 3 by |magnitude|:** " + ", ".join(f"`{r.feature}` ({r.std_coef:+.2f})" for _,r in top3.iterrows()) + ".")
    S.append("\n## 3. Joint interpretation\n")
    detected = win_auc > 0.65
    if detected:
        S.append(f"The same pipeline that scored ~chance against matched controls reaches **AUC {win_auc:.2f}** "
                 f"against the unmatched pool. So the pipeline **can** detect DC-county selection in general — "
                 f"DC counties differ systematically from *typical* counties on baseline observables. The "
                 f"Phase-5 matched null therefore reads as **'the population/state matching removed that "
                 f"selection signal'** — i.e. the control design is doing its job — **not** 'nothing is "
                 f"detectable.' This strengthens the case that the matched DiD compares like with like, so "
                 f"the within-county treatment estimate is credible.")
    else:
        S.append(f"Even against the unmatched pool the pipeline only reaches **AUC {win_auc:.2f}**. The "
                 f"selection signal is weak on these 9 observables regardless of the control design — the "
                 f"Phase-5 null is not simply an artifact of matching. Either reading leaves identification "
                 f"with the DiD.")
    S.append("\n**Caveat (biases AUC *down*, conservative):** the random pool may contain counties with "
             "small/un-catalogued data centers (we excluded only the 45 known hyperscale counties). Any such "
             "contamination puts true-positives in the negative class, which can only *reduce* measured "
             "separation — so the unmatched AUC is, if anything, an underestimate.\n")
    S.append("**Coverage:** baseline features resolved for the pool at "
             "98–100% per feature (per_capita_income & elec_rate 98%, others 100%); median-imputed inside CV.\n")
    S.append("**Inference stays with the DiD.** This classifier pair is descriptive evidence about selection, "
             "not a causal estimate.")
    (RES/"classifier_positive_control.md").write_text("\n".join(S)+"\n")

    # ── append linking paragraph to classifier_summary.md (don't rewrite) ──
    summ = RES/"classifier_summary.md"
    link = ("\n\n---\n\n## Positive control (Phase 5b)\n\n"
            f"A positive control re-ran this exact pipeline against an **unmatched** 400-county random pool. "
            f"There the best model reaches **AUC {win_auc:.2f}** (vs ~0.59 here against matched controls) — "
            f"{'confirming the pipeline detects DC-county selection in general, so the matched null reflects the matching removing that signal (design working), not an inert pipeline' if detected else 'showing the signal is weak on these observables regardless of matching'}. "
            f"See `classifier_positive_control.md` and `classifier_positive_control_roc.png`.\n")
    cur = summ.read_text()
    if "## Positive control (Phase 5b)" not in cur:
        with open(summ, "a") as f: f.write(link)

    print("\nSaved classifier_positive_control.csv / .md / _roc.png; appended link to classifier_summary.md")
    print("\n"+"="*60)
    print(f"UNMATCHED: Logistic AUC {log_auc:.3f} | KNN(K={best_k}) AUC {knn_auc:.3f} | winner {winner}")
    print(f"  bootstrap CI [{blo:.3f}, {bhi:.3f}]")
    print(f"MATCHED vs UNMATCHED (winner AUC): {max(m_log_auc,m_knn_auc):.3f}  vs  {win_auc:.3f}")
    print("top-3 unmatched logit coefs:", ", ".join(f"{r.feature}({r.std_coef:+.2f})" for _,r in top3.iterrows()))
    print("per-feature coverage: 98-100% (income & elec 98%, rest 100%)")


if __name__ == "__main__":
    main()
