"""Reference tables shared by the release scripts.

Everything here is a fixed lookup: state names and FIPS codes, the 1987 Standard
Industrial Classification (SIC) major groups and divisions, and the mapping from the
research pipeline's internal labels to the plain categories used in the public file.
"""

# Full state name -> (USPS abbreviation, 2-digit state FIPS)
STATES = {
    'Alabama': ('AL', '01'), 'Alaska': ('AK', '02'), 'Arizona': ('AZ', '04'), 'Arkansas': ('AR', '05'),
    'California': ('CA', '06'), 'Colorado': ('CO', '08'), 'Connecticut': ('CT', '09'), 'Delaware': ('DE', '10'),
    'District of Columbia': ('DC', '11'), 'Florida': ('FL', '12'), 'Georgia': ('GA', '13'), 'Hawaii': ('HI', '15'),
    'Idaho': ('ID', '16'), 'Illinois': ('IL', '17'), 'Indiana': ('IN', '18'), 'Iowa': ('IA', '19'),
    'Kansas': ('KS', '20'), 'Kentucky': ('KY', '21'), 'Louisiana': ('LA', '22'), 'Maine': ('ME', '23'),
    'Maryland': ('MD', '24'), 'Massachusetts': ('MA', '25'), 'Michigan': ('MI', '26'), 'Minnesota': ('MN', '27'),
    'Mississippi': ('MS', '28'), 'Missouri': ('MO', '29'), 'Montana': ('MT', '30'), 'Nebraska': ('NE', '31'),
    'Nevada': ('NV', '32'), 'New Hampshire': ('NH', '33'), 'New Jersey': ('NJ', '34'), 'New Mexico': ('NM', '35'),
    'New York': ('NY', '36'), 'North Carolina': ('NC', '37'), 'North Dakota': ('ND', '38'), 'Ohio': ('OH', '39'),
    'Oklahoma': ('OK', '40'), 'Oregon': ('OR', '41'), 'Pennsylvania': ('PA', '42'), 'Rhode Island': ('RI', '44'),
    'South Carolina': ('SC', '45'), 'South Dakota': ('SD', '46'), 'Tennessee': ('TN', '47'), 'Texas': ('TX', '48'),
    'Utah': ('UT', '49'), 'Vermont': ('VT', '50'), 'Virginia': ('VA', '51'), 'Washington': ('WA', '53'),
    'West Virginia': ('WV', '54'), 'Wisconsin': ('WI', '55'), 'Wyoming': ('WY', '56'), 'Puerto Rico': ('PR', '72'),
}
ABBREV_TO_STATE = {ab: name for name, (ab, _) in STATES.items()}
FIPS_TO_STATE = {fips: name for name, (_, fips) in STATES.items()}


def normalize_state(value):
    """Return the full state name for a full name or a 2-letter abbreviation, else ''."""
    v = (value or '').strip()
    if v in STATES:
        return v
    return ABBREV_TO_STATE.get(v.upper(), '')


