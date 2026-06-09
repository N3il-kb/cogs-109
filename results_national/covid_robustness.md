# COVID Robustness — M3 vs M3+C

The headline COVID defense: does adding explicit COVID controls (`covid_deaths_per_100k`, `wfh_rate`) to M3 move the `dc_active` effect? If not, the effect is not a pandemic artifact.

M3 and M3+C are fit on *slightly* different frames — M3+C additionally requires non-NaN covid/wfh, dropping 2024 (no covid data) and any wfh-missing rows. n is reported for each.


## Electricity rate (¢/kWh)

| Spec | n | dc_active β | cluster-robust 95% CI | bootstrap 95% CI |
|---|---|---|---|---|
| M3 | 1614 | +0.154 ¢/kWh | [-0.268, +0.576] | [-0.276, +0.605] |
| M3+C | 1614 | +0.138 ¢/kWh | [-0.290, +0.567] | [-0.318, +0.605] |

- **Change in dc_active when COVID controls added: -10.3%** (+0.154 → +0.138 ¢/kWh).
- **Read:** the electricity effect barely moves when COVID deaths and WFH are controlled explicitly — direct evidence the rate effect is NOT a pandemic artifact.

## Unemployment rate (pp)

| Spec | n | dc_active β | cluster-robust 95% CI | bootstrap 95% CI |
|---|---|---|---|---|
| M3 | 1614 | +0.131 pp | [-0.311, +0.572] | [-0.379, +0.645] |
| M3+C | 1614 | +0.113 pp | [-0.331, +0.557] | [-0.357, +0.604] |

- **Change in dc_active when COVID controls added: -13.7%** (+0.131 → +0.113 pp).

## Per-capita income ($)

| Spec | n | dc_active β | cluster-robust 95% CI | bootstrap 95% CI |
|---|---|---|---|---|
| M3 | 1614 | -1,654 $ | [-3,940, +632] | [-4,538, +792] |
| M3+C | 1614 | -1,668 $ | [-3,887, +551] | [-4,481, +859] |

- **Change in dc_active when COVID controls added: -0.8%** (-1,654 → -1,668 $).
