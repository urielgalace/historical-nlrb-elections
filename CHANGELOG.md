# Changelog

## 1.0 (prepared 2026-10-19, release candidate)

First release: 13,673 election records from 17 years (1936 to 1950, 1955, and 1960), 89.8% with
a county. Built from the research workbooks with `scripts/build_release.py`. Compared with the
workbooks: 255 county codes corrected (Connecticut planning regions, Virginia independent
cities, and five records with no code), one spelling per county and per SIC title, 40 vote
tallies held back for review, and `plant_or_hq` and `industry_basis` reduced to fixed
categories. The full list of county code changes is in
`docs/data/releases/v1.0/county_code_fixes.csv`.
