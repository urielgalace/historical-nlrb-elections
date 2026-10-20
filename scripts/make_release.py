"""Make the next release by applying accepted corrections to the current one.

Usage:
    python scripts/make_release.py --version 1.1 --date 2026-11-30 \
        --title "RA research on missing locations" [--summary "..."] [--status Published] [--dry-run]

Steps:
1. Read every CSV in corrections/pending/ (columns: election_id, field, current_value,
   proposed_value, source, source_url, notes, credit) and check it with the same rules as
   validate.py.
2. Apply the corrections to the current release. Columns computed from others (county_fips,
   SIC group and division, location status) follow automatically. A county correction that does
   not also set location_source, location_tier, or location_evidence gets "Contributed
   research", tier 2, and the correction's source.
3. Write docs/data/releases/v<version>/ with the dataset, codebook, gap lists, held-back tallies,
   and a list of every changed value; refresh the website data and version history.
4. Move the applied files to corrections/applied/v<version>/ and add an entry to CHANGELOG.md.

Earlier releases are never modified. Standard library only.
"""
import argparse
import glob
import json
import os
import shutil
import sys
from collections import Counter

from fips import LOOKUP, base, is_city
from reference import sic_division, sic_major_group
from schema import (HELD_BACK_FIELDS, PUBLIC, codebook_for, num, read_csv, release_files, tally_ok, write_csv,
                    write_release_tables)
from site_data import write_site_data
import validate

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, 'docs')
SITE = os.path.join(DOCS, 'data', 'site')
PENDING = os.path.join(ROOT, 'corrections', 'pending')
CHANGE_FIELDS = ['election_id', 'field', 'old_value', 'new_value', 'source', 'source_url', 'credit', 'notes']
SIC_TITLES_PATH = os.path.join(ROOT, 'data', 'reference', 'sic_titles.csv')
CARRY_STATS = ['n_county_fixes', 'n_county_fixes_ct', 'n_county_fixes_city', 'n_county_fixes_other']


def load_sic_titles():
    return {r['sic_code']: r['sic_title'] for r in read_csv(SIC_TITLES_PATH)} if os.path.exists(SIC_TITLES_PATH) else {}


def county_code(county, state):
    exact = [f for f, (s, n) in LOOKUP.items() if s == state and n == county]
    if len(exact) == 1:
        return exact[0]
    hits = [f for f, (s, n) in LOOKUP.items() if s == state and base(n) == base(county) and is_city(n) == is_city(county)]
    return hits[0] if len(hits) == 1 else ''