# 1987 SIC major groups: code -> (official title, short label used in charts)
SIC_MAJOR_GROUPS = {
    '01': ('Agricultural Production - Crops', 'Crop farming'),
    '02': ('Agricultural Production - Livestock and Animal Specialties', 'Livestock'),
    '07': ('Agricultural Services', 'Agricultural services'),
    '08': ('Forestry', 'Forestry'),
    '09': ('Fishing, Hunting, and Trapping', 'Fishing'),
    '10': ('Metal Mining', 'Metal mining'),
    '12': ('Coal Mining', 'Coal mining'),
    '13': ('Oil and Gas Extraction', 'Oil and gas extraction'),
    '14': ('Mining and Quarrying of Nonmetallic Minerals, Except Fuels', 'Nonmetallic mining'),
    '15': ('Building Construction - General Contractors and Operative Builders', 'Building construction'),
    '16': ('Heavy Construction Other Than Building Construction - Contractors', 'Heavy construction'),
    '17': ('Construction - Special Trade Contractors', 'Special trade contractors'),
    '20': ('Food and Kindred Products', 'Food products'),
    '21': ('Tobacco Products', 'Tobacco products'),
    '22': ('Textile Mill Products', 'Textile mills'),
    '23': ('Apparel and Other Finished Products Made from Fabrics and Similar Materials', 'Apparel'),
    '24': ('Lumber and Wood Products, Except Furniture', 'Lumber and wood'),
    '25': ('Furniture and Fixtures', 'Furniture'),
    '26': ('Paper and Allied Products', 'Paper'),
    '27': ('Printing, Publishing, and Allied Industries', 'Printing and publishing'),
    '28': ('Chemicals and Allied Products', 'Chemicals'),
    '29': ('Petroleum Refining and Related Industries', 'Petroleum refining'),
    '30': ('Rubber and Miscellaneous Plastics Products', 'Rubber and plastics'),
    '31': ('Leather and Leather Products', 'Leather'),
    '32': ('Stone, Clay, Glass, and Concrete Products', 'Stone, clay, and glass'),
    '33': ('Primary Metal Industries', 'Primary metals'),
    '34': ('Fabricated Metal Products, Except Machinery and Transportation Equipment', 'Fabricated metals'),
    '35': ('Industrial and Commercial Machinery and Computer Equipment', 'Industrial machinery'),
    '36': ('Electronic and Other Electrical Equipment and Components, Except Computer Equipment', 'Electrical equipment'),
    '37': ('Transportation Equipment', 'Transportation equipment'),
    '38': ('Measuring, Analyzing, and Controlling Instruments; Photographic, Medical and Optical Goods; Watches and Clocks', 'Instruments'),
    '39': ('Miscellaneous Manufacturing Industries', 'Other manufacturing'),
    '40': ('Railroad Transportation', 'Railroads'),
    '41': ('Local and Suburban Transit and Interurban Highway Passenger Transportation', 'Local transit'),
    '42': ('Motor Freight Transportation and Warehousing', 'Trucking and warehousing'),
    '43': ('United States Postal Service', 'Postal service'),
    '44': ('Water Transportation', 'Water transportation'),
    '45': ('Transportation by Air', 'Air transportation'),
    '46': ('Pipelines, Except Natural Gas', 'Pipelines'),
    '47': ('Transportation Services', 'Transportation services'),
    '48': ('Communications', 'Communications'),
    '49': ('Electric, Gas, and Sanitary Services', 'Utilities'),
    '50': ('Wholesale Trade - Durable Goods', 'Wholesale, durable goods'),
    '51': ('Wholesale Trade - Nondurable Goods', 'Wholesale, nondurable goods'),
    '52': ('Building Materials, Hardware, Garden Supply, and Mobile Home Dealers', 'Building materials stores'),
    '53': ('General Merchandise Stores', 'General merchandise stores'),
    '54': ('Food Stores', 'Food stores'),
    '55': ('Automotive Dealers and Gasoline Service Stations', 'Auto dealers and gas stations'),
    '56': ('Apparel and Accessory Stores', 'Apparel stores'),
    '57': ('Home Furniture, Furnishings, and Equipment Stores', 'Furniture stores'),
    '58': ('Eating and Drinking Places', 'Eating and drinking places'),
    '59': ('Miscellaneous Retail', 'Other retail'),
    '60': ('Depository Institutions', 'Banks'),
    '61': ('Nondepository Credit Institutions', 'Credit institutions'),
    '62': ('Security and Commodity Brokers, Dealers, Exchanges, and Services', 'Securities brokers'),
    '63': ('Insurance Carriers', 'Insurance carriers'),
    '64': ('Insurance Agents, Brokers, and Service', 'Insurance agents'),
    '65': ('Real Estate', 'Real estate'),
    '67': ('Holding and Other Investment Offices', 'Holding companies'),
    '70': ('Hotels, Rooming Houses, Camps, and Other Lodging Places', 'Hotels and lodging'),
    '72': ('Personal Services', 'Personal services'),
    '73': ('Business Services', 'Business services'),
    '75': ('Automotive Repair, Services, and Parking', 'Auto repair and parking'),
    '76': ('Miscellaneous Repair Services', 'Repair services'),
    '78': ('Motion Pictures', 'Motion pictures'),
    '79': ('Amusement and Recreation Services', 'Amusement and recreation'),
    '80': ('Health Services', 'Health services'),
    '81': ('Legal Services', 'Legal services'),
    '82': ('Educational Services', 'Educational services'),
    '83': ('Social Services', 'Social services'),
    '84': ('Museums, Art Galleries, and Botanical and Zoological Gardens', 'Museums'),
    '86': ('Membership Organizations', 'Membership organizations'),
    '87': ('Engineering, Accounting, Research, Management, and Related Services', 'Professional services'),
    '88': ('Private Households', 'Private households'),
    '89': ('Miscellaneous Services', 'Other services'),
    '91': ('Executive, Legislative, and General Government, Except Finance', 'General government'),
    '92': ('Justice, Public Order, and Safety', 'Justice and public safety'),
    '93': ('Public Finance, Taxation, and Monetary Policy', 'Public finance'),
    '94': ('Administration of Human Resource Programs', 'Human resource programs'),
    '95': ('Administration of Environmental Quality and Housing Programs', 'Environment and housing programs'),
    '96': ('Administration of Economic Programs', 'Economic programs'),
    '97': ('National Security and International Affairs', 'National security'),
    '99': ('Nonclassifiable Establishments', 'Nonclassifiable'),
}

