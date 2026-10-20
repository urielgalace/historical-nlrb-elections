"""Turn the RA research worksheet into correction records.

Usage:
    python scripts/import_worksheet.py path/to/nlrb_unmatched_county_1936-1960_research.xlsx \
        --contributor "Name" [--out corrections/pending/ra_worksheet_2026-11-30.csv]

Reads the "Unmatched County" sheet (an .xlsx file needs openpyxl; a CSV export of that sheet
works without it). Rows whose Status is "Resolved" become corrections:
  - county and state, with location_source "Contributed research", tier 2, and the citation as
    the location evidence, when County (found) and State (found) are filled in;
  - industry_description, with industry_basis "Contributed research", when Industry (found) is
    filled in. A project member then assigns the SIC code.
Rows with an Election ID (the October 2026 supplement has the column) are matched by it. The
original worksheet has no election IDs, so its rows are matched to the current release by year and
case name, in order, among records that have no county. Unmatched rows are listed, not guessed.
Review the output before running make_release.py.
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys
from collections import defaultdict

from fips import LOOKUP, base, is_city
from reference import normalize_state
from schema import read_csv, write_csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'docs', 'data', 'site')
OUT_FIELDS = ['election_id', 'field', 'current_value', 'proposed_value', 'source', 'source_url', 'notes', 'credit']


def read_sheet(path):
    if path.lower().endswith('.csv'):
        return read_csv(path)
    import openpyxl
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)['Unmatched County']
    rows = ws.iter_rows(values_only=True)
    header = [str(h or '').strip() for h in next(rows)]
    return [{h: ('' if v is None else str(v).strip()) for h, v in zip(header, row)} for row in rows]


def squash(s):
    return re.sub(r'\s+', ' ', s or '').strip().rstrip('.').lower()


def standard_county(county, state):
    """The standard name for a county an RA typed ("Cook", "Cook Co.", "City of Richmond")."""
    typed = re.sub(r'\bco\.?$', 'County', county.strip(), flags=re.I)
    hits = [n for f, (s, n) in LOOKUP.items() if s == state and base(n) == base(typed)]
    if len(hits) > 1:
        hits = [n for n in hits if is_city(n) == is_city(typed)]
    return hits[0] if len(hits) == 1 else ''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('worksheet')
    ap.add_argument('--contributor', required=True, help='name to credit, or "Project RAs"')
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    v = json.load(open(os.path.join(SITE, 'versions.json')))['current']
    records = read_csv(os.path.join(ROOT, 'docs', 'data', 'releases', f'v{v}', f'nlrb_elections_v{v}.csv'))
    open_rows = defaultdict(list)                  # year -> records without a county, in ID order
    open_by_id = {}
    for r in records:
        if not r['county']:
            open_rows[r['year']].append(r)
            open_by_id[r['election_id']] = r

    sheet = read_sheet(args.worksheet)
    out, unmatched, skipped = [], [], []
    cursor = defaultdict(int)
    for i, row in enumerate(sheet, start=2):
        year, name = str(row.get('Year', '')).split('.')[0], squash(row.get('Name of Case'))
        candidates = open_rows.get(year, [])
        rec = None
        if row.get('Election ID'):
            rec = open_by_id.get(row['Election ID'])
        else:
            for j in range(cursor[year], len(candidates)):   # the sheet keeps the dataset's order
                if squash(candidates[j]['case_name']) == name:
                    rec, cursor[year] = candidates[j], j + 1
                    break
        if row.get('Status') != 'Resolved':
            continue
        if not rec:
            unmatched.append(f'line {i}: {year} {row.get("Name of Case")}')
            continue
        note = row.get('Research Notes', '')
        county, state = row.get('County (found)', ''), normalize_state(row.get('State (found)', ''))
        if county and state:
            std = standard_county(county, state)
            if not std:
                skipped.append(f'line {i} ({rec["election_id"]}): "{county}, {state}" is not a recognized county')
            else:
                src = row.get('Location Source / Citation', '')
                url = row.get('Location Source URL', '')
                city = row.get('City (found)', '')
                evidence = (f'{city}: ' if city else '') + src + (f' ({url})' if url else '')
                base_row = {'election_id': rec['election_id'], 'source': src or 'RA research', 'source_url': url,
                            'notes': note, 'credit': args.contributor}
                for field, value in [('county', std), ('state', state), ('location_source', 'Contributed research'),
                                     ('location_tier', '2'), ('location_evidence', evidence)]:
                    out.append({**base_row, 'field': field, 'current_value': rec[field], 'proposed_value': value})
        industry = row.get('Industry (found)', '')
        if industry:
            src = row.get('Industry Source / Citation', '')
            base_row = {'election_id': rec['election_id'], 'source': src or 'RA research', 'source_url': '',
                        'notes': note, 'credit': args.contributor}
            for field, value in [('industry_description', industry), ('industry_basis', 'Contributed research')]:
                out.append({**base_row, 'field': field, 'current_value': rec[field], 'proposed_value': value})

    path = args.out or os.path.join(ROOT, 'corrections', 'pending', f'ra_worksheet_{datetime.date.today()}.csv')
    if out:
        write_csv(path, out, OUT_FIELDS)
    print(f'{len(out)} corrections from {len({o["election_id"] for o in out})} records -> '
          f'{os.path.relpath(path, ROOT) if out else "nothing written"}')
    for msg in unmatched:
        print(f'  not matched to a record: {msg}')
    for msg in skipped:
        print(f'  skipped: {msg}')
    if unmatched or skipped:
        sys.exit(1)


if __name__ == '__main__':
    main()
