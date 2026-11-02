# How the data was built

Where each value comes from, and how far to trust it. Every record in release {{version}} keeps the quoted passage or source behind its location, industry, and result, so any value can be checked.

## Sources

**Lists of cases.** For 1936 to 1943 and 1947 to 1949, the project starts from the lists of cases printed in the NLRB's [annual reports](https://www.nlrb.gov/reports/agency-performance-reports/historical-reports/annual-reports). Section 3(c) of the National Labor Relations Act told the Board to report "the cases it has heard," so each of these reports prints a list for its fiscal year, which ran from July 1 to June 30. The lists are of cases heard, not of elections: some of these cases were settled, withdrawn, or dismissed without an election, and elections held by agreement without a hearing do not appear. From 1938 on, the project uses the part of each list headed "Representation Cases." The 1936 and 1937 lists are not divided this way, so they also include unfair labor practice cases: the 1936 report counts 152 hearings in those cases, and the 1937 report 153. The lists give the case name, along with the hearing and decision dates (1936 to 1940) or the case number (1947 to 1949). Rows marked "Do." (ditto) repeat the employer of the row above; they are kept as separate records ({{n_ditto}} rows), as are {{n_further_hearing}} further hearings.

**Years built from the index.** For 1944 to 1946, and for the pilot years 1950, 1955, and 1960, records come straight from the NLRB's index of Board decisions: one record for each representation case decided in that calendar year. The 1944 and 1945 reports do not print a list, and the reports stop printing lists after 1949. The 1946 report does print one, but this release builds 1946 from the index.

**NLRB decisions.** The Board's decisions are printed in the bound volumes Decisions and Orders of the National Labor Relations Board, and the NLRB website indexes them with a scanned copy of each. The project downloaded and read 12,399 decisions and 2,603 certification documents. Their text comes from the text layer of the scans, so it contains scanning errors.

## Matching elections to decisions

Each election is matched to the Board decision about it by employer name and date. Three passes run in order, and the pass that found the match is recorded in `match_category`:

| Category | What was matched | Records |
|---|---|---|
| 1 | A representation case decided in the election's year | {{n_match_cat1}} |
| 2 | Any case within one year | {{n_match_cat2}} |
| 3 | Any case in any year | {{n_match_cat3}} |
| Blank | No decision matched, or the match was rejected | {{n_unmatched}} |

An earlier check removed matches where the employer's name does not appear in the decision. In October 2026, all 7,224 matched records in the source lists were checked again, because some had been matched to a different company with a similar name: for example, American Granite Company to a decision about The American Furniture Co. Each employer's name was compared with the caption and text of its decision, and 353 unclear cases were read by hand. 1,405 matches were wrong. 755 were moved to the decision about the right company, and 650 were removed, leaving those records for research. The `notes` column of each record says what changed. When the right decision is from a different year, the record takes only its location and industry, since its union and result may belong to another election. The years built from the index were not affected, because each of their records comes from its own decision.

Category 2 and 3 matches are weaker in general and deserve more care.

## Location

For matched elections, the county comes from the decision itself, which usually names the plant's town, as in "its plant at Bridgeport, Connecticut." Towns are assigned to counties with the GeoNames gazetteer, and the passage is kept in `location_evidence`. Elections without a usable decision were placed by research in company histories, newspapers, and similar sources, with the source recorded.

Each location has an evidence tier:

| Tier | Meaning | Records |
|---|---|---|
| 1 | Stated in the matched NLRB decision | {{n_tier1}} |
| 2 | Documented by an independent source | {{n_tier2}} |
| 3 | Inferred or uncertain | {{n_tier3}} |

In June 2026, 1,522 uncertain locations were checked against independent sources: 505 were confirmed and 299 corrected. The county is that of the plant where the election was held when the decision names it, and otherwise that of the company headquarters (see `plant_or_hq`). When a decision covers several plants, the others are listed in `additional_counties`.

**County codes.** Counties carry five-digit FIPS codes. Connecticut uses its eight historical counties; the Census Bureau replaced them with planning regions in 2022, which did not exist in this period. For this release, {{n_county_fixes}} county codes were corrected from the research workbooks: {{n_county_fixes_ct}} Connecticut records that had been coded to the new planning regions, {{n_county_fixes_city}} records in Virginia independent cities that had been coded as the county of the same name (for example, the City of Richmond as Richmond County), and {{n_county_fixes_other}} records whose county had no code. Each correction is listed in `county_code_fixes.csv` in the release folder of the repository. County names follow the standard name for each code. The map uses present-day county lines.