# 1987 SIC divisions: (first major group, last major group, letter, title)
SIC_DIVISIONS = [
    (1, 9, 'A', 'Agriculture, Forestry, and Fishing'),
    (10, 14, 'B', 'Mining'),
    (15, 17, 'C', 'Construction'),
    (20, 39, 'D', 'Manufacturing'),
    (40, 49, 'E', 'Transportation and Public Utilities'),
    (50, 51, 'F', 'Wholesale Trade'),
    (52, 59, 'G', 'Retail Trade'),
    (60, 67, 'H', 'Finance, Insurance, and Real Estate'),
    (70, 89, 'I', 'Services'),
    (91, 99, 'J', 'Public Administration'),
]


def sic_major_group(code):
    code = (code or '').strip()
    return code[:2] if len(code) >= 2 and code[:2].isdigit() else ''


def sic_division(code):
    """Return (letter, title) of the SIC division for a SIC code, or ('', '')."""
    group = sic_major_group(code)
    if not group:
        return '', ''
    n = int(group)
    for lo, hi, letter, title in SIC_DIVISIONS:
        if lo <= n <= hi:
            return letter, title
    return '', ''


# Pipeline "Outcome" label -> public outcome category
OUTCOME_MAP = {
    'Union certified': 'Union certified',
    'No union (neither/union not selected)': 'No union',
    'Petition dismissed (no election held)': 'Petition dismissed',
    'Election directed - result in separate certification document': 'Election directed, result not yet found',
    'Result not found in this document': 'Not found in decision',
}
OUTCOME_ORDER = ['Union certified', 'No union', 'Petition dismissed',
                 'Election directed, result not yet found', 'Not found in decision']

# Pipeline "Source Type" (for rows that HAVE a county) -> public location source
LOCATION_SOURCE_MAP = {
    'NLRB Board Decision PDF': 'NLRB decision',
    'Phase 1 web research': 'Web research',
    'Web-verified (Tier-3 claim confirmed by independent source)': 'Web research, verified',
    'Web-verified (Tier-3 claim CORRECTED)': 'Web research, corrected',
    'NLRB name-match (date-inconsistent — UNVERIFIED)': 'NLRB decision, unverified match',
    'Name-based inference': 'Inferred from employer name',
    'NLRB match + name inference (PDF pending)': 'Inferred from employer name',
}

# Pipeline "Source Type" (for rows WITHOUT a county) -> why the location is missing
LOCATION_GAP_MAP = {
    'NLRB PDF retrieved, location not parsed': 'Decision found, location not yet extracted',
    'NLRB index match (PDF pending)': 'Decision found, location not yet extracted',
    'NLRB index match (PDF download failed — retry)': 'Decision found, location not yet extracted',
    'NLRB match rejected (company name absent from linked decision)': 'Decision match rejected',
}
LOCATION_STATUS_ORDER = ['Located', 'Decision found, location not yet extracted',
                         'Decision match rejected', 'No decision found']

PERIODS = [
    ('all', 'All years', None, None),
    ('1936-1940', '1936 to 1940', 1936, 1940),
    ('1941-1945', '1941 to 1945', 1941, 1945),
    ('1946-1950', '1946 to 1950', 1946, 1950),
    ('1955', '1955', 1955, 1955),
    ('1960', '1960', 1960, 1960),
]
