"""Build the first public release (v1.0) from the research pipeline's yearly workbooks.

Reads the 17 processed workbooks (nlrb<year>_processed.xlsx), writes the public dataset,
its codebook, gap lists, a review list of held-back vote tallies, and the JSON files the
website draws from.

Usage:
    python scripts/build_release.py --source "/path/to/Finished Spreadsheets" \
        --version 1.0 --date 2026-10-19

Later releases are made with scripts/make_release.py, which applies correction records to
the previous release instead of rebuilding from the workbooks.
"""
import argparse
import os
import re
import shutil
from collections import Counter, defaultdict

import pandas as pd

from reference import OUTCOME_MAP, LOCATION_SOURCE_MAP, LOCATION_GAP_MAP, normalize_state, sic_major_group, sic_division
from schema import HELD_BACK_FIELDS, num, release_files, tally_ok, write_csv, write_release_tables
from site_data import write_site_data
from fips import standard_county

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YEARS = [1936, 1937, 1938, 1939, 1940, 1941, 1942, 1943, 1944, 1945, 1946, 1947, 1948, 1949, 1950, 1955, 1960]


def clean_int(v):
    x = num(v)
    return '' if x is None else str(int(round(x)))


def plant_or_hq(value):
    """Fold the research notes in 'Plant or HQ' into four public categories."""
    s = value.lower()
    if not s:
        return ''
    s = re.sub(r'multi-(plant|mill|store)', ' ', s)
    hq = bool(re.search(r'\bhq\b|headquarters', s))
    plant = bool(re.search(r'plant|mill|mine|quarry|factory|cannery|smelter|store|establishment|division', s))
    if 'single establishment' in s or (hq and plant):
        return 'Plant and headquarters'
    if hq:
        return 'Headquarters'
    if plant:
        return 'Plant'
    return 'Office' if 'office' in s else 'Plant'


INDUSTRY_BASIS = {'header': 'Industry header', 'text': 'Decision text', 'text (careful read)': 'Decision text',
                  'same employer': 'Same employer, other decision', 'insufficient': 'Not enough information'}


def industry_basis(value):
    if value.startswith('header (mis-attributed'):
        return 'Header rejected'
    return INDUSTRY_BASIS.get(value, value)


def standardize_sic_titles(records):
    """One title per SIC code: the most common spelling without '&' (the manual's wording)."""
    seen = defaultdict(Counter)
    for r in records:
        if r['sic_code']:
            seen[r['sic_code']][r['sic_title']] += 1
    titles = {code: min(c, key=lambda t: ('&' in t, -c[t], len(t))).replace(' And ', ' and ')
              for code, c in seen.items()}
    changed = 0
    for r in records:
        if r['sic_code'] and r['sic_title'] != titles[r['sic_code']]:
            r['sic_title'] = titles[r['sic_code']]
            changed += 1
    write_csv(os.path.join(ROOT, 'data', 'reference', 'sic_titles.csv'),
              [{'sic_code': k, 'sic_title': titles[k]} for k in sorted(titles)], ['sic_code', 'sic_title'])
    return changed


def load_year(source, year):
    path = os.path.join(source, f'nlrb{year}_processed.xlsx')
    return pd.read_excel(path, sheet_name=f'{year} NLRB Cases', dtype=str).fillna('')


