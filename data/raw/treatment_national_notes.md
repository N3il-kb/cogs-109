# National Hyperscale Treatment List — Notes

**Generated:** 2026-06-09 via multi-agent web research (6 operator-research agents + 6 FIPS/year-verification agents).

**Scope:** US counties that received a hyperscale data center (Meta, Google, AWS, Microsoft, Apple, Oracle). Colocation/enterprise facilities excluded. Output is **county-level** — multiple facilities in one county collapse to a single row, with `dc_opening_year` = the *earliest* operator's opening (first treatment) and `all_operators` listing every hyperscaler found.

**Output:** `data/raw/treatment_national.csv` — 45 counties (from 59 distinct facility findings).

## Counts

- **Total counties:** 45
- **In-panel treatment events (opening 2010–2022):** 28
- **Pre-2010 (already-treated at panel start, no clean pre-trend):** 11
- **Post-2022 (outside panel, listed for completeness):** 6
- **Multiple-operator (compound treatment):** 8
- **Huge-metro (treatment dilution risk):** 10
- **County-border FIPS ambiguity:** 8

### By primary operator (earliest in county)

- Google: 12
- Meta: 12
- AWS: 10
- Microsoft: 6
- Apple: 4
- Oracle: 1

### By opening-year bucket

- pre-2010: 11
- 2010–2018 (PRE_COVID_COHORT): 16
- 2019–2020: 5
- 2021–2022: 7
- post-2022: 6

### Opening-year confidence

- high: 32
- medium: 8
- low: 5

## PRE-2019 COHORT (the COVID-defense counties) — clean pre-COVID identification

These open 2010–2018, giving a clean pre-2020 treatment window not confounded by the pandemic. This is the cohort the brief specifically wanted.

- `37035` Catawba County NC — Apple 2010 (high)
- `51165` Prince William County VA — AWS 2010 (low)
- `40097` Mayes County OK — Google 2011 (high)
- `41013` Crook County OR — Meta 2011 (high)
- `41049` Morrow County OR — AWS 2011 (high)
- `51059` Fairfax County VA — AWS 2011 (low)
- `19153` Polk County IA — Microsoft 2012 (high)
- `37161` Rutherford County NC — Meta 2012 (high)
- `32031` Washoe County NV — Apple 2012 (high)
- `51117` Mecklenburg County VA — Microsoft 2012 (high)
- `56021` Laramie County WY — Microsoft 2013 (high)
- `04013` Maricopa County AZ — Oracle 2016 (high)
- `39049` Franklin County OH — AWS 2016 (high)
- `39089` Licking County OH — AWS 2016 (high)
- `41059` Umatilla County OR — AWS 2017 (medium)
- `48439` Tarrant County TX — Meta 2017 (high)

Brief specifically requested two of these — both found and verified:
- Valencia County NM (Meta Los Lunas): found, **2019** opening (Meta engineering blog, Feb 2019) — note this lands just *outside* the 2010–2018 pre-COVID window by the verified date, so it sits in the 2019–2020 bucket, not pre-COVID.
- Newton County GA (Meta Stanton Springs): found, **2021** (medium confidence; 2020–2021 sources conflict) — also lands after 2018.

Both requested counties verified to open *later* than the brief's ~2018 guess, so neither is actually pre-COVID. The genuine pre-COVID Meta sites are Prineville OR (2011), Forest City NC (2012), Altoona IA (2014), Fort Worth TX (2017).

## Original cohort (the 3 from `treatment.csv`)

- `39089` Licking County OH — AWS 2016 (high)  
    ORIGINAL_COHORT | PRE_COVID_COHORT | MULTIPLE_OPERATORS(AWS;Meta;Google) | COUNTY_BORDER_AMBIGUITY || per-operator opening years: AWS:2016, Meta:2020, Google:2021 || AWS US East (Ohio) Data Centers - New Albany
- `51087` Henrico County VA — Meta 2020 (high)  
    ORIGINAL_COHORT || Meta Henrico Data Center
