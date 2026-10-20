"""The public dataset's columns and the rules every release follows.

Shared by build_release.py (v1.0, from the research workbooks), make_release.py (later
versions, from correction records), validate.py, and import_worksheet.py. Standard library only,
so the checks run anywhere, including GitHub Actions.
"""
import csv
import os

# Public columns, in file order: (name, description). The codebook is generated from this list.
COLUMNS = [
    ('election_id', 'Stable identifier: the list year and the row number within that year (for example 1944-0001). IDs never change once published.'),
    ('year', 'Year of the election list the record comes from.'),
    ('row_type', '"listing" for an ordinary row; "ditto" for a row marked "Do." in the source list (same employer as the row above); "further_hearing" for a further hearing of the case above.'),
    ('refers_to', 'For ditto and further-hearing rows, the election_id of the row they refer to.'),
    ('case_name', 'Case name exactly as written in the source list, or in the NLRB decisions index for 1944 to 1946, 1950, 1955, and 1960.'),
    ('employer', 'Employer name as written in the source, with spacing tidied. Ditto and further-hearing rows take the employer of the row they refer to.'),
    ('source_hearing_date', 'Hearing date as written in the source list (1936 to 1940 only). Kept verbatim, including footnote markers.'),
    ('source_decision_date', 'Decision date as written in the source list. Kept verbatim, including footnote markers such as "(b)".'),
    ('nlrb_case_number', 'Case number of the matched NLRB decision. Early numbers without a regional prefix are written with "00".'),
    ('nlrb_citation', 'Citation of the matched decision in the bound volumes, Decisions and Orders of the NLRB (volume NLRB page).'),
    ('nlrb_decision_date', 'Date of the matched NLRB decision (MM/DD/YYYY).'),
    ('nlrb_region', 'NLRB regional office, from the case number prefix. Blank for case numbers without a regional prefix (most cases before about 1943).'),
    ('match_category', 'How the election was matched to a decision: 1 = a representation case in the election year; 2 = any case within one year; 3 = any case in any year. Blank = no decision matched, or the match was rejected on review (see notes).'),
    ('location_status', 'Located; Decision found, location not yet extracted; Decision match rejected; or No decision found.'),
    ('county', 'County (or parish, borough, or independent city) of the establishment where the election took place, under the standard name for its FIPS code. Connecticut uses its eight historical counties.'),
    ('state', 'State of the establishment (full name).'),
    ('county_fips', 'Five-digit county FIPS code (state code + county code). Connecticut uses its historical county codes (09001 to 09015), not the planning regions adopted in 2022.'),
    ('location_source', 'Where the location comes from: NLRB decision; Web research; Web research, verified; Web research, corrected; NLRB decision, unverified match; or Inferred from employer name.'),
    ('location_tier', 'Evidence tier for the location. 1 = stated in the matched NLRB decision; 2 = documented by an independent source; 3 = inferred or uncertain.'),
    ('location_evidence', 'Quoted passage that supports the location.'),
    ('source_url', 'Link to the matched NLRB decision or to the source used for the location.'),
    ('plant_or_hq', 'What the county refers to: Plant (the establishment where the election was held), Headquarters (the company headquarters), Plant and headquarters (both in the same place), or Office (another company office).'),
    ('multiple_units', 'Yes when the decision covers more than one plant or unit.'),
    ('additional_counties', 'Other counties named for multi-plant cases.'),
    ('industry_description', 'Short description of the employer\'s business, in the style of the NLRB\'s industry headers.'),
    ('sic_code', 'Four-digit 1987 Standard Industrial Classification (SIC) code, assigned from the decision\'s own description of the business.'),
    ('sic_title', 'Title of the SIC code.'),
    ('sic_major_group', 'Two-digit SIC major group.'),
    ('sic_division', 'SIC division letter and name (for example "D Manufacturing").'),
    ('industry_basis', 'Where the industry came from: Industry header (the heading printed above the decision in the bound volume), Decision text (the decision\'s description of the business), Not enough information, or Header rejected (the heading belonged to another case, so no code was kept).'),
    ('industry_evidence', 'The text the industry was read from (OCR text; may contain scanning errors).'),
    ('union_name', 'Name of the petitioning union, as written in the decision caption.'),
    ('union_affiliation', 'AFL, CIO, AFL-CIO (after the December 1955 merger), or Independent.'),
    ('election_type', 'Consent (agreed by the parties) or Board-directed (ordered by the Board after a hearing).'),
    ('bargaining_unit_size', 'Approximate number of employees in the bargaining unit, when the decision states it.'),
    ('outcome', 'Union certified; No union; Petition dismissed; Election directed, result not yet found (the result is in a separate certification document we have not located); or Not found in decision.'),
    ('outcome_evidence', 'Quoted passage that supports the outcome.'),
    ('outcome_source', 'Citation of the document the outcome comes from.'),
    ('eligible_voters', 'Eligible voters, from the tally of ballots.'),
    ('votes_for', 'Votes for the union (or for the leading union).'),
    ('votes_against', 'Votes against union representation.'),
    ('challenged_ballots', 'Challenged ballots.'),
    ('void_ballots', 'Void or blank ballots.'),
    ('vote_tally_source', 'Citation of the document the tally comes from.'),
    ('needs_review', 'Yes when the record is flagged for manual research or verification.'),
    ('notes', 'Notes from the research process.'),
]
PUBLIC = [c for c, _ in COLUMNS]

