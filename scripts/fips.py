"""County names and FIPS codes for the public release.

The research workbooks assigned counties through a GeoNames place lookup. Two problems surfaced
when the release was prepared, and this module fixes both:

1. GeoNames now files Connecticut places under the state's 2022 planning regions (FIPS 09110 to
   09190), which did not exist before 2022. Those records are moved back to the historical
   county of the town named in the location evidence.
2. Independent cities and same-name counties were sometimes confused (for example the City of
   Richmond, 51760, coded as Richmond County, 51159). Each record's county name is checked
   against its code, and the code is corrected when the name clearly points to the other unit.

The county name in the release is then the standard name for the code, so one county is always
spelled one way. Standard names come from data/reference/county_fips_lookup.csv.
"""
import csv
import os
import re
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOOKUP_PATH = os.path.join(ROOT, 'data', 'reference', 'county_fips_lookup.csv')

with open(LOOKUP_PATH, encoding='utf-8') as _f:
    LOOKUP = {r['county_fips']: (r['state'], r['county']) for r in csv.DictReader(_f)}

# Connecticut towns, and villages named in decisions, by historical county (FIPS county code).
CT_PLACES = {
    '001': 'Bethel|Bridgeport|Brookfield|Danbury|Darien|Easton|Fairfield|Greenwich|Monroe|New Canaan|'
           'New Fairfield|Newtown|Norwalk|Redding|Ridgefield|Shelton|Sherman|Stamford|Stratford|Trumbull|'
           'Weston|Westport|Wilton|South Norwalk|East Norwalk|Southport|Cos Cob|Byram|Riverside|'
           'Old Greenwich|Georgetown|Sandy Hook|Glenbrook|Springdale|Huntington|Botsford|Black Rock',
    '003': 'Avon|Berlin|Bloomfield|Bristol|Burlington|Canton|East Granby|East Hartford|East Windsor|Enfield|'
           'Farmington|Glastonbury|Granby|Hartford|Hartland|Manchester|Marlborough|New Britain|Newington|'
           'Plainville|Rocky Hill|Simsbury|Southington|South Windsor|Suffield|West Hartford|Wethersfield|'
           'Windsor|Windsor Locks|Collinsville|Unionville|Thompsonville|Hazardville|Plantsville|Milldale|'
           'Forestville|Kensington|East Berlin|Poquonock|Broad Brook|Warehouse Point|Tariffville|Elmwood|'
           'Hockanum|South Manchester',
    '005': 'Barkhamsted|Bethlehem|Bridgewater|Canaan|Colebrook|Cornwall|Goshen|Harwinton|Kent|Litchfield|'
           'Morris|New Hartford|New Milford|Norfolk|North Canaan|Plymouth|Roxbury|Salisbury|Sharon|'
           'Thomaston|Torrington|Warren|Washington|Watertown|Winchester|Woodbury|Winsted|Terryville|'
           'Oakville|Bantam|Falls Village|Lakeville|Pine Meadow|Riverton|Gaylordsville',
    '007': 'Chester|Clinton|Cromwell|Deep River|Durham|East Haddam|East Hampton|Essex|Haddam|Killingworth|'
           'Middlefield|Middletown|Old Saybrook|Portland|Westbrook|Ivoryton|Centerbrook|Moodus|Higganum|'
           'Rockfall',
    '009': 'Ansonia|Beacon Falls|Bethany|Branford|Cheshire|Derby|East Haven|Guilford|Hamden|Madison|Meriden|'
           'Middlebury|Milford|Naugatuck|New Haven|North Branford|North Haven|Orange|Oxford|Prospect|'
           'Seymour|Southbury|Wallingford|Waterbury|West Haven|Wolcott|Woodbridge|Yalesville|Whitneyville|'
           'Mount Carmel|Stony Creek|Devon|Union City|Fair Haven|Westville|Waterville',
    '011': 'Bozrah|Colchester|East Lyme|Franklin|Griswold|Groton|Lebanon|Ledyard|Lisbon|Lyme|Montville|'
           'New London|North Stonington|Norwich|Old Lyme|Preston|Salem|Sprague|Stonington|Voluntown|'
           'Waterford|Jewett City|Taftville|Mystic|Baltic|Uncasville|Noank|Niantic|Versailles|Occum|'
           'Pawcatuck|Greeneville|Yantic|Hanover|Montville Center',
    '013': 'Andover|Bolton|Columbia|Coventry|Ellington|Hebron|Mansfield|Somers|Stafford|Tolland|Union|'
           'Vernon|Willington|Rockville|Stafford Springs|Talcottville|Somersville|South Coventry|Storrs|'
           'Mansfield Center|Staffordville|Hydeville',
    '015': 'Ashford|Brooklyn|Canterbury|Chaplin|Eastford|Hampton|Killingly|Plainfield|Pomfret|Putnam|'
           'Scotland|Sterling|Thompson|Windham|Woodstock|Willimantic|Danielson|Moosup|Wauregan|'
           'Grosvenordale|North Grosvenordale|Dayville|Rogers|Central Village|Quinebaug|Attawaugan|'
           'Ballouville|Williamsville|Goodyear|Plainfield Village',
}
_CT_TOWN = {}
for _code, _names in CT_PLACES.items():
    for _n in _names.split('|'):
        _CT_TOWN[_n.strip().lower()] = '09' + _code
