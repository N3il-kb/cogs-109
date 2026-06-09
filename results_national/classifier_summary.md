# DC-County Classifier — Summary (Phase 5)

**Question (Prof. Mukamel):** can the M3 baseline covariates distinguish DC counties from controls?

**Result — a near-null:** both models land at **AUC ≈ 0.59** (essentially chance), the winner's bootstrap 95% CI **[0.48, 0.68] includes 0.5**, and accuracy (0.77) is **no better than the base-rate baseline** (0.77, i.e. always predict no-DC). On these features and this control set, DC counties are **not** strongly separable from controls on pre-treatment observables.

**Why this is the EXPECTED result here, not a failure (key caveat):** the control counties were *deliberately matched* to treated counties in Phase 2 — same state, and inside the treated-county population band. Matching mechanically removes the two strongest natural separators (county **size** and **region/state**) *before* the classifier ever runs. So a low AUC is partly **designed in** by good control selection — it is evidence that the matching worked, not proof that no selection exists. (Against an *unmatched* random-county pool, the AUC would almost certainly be far higher.) Two further limiters: small n (169) and only 9 features.

**What it means for the paper (COVID-independent, supports the MLR read):** because both DC and control counties lived through COVID, *any* baseline separability is COVID-independent — so the classifier speaks to **selection on observables**, not the pandemic. The finding is that, *within the matched design*, residual gross selection on observables is weak: identification therefore rests on the **DiD** (within-county change around opening), not on cross-sectional differences. This is consistent with Phase 4 — explicit COVID controls (M3+C) barely moved the electricity coefficient. The classifier **supports** the regression read and is corroborating evidence; it is **not** a causal estimator, and inference stays with the MLR.

**Sample:** one row per county, n=169 (39 DC-positive, 130 negative; base rate 23.1%). Note the brief estimated 124 controls / 24% base rate; the actual label `classifier_dc` counts the 6 post-2022 treated counties as negatives (no operational DC in-panel), giving 130 negatives. Features = per-county **2010–2012 baseline means** of the 9 M3 covariates (standardized; median-imputed for 5 counties missing a baseline electricity rate). No treatment/flag columns used as features.

**Caveat:** the 2010–2012 baseline is genuinely pre-treatment for almost all in-panel treated counties; a few 2011–2012 openers have ≤1–2 baseline years overlapping treatment onset. Noted, not engineered around.

## Model comparison (stratified 10-fold CV, seed 42)

| Model | params | CV AUC | CV accuracy |
|---|---|---|---|
| Logistic | unpenalized | 0.588 | 0.782 |
| KNN | K=10 | 0.592 | 0.775 |
| Baseline (predict no-DC) | — | 0.500 | 0.769 |

**Winner: KNN(K=10)** (CV AUC 0.592). Bootstrap 95% CI on the winner's AUC: **[0.484, 0.684]** (1000 county resamples).

At threshold 0.5 the winner reaches accuracy 0.77 vs the 0.77 base-rate baseline (sensitivity 0.13, specificity 0.96, precision 0.50).

## Logistic coefficients (standardized — drivers of selection)

| feature | std coef |
|---|---|
| per_capita_income | -0.674 |
| avg_annual_wage | +0.609 |
| poverty_rate | -0.512 |
| log_total_employment | +0.455 |
| unemployment_rate | +0.272 |
| elec_rate_cents_kwh | -0.104 |
| pct_bachelors | -0.080 |
| log_pop_density | -0.033 |
| median_age | +0.007 |

**Top 3 by |magnitude|:** `per_capita_income` (-0.67), `avg_annual_wage` (+0.61), `poverty_rate` (-0.51).

## Robustness

| Run | n | positives | logistic CV AUC | best-KNN CV AUC |
|---|---|---|---|---|
| Main | 169 | 39 | 0.588 | 0.592 |
| Exclude 13 ALWAYS_TREATED (2011–2022 cohort) | 156 | 26 | 0.487 | 0.572 |
| Exclude 29 FUTURE_DC_2023plus controls | 140 | 39 | 0.619 | 0.606 |

**Read:** AUC stays near chance across both reruns (logistic 0.49 / 0.62; dropping the NoVA always-treated extremes even pushes logistic *below* 0.5). The near-null is not driven by a few extreme observations or by the future-DC label edge-cases — it is stable. Separability stays weak whichever subset we look at.

## Interpretation for the paper

Within the matched design, DC counties are **barely** separable from controls on pre-treatment observables (AUC 0.59, CI includes chance; accuracy = base rate). The honest read is two-sided: (1) the control matching in Phase 2 (same state + population band) deliberately stripped out the biggest selectors, so weak residual separability is expected and is a sign the matching worked; (2) whatever cross-sectional selection remains is too faint for these 9 observables to detect at n=169. Either way, identification leans on the **DiD within-county comparison**, not on cross-sectional contrasts. Because both classes experienced COVID, this is a **COVID-independent** statement about selection — consistent with Phase 4, where explicit COVID controls (M3+C) barely moved the electricity coefficient. **The classifier corroborates the regression read; it is not a causal estimator, and inference stays with the MLR.** (It does *not*, on its own, explain why the 3-county estimate was +0.89 vs the national ~+0.15 — that gap is better attributed to the 3-county design's tiny, non-representative treated sample than to a measured selection signature here.)

