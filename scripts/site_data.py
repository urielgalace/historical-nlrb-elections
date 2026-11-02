"""Compute the JSON files the website draws from, for one release.

Shared by build_release.py (v1.0) and make_release.py (later versions), so every release
regenerates the statistics, the browse table, the codebook, and the version manifest from
the release's own records.
"""
import json
import os
import re
import statistics
from collections import Counter, defaultdict

from reference import (STATES, OUTCOME_ORDER, LOCATION_STATUS_ORDER, PERIODS, SIC_MAJOR_GROUPS,
                       SIC_DIVISIONS)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, 'docs', 'data', 'site')
NLRB_DOC_PREFIX = 'https://apps.nlrb.gov/link/document.aspx/'
AFFILIATIONS = ['AFL', 'CIO', 'AFL-CIO', 'Independent']
DEFINITE = {'Union certified', 'No union', 'Petition dismissed'}
UNIT_BINS = [(1, 10, '1–9'), (10, 25, '10–24'), (25, 50, '25–49'), (50, 100, '50–99'),
             (100, 250, '100–249'), (250, 500, '250–499'), (500, 1000, '500–999'),
             (1000, 5000, '1,000–4,999'), (5000, 10 ** 9, '5,000+')]

# Development milestones before the first public release (from the project's working notes).
HISTORY = [
    {'date': '2026-10-20', 'title': 'Wrong matches corrected',
     'summary': 'All 7,224 matched elections in the 1936 to 1943 and 1947 to 1949 lists checked against the text of their decisions. 1,405 had been matched to a different company: 755 moved to the right decision and 650 left for research.'},
    {'date': '2026-07-11', 'title': 'Accuracy pass and integrity checks',
     'summary': 'Union names re-extracted with case-number checks; a blind audit of 71 records found 87% correct. 23 automated integrity checks pass on all 17 yearly files.'},
    {'date': '2026-07-07', 'title': 'Eight new variables',
     'summary': 'Added county FIPS codes, NLRB region, SIC major group and division, union name and affiliation, election type, and bargaining unit size.'},
    {'date': '2026-07', 'title': 'Index years limited to representation cases, with match categories',
     'summary': 'Unfair labor practice cases removed from the years built from the index, leaving 13,673 records. Each record re-matched in three tiers, recorded in a new match category column.'},
    {'date': '2026-06-26', 'title': 'Industry codes and vote tallies',
     'summary': 'Industry read from each decision and coded to the 1987 SIC; vote counts read from published tallies of ballots.'},
    {'date': '2026-06-22', 'title': 'Pilot years 1950, 1955, and 1960',
     'summary': 'Three later years added from the NLRB decisions index, bringing the total to 15,032 records, 90% with a county.'},
    {'date': '2026-06-18', 'title': '1944 to 1946 added',
     'summary': 'Three years without source lists built directly from the NLRB decisions index: 4,008 cases, 91% to 96% located per year.'},
    {'date': '2026-06-11', 'title': 'Location claims verified',
     'summary': '1,522 uncertain locations checked against independent sources: 505 confirmed and 299 corrected.'},
    {'date': '2026-05-29', 'title': 'First pass: county identification',
     'summary': 'Elections in the 1936 to 1943 and 1947 to 1949 source lists matched to NLRB decisions, with web research for the rest: 8,757 records, 94% with a county.'},
]
PLANNED = [
    {'version': '1.1', 'title': 'RA research on missing locations and industries',
     'summary': 'County, city, and industry for elections the automated pipeline could not place, researched by the project RAs with a source for each.',
     'status': 'In progress'},
    {'version': '2.0', 'title': 'NLRB records from FOIA request 2026-NLFO-01920',
     'summary': 'Election outcomes and vote tallies from the NLRB\'s already-scanned records of certified elections before 1961. Request received July 31, 2026; the NLRB extended processing on September 15, 2026.',
     'status': 'Waiting on the NLRB'},
]


def _pct(a, b):
    return round(100 * a / b, 1) if b else 0.0


def _in_period(year, key):
    for k, _label, lo, hi in PERIODS:
        if k == key:
            return lo is None or lo <= year <= hi
    return False