# Historical counties that each 2022 planning region overlaps; the first is the main one.
CT_REGION_COUNTIES = {
    '09110': ['09003', '09013'], '09120': ['09001'], '09130': ['09007', '09011'],
    '09140': ['09009', '09003', '09005', '09001'], '09150': ['09015', '09013'], '09160': ['09005', '09003'],
    '09170': ['09009'], '09180': ['09011', '09015', '09013'], '09190': ['09001'],
}
CT_PLANNING_REGIONS = set(CT_REGION_COUNTIES)


def _fold(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'\s+', ' ', s).strip()


def is_city(name):
    n = _fold(name).lower()
    return bool(re.search(r'^city of\b|\bcity$|\(city\)|\bindependent city\b', n))


def base(name):
    """Name without the unit word, for comparing a county name to its code."""
    n = _fold(name).lower()
    n = re.sub(r'\(.*?\)', ' ', n)
    n = re.sub(r'^city and county of |^city of |^town of ', '', n)
    n = re.sub(r'\b(county|parish|borough|census area|municipality|municipio|city and borough|city)\b', ' ', n)
    n = n.replace('saint ', 'st ').replace('sainte ', 'ste ').replace('.', ' ').replace("'", '')
    return re.sub(r'\s+', ' ', n).strip()


def ct_county_from_text(text, region=''):
    """Historical Connecticut county of the town named in a passage, or ''."""
    if not text:
        return ''
    found = []
    for m in re.finditer(r'([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,2}),?\s+(?:Connecticut|Conn\b)', text):
        words = m.group(1).split()
        for k in range(len(words)):                    # longest place name ending at the state
            cand = ' '.join(words[k:]).lower().rstrip('.')
            if cand in _CT_TOWN:
                found.append(_CT_TOWN[cand])
                break
    inside = [f for f in found if f in CT_REGION_COUNTIES.get(region, [])]
    if inside or found:
        return (inside or found)[0]
    # No "Town, Connecticut" phrase: accept a town named anywhere in the passage, if it lies in
    # one of the region's counties (for example "THE HARTFORD TIMES").
    low = text.lower()
    named = sorted((n for n, f in _CT_TOWN.items()
                    if f in CT_REGION_COUNTIES.get(region, []) and re.search(rf'\b{re.escape(n)}\b', low)),
                   key=len, reverse=True)
    return _CT_TOWN[named[0]] if named else ''


def standard_county(county, state, fips, evidence=''):
    """Return (county_name, county_fips, note) for one record.

    note is '' when nothing changed, otherwise a short description for the build log."""
    if not county:
        return county, fips, ''
    if not fips:
        # A county with no code: find the code from the name, or clear a name that is not one county.
        name = re.sub(rf',\s*{re.escape(state)}$', '', county)
        hits = [f for f, (s, n) in LOOKUP.items() if s == state and base(n) == base(name)]
        if len(hits) == 1:
            return LOOKUP[hits[0]][1], hits[0], f'"{county}" had no code -> {hits[0]}'
        return '', '', f'"{county}" is not a single county; location cleared for research'
    if fips in CT_PLANNING_REGIONS:
        new = ct_county_from_text(evidence, fips)
        if not new and len(CT_REGION_COUNTIES[fips]) == 1:
            new = CT_REGION_COUNTIES[fips][0]
        if not new:
            return county, fips, f'unresolved Connecticut planning region {fips}'
        return LOOKUP[new][1], new, f'Connecticut planning region {fips} -> {new}'
    if fips not in LOOKUP:
        return county, fips, f'code {fips} not in lookup'
    std_name = LOOKUP[fips][1]
    if base(county) == base(std_name) and is_city(county) == is_city(std_name):
        return std_name, fips, ''
    typed = is_city(county) or re.search(r'\b(county|parish|borough|census area|municipality|municipio)\b',
                                         county.lower())
    if base(county) == base(std_name) and not typed:
        return std_name, fips, ''          # a bare name ("Baltimore") keeps its code
    # Look for another unit in the same state whose standard name fits the recorded name
    # (an independent city coded as the same-name county, or the reverse).
    want_city, want_base = is_city(county), base(county)
    alts = [f for f, (_s, n) in LOOKUP.items()
            if f[:2] == fips[:2] and f != fips and base(n) == want_base and is_city(n) == want_city]
    if len(alts) == 1:
        return LOOKUP[alts[0]][1], alts[0], f'"{county}" was coded {fips} ({std_name}) -> {alts[0]}'
    if base(county) == base(std_name):
        return std_name, fips, ''          # same unit written differently (San Francisco)
    return county, fips, f'name "{county}" does not match code {fips} ({std_name})'
