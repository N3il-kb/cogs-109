# Treatment Variable Notes

## Summary

| FIPS  | County            | Operational Year | Company |
|-------|-------------------|-----------------|---------|
| 39089 | Licking County OH | 2020            | Meta    |
| 51087 | Henrico County VA | 2020            | Meta    |
| 31153 | Sarpy County NE   | 2019            | Meta    |

---

## 1. Licking County, OH (FIPS 39089) — Meta New Albany Data Center

**First operational year: 2020**

### Sources
- **Baxtel (primary listing):** https://baxtel.com/data-center/meta-new-albany-ohio  
  States "Year Built: 2020." Notes Facebook announced in August 2017, construction began 2017.
- **Data Center News Asia:** https://datacenternews.asia/story/facebook-opens-new-data-center-in-new-albany-ohio  
  "February has marked the launch of Facebook's new data center in New Albany, Ohio" — confirms February 2020 as first operational month.
- **NBC4 Columbus (10tv.com photo report):** https://www.10tv.com/article/news/local/photos-look-inside-new-facebook-data-center-new-albany-2020-feb/530-e41bf85d-e37e-4ce2-858f-9151fd03f17a  
  Published February 2020, documents opening of the first building.
- **Meta's own New Albany page:** https://datacenters.atmeta.com/ohio-new-albany/  
  States Meta "have been part of the New Albany community since breaking ground on the data center in 2017." Does not give exact operational date, but is consistent with a 2017 groundbreak / 2020 go-live.
- **Data Center Dynamics headline:** https://www.datacenterdynamics.com/en/news/facebook-launches-ohio-data-center/  
  (403 at fetch time, but headline and URL confirm "launches" framing contemporaneous with 2020.)

### Ambiguities resolved
- **Announced 2017, broke ground 2017, operational 2020.** The task prompt listed "reported ~2017" — this refers to the announcement/groundbreaking year, not the operational year. Treatment year is coded **2020**.
- The campus was built in phases: Building 1 (February 2020), Building 2 (also ~2020), Building 3 (2021), Buildings 4–5 (2022). First operational date = February 2020.

---

## 2. Henrico County, VA (FIPS 51087) — Meta Henrico Data Center

**First operational year: 2020**

### Sources
- **Meta Data Centers newsroom (primary source):** https://datacenters.atmeta.com/2020/08/henrico-county-we-are-online/  
  Meta's own announcement post dated August 5, 2020: "We are excited to announce that our Henrico Data Center in Virginia is now serving traffic." States the facility had begun serving traffic "a few weeks" before the August 5, 2020 publication date, placing first traffic in approximately mid-July 2020.
- **GRPVA (Greater Richmond Partnership):** https://www.grpva.com/news/first-phase-of-the-facebook-data-center-in-henrico-county-is-now-operational/  
  Confirms first phase operational as of August 2020. Article published August 5, 2020.
- **Baxtel (facility listing):** https://baxtel.com/data-center/meta-henrico-campus  
  Lists "Year Built: 2020."

### Ambiguities resolved
- **Broke ground 2017, operational 2020.** Task prompt listed "reported ~2018" — likely refers to a construction milestone or early announcement update, not operations. Treatment year is coded **2020**.
- The Henrico campus is a 7-building, 2.5 million sq ft campus; first building(s) went live August 2020. Subsequent buildings came online in later years. First operational date = 2020.

---

## 3. Sarpy County, NE (FIPS 31153) — Meta Sarpy Data Center

**First operational year: 2019**

### Sources
- **Baxtel (primary listing):** https://baxtel.com/data-center/meta-sarpy-nebraska  
  States "Year Built: 2019" and "The first data center comes online in 2019."
- **WOWT Omaha (local news):** https://www.wowt.com/2022/07/28/sarpy-county-meta-data-center-campus-grow-even-bigger/  
  "The data center went online in 2019 which helps power Meta's technologies."
- **Omaha World-Herald / Data Center Dynamics:** https://www.datacenterdynamics.com/en/news/meta-to-expand-sarpy-data-center-in-nebraska/  
  Multiple expansion articles reference the 2019 opening.
