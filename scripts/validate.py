"""Check the current release, its website files, and any pending corrections.

Usage:
    python scripts/validate.py            # the current release and corrections/pending/
    python scripts/validate.py --release docs/data/releases/v1.0/nlrb_elections_v1.0.csv

Prints a short report and exits with status 1 if anything fails, so GitHub Actions can block a
change that would break the data. Standard library only.
"""
import argparse
import glob
import json
import os
import re
import sys
from collections import Counter, defaultdict

from fips import LOOKUP
from reference import STATES, sic_division, sic_major_group
from schema import ALLOWED, DERIVED_COLUMNS, FIXED_COLUMNS, INTEGER_COLUMNS, PUBLIC, num, read_csv, tally_ok

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
SITE = os.path.join(DOCS, 'data', 'site')
CORRECTION_COLUMNS = ['election_id', 'field', 'current_value', 'proposed_value', 'source', 'source_url', 'notes',
                      'credit']


class Report:
    def __init__(self):
        self.errors = defaultdict(list)
        self.checked = []

    def check(self, name, problems):
        self.checked.append(name)
        if problems:
            self.errors[name].extend(problems)

    def print(self):
        for name in self.checked:
            probs = self.errors.get(name)
            print(f"  {'FAIL' if probs else 'ok  '}  {name}" + (f' ({len(probs)})' if probs else ''))
            for p in (probs or [])[:5]:
                print(f'          {p}')
        return not self.errors


def current_release_path():
    manifest = json.load(open(os.path.join(SITE, 'versions.json')))
    v = manifest['current']
    return os.path.join(DOCS, 'data', 'releases', f'v{v}', f'nlrb_elections_v{v}.csv'), manifest


def check_release(path, rep):
    rows = read_csv(path)
    with open(path, encoding='utf-8') as f:
        header = f.readline().strip().split(',')
    rep.check('columns match the codebook', [] if header == PUBLIC else [f'got {header}'])

    ids = Counter(r['election_id'] for r in rows)
    by_id = {r['election_id']: r for r in rows}
    rep.check('election IDs are unique and well formed',
              [f'{i} appears {n} times' for i, n in ids.items() if n > 1]
              + [r['election_id'] for r in rows if not re.fullmatch(r'\d{4}-\d{4}', r['election_id'])
                 or r['election_id'][:4] != r['year']])
    rep.check('ditto and further-hearing rows point to an existing listing',
              [r['election_id'] for r in rows if (r['row_type'] != 'listing') != bool(r['refers_to'])
               or (r['refers_to'] and by_id.get(r['refers_to'], {}).get('row_type') != 'listing')])

    bad_values = []
    for col, allowed in ALLOWED.items():
        for r in rows:
            if r[col] and r[col] not in allowed:
                bad_values.append(f"{r['election_id']} {col}={r[col]!r}")
    rep.check('categorical columns hold allowed values', bad_values)
    rep.check('count columns are whole numbers',
              [f"{r['election_id']} {c}={r[c]!r}" for r in rows for c in INTEGER_COLUMNS
               if r[c] and not re.fullmatch(r'\d+', r[c])])

    loc = []
    for r in rows:
        if r['county']:
            st = STATES.get(r['state'])
            f = r['county_fips']
            if not st:
                loc.append(f"{r['election_id']} unknown state {r['state']!r}")
            elif not re.fullmatch(r'\d{5}', f) or f[:2] != st[1]:
                loc.append(f"{r['election_id']} FIPS {f!r} does not fit {r['state']}")
            elif LOOKUP.get(f) != (r['state'], r['county']):
                loc.append(f"{r['election_id']} {r['county']}, {r['state']} is not the standard name for {f}")
            if r['location_status'] != 'Located' or r['location_tier'] not in ALLOWED['location_tier']:
                loc.append(f"{r['election_id']} has a county but status {r['location_status']!r}, tier {r['location_tier']!r}")
        elif r['county_fips'] or r['location_tier'] or r['location_status'] == 'Located':
            loc.append(f"{r['election_id']} has no county but has a code, tier, or Located status")
    rep.check('counties, states, and FIPS codes agree', loc)

    sic = []
    for r in rows:
        code = r['sic_code']
        if code:
            letter, title = sic_division(code)
            if not re.fullmatch(r'\d{4}', code):
                sic.append(f"{r['election_id']} SIC {code!r}")
            elif r['sic_major_group'] != sic_major_group(code) or r['sic_division'] != f'{letter} {title}'.strip():
                sic.append(f"{r['election_id']} SIC group or division does not follow {code}")
        elif r['sic_major_group'] or r['sic_division'] or r['sic_title']:
            sic.append(f"{r['election_id']} SIC parts without a code")
    rep.check('SIC codes, groups, and divisions agree', sic)
    titles = defaultdict(set)
    for r in rows:
        if r['sic_code']:
            titles[r['sic_code']].add(r['sic_title'])
    rep.check('each SIC code has one title', [f'{k}: {sorted(v)}' for k, v in titles.items() if len(v) > 1])

    rep.check('match category is set only for matched records',
              [r['election_id'] for r in rows if bool(r['match_category']) != bool(r['nlrb_citation'])])
    rep.check('NLRB region matches the case number',
              [r['election_id'] for r in rows if r['nlrb_region'] and (
                  not r['nlrb_case_number'] or int(r['nlrb_case_number'].split('-')[0]) != int(r['nlrb_region']))])
    rep.check('vote tallies pass the consistency rules',
              [r['election_id'] for r in rows if (r['votes_for'] or r['votes_against']) and not tally_ok(
                  num(r['eligible_voters']), num(r['votes_for']), num(r['votes_against']),
                  num(r['bargaining_unit_size']))[0]])
    return rows