- `31153` Sarpy County NE — Meta 2019 (high)  
    ORIGINAL_COHORT | MULTIPLE_OPERATORS(Meta;Google) || per-operator opening years: Meta:2019, Google:2021 || Meta Sarpy (Papillion) Data Center

**IMPORTANT — Licking County OH (39089) treatment-year change:** in the original 3-county file this county was coded `dc_opening_year=2020` (Meta). The national scan finds **AWS opened in New Albany/Licking in 2016** (us-east-2 region launch, Oct 2016), four years before Meta. Under a 'any hyperscaler = treatment' definition, Licking's first treatment is **2016**, and the CSV reflects that. If the study intends 'Meta specifically' as treatment, override back to 2020. Flag for the controls/spec decision.

## Pre-2010 counties (no clean pre-trend in a 2010-start panel)

Already treated when the panel begins — usable only as 'always-treated' (drop, or use as a separate never-clean group). Do NOT use as controls.

- `13097` Douglas County GA — Google 2003 (low)
- `06001` Alameda County CA — Apple 2006 (high)
- `41065` Wasco County OR — Google 2006 (high)
- `51107` Loudoun County VA — AWS 2006 (high)
- `53025` Grant County WA — Microsoft 2007 (high)
- `37027` Caldwell County NC — Google 2008 (medium)
- `45015` Berkeley County SC — Google 2008 (medium)
- `48029` Bexar County TX — Microsoft 2008 (high)
- `06085` Santa Clara County CA — AWS 2009 (medium)
- `19155` Pottawattamie County IA — Google 2009 (high)
- `17031` Cook County IL — Microsoft 2009 (high)

## Multiple-operator counties (compound treatment — same issue as Sarpy in the original)

- `04013` Maricopa County AZ — Oracle 2016 (high)  — operators: Oracle;Apple;Microsoft;Meta
- `06085` Santa Clara County CA — AWS 2009 (medium)  — operators: AWS;Oracle
- `17031` Cook County IL — Microsoft 2009 (high)  — operators: Microsoft;Oracle
- `19153` Polk County IA — Microsoft 2012 (high)  — operators: Microsoft;Meta
- `31153` Sarpy County NE — Meta 2019 (high)  — operators: Meta;Google
- `39089` Licking County OH — AWS 2016 (high)  — operators: AWS;Meta;Google
- `41013` Crook County OR — Meta 2011 (high)  — operators: Meta;Apple
- `51107` Loudoun County VA — AWS 2006 (high)  — operators: AWS;Oracle;Google

## Huge-metro counties (treatment dilution — candidate exclusions)

County populations ~1.5M+; a single campus is a rounding error against the local economy, so effects attenuate. Consider excluding or modeling separately.

- `04013` Maricopa County AZ — Oracle 2016 (high)
- `06001` Alameda County CA — Apple 2006 (high)
- `06085` Santa Clara County CA — AWS 2009 (medium)
- `17031` Cook County IL — Microsoft 2009 (high)
- `32003` Clark County NV — Google 2020 (medium)
- `39049` Franklin County OH — AWS 2016 (high)
- `48029` Bexar County TX — Microsoft 2008 (high)
- `48439` Tarrant County TX — Meta 2017 (high)
- `49049` Utah County UT — Meta 2021 (high)
- `51107` Loudoun County VA — AWS 2006 (high)

## County-border FIPS ambiguity (verify before final use)

- `19153` Polk County IA — Microsoft 2012 (high)  — PRE_COVID_COHORT | MULTIPLE_OPERATORS(Microsoft;Meta) | COUNTY_BORDER_AMBIGUITY
- `29047` Clay County MO — Meta 2025 (high)  — POST_PANEL_2023plus | COUNTY_BORDER_AMBIGUITY
- `32031` Washoe County NV — Apple 2012 (high)  — PRE_COVID_COHORT | COUNTY_BORDER_AMBIGUITY
- `39049` Franklin County OH — AWS 2016 (high)  — PRE_COVID_COHORT | HUGE_METRO | COUNTY_BORDER_AMBIGUITY
- `39089` Licking County OH — AWS 2016 (high)  — ORIGINAL_COHORT | PRE_COVID_COHORT | MULTIPLE_OPERATORS(AWS;Meta;Google) | COUNTY_BORDER_AMBIGUITY
- `48139` Ellis County TX — Google 2021 (low)  — COUNTY_BORDER_AMBIGUITY
- `51059` Fairfax County VA — AWS 2011 (low)  — PRE_COVID_COHORT | COUNTY_BORDER_AMBIGUITY
- `51165` Prince William County VA — AWS 2010 (low)  — PRE_COVID_COHORT | COUNTY_BORDER_AMBIGUITY

