# Control Selection & Master County List — Notes (Phase 2)

**Generated:** 2026-06-09. Inputs: `treatment_national.csv` (45 DC counties, Phase 1); county population from ACS 2019 5-yr B01003 (pulled for all 1,770 counties in the 22 treated states, cached in `data/cache/county_pop_2019.csv`).

## Population band

- Band computed from the **core** treated counties = in-panel treated (opening 2010–2022) **excluding the 5 huge-metro outliers** (Maricopa AZ, Tarrant TX, Clark NV, Franklin OH, Utah UT).
- **Band applied to control candidates: [25,000 , 1,150,000].** Lower bound per brief (~25k floor drops too-rural counties); upper bound ≈ largest core (non-huge-metro) treated county.
- Treated counties themselves are kept regardless of band (3 core treated sit below 25k: Storey NV 3,988; Mayes OK 11,303; Crook OR 23,011 — they stay treated; the band only filters *controls*).

## Sampling

- Seed = **42**. Target ≈4 controls per in-panel treated county, allocated by state; the 6 treated states with zero *in-panel* treated (CA, IL, IN, MO, SC, WA — their DC counties are pre-2010 or post-2022) received a baseline of 2 each so state FE remain estimable.
- Within each state: loose **nearest-population matching** to that state's treated county population(s), round-robin, no formal propensity scoring.
- **Final controls: 124** (target ~120 met).

## Data-center cross-check of candidate controls

All 124 sampled candidates were web-checked for DC presence (datacentermap / Baxtel / local news) via a parallel multi-agent pass. Verdicts: 59 clean, 29 minor-colo, 36 flagged for a major DC.

**Key decision — panel-window timing.** The study window is 2010–2022. Of the 36 flagged, only **7 host a data center that was operational *during* the panel** (genuine contamination); the other **29 are 2023–2028 announcements / land purchases** — the county was a clean control throughout 2010–2022. Per the agreed decision:

- **7 in-panel-contaminated controls were DROPPED and back-filled** (same-state nearest-population, re-screened):
  - Whitfield County, Georgia (13313) → **Floyd County GA (13115)**
  - DuPage County, Illinois (17043) → **Lake County IL (17097)**
  - Buffalo County, Nebraska (31019) → **Scotts Bluff County NE (31157)**
  - Collin County, Texas (48085) → **Fort Bend County TX (48157)**
  - Denton County, Texas (48121) → **Montgomery County TX (48339)**
  - Salt Lake County, Utah (49035) → **Iron County UT (49021)**
  - Prince William County, Virginia (51153) → **Alexandria city VA (51510)**

  Dropped (in-panel DC operational ≤2022): Whitfield GA (Core Scientific 170MW, 2021), DuPage IL (CyrusOne cluster), Prince William VA (Data Center Alley, 44 bldgs), Collin TX & Denton TX (DFW clusters), Salt Lake UT (Aligned/Oracle), Buffalo NE (Compute North 70MW). All 7 backfills re-screened clean (Montgomery TX has only small pre-2022 colo → kept, noted).

- **29 post-panel-DC controls were KEPT and tagged `FUTURE_DC_2023plus`** in `cohort_flags`. They are valid controls for 2010–2022 but flagged so Phase 3+ can run a sensitivity analysis excluding them. Dropping all of them would have biased the control pool toward counties that never attracted DC investment (itself correlated with treatment drivers).

  Tagged future-DC controls: Bartow County GE, Box Elder County UT, Caroline County VI, Chaves County NE, Chesterfield County VI, Contra Costa County CA, Dona Ana County NE, Ector County TE, El Paso County TE, Elkhart County IN, Fairfield County OH, Fayette County GE, Greene County OH, Guadalupe County TE, Hamilton County IN, Jefferson County MI, Lancaster County NE, Lea County NE, Linn County IO, Lyon County NE, Medina County OH, Montgomery County AL, Natrona County WY, Petersburg city VI, Pickaway County OH, Pima County AR, Pinal County AR, Scott County IO, Shelby County AL.

## Controls per state

