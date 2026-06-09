# Classifier — Matched Null vs Unmatched Positive Control

Phase 5 found the DC-county classifier scored **near chance (AUC ≈ 0.59)** against the population-matched controls. This phase runs the **identical pipeline** — same 39 positives, same 9 baseline features, same models and CV — against an **unmatched random pool of 400 counties** drawn from the same 22 states. It disambiguates the null: does the pipeline detect selection when matching is *not* in the way?

Pre-committed: reported whichever direction it comes out; the **matched null stays first**. This is corroborating context — causal inference stays with the DiD.

## 1. Matched design (Phase 5) — the null, restated first

- Negatives = 124 population/state-matched controls. Base rate ≈ 23%.
- **Logistic AUC 0.588 · KNN(10) AUC 0.592** — near chance; accuracy = base rate.
- Read: within the matched design, DC counties are barely separable on pre-treatment observables.

## 2. Unmatched positive control (this phase)

- Negatives = 400 random counties (seed 42, proportional by state), excluding all 169 master counties and all treated counties. Base rate ≈ 9%.
- **Logistic AUC 0.865 · KNN(K=47) AUC 0.830.** Winner **Logistic**, bootstrap 95% CI **[0.810, 0.917]**.
- Accuracy note: AUC is base-rate-insensitive, which is exactly why it is the metric compared across the two designs (the ~23% vs ~9% base rates don't distort it).

### Unmatched logistic coefficients (which features carry the separation)

| feature | std coef |
|---|---|
| log_total_employment | +1.358 |
| poverty_rate | -1.098 |
| unemployment_rate | +0.689 |
| per_capita_income | -0.617 |
| elec_rate_cents_kwh | -0.530 |
| log_pop_density | -0.322 |
| avg_annual_wage | +0.305 |
| median_age | -0.231 |
| pct_bachelors | +0.134 |

**Top 3 by |magnitude|:** `log_total_employment` (+1.36), `poverty_rate` (-1.10), `unemployment_rate` (+0.69).

## 3. Joint interpretation

The same pipeline that scored ~chance against matched controls reaches **AUC 0.86** against the unmatched pool. So the pipeline **can** detect DC-county selection in general — DC counties differ systematically from *typical* counties on baseline observables. The Phase-5 matched null therefore reads as **'the population/state matching removed that selection signal'** — i.e. the control design is doing its job — **not** 'nothing is detectable.' This strengthens the case that the matched DiD compares like with like, so the within-county treatment estimate is credible.

**Caveat (biases AUC *down*, conservative):** the random pool may contain counties with small/un-catalogued data centers (we excluded only the 45 known hyperscale counties). Any such contamination puts true-positives in the negative class, which can only *reduce* measured separation — so the unmatched AUC is, if anything, an underestimate.

**Coverage:** baseline features resolved for the pool at 98–100% per feature (per_capita_income & elec_rate 98%, others 100%); median-imputed inside CV.

**Inference stays with the DiD.** This classifier pair is descriptive evidence about selection, not a causal estimate.