## Found but could not confidently date (excluded from CSV)

Mostly announced/under-construction sites with no operational date yet (overwhelmingly post-2022), plus a few ambiguous colocation/leased cloud regions. Listed so we don't re-research them.

- Meta: Meta Temple Data Center, Temple, Bell County, TX -- Broke ground 2022, paused, construction resumed Oct 2023; ~900k sqft / 386 acres at 3101 Industrial Blvd; not yet operational as of mid-2026 (target ~2026+). Bell County. Beyond 2010-2022 panel.
- Meta: Meta El Paso Data Center, El Paso, El Paso County, TX -- Groundbreaking announced Oct 2025; ~1.2M sqft scaling to 1GW; investment raised to $10B; target operational 2028. Not operational. Beyond panel.
- Meta: Meta Kuna Data Center, Kuna, Ada County, ID -- Announced 2022, broke ground Sept 2022; 960k sqft, $800M; completion targeted 2025 but still under construction in early 2026. Kuna is in Ada County (SW of Boise). Beyond panel.
- Meta: Meta Rosemount Data Center, Rosemount, Dakota County, MN -- Announced March 2024; 715k sqft at UMore Park; operations slated to begin 2026. Not yet operational. Rosemount is in Dakota County. Beyond panel.
- Meta: Meta Jeffersonville Data Center, Jeffersonville, Clark County, IN -- Announced Jan 2024; ~700k sqft in River Ridge Commerce Center; expected operational 2026. Not yet operational. Jeffersonville is in Clark County. Beyond panel.
- Meta: Meta Lebanon Data Center, Lebanon, Boone County, IN -- Groundbreaking Feb 2026 at LEAP District; ~4M sqft, $10B+; first phase target late 2027/early 2028. Not operational. Lebanon is in Boone County. Beyond panel.
- Meta: Meta Richland Parish Data Center (Hyperion), Richland Parish, LA -- Announced Dec 2024; 4M sqft, Meta's largest; construction started late 2024; expected operational ~2030. Not operational. Richland Parish (parish = county equivalent). Beyond panel.
- Meta: Meta Aiken Data Center, Aiken, Aiken County, SC -- Announced Aug 2024; 715k sqft in Sage Mill Industrial Park; expected operational spring 2027. Not operational. Aiken County. Beyond panel.
- Meta: Meta Bowling Green Data Center, Bowling Green / Middleton Township, Wood County, OH -- Announced 2025; 715k sqft, $800M; target operational ~2027. Not operational. Site is in Middleton Township, Wood County (north of Bowling Green). Beyond panel.
- Meta: Meta Beaver Dam Data Center, Beaver Dam, Dodge County, WI -- Groundbreaking Nov 12, 2025; 700k+ sqft, $1B; expected online 2027. Not operational. Beaver Dam is in Dodge County. Beyond panel.
- Meta: Meta Montgomery Data Center, Montgomery, Montgomery County, AL -- Announced April 2024, expanded Sept 2025; $1.5B; expected live end of 2026. Not yet operational. Montgomery County. Beyond panel.
- Meta: Meta Cheyenne Data Center, Cheyenne, Laramie County, WY -- Announced July 2024; 715k sqft, $800M, in High Plains Business Park; construction started early 2024; expected online 2027. Not operational. Laramie County. Beyond panel.
- Meta: Meta Tulsa Data Center ('Project Anthem'), Tulsa, Tulsa County, OK -- Groundbreaking announced April 2026; $1B+; expected operational 2028. Not operational. Tulsa County. Beyond panel.
- Google: Google Omaha, Nebraska (listed as active on Google's locations page, distinct from Papillion/Sarpy; likely a newer northwest-Omaha Douglas County build announced 2022, opening year not confidently established and likely post-2022)
- Google: Google Eagle Mountain, Utah (Utah County) - Google bought ~300 acres but no confirmed build timeline; Salt Lake City us-west3 cloud region (Feb 2020) appears to be leased space, not an owned hyperscale facility, so excluded from dated list
- AWS: AWS GovCloud (US-West) region - launched 2011, hosted in Eastern Oregon (Morrow/Umatilla counties); not a distinct new site beyond the Boardman/Hermiston campuses already listed
- AWS: AWS GovCloud (US-East) region - launched Nov 2018 in Columbus OH area; likely co-located within the existing Franklin/Licking County us-east-2 campuses rather than a separate site
- AWS: AWS Local Zones (Los Angeles 2019, Boston/Miami/Houston 2021, plus Atlanta/Chicago/Dallas/Denver/Las Vegas/NYC/Phoenix/Seattle) - small edge facilities, typically hosted in third-party colocation; excluded as non-hyperscale and ambiguous treatment
- AWS: AWS Arizona (Mesa/Pecos campus, Goodyear, Laveen/Phoenix, Tucson 'Project Blue') - all announced/under construction 2024-2027, post-panel
- AWS: AWS Mississippi (Madison County Mega Site & Ridgeland; Warren County/Vicksburg) - announced 2024-2025, post-panel
- AWS: AWS Georgia (Butts County, Douglas County, Covington/Newton County, Lamar County) - announced 2024-2025, post-panel
- AWS: AWS Pennsylvania (Schuylkill County/Kline Township; Salem Township/Susquehanna nuclear campus) - 2024-2025, post-panel
- AWS: AWS Maryland (Lusby/Calvert County near Calvert Cliffs; BWI/Anne Arundel campuses) - mostly post-panel
- AWS: AWS Indiana Phase II / Hobart (Lake County) and additional New Carlisle campuses - 2025-2026, post-panel
- AWS: AWS Texas (San Antonio/Bexar County; Hood County 'Project Spectrum') - post-panel
- AWS: AWS North Carolina (Richmond County) - announced post-panel
- AWS: Ohio Sidney 'Project Galaxy' (Shelby County, $3B) - announced ~2024, post-panel
- Microsoft: Microsoft Atlanta / East US 3 region (Douglasville in Douglas County GA, plus East Point/Palmetto/Union City in Fulton County GA) — under construction, region launch targeted 2027, OUTSIDE the 2010-2022 panel window
- Microsoft: Microsoft Mount Pleasant / Fairwater data center (Racine County, WI) — operational targeted early 2026, OUTSIDE the panel window
- Microsoft: Microsoft San Jose / Alviso / Orchard Pkwy data centers (Santa Clara County, CA) — under development, operational ~2028, OUTSIDE the panel window
- Microsoft: Microsoft Texas Research Park / Castroville campus (Medina County, TX) — construction from ~2022 onward, at/after the edge of the panel window
- Microsoft: Microsoft Project Osmium (Warren County + Madison County, IA) — announced ~2022+, OUTSIDE the panel window; original Iowa treatment captured under the Polk County West Des Moines entry
- Microsoft: An 'operational Microsoft Santa Clara, CA' facility appears in some location databases but is likely leased/colocation capacity rather than a Microsoft-built hyperscale campus — SKIPPED as ambiguous

## Method / caveats

- Opening year = first-building operational / region-GA date, NOT announcement or groundbreaking.
- FIPS verified per-facility; one correction applied at synthesis: AWS Chantilly VA Fairfax County = **51059** (a research note had written 51061, which is Fauquier).
- AWS/Oracle dates are often region-launch dates and several are leased/colocation rather than owned campuses — treatment is more ambiguous for those; flagged in per-row notes.
- This step does NOT pull federal data, select controls, or touch existing scripts (per brief). Not committed — left for review.
