# Model Comparison v2 — Winner Summary

**v2 fix:** all five models for a given outcome are fit on the *same rows* — the common sample defined by complete cases on the M3 (largest) predictor union. CV-MSE is now comparable across M1–M5 within an outcome (v1 fit them on 3811/3259/2757 rows and the numbers were not comparable).


**Cross-validation note:** 10-fold `GroupKFold` grouped on `fips`. With only 3 treated counties (~10 post-treatment county-years), most CV test folds contain zero treated units, so CV-MSE measures overall predictive fit (dominated by control counties) for model selection — it is *not* a test of the treatment effect.


**Treatment inference:** the `dc_active` coefficient, SE and 95% CI come from the **full-data fit with cluster-robust standard errors clustered on `fips`** (standard DiD practice for serially-correlated county panels). For M4/M5 the regularized (standardized) dc_active coefficient is reported alongside, but inference uses the unpenalized cluster-robust OLS on the same predictors.


## Electricity rate (¢/kWh)  (`elec_rate_cents_kwh`)

- **Common sample:** n = 2757, years 2012–2022, 255 counties.
- **Winner (lowest CV-MSE): M3** (CV-MSE = 0.6781, CV-RMSE = 0.8235).
- **dc_active (winner, OLS):** +0.892 ¢/kWh, 95% CI [0.481, 1.303].
- **Interpretation:** Data centers becoming active are associated with a +0.892 ¢/kWh change in residential electricity rates — **distinguishable from zero**.

| Model | CV-MSE | CV-RMSE | overfit gap | dc_active β (OLS) | 95% CI | sig? |
|---|---|---|---|---|---|---|
| M3 **(winner)** | 0.6781 | 0.8235 | -0.029 | +0.892 | [0.481, 1.303] | ✓ |
| M4 | 0.6824 | 0.8261 | -0.0284 | +0.892 | [0.481, 1.303] | ✓ |
| M5 | 0.6831 | 0.8265 | -0.0277 | +0.892 | [0.481, 1.303] | ✓ |
| M2 | 0.685 | 0.8276 | -0.0183 | +0.916 | [0.532, 1.300] | ✓ |
| M1 | 0.7176 | 0.8471 | -0.0104 | +0.519 | [0.264, 0.774] | ✓ |


## Unemployment rate (pp)  (`unemployment_rate`)

- **Common sample:** n = 2757, years 2012–2022, 255 counties.
- **Winner (lowest CV-MSE): M3** (CV-MSE = 0.9526, CV-RMSE = 0.976).
- **dc_active (winner, OLS):** +0.588 pp, 95% CI [0.013, 1.163].
- **Interpretation:** Data centers becoming active are associated with a +0.588 percentage-point change in the unemployment rate — **distinguishable from zero**.

| Model | CV-MSE | CV-RMSE | overfit gap | dc_active β (OLS) | 95% CI | sig? |
|---|---|---|---|---|---|---|
| M3 **(winner)** | 0.9526 | 0.976 | -0.0373 | +0.588 | [0.013, 1.163] | ✓ |
| M4 | 0.9533 | 0.9764 | -0.0375 | +0.588 | [0.013, 1.163] | ✓ |
| M5 | 1.009 | 1.005 | -0.0183 | +0.588 | [0.013, 1.163] | ✓ |
| M2 | 1.154 | 1.074 | -0.0312 | +0.295 | [-0.418, 1.008] |  |
| M1 | 1.391 | 1.179 | -0.0198 | -0.125 | [-0.762, 0.512] |  |


## Per-capita income ($)  (`per_capita_income`)

- **Common sample:** n = 2757, years 2012–2022, 255 counties.
- **Winner (lowest CV-MSE): M4** (CV-MSE = 5.005e+07, CV-RMSE = 7074).
- **dc_active (winner, OLS):** $-2,353, 95% CI [$-8,755, $4,049].
- **Interpretation:** Data centers becoming active are associated with a $-2,353 change in per-capita income — not distinguishable from zero (CI spans 0).

| Model | CV-MSE | CV-RMSE | overfit gap | dc_active β (OLS) | 95% CI | sig? |
|---|---|---|---|---|---|---|
| M4 **(winner)** | 5.005e+07 | 7074 | -4.64e+06 | -2,353 | [-8,755, 4,049] |  |
| M3 | 5.01e+07 | 7078 | -4.7e+06 | -2,353 | [-8,755, 4,049] |  |
| M5 | 5.012e+07 | 7079 | -4.23e+06 | -2,353 | [-8,755, 4,049] |  |
| M2 | 9.307e+07 | 9647 | -9.95e+06 | +2,918 | [-5,426, 11,262] |  |
| M1 | 1.122e+08 | 1.059e+04 | -4.61e+06 | +5,837 | [-3,504, 15,178] |  |
