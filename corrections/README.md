# Corrections

Accepted corrections wait in `pending/` until the next release applies them. `make_release.py`
then moves each file to `applied/v<version>/`, so every change stays on record.

## File format

One CSV file per batch, with these columns (see `TEMPLATE.csv`):

| Column | What to put in it |
|---|---|
| `election_id` | The record's ID, for example `1944-0123`. |
| `field` | The column to change, as named in the codebook. |
| `current_value` | The value in the current release. The release script stops if it no longer matches, so two edits cannot collide. Leave blank to skip this check. |
| `proposed_value` | The new value. |
| `source` | A source someone else can check: an NLRB citation, an archive reference, or a newspaper and date. Required. |
| `source_url` | A link to the source, if there is one. |
| `notes` | Anything else a reviewer should know. |
| `credit` | The contributor's name as they want it shown, or blank. |

## Rules

- Use the full state name (`Illinois`) and the standard county name (`Cook County`, `City of Richmond`).
  The standard names are in `data/reference/county_fips_lookup.csv`.
- Do not set `county_fips`, `sic_major_group`, `sic_division`, or `location_status`: they follow
  from the county, state, and SIC code.
- A county correction that does not also set `location_source`, `location_tier`, and
  `location_evidence` gets "Contributed research", tier 2, and the source.
- A new SIC code needs a `sic_title` row too, unless the code already appears in
  `data/reference/sic_titles.csv`.
- `election_id`, `year`, `row_type`, `refers_to`, and `case_name` identify the record and cannot
  be corrected.

Run `python scripts/validate.py` to check pending files before making a release.