- **Meta Sarpy Data Center Facebook page:** https://www.facebook.com/SarpyDataCenter/  
  Community page references the facility opening in 2019.

### Ambiguities resolved
- Broke ground 2017, operational 2019. Consistent with task prompt ("reported 2019").
- Originally named the "Papillion Data Center," renamed "Sarpy Data Center" after a 2021 expansion crossed into Springfield, NE. FIPS 31153 (Sarpy County) covers both Papillion and Springfield, so the FIPS assignment is unambiguous.
- Treatment year is coded **2019**.

---

## Other Hyperscale Data Centers in OH, VA, NE (2010–2022)
*Relevant for identifying potential control county contamination.*

### Ohio

| Company   | County         | FIPS  | Approx. Operational | Notes |
|-----------|---------------|-------|---------------------|-------|
| Google    | Franklin      | 39049 | 2022                | New Albany campus; construction began 2019 |
| Google    | Fairfield     | 39045 | ~2022               | Lancaster campus; construction began 2019 |
| Google    | Scioto        | 39145 | ~2022+              | Portsmouth area; announced later |
| Various   | Franklin      | 39049 | 2014+               | New Albany Business Park hosts multiple operators (Cologix, QTS, Vantage, Compass) |

**Note:** Meta's New Albany facility (Licking County, FIPS 39089) is adjacent to Franklin County. Google's New Albany campus is in Franklin County (next county over). Licking and Franklin counties share a border — **Franklin County (39049) should be excluded from the control group** due to spillover and its own hyperscale presence.

### Virginia

Virginia hosts >35% of all known US hyperscale capacity, concentrated in "Data Center Alley":

| Company        | County/City      | FIPS  | Operational | Notes |
|---------------|-----------------|-------|-------------|-------|
| Amazon (AWS)  | Loudoun          | 51107 | 2006+       | Ashburn; dozens of facilities; $63.9B invested 2011–2022 |
| Amazon (AWS)  | Prince William   | 51153 | 2010s+      | Manassas/Haymarket |
| Amazon (AWS)  | Fairfax          | 51059 | 2010s+      | Chantilly |
| Microsoft     | Mecklenburg      | 51117 | ~2011       | Boydton campus; announced 2010, built ~2011 |
| Microsoft     | Loudoun          | 51107 | 2010s+      | Leesburg |
| Google        | Loudoun/Prince William | varies | 2009+ | Multiple facilities |

**Note:** Henrico County (FIPS 51087) is in the Richmond metro, distinct from Northern Virginia's Data Center Alley. However, its proximity to the broader Virginia data center ecosystem means adjacent counties should be checked carefully. Mecklenburg County (Microsoft, ~2011) is in southern Virginia and unlikely to contaminate Henrico's control group unless the study uses statewide controls.

### Nebraska

| Company   | County    | FIPS  | Approx. Operational | Notes |
|-----------|-----------|-------|---------------------|-------|
| Google    | Sarpy     | 31153 | ~2019–2020          | Papillion campus; groundbreaking October 2019; same county as Meta |
| Google    | Douglas   | 31055 | ~2022+              | NW Omaha; announced 2022 |
| Google    | Lancaster | 31109 | ~2024+              | Lincoln; announced 2023 |

**CRITICAL FLAG — Sarpy County contamination:** Google broke ground on a data center in Papillion (Sarpy County, FIPS 31153) in October 2019, the same county as Meta's treated unit. Google's Sarpy facility is a separate treatment confound. The regression cannot attribute all economic effects in Sarpy County solely to Meta. If the study uses a binary treated/control framework, Sarpy County has a compound treatment (both Meta 2019 and Google ~2019/2020). This should be disclosed and potentially addressed by including a Google indicator or restricting the analysis.

---

## Data Quality Notes
- DCD (datacenterdynamics.com) returned HTTP 403 for direct fetches; headline/URL content used indirectly.
- Nebraska Examiner and Omaha World-Herald redirect to paywalls; WOWT local TV and Baxtel used instead for Sarpy.
- NBC4 Columbus returned 403; 10tv.com (also local Columbus TV) provided corroborating photo coverage.
- Meta's own newsroom posts (datacenters.atmeta.com) are treated as primary sources where available.