# Values a categorical column may hold ('' is always allowed).
ALLOWED = {
    'row_type': {'listing', 'ditto', 'further_hearing'},
    'match_category': {'1', '2', '3'},
    'location_status': {'Located', 'Decision found, location not yet extracted', 'Decision match rejected',
                        'No decision found'},
    'location_source': {'NLRB decision', 'NLRB decision, unverified match', 'Web research', 'Web research, verified',
                        'Web research, corrected', 'Inferred from employer name', 'Contributed research'},
    'location_tier': {'1', '2', '3'},
    'plant_or_hq': {'Plant', 'Headquarters', 'Plant and headquarters', 'Office'},
    'multiple_units': {'Yes', 'No'},
    'industry_basis': {'Industry header', 'Decision text', 'Not enough information', 'Header rejected',
                       'Contributed research'},
    'union_affiliation': {'AFL', 'CIO', 'AFL-CIO', 'Independent'},
    'election_type': {'Consent', 'Board-directed'},
    'outcome': {'Union certified', 'No union', 'Petition dismissed', 'Election directed, result not yet found',
                'Not found in decision'},
    'needs_review': {'Yes', 'No'},
}
INTEGER_COLUMNS = ['bargaining_unit_size', 'eligible_voters', 'votes_for', 'votes_against', 'challenged_ballots',
                   'void_ballots']
# Columns a correction may not change: they identify the record.
FIXED_COLUMNS = {'election_id', 'year', 'row_type', 'refers_to', 'case_name'}
# Columns computed from others; corrections set the source column instead.
DERIVED_COLUMNS = {'county_fips', 'sic_major_group', 'sic_division', 'location_status'}

GAP_FIELDS = ['election_id', 'year', 'employer', 'case_name', 'county', 'state', 'nlrb_case_number',
              'nlrb_citation', 'nlrb_decision_date', 'location_status', 'source_url']
HELD_BACK_FIELDS = ['election_id', 'year', 'employer', 'reason', 'eligible_voters', 'votes_for', 'votes_against',
                    'challenged_ballots', 'void_ballots', 'bargaining_unit_size', 'vote_tally_source', 'tally_text']


def num(v):
    v = str(v or '').replace(',', '').strip()
    try:
        return float(v)
    except ValueError:
        return None


def tally_ok(eligible, votes_for, votes_against, unit_size):
    """Consistency checks for a parsed tally of ballots. Returns (ok, reason)."""
    total = (votes_for or 0) + (votes_against or 0)
    if eligible is not None and total > eligible * 1.05 + 2:
        return False, 'more votes cast than eligible voters'
    if unit_size is not None and total > unit_size * 3 + 10:
        return False, 'votes far exceed the bargaining unit size'
    biggest = max(votes_for or 0, votes_against or 0)
    if eligible is None and unit_size is None and biggest > 5000:
        return False, 'implausibly large count with no eligible-voter figure'
    return True, ''


def read_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows, fields):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def codebook_for(records):
    n = len(records)
    return [{'column': name, 'description': desc,
             'filled': sum(1 for r in records if str(r.get(name, '')).strip()),
             'filled_pct': round(100 * sum(1 for r in records if str(r.get(name, '')).strip()) / n, 1)}
            for name, desc in COLUMNS]


def gap_lists(records):
    """Records still missing a result, a county, or an industry (listing rows for the last two)."""
    return {
        'result': [r for r in records if r['outcome'] == 'Election directed, result not yet found'],
        'county': [r for r in records if not r['county'] and r['row_type'] == 'listing'],
        'industry': [r for r in records if not r['sic_code'] and r['row_type'] == 'listing'],
    }


def write_release_tables(rel_dir, version, records):
    """Dataset, codebook, and gap lists for one release. Returns (codebook, gaps)."""
    write_csv(os.path.join(rel_dir, f'nlrb_elections_v{version}.csv'), records, PUBLIC)
    codebook = codebook_for(records)
    write_csv(os.path.join(rel_dir, f'codebook_v{version}.csv'), codebook,
              ['column', 'description', 'filled', 'filled_pct'])
    gaps = gap_lists(records)
    for key, name in [('result', 'missing_result.csv'), ('county', 'missing_county.csv'),
                      ('industry', 'missing_industry.csv')]:
        write_csv(os.path.join(rel_dir, 'gaps', name), gaps[key], GAP_FIELDS)
    return codebook, gaps


def release_files(version, extra=()):
    """File entries for versions.json, in display order."""
    v = version
    files = [
        {'label': 'Dataset (CSV)', 'path': f'data/releases/v{v}/nlrb_elections_v{v}.csv', 'kind': 'data'},
        {'label': 'Codebook (CSV)', 'path': f'data/releases/v{v}/codebook_v{v}.csv', 'kind': 'codebook'},
        *[f for f in extra if f['kind'] in ('research', 'changes')],
        {'label': 'Elections missing a result (CSV)', 'path': f'data/releases/v{v}/gaps/missing_result.csv', 'kind': 'gap'},
        {'label': 'Elections missing a county (CSV)', 'path': f'data/releases/v{v}/gaps/missing_county.csv', 'kind': 'gap'},
        {'label': 'Elections missing an industry (CSV)', 'path': f'data/releases/v{v}/gaps/missing_industry.csv', 'kind': 'gap'},
        *[f for f in extra if f['kind'] not in ('research', 'changes')],
    ]
    return files
