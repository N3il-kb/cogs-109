# Model Comparison — Winner Summary

CV-MSE is computed via 10-fold `GroupKFold` grouped on `fips`. Because there are only 3 treated counties (~10 post-treatment county-years after dropping contaminated controls), most CV test folds contain **zero** treated units — so the cross-validated MSE measures overall **predictive/model-selection fit** (dominated by control counties), **not** a test of the treatment effect. The causal `dc_active` estimate comes from the **full-data fit with cluster-robust standard errors (clustered on `fips`)**, reported below.


**Comparability caveat:** M1–M5 are fit on different sample frames due to listwise deletion on different predictor sets (M1 ≈3.7–4.0k rows; M2 = 3,259; M3/M4/M5 = 2,757 after dropping 2010–2011 for `poverty_rate`). CV-MSE is best read as a within-outcome model-selection metric, and absolute MSE values shift with the sample frame.


## Electricity rate (¢/kWh)  (`elec_rate_cents_kwh`)

**Winner (lowest CV-MSE): M1** — CV-MSE = 0.6589, CV-RMSE = 0.8117, n = 3811.


Data centers becoming active are associated with a +0.416 ¢/kWh change in residential electricity rates (95% CI [0.184, 0.649]) — **statistically distinguishable from zero**.


| Model | CV-MSE | CV-RMSE | dc_active β | 95% CI | sig? |
|---|---|---|---|---|---|
| M1 **(winner)** | 0.6589 | 0.8117 | +0.416 | [0.184, 0.649] | ✓ |
| M3 | 0.6781 | 0.8235 | +0.892 | [0.481, 1.303] | ✓ |
| M2 | 0.6792 | 0.8242 | +0.887 | [0.538, 1.237] | ✓ |
| M4 | 0.6824 | 0.8261 | +0.892 | [0.481, 1.303] | ✓ |
| M5 | 0.6831 | 0.8265 | +0.892 | [0.481, 1.303] | ✓ |


## Unemployment rate (pp)  (`unemployment_rate`)

**Winner (lowest CV-MSE): M3** — CV-MSE = 0.9526, CV-RMSE = 0.976, n = 2757.


Data centers becoming active are associated with a +0.588 percentage-point change in the unemployment rate (95% CI [0.013, 1.163]) — **statistically distinguishable from zero**.


| Model | CV-MSE | CV-RMSE | dc_active β | 95% CI | sig? |
|---|---|---|---|---|---|
| M3 **(winner)** | 0.9526 | 0.976 | +0.588 | [0.013, 1.163] | ✓ |
| M4 | 0.9533 | 0.9763 | +0.588 | [0.013, 1.163] | ✓ |
| M5 | 1.009 | 1.005 | +0.588 | [0.013, 1.163] | ✓ |
| M2 | 1.606 | 1.267 | +0.424 | [-0.510, 1.358] |  |
| M1 | 1.991 | 1.411 | -0.112 | [-1.030, 0.805] |  |


## Per-capita income ($)  (`per_capita_income`)

**Winner (lowest CV-MSE): M4** — CV-MSE = 5.004e+07, CV-RMSE = 7074, n = 2757.


Data centers becoming active are associated with a $-2,353 change in per-capita income (95% CI [$-8,755, $4,049]) — not distinguishable from zero (CI spans 0).


| Model | CV-MSE | CV-RMSE | dc_active β | 95% CI | sig? |
|---|---|---|---|---|---|
| M4 **(winner)** | 5.004e+07 | 7074 | -2,353 | [-8,755, 4,049] |  |
| M3 | 5.01e+07 | 7078 | -2,353 | [-8,755, 4,049] |  |
| M5 | 5.012e+07 | 7079 | -2,353 | [-8,755, 4,049] |  |
| M2 | 8.285e+07 | 9102 | +2,618 | [-5,680, 10,916] |  |
| M1 | 1.058e+08 | 1.028e+04 | +5,961 | [-3,441, 15,363] |  |