def apply(records, corrections, force=False):
    """Apply corrections in place. Returns (changes, problems)."""
    by_id = {r['election_id']: r for r in records}
    sic_titles = load_sic_titles()
    changes, problems = [], []
    touched = {}
    for c in corrections:
        r = by_id[c['election_id']]
        field, new = c['field'].strip(), c['proposed_value'].strip()
        old = r[field]
        stated = c.get('current_value', '').strip()
        if stated and stated != old and not force:
            problems.append(f"{c['election_id']} {field}: the correction expects {stated!r} but the release has {old!r}")
            continue
        if new == old:
            continue
        r[field] = new
        changes.append({'election_id': r['election_id'], 'field': field, 'old_value': old, 'new_value': new,
                        'source': c['source'].strip(), 'source_url': c.get('source_url', '').strip(),
                        'credit': c.get('credit', '').strip(), 'notes': c.get('notes', '').strip()})
        touched.setdefault(r['election_id'], {})[field] = changes[-1]

    for eid, fields in touched.items():
        r = by_id[eid]
        first = next(iter(fields.values()))

        def derive(field, value, why):
            if r[field] != value:
                changes.append({'election_id': eid, 'field': field, 'old_value': r[field], 'new_value': value,
                                'source': first['source'], 'source_url': first['source_url'],
                                'credit': first['credit'], 'notes': why})
                r[field] = value

        if 'county' in fields or 'state' in fields:
            if r['county']:
                code = county_code(r['county'], r['state'])
                if not code:
                    problems.append(f"{eid}: {r['county']!r}, {r['state']!r} is not a standard county name")
                    continue
                derive('county', LOOKUP[code][1], 'standard county name')
                derive('county_fips', code, 'set from county and state')
                derive('location_status', 'Located', 'set from county')
                if 'location_source' not in fields:
                    derive('location_source', 'Contributed research', 'set with the county correction')
                if 'location_tier' not in fields:
                    derive('location_tier', '2', 'set with the county correction')
                if 'location_evidence' not in fields:
                    derive('location_evidence', first['source'], 'set with the county correction')
            else:
                for f in ['county_fips', 'location_source', 'location_tier']:
                    derive(f, '', 'county removed')
                derive('location_status', 'Decision found, location not yet extracted' if r['nlrb_citation']
                       else 'No decision found', 'county removed')
        if 'sic_code' in fields:
            code = r['sic_code']
            letter, title = sic_division(code)
            derive('sic_major_group', sic_major_group(code), 'set from SIC code')
            derive('sic_division', f'{letter} {title}'.strip(), 'set from SIC code')
            if 'sic_title' not in fields:
                if code and code not in sic_titles:
                    problems.append(f'{eid}: SIC {code} is new; add a sic_title correction for it')
                derive('sic_title', sic_titles.get(code, ''), 'set from SIC code')
            if 'industry_basis' not in fields and code:
                derive('industry_basis', 'Contributed research', 'set with the SIC correction')
        if {'votes_for', 'votes_against', 'eligible_voters', 'bargaining_unit_size'} & set(fields):
            ok, reason = tally_ok(num(r['eligible_voters']), num(r['votes_for']), num(r['votes_against']),
                                  num(r['bargaining_unit_size']))
            if not ok:
                problems.append(f'{eid}: the corrected tally fails a consistency check ({reason})')
    return changes, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', required=True)
    ap.add_argument('--date', required=True, help='YYYY-MM-DD')
    ap.add_argument('--title', required=True)
    ap.add_argument('--summary', default='')
    ap.add_argument('--status', default='Published')
    ap.add_argument('--force', action='store_true', help='apply even when current_value no longer matches')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    manifest = json.load(open(os.path.join(SITE, 'versions.json')))
    prev = manifest['current']
    v = args.version
    if [int(x) for x in v.split('.')] <= [int(x) for x in prev.split('.')]:
        sys.exit(f'Version {v} must be higher than the current release {prev}.')
    prev_dir = os.path.join(DOCS, 'data', 'releases', f'v{prev}')
    records = read_csv(os.path.join(prev_dir, f'nlrb_elections_v{prev}.csv'))

    files = sorted(glob.glob(os.path.join(PENDING, '*.csv')))
    if not files:
        sys.exit('No correction files in corrections/pending/.')
    rep = validate.Report()
    validate.check_corrections({r['election_id']: r for r in records}, rep)
    if rep.errors:
        rep.print()
        sys.exit('Fix the correction files first.')
    corrections = [c for path in files for c in read_csv(path)]

    changes, problems = apply(records, corrections, force=args.force)
    if problems:
        print('\n'.join(problems))
        sys.exit('Nothing was written.')
    n_records = len({c['election_id'] for c in changes})
    print(f'v{prev} -> v{v}: {len(changes)} values changed in {n_records} records')
    for field, n in Counter(c['field'] for c in changes).most_common():
        print(f'  {field:22s} {n}')
    if args.dry_run:
        print('Dry run: nothing written.')
        return

    rel = os.path.join(DOCS, 'data', 'releases', f'v{v}')
    if os.path.exists(rel):
        sys.exit(f'{os.path.relpath(rel, ROOT)} already exists; releases are never overwritten.')
    codebook, gaps = write_release_tables(rel, v, records)
    change_name = f'changes_v{prev}_to_v{v}.csv'
    write_csv(os.path.join(rel, change_name), changes, CHANGE_FIELDS)

    # Held-back tallies stay held back unless a correction replaced them.
    retallied = {c['election_id'] for c in changes if c['field'] in ('votes_for', 'votes_against')}
    held_path = os.path.join(prev_dir, 'review_held_back_tallies.csv')
    held = [h for h in (read_csv(held_path) if os.path.exists(held_path) else []) if h['election_id'] not in retallied]
    write_csv(os.path.join(rel, 'review_held_back_tallies.csv'), held, HELD_BACK_FIELDS)

    extra = [{'label': f'Changes since version {prev} (CSV)', 'path': f'data/releases/v{v}/{change_name}', 'kind': 'changes'},
             {'label': 'Vote tallies held back for review (CSV)', 'path': f'data/releases/v{v}/review_held_back_tallies.csv', 'kind': 'review'}]
    rel_files = release_files(v, extra)
    for f in rel_files:
        f['bytes'] = os.path.getsize(os.path.join(DOCS, f['path']))

    contributors = sorted({c['credit'] for c in changes if c['credit']})
    summary = {
        'from': prev, 'n_values': len(changes), 'n_records': n_records,
        'by_field': [{'field': f, 'n': n} for f, n in Counter(c['field'] for c in changes).most_common()],
        'contributors': contributors, 'file': f'data/releases/v{v}/{change_name}',
        'sample': [{'election_id': c['election_id'], 'field': c['field'], 'old': c['old_value'],
                    'new': c['new_value'], 'source': c['source']} for c in changes[:200]],
    }
    prev_stats = json.load(open(os.path.join(SITE, 'aggregates.json')))['stats']
    write_site_data(records, codebook, version=v, date=args.date, files=rel_files, n_held_back=len(held),
                    gap_counts={k: len(rows) for k, rows in gaps.items()}, changes=summary, title=args.title,
                    summary=args.summary or None, status=args.status,
                    extra_stats={k: prev_stats[k] for k in CARRY_STATS if k in prev_stats})

    applied = os.path.join(ROOT, 'corrections', 'applied', f'v{v}')
    os.makedirs(applied, exist_ok=True)
    for path in files:
        shutil.move(path, os.path.join(applied, os.path.basename(path)))

    log = os.path.join(ROOT, 'CHANGELOG.md')
    old = open(log, encoding='utf-8').read() if os.path.exists(log) else '# Changelog\n'
    head, _, rest = old.partition('\n')
    fields = ', '.join(f"{x['field']} {x['n']}" for x in summary['by_field'])
    entry = (f'\n## {v} ({args.date})\n\n{args.title}. {len(changes)} values changed in {n_records} records '
             f'since version {prev} ({fields}).' + (f' Contributors: {", ".join(contributors)}.' if contributors else '')
             + f' Full list: docs/{summary["file"]}.\n')
    with open(log, 'w', encoding='utf-8') as f:
        f.write(head + '\n' + entry + rest)
    print(f'Wrote {os.path.relpath(rel, ROOT)}; moved {len(files)} correction files to '
          f'{os.path.relpath(applied, ROOT)}. Run scripts/validate.py before committing.')


if __name__ == '__main__':
    main()