def _norm_employer(name):
    s = re.sub(r'\([^)]*\)', ' ', name.lower()).replace('&', ' and ')
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    s = re.sub(r'\b(the|inc|incorporated|co|company|corp|corporation|ltd|limited)\b', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def _compact_url(url):
    return 'nlrb:' + url[len(NLRB_DOC_PREFIX):] if url.startswith(NLRB_DOC_PREFIX) else url


def compute_aggregates(records):
    n = len(records)
    years = sorted({int(r['year']) for r in records})
    abbrev = {name: ab for name, (ab, _) in STATES.items()}

    def has(r, c):
        return bool(str(r.get(c, '')).strip())

    def definite(r):
        return r['outcome'] in DEFINITE

    by_year, aff_by_year, out_by_year = [], [], []
    for y in years:
        rs = [r for r in records if int(r['year']) == y]
        by_year.append({
            'year': y, 'n': len(rs),
            'located': sum(has(r, 'county') for r in rs),
            'tier1': sum(r['location_tier'] == '1' for r in rs),
            'matched': sum(has(r, 'nlrb_citation') for r in rs),
            'sic': sum(has(r, 'sic_code') for r in rs),
            'union_name': sum(has(r, 'union_name') for r in rs),
            'affiliation': sum(has(r, 'union_affiliation') for r in rs),
            'election_type': sum(has(r, 'election_type') for r in rs),
            'outcome_definite': sum(definite(r) for r in rs),
            'tally': sum(has(r, 'votes_for') or has(r, 'votes_against') for r in rs),
            'unit_size': sum(has(r, 'bargaining_unit_size') for r in rs),
            'region': sum(has(r, 'nlrb_region') for r in rs),
        })
        a = Counter(r['union_affiliation'] or 'Not identified' for r in rs)
        aff_by_year.append({'year': y, **{k: a.get(k, 0) for k in AFFILIATIONS + ['Not identified']}})
        o = Counter(r['outcome'] or 'No outcome information' for r in rs)
        out_by_year.append({'year': y, **{k: o.get(k, 0) for k in OUTCOME_ORDER + ['No outcome information']}})

    # Industry, counties, and states by period
    industry, counties, states = {}, {}, {}
    county_name_votes = defaultdict(Counter)
    for key, label, lo, hi in PERIODS:
        rs = [r for r in records if _in_period(int(r['year']), key)]
        div = Counter(r['sic_division'][:1] for r in rs if r['sic_code'])
        grp = Counter(r['sic_major_group'] for r in rs if r['sic_code'])
        industry[key] = {
            'label': label, 'total': len(rs),
            'classified': sum(1 for r in rs if r['sic_code']),
            'divisions': [{'letter': L, 'title': T, 'n': div.get(L, 0)} for _a, _b, L, T in SIC_DIVISIONS
                          if div.get(L, 0)],
            'groups': [{'code': g, 'label': SIC_MAJOR_GROUPS.get(g, ('', g))[1],
                        'title': SIC_MAJOR_GROUPS.get(g, (g, g))[0], 'n': c}
                       for g, c in grp.most_common()],
        }
        cc = Counter(r['county_fips'] for r in rs if r['county_fips'])
        counties[key] = {'label': label, 'total': len(rs), 'located': sum(1 for r in rs if r['county']),
                         'mapped': sum(cc.values()), 'counts': dict(cc)}
        sc = Counter(r['state'] for r in rs if r['state'])
        states[key] = [{'state': s, 'abbrev': abbrev.get(s, ''), 'n': c} for s, c in sc.most_common()]
    for r in records:
        if r['county_fips']:
            county_name_votes[r['county_fips']][f"{r['county']}, {abbrev.get(r['state'], r['state'])}"] += 1
    county_names = {f: c.most_common(1)[0][0] for f, c in county_name_votes.items()}

    # Bargaining unit sizes
    sizes = [int(r['bargaining_unit_size']) for r in records if r['bargaining_unit_size']]
    unit_bins = [{'label': lab, 'lo': lo, 'n': sum(1 for s in sizes if lo <= s < hi)} for lo, hi, lab in UNIT_BINS]

    # Top counties and employers (all years)
    allc = Counter(r['county_fips'] for r in records if r['county_fips'])
    top_counties = [{'fips': f, 'name': county_names.get(f, f), 'n': c} for f, c in allc.most_common(20)]
    emp_votes, emp_counts = defaultdict(Counter), Counter()
    for r in records:
        if r['row_type'] != 'listing' or not r['employer']:
            continue
        k = _norm_employer(r['employer'])
        if k:
            emp_counts[k] += 1
            emp_votes[k][r['employer']] += 1
    top_employers = [{'name': emp_votes[k].most_common(1)[0][0], 'n': c} for k, c in emp_counts.most_common(20)]

    # Completeness by field and year
    fields = [('located', 'County'), ('sic', 'Industry (SIC)'), ('affiliation', 'Union affiliation'),
              ('union_name', 'Union name'), ('election_type', 'Election type'),
              ('outcome_definite', 'Definite result'), ('unit_size', 'Unit size'), ('tally', 'Vote tally'),
              ('region', 'NLRB region')]
    completeness = [{'field': f, 'label': lab,
                     'by_year': {str(b['year']): _pct(b[f], b['n']) for b in by_year},
                     'all': _pct(sum(b[f] for b in by_year), n)} for f, lab in fields]

    oc = Counter(r['outcome'] for r in records)
    ls = Counter(r['location_status'] for r in records)
    rt = Counter(r['row_type'] for r in records)
    mc = Counter(r['match_category'] for r in records)
    located = sum(1 for r in records if r['county'])
    stats = {
        'n_elections': n, 'n_years': len(years), 'first_year': years[0], 'last_year': years[-1],
        'n_listings': rt['listing'], 'n_ditto': rt['ditto'], 'n_further_hearing': rt['further_hearing'],
        'n_located': located, 'pct_located': _pct(located, n),
        'n_tier1': sum(1 for r in records if r['location_tier'] == '1'),
        'n_tier2': sum(1 for r in records if r['location_tier'] == '2'),
        'n_tier3': sum(1 for r in records if r['location_tier'] == '3'),
        'n_fips': sum(1 for r in records if r['county_fips']),
        'n_matched': sum(1 for r in records if r['nlrb_citation']),
        'n_match_cat1': mc.get('1', 0), 'n_match_cat2': mc.get('2', 0), 'n_match_cat3': mc.get('3', 0),
        'n_unmatched': mc.get('', 0),
        'n_sic': sum(1 for r in records if r['sic_code']),
        'n_union_name': sum(1 for r in records if r['union_name']),
        'n_affiliation': sum(1 for r in records if r['union_affiliation']),
        'n_election_type': sum(1 for r in records if r['election_type']),
        'n_unit_size': len(sizes), 'median_unit_size': int(statistics.median(sizes)) if sizes else 0,
        'n_tally': sum(1 for r in records if r['votes_for'] or r['votes_against']),
        'n_region': sum(1 for r in records if r['nlrb_region']),
        'n_certified': oc.get('Union certified', 0), 'n_no_union': oc.get('No union', 0),
        'n_dismissed': oc.get('Petition dismissed', 0),
        'n_directed': oc.get('Election directed, result not yet found', 0),
        'n_not_found': oc.get('Not found in decision', 0), 'n_no_outcome': oc.get('', 0),
        'n_counties': len(allc), 'n_states': len({r['state'] for r in records if r['state']}),
        'n_loc_extract': ls.get('Decision found, location not yet extracted', 0),
        'n_loc_rejected': ls.get('Decision match rejected', 0),
        'n_loc_nodecision': ls.get('No decision found', 0),
    }
    stats['n_definite'] = stats['n_certified'] + stats['n_no_union'] + stats['n_dismissed']
    stats['n_no_county'] = n - located
    stats['n_no_sic'] = n - stats['n_sic']
    by_id = {r['election_id']: r for r in records}
    other = [r for r in records if r['row_type'] != 'listing']
    stats['n_other_rows'] = len(other)
    stats['n_other_no_county'] = sum(1 for r in other if not r['county'])
    stats['n_other_parent_county'] = sum(1 for r in other if not r['county']
                                         and by_id.get(r['refers_to'], {}).get('county'))
    stats['n_other_no_sic'] = sum(1 for r in other if not r['sic_code'])
    for k in ['tier1', 'fips', 'sic', 'union_name', 'affiliation', 'election_type', 'unit_size', 'tally',
              'region', 'definite', 'directed', 'certified', 'matched', 'match_cat1']:
        stats[f'pct_{k}'] = _pct(stats[f'n_{k}'], n)
    stats['pct_tier1_of_located'] = _pct(stats['n_tier1'], located)

    return {
        'stats': stats, 'periods': [{'key': k, 'label': lab} for k, lab, _lo, _hi in PERIODS],
        'years': years, 'by_year': by_year, 'affiliation_by_year': aff_by_year,
        'affiliations': AFFILIATIONS + ['Not identified'],
        'outcome_by_year': out_by_year, 'outcomes': OUTCOME_ORDER + ['No outcome information'],
        'industry': industry, 'counties': counties, 'county_names': county_names, 'states': states,
        'unit_bins': unit_bins, 'top_counties': top_counties, 'top_employers': top_employers,
        'completeness': completeness,
    }


def compute_browse(records):
    """Compact rows for the searchable table on the Data page."""
    abbrev = {name: ab for name, (ab, _) in STATES.items()}
    cols = ['id', 'year', 'employer', 'county', 'state', 'fips', 'sic', 'sic_title', 'division',
            'union', 'affiliation', 'election_type', 'unit', 'outcome', 'votes_for', 'votes_against',
            'case', 'citation', 'decided', 'tier', 'status', 'url', 'row_type']
    rows = []
    for r in records:
        rows.append([
            r['election_id'], int(r['year']), r['employer'], r['county'], abbrev.get(r['state'], ''),
            r['county_fips'], r['sic_code'], r['sic_title'], r['sic_division'][:1], r['union_name'],
            r['union_affiliation'], r['election_type'], r['bargaining_unit_size'],
            OUTCOME_ORDER.index(r['outcome']) if r['outcome'] in OUTCOME_ORDER else -1,
            r['votes_for'], r['votes_against'], r['nlrb_case_number'], r['nlrb_citation'],
            r['nlrb_decision_date'], r['location_tier'],
            LOCATION_STATUS_ORDER.index(r['location_status']), _compact_url(r['source_url']),
            r['row_type'],
        ])
    return {'columns': cols, 'outcomes': OUTCOME_ORDER, 'statuses': LOCATION_STATUS_ORDER,
            'url_prefixes': {'nlrb': NLRB_DOC_PREFIX}, 'rows': rows}


def write_site_data(records, codebook, version, date, files, n_held_back, gap_counts, changes=None,
                    title='First public release', summary=None, status='Release candidate',
                    extra_stats=None, notes=None):
    os.makedirs(SITE, exist_ok=True)
    agg = compute_aggregates(records)
    agg['release'] = {'version': version, 'date': date}
    agg['stats']['n_tally_held_back'] = n_held_back
    agg['stats']['n_tally_found'] = agg['stats']['n_tally'] + n_held_back
    agg['stats'].update(extra_stats or {})
    agg['gap_counts'] = gap_counts
    with open(os.path.join(SITE, 'aggregates.json'), 'w') as f:
        json.dump(agg, f, separators=(',', ':'))
    with open(os.path.join(SITE, 'browse.json'), 'w') as f:
        json.dump(compute_browse(records), f, separators=(',', ':'), ensure_ascii=False)
    with open(os.path.join(SITE, 'codebook.json'), 'w') as f:
        json.dump(codebook, f, indent=1, ensure_ascii=False)

    vpath = os.path.join(SITE, 'versions.json')
    manifest = json.load(open(vpath)) if os.path.exists(vpath) else {'releases': [], 'history': HISTORY,
                                                                      'planned': PLANNED}
    s = agg['stats']
    entry = {
        'version': version, 'date': date, 'status': status, 'title': title,
        'summary': summary or (f"{s['n_elections']:,} election records from {s['n_years']} years "
                               f"({s['first_year']} to {s['last_year']}), {s['pct_located']}% with a county."),
        'files': files,
        'coverage': {'Elections': s['n_elections'], 'With a county': s['n_located'],
                     'With an industry code': s['n_sic'], 'With a definite result': s['n_definite'],
                     'With a union name': s['n_union_name'], 'With a vote tally': s['n_tally']},
        'changes': changes,
        'notes': notes or [],
    }
    manifest['releases'] = [r for r in manifest['releases'] if r['version'] != version] + [entry]
    manifest['releases'].sort(key=lambda r: [int(p) for p in r['version'].split('.')], reverse=True)
    manifest['current'] = manifest['releases'][0]['version']
    manifest['planned'] = [p for p in manifest.get('planned', [])
                           if [int(x) for x in p['version'].split('.')] > [int(x) for x in version.split('.')]]
    with open(vpath, 'w') as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False)
    return agg
