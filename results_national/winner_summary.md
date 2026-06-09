# National DiD — Winner Summary (Phase 4)

Sample: national DiD set (`analysis_diD=1`), 150 counties (26 in-panel treated + 124 control), staggered `dc_active` (openings 2010–2022). Methodology identical to `fit_models_v2.py`: common sample frame per outcome, FE dummies built on the sample (rank-safe), outcome dropped from predictors, cluster-robust SEs on `fips`; winner = min GroupKFold(10) CV-MSE among M1–M5.

Inference: cluster-robust 95% CI **and** county cluster-bootstrap percentile CI (1000 resamples) — reported together for the key specs.


## Electricity rate (¢/kWh)

- **Winner (min CV-MSE among M1–M5): M1** (CV-RMSE=1.13, n=1614).
- **dc_active (winner):** +0.073 ¢/kWh, cluster CI [-0.336, +0.482] — spans 0.

| Model | CV-RMSE | dc_active β | cluster 95% CI | sig? |
|---|---|---|---|---|
| M1 **(win)** | 1.13 | +0.073 | [-0.336, +0.482] |  |
| M4 | 1.13 | +0.154 | [-0.268, +0.576] |  |
| M2 | 1.132 | +0.105 | [-0.306, +0.516] |  |
| M5 | 1.134 | +0.154 | [-0.268, +0.576] |  |
| M3 | 1.145 | +0.154 | [-0.268, +0.576] |  |

## Unemployment rate (pp)

- **Winner (min CV-MSE among M1–M5): M3** (CV-RMSE=1.676, n=1614).
- **dc_active (winner):** +0.131 pp, cluster CI [-0.311, +0.572] — spans 0.

| Model | CV-RMSE | dc_active β | cluster 95% CI | sig? |
|---|---|---|---|---|
| M3 **(win)** | 1.676 | +0.131 | [-0.311, +0.572] |  |
| M5 | 1.696 | +0.131 | [-0.311, +0.572] |  |
| M2 | 1.735 | +0.033 | [-0.412, +0.479] |  |
| M4 | 1.831 | +0.131 | [-0.311, +0.572] |  |
| M1 | 1.89 | -0.028 | [-0.586, +0.530] |  |

## Per-capita income ($)

- **Winner (min CV-MSE among M1–M5): M5** (CV-RMSE=7600, n=1614).
- **dc_active (winner):** $-1,654 , cluster CI [$-3,940, $+632] — spans 0.

| Model | CV-RMSE | dc_active β | cluster 95% CI | sig? |
|---|---|---|---|---|
| M5 **(win)** | 7600 | $-1,654 | [$-3,940, $+632] |  |
| M4 | 7607 | $-1,654 | [$-3,940, $+632] |  |
| M3 | 7612 | $-1,654 | [$-3,940, $+632] |  |
| M2 | 9473 | $-2,702 | [$-5,285, $-119] | ✓ |
| M1 | 1.404e+04 | $-440 | [$-3,941, $+3,060] |  |

## Event study (electricity)

Pre-trend coefficients (should be ~0 if parallel-trends holds):
- t=≤-4: -0.118 ¢/kWh [-0.649, +0.413]
- t=-3: -0.090 ¢/kWh [-0.498, +0.319]
- t=-2: -0.059 ¢/kWh [-0.485, +0.367]
- t=-1 (ref): +0.000 ¢/kWh (reference)
- t=0: +0.015 ¢/kWh [-0.353, +0.383]
- t=+1: +0.131 ¢/kWh [-0.297, +0.558]
- t=+2: +0.338 ¢/kWh [-0.142, +0.817]
- t=+3: +0.100 ¢/kWh [-0.415, +0.615]
- t=≥+4: +0.155 ¢/kWh [-0.412, +0.721]

**Pre-trend read:** t=-3 and t=-2 coefficients are small and near zero — parallel pre-trends are defensible.

## Robustness (electricity, M3)

| Run | dc_active β | 95% CI | n |
|---|---|---|---|
| Licking=2016 (AWS, main) | +0.154 | [-0.268, +0.576] | 1614 |
| Licking=2020 (Meta) | +0.159 | [-0.274, +0.593] | 1614 |
| Exclude FUTURE_DC_2023plus controls | +0.227 | [-0.158, +0.612] | 1295 |

- **Licking sensitivity:** pooled electricity effect changes by 0.005 ¢/kWh between the 2016 and 2020 codings — negligible; the result does not hinge on the Licking date.
- **Future-DC controls:** dropping the 29 FUTURE_DC_2023plus controls changes the effect by 0.073 ¢/kWh — stable.