| State | Controls | of which future-DC tagged | minor-colo |
|---|---|---|---|
| AL | 8 | 2 | 1 |
| AZ | 5 | 2 | 0 |
| CA | 2 | 1 | 1 |
| GA | 4 | 2 | 0 |
| IA | 4 | 2 | 1 |
| IL | 2 | 0 | 0 |
| IN | 2 | 2 | 0 |
| MO | 2 | 1 | 1 |
| NC | 8 | 0 | 0 |
| NE | 4 | 1 | 1 |
| NM | 7 | 3 | 1 |
| NV | 5 | 1 | 2 |
| OH | 12 | 4 | 4 |
| OK | 4 | 0 | 0 |
| OR | 12 | 0 | 3 |
| SC | 2 | 0 | 1 |
| TN | 4 | 0 | 2 |
| TX | 8 | 3 | 3 |
| UT | 7 | 1 | 3 |
| VA | 16 | 3 | 4 |
| WA | 2 | 0 | 2 |
| WY | 4 | 1 | 0 |
| **Total** | **124** | **29** | **30** |

## Cross-state fills

Nevada had only 5 eligible in-band controls (needed 12). Shortfall of 7 filled from same Census division (Mountain): UT, NM, AZ. These keep NV's treated counties matched to demographically/geographically similar Mountain-West controls; flagged `CROSS_STATE_FILL`.

## Final counts (input to Phase 3)

- **Total counties: 169** (45 treated + 124 control)
- **DiD analysis set (`analysis_diD=1`): 150** = 26 in-panel treated + 124 controls
- **Classifier positives (`classifier_dc=1`): 39** = 26 in-panel treated + 13 always-treated (pre-2010, operational throughout panel)
- **Always-treated (pre-2010, classifier-only, excluded from DiD): 13**
- **Post-2022 treated (excluded from BOTH DiD and classifier): 6**

**Flag semantics:** DiD subset = rows where `analysis_diD=1`. Classifier dataset = all rows, label = `classifier_dc`. The two post-2022 / always-treated rules ensure no county that is 'half-treated' during the panel pollutes either analysis.

## Caveats

- Population is a single 2019 vintage used only for band/matching; not a time-varying control (that comes in Phase 3).
- Minor colocation in 29 control counties is noted, not excluded (too small to move county outcomes) — a stated limitation.
- DC cross-check reflects web sources as of June 2026; a county's 'future DC' status could change.
- Did NOT pull the federal panel, modify scripts, or commit (per brief).

## Correction log (post-Phase-2 FIPS/year audit)

A review of the VA treated entries found and fixed three errors in `treatment_national.csv`; `county_master_list.csv` was rebuilt from the corrected source. The control set itself was unchanged (only 8 VA controls had their `matched_to_treated_fips` pointer re-targeted; see below).

1. **Removed bogus `51165` row.** The AWS Manassas/Prince William entry carried FIPS `51165`, which is **Rockingham County, VA** (Shenandoah Valley, no data center). The `county` label said "Prince William" but the code was wrong.
2. **Added Prince William as `51153`** (the correct FIPS). AWS has been in the us-east-1 NoVA footprint since ~2006–2009 (7505 Mason King Ct leased 100% to an unnamed IT enterprise from Jan 2009, plausibly AWS). Coded **pre-2010 / `ALWAYS_TREATED`** (classifier-positive, excluded from DiD) per decision — no clean pre-trend. The 2009-vs-2011 onset is genuinely ambiguous; an optional sensitivity check could treat it as in-panel onset 2011.
3. **Re-coded Fairfax `51059`: year 2011 → 2006.** AWS IAD1 ("VDC", 4101A Westfax Dr, Chantilly/Fairfax) was operational in 2006 (us-east-1 launch year) and IAD9 in 2009 — both pre-2010. Fairfax flips from in-panel `PRE_COVID_COHORT` to `ALWAYS_TREATED` (high confidence).

**Downstream effect on counts:** in-panel treated **28 → 26** (Prince William and Fairfax both leave the DiD set); always-treated **11 → 13**. Total counties (169), control count (124), and classifier-positive count (39) are unchanged. Eight VA controls previously matched to `51165`/`51059` were re-pointed to the nearest remaining in-panel VA treated unit (Henrico `51087` or Mecklenburg `51117`) by population; no control was added, dropped, or re-sampled, preserving seed-42 reproducibility.

**FIPS reference (verified against Census/ACS):** 51153 = Prince William County · 51165 = Rockingham County · 51059 = Fairfax County · 51061 = Fauquier County · 51600 = Fairfax city · 51683 = Manassas city. The remaining VA treated rows (Loudoun 51107, Mecklenburg 51117, Henrico 51087) were checked and are correct.