def check_site(manifest, rep):
    probs = []
    for name in ['aggregates.json', 'browse.json', 'codebook.json', 'versions.json', 'config.json']:
        p = os.path.join(SITE, name)
        try:
            json.load(open(p, encoding='utf-8'))
        except Exception as e:  # noqa: BLE001 - report any unreadable file
            probs.append(f'{name}: {e}')
    for rel in manifest['releases']:
        for f in rel['files']:
            if not os.path.exists(os.path.join(DOCS, f['path'])):
                probs.append(f"v{rel['version']}: missing {f['path']}")
    for name in ['overview.md', 'methods.md', 'contribute.md']:
        if not os.path.exists(os.path.join(DOCS, 'content', name)):
            probs.append(f'missing content/{name}')
    rep.check('website data and release files are present', probs)


def check_corrections(by_id, rep):
    files = sorted(glob.glob(os.path.join(ROOT, 'corrections', 'pending', '*.csv')))
    probs = []
    seen = Counter()
    for path in files:
        name = os.path.relpath(path, ROOT)
        with open(path, encoding='utf-8') as f:
            header = f.readline().strip().split(',')
        missing = [c for c in CORRECTION_COLUMNS if c not in header]
        if missing:
            probs.append(f'{name}: missing columns {missing}')
            continue
        for i, c in enumerate(read_csv(path), start=2):
            where = f'{name} line {i}'
            field, new = c['field'].strip(), c['proposed_value'].strip()
            if c['election_id'] not in by_id:
                probs.append(f"{where}: unknown election_id {c['election_id']!r}")
            if field not in PUBLIC or field in FIXED_COLUMNS or field in DERIVED_COLUMNS:
                probs.append(f'{where}: field {field!r} cannot be corrected directly')
            if not c['source'].strip():
                probs.append(f'{where}: no source')
            if field in ALLOWED and new and new not in ALLOWED[field]:
                probs.append(f'{where}: {field} cannot be {new!r}')
            if field in INTEGER_COLUMNS and new and not re.fullmatch(r'\d+', new):
                probs.append(f'{where}: {field} must be a whole number')
            if field == 'state' and new and new not in STATES:
                probs.append(f'{where}: use the full state name, not {new!r}')
            if field == 'sic_code' and new and not re.fullmatch(r'\d{4}', new):
                probs.append(f'{where}: SIC codes have four digits')
            seen[(c['election_id'], field)] += 1
    probs += [f'{eid} {field} is corrected {n} times in pending files' for (eid, field), n in seen.items() if n > 1]
    rep.check(f'pending corrections ({len(files)} files)', probs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--release', help='dataset CSV to check (default: the current release)')
    args = ap.parse_args()
    path, manifest = current_release_path()
    path = args.release or path
    rep = Report()
    print(f'Checking {os.path.relpath(path, ROOT)}')
    rows = check_release(path, rep)
    check_site(manifest, rep)
    check_corrections({r['election_id']: r for r in rows}, rep)
    ok = rep.print()
    print('All checks passed.' if ok else 'Some checks failed.')
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
