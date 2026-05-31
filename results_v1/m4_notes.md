# M4 — Lasso on the M3 predictor set
## 1. Why dc_active_coef/se/ci come from OLS, not Lasso

LassoCV applies an L1 penalty to **all** coefficients, including `dc_active`, the treatment indicator. This shrinks `dc_active` toward zero (and can set it exactly to zero) purely to reduce prediction variance, and Lasso does not produce standard errors. To keep the treatment effect estimate comparable to the other models in the forest plot, the reported `dc_active_coef`, `dc_active_se`, `dc_active_ci_lo`, `dc_active_ci_hi` come from an **unpenalized cluster-robust OLS** (`cov_type='cluster'`, clustered on `fips`) fit on the exact same (unstandardized) M3 design matrix. The Lasso's own standardized `dc_active` coefficient is reported separately as `dc_active_lasso_std_coef`.
All predictors were standardized with `StandardScaler` (fit on the training fold only inside CV; fit on all rows for the full-data report); the outcome `y` is never standardized, so MSE/RMSE are on the original scale. Outer CV is `GroupKFold(10)` grouped by `fips`. Because every M3 predictor set includes `poverty_rate`, rows with `year in {2010, 2011}` are dropped for all three outcomes before listwise deletion.
## 2. Per-outcome chosen alpha and predictors Lasso kept

### elec_rate_cents_kwh

- n_obs = 2757, n_groups = 255, n_predictors = 21
- chosen alpha = 0.00686649
- CV RMSE = 0.826084 (cv_mse_mean = 0.682415)
- # non-zero predictors kept = 18
- non-zero predictors: dc_active, year_2014, year_2015, year_2016, year_2017, year_2018, year_2019, year_2021, year_2022, state_39, state_51, per_capita_income, log_total_employment, avg_annual_wage, poverty_rate, unemployment_rate, log_pop_density, pct_bachelors

### unemployment_rate

- n_obs = 2757, n_groups = 255, n_predictors = 21
- chosen alpha = 0.00212095
- CV RMSE = 0.976346 (cv_mse_mean = 0.953252)
- # non-zero predictors kept = 20
- non-zero predictors: dc_active, year_2013, year_2014, year_2015, year_2016, year_2017, year_2018, year_2019, year_2020, year_2021, year_2022, state_39, state_51, per_capita_income, log_total_employment, avg_annual_wage, poverty_rate, log_pop_density, median_age, pct_bachelors

### per_capita_income

- n_obs = 2757, n_groups = 255, n_predictors = 21
- chosen alpha = 10
- CV RMSE = 7074.24 (cv_mse_mean = 5.00449e+07)
- # non-zero predictors kept = 20
- non-zero predictors: dc_active, year_2013, year_2014, year_2015, year_2016, year_2017, year_2018, year_2020, year_2021, year_2022, state_39, state_51, log_total_employment, avg_annual_wage, elec_rate_cents_kwh, poverty_rate, unemployment_rate, log_pop_density, median_age, pct_bachelors

## 3. Did dc_active survive penalization?

- **elec_rate_cents_kwh**: dc_active SURVIVED (Lasso std coef = 0.0455306). OLS dc_active coef = 0.892025 [0.480974, 1.30308].
- **unemployment_rate**: dc_active SURVIVED (Lasso std coef = 0.0322947). OLS dc_active coef = 0.588186 [0.0129739, 1.1634].
- **per_capita_income**: dc_active SURVIVED (Lasso std coef = -128.34). OLS dc_active coef = -2353.31 [-8755.34, 4048.71].