def build_records(source):
    records, held_back, county_fixes = [], [], []
    for year in YEARS:
        df = load_year(source, year)
        last_listing_id, last_listing_employer = '', ''
        for i, r in enumerate(df.to_dict('records'), start=1):
            g = lambda c: str(r.get(c, '') or '').strip()
            eid = f'{year}-{i:04d}'
            raw_name = g('Name of Case')
            low = raw_name.lower()
            if low in ('do', 'do.'):
                row_type, refers_to = 'ditto', last_listing_id
                employer = last_listing_employer
            elif low.startswith('further hearing'):
                row_type, refers_to = 'further_hearing', last_listing_id
                employer = last_listing_employer
            else:
                row_type, refers_to = 'listing', ''
                employer = re.sub(r'\s+', ' ', raw_name).strip(' ,;')
                last_listing_id, last_listing_employer = eid, employer

            county = g('County Name')
            state = normalize_state(g('State'))
            fips = g('County FIPS') if county else ''
            src_type = g('Source Type')
            if county:
                std_county, std_fips, fix = standard_county(county, state, fips, g('Direct Quotation'))
                if fix:
                    county_fixes.append({'election_id': eid, 'state': state, 'old_county': county,
                                         'old_fips': fips, 'county': std_county, 'county_fips': std_fips,
                                         'reason': fix})
                county, fips = std_county, std_fips
                if not county:
                    state = ''
                    src_type = 'NLRB PDF retrieved, location not parsed' if g('NLRB Citation') else ''
            if county:
                location_status = 'Located'
                location_source = LOCATION_SOURCE_MAP.get(src_type, 'Web research' if src_type else '')
            else:
                location_status = LOCATION_GAP_MAP.get(src_type, 'No decision found')
                location_source = ''

            region = g('NLRB Region')
            region = '' if region in ('', '00') else str(int(region))

            sic = g('SIC Code')
            letter, title = sic_division(sic)

            outcome_raw = g('Outcome (from NLRB disposition)')
            outcome = OUTCOME_MAP.get(outcome_raw, '')

            eligible, vfor = num(g('Eligible Voters')), num(g('Votes For'))
            vagainst, unit = num(g('Votes Against')), num(g('Bargaining Unit Size'))
            tally = {
                'eligible_voters': clean_int(g('Eligible Voters')),
                'votes_for': clean_int(g('Votes For')),
                'votes_against': clean_int(g('Votes Against')),
                'challenged_ballots': clean_int(g('Challenged Ballots')),
                'void_ballots': clean_int(g('Void or Blank Ballots')),
                'vote_tally_source': g('Vote Tally Source'),
            }
            if vfor is not None or vagainst is not None:
                ok, reason = tally_ok(eligible, vfor, vagainst, unit)
                if not ok:
                    held_back.append({'election_id': eid, 'year': year, 'employer': employer,
                                      'reason': reason, **tally,
                                      'bargaining_unit_size': clean_int(g('Bargaining Unit Size')),
                                      'tally_text': g('Vote Tally Verbatim')[:400]})
                    tally = {k: '' for k in tally}

            tier = g('Evidence Tier').replace('Tier', '').strip()
            rec = {
                'election_id': eid, 'year': str(year), 'row_type': row_type, 'refers_to': refers_to,
                'case_name': raw_name, 'employer': employer,
                'source_hearing_date': g('Date Hearing Held'), 'source_decision_date': g('Date Decision Issued'),
                'nlrb_case_number': g('NLRB Case Number'), 'nlrb_citation': g('NLRB Citation'),
                'nlrb_decision_date': g('NLRB Decision Date'), 'nlrb_region': region,
                'match_category': g('Match Category').replace('.0', '') if g('NLRB Citation') else '',
                'location_status': location_status, 'county': county, 'state': state,
                'county_fips': fips,
                'location_source': location_source, 'location_tier': tier if county else '',
                'location_evidence': g('Direct Quotation'), 'source_url': g('Source URL/Identifier'),
                'plant_or_hq': plant_or_hq(g('Plant or HQ')), 'multiple_units': g('Multiple Units'),
                'additional_counties': g('Additional Counties'),
                'industry_description': g('Industry Description'), 'sic_code': sic, 'sic_title': g('SIC Title'),
                'sic_major_group': sic_major_group(sic), 'sic_division': f'{letter} {title}'.strip(),
                'industry_basis': industry_basis(g('Industry Source')),
                'industry_evidence': g('Industry (from NLRB headnote)')[:300],
                'union_name': g('Union Name'), 'union_affiliation': g('Union Affiliation'),
                'election_type': g('Election Type'), 'bargaining_unit_size': clean_int(g('Bargaining Unit Size')),
                'outcome': outcome, 'outcome_evidence': g('Outcome Verbatim'),
                'outcome_source': g('Outcome Source Doc') if outcome else '',
                **tally,
                'needs_review': g('ManualResearchFlag'), 'notes': g('Notes'),
            }
            records.append(rec)
    return records, held_back, county_fixes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', required=True, help='folder holding nlrb<year>_processed.xlsx')
    ap.add_argument('--version', default='1.0')
    ap.add_argument('--date', required=True, help='release date, YYYY-MM-DD')
    ap.add_argument('--research-zip', default='', help='zip of the 17 research workbooks to ship with the release')
    ap.add_argument('--status', default='Release candidate', help='Release candidate until the site is public, then Published')
    args = ap.parse_args()

    records, held_back, county_fixes = build_records(args.source)
    n_titles = standardize_sic_titles(records)
    v = args.version
    rel = os.path.join(ROOT, 'docs', 'data', 'releases', f'v{v}')
    os.makedirs(rel, exist_ok=True)

    codebook, gaps = write_release_tables(rel, v, records)
    write_csv(os.path.join(rel, 'review_held_back_tallies.csv'), held_back, HELD_BACK_FIELDS)
    write_csv(os.path.join(rel, 'county_code_fixes.csv'), county_fixes,
              ['election_id', 'state', 'old_county', 'old_fips', 'county', 'county_fips', 'reason'])

    extra = []
    if args.research_zip:
        shutil.copyfile(args.research_zip, os.path.join(rel, f'nlrb_research_files_v{v}.zip'))
        extra.append({'label': 'Research workbooks, one per year (Excel, zipped)',
                      'path': f'data/releases/v{v}/nlrb_research_files_v{v}.zip', 'kind': 'research'})
    extra += [
        {'label': 'Vote tallies held back for review (CSV)', 'path': f'data/releases/v{v}/review_held_back_tallies.csv', 'kind': 'review'},
        {'label': 'County codes corrected from the research workbooks (CSV)', 'path': f'data/releases/v{v}/county_code_fixes.csv', 'kind': 'fixes'},
    ]
    files = release_files(v, extra)
    for f in files:
        f['bytes'] = os.path.getsize(os.path.join(ROOT, 'docs', f['path']))

    n_ct = sum(1 for f in county_fixes if f['reason'].startswith('Connecticut'))
    n_city = sum(1 for f in county_fixes if ' was coded ' in f['reason'])
    n_other = len(county_fixes) - n_ct - n_city
    notes = [
        'An October 2026 review checked every matched election in the 1936 to 1943 and 1947 to 1949 lists '
        'against the text of its decision. 1,405 records had been matched to a decision about a different '
        'company: 755 now point to the right decision, and 650 have no decision until they are researched. '
        'The notes column of each record says what changed.',
        f'County codes for {len(county_fixes)} records differ from the research workbooks: {n_ct} Connecticut '
        f'records moved from the 2022 planning regions back to the historical counties, {n_city} records in '
        f'independent cities that had been coded as the county of the same name, and {n_other} records whose '
        f'county had no code (fixed where the name identified one county, otherwise cleared for research). '
        f'Each change is listed in county_code_fixes.csv in the release folder of the repository.',
        f'{len(held_back)} vote tallies failed a consistency check and are held back until checked by hand.',
        'County names follow the standard name for each FIPS code, so each county is spelled one way.',
        f'SIC titles follow one spelling per code ({n_titles} records changed, for example "&" written as "and").',
    ]
    write_site_data(records, codebook, version=v, date=args.date, files=files,
                    n_held_back=len(held_back), gap_counts={k: len(rows) for k, rows in gaps.items()},
                    extra_stats={'n_county_fixes': len(county_fixes), 'n_county_fixes_ct': n_ct,
                                 'n_county_fixes_city': n_city, 'n_county_fixes_other': n_other},
                    notes=notes, status=args.status)

    print(f'v{v}: {len(records)} records -> {rel}')
    print(f'  county codes corrected: {len(county_fixes)}')
    print(f"  held back {len(held_back)} tallies; gaps: result {len(gaps['result'])}, "
          f"county {len(gaps['county'])}, industry {len(gaps['industry'])}")
    for c in codebook:
        print(f"  {c['column']:22s} {c['filled']:6d}  {c['filled_pct']:5.1f}%")


if __name__ == '__main__':
    main()