## Industry

Industry comes from the matched decision: either the heading printed above the decision in the bound volume, or the decision's own description of the business, such as "engaged in the manufacture of steel castings." Each description is coded to a four-digit code in the 1987 Standard Industrial Classification (SIC), the last edition before NAICS replaced it in 1997. The division and two-digit major group follow from the code.

{{n_sic}} records ({{pct_sic}}) have a code. A blind check of 65 records found the right industry in 91% and the exact four-digit code in 85%. About 5% were wrong, usually because text from a neighboring case on the same page had been read. Headings that turned out to belong to another case were removed (`industry_basis` reads "Header rejected"). When a decision does not describe the business, the code can come from the same employer's other decisions, if most of them agree ("Same employer, other decision").

## Union, election type, and unit size

The union is the petitioning union named in the decision's caption. A name was accepted only when the decision's case number and employer agree with the record, and left blank when in doubt. A blind check of 71 records found 87% correct, 9% partly correct (the right union under a shortened name), and 4% wrong. Affiliation (AFL, CIO, AFL-CIO, or Independent) comes from the caption or text. Election type records whether the election was held by consent of the parties or directed by the Board. Unit size is the approximate number of employees in the bargaining unit when the decision states it ({{pct_unit_size}} of records).

## Results

Most decisions in this period order an election. The result came later, in a certification or a supplemental decision. The `outcome` column reports what is known:

| Outcome | Meaning | Records |
|---|---|---|
| Union certified | The Board certified the union | {{n_certified}} |
| No union | The employees voted against representation | {{n_no_union}} |
| Petition dismissed | The petition was dismissed and no election was held | {{n_dismissed}} |
| Election directed, result not yet found | The Board ordered an election; the result is in a later document not found yet | {{n_directed}} |
| Not found in decision | The matched decision does not give a result | {{n_not_found}} |
| Blank | No decision to read | {{n_no_outcome}} |

Only the first three, {{n_definite}} records ({{pct_definite}}), are definite results. The column is filled for about 72% of records, but most of those entries are procedural steps, not results.

The known results lean heavily toward union wins: a win produces a certification that is easy to find, while a loss often does not. **Do not compute win rates from this release.** In July 2026 the project asked the NLRB for its records of elections before 1961 (FOIA request 2026-NLFO-01920). Those records should fill many of these gaps in a later release.

**Vote tallies.** {{n_tally_found}} tallies of ballots were read from decisions and certifications. {{n_tally_held_back}} failed a consistency check and are held back until checked by hand: more votes than eligible voters, votes far above the size of the unit, or a very large count with nothing to check it against. They are listed on the Contribute page. The other {{n_tally}} ({{pct_tally}} of records) are in the dataset.

## Other fields

- **NLRB region** comes from the prefix of the case number. Case numbers before about 1943 had no regional prefix, so the region is blank for those; {{pct_region}} of records have one.
- **Employer** is the name as written in the source, with spacing tidied. Names are not standardized, so one company can appear under several spellings.
- **Needs review** marks records flagged for more research.

## Quality checks

The research workbooks pass 23 automated checks. Among them: every FIPS code has five digits and matches its county, the NLRB region matches the case number, SIC groups and divisions agree with the code, and categorical fields hold only allowed values. The published dataset is checked again by `scripts/validate.py` whenever the repository changes.

## Known limits

- Coverage differs by year and by source. Counts are not totals of NLRB elections.
- Records are cases, not a count of elections. The lists hold cases the Board heard, and the 1936 and 1937 lists include unfair labor practice cases.
- List years are fiscal years (July to June), and years built from the index are calendar years.
- Matches rest on names. An election at a company with several plants may be matched to the decision about another of its plants, and a few matches to a company with nearly the same name may remain.
- Results are incomplete and lean toward union wins, as explained above.
- Text comes from scans, so quoted passages contain scanning errors.
- The 1987 SIC was written decades after these elections, so some industries of the period fit its categories loosely.
- Locations are counties, not addresses. For cases covering several plants, the county is the main plant's.
