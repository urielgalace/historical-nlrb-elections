# Changelog

## 1.0 (2026-11-02)

First release: 13,673 election records from 17 years (1936 to 1950, 1955, and 1960), 86.1% with
a county. Built from the research workbooks with `scripts/build_release.py`. Before release, a
review of every matched election in the 1936 to 1943 and 1947 to 1949 lists found 1,405 matched
to a decision about a different company: 755 were moved to the right decision and 650 were left
without one for research. Compared with the workbooks: 250 county codes corrected (Connecticut
planning regions, Virginia independent cities, and five records with no code), one spelling per
county and per SIC title, 40 vote tallies held back for review, and `plant_or_hq` and
`industry_basis` reduced to fixed categories. The full list of county code changes is in
`docs/data/releases/v1.0/county_code_fixes.csv`.
