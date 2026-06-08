# Read raw hospital CSV     → messy, complex, many columns
#Filter to CPT codes only  → ignore APC, CDM-only rows
#Extract clean rates       → dollar amounts only for now
#Output a simple CSV       → one row per procedure per insurer matching our procedures.csv structure
import csv
import os

# ─────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────

# The CPT codes we care about from our 
# procedures.csv seed file
TARGET_CPT_CODES = {
    '73721',  # Knee MRI
    '45378',  # Colonoscopy
    '80061',  # Lipid Panel
}

# The columns we want from the raw file
# These match the CMS v3.0.0 schema we inspected
GROSS_CHARGE_COL        = 'standard_charge|gross'
CASH_COL                = 'standard_charge|discounted_cash'
PAYER_COL               = 'payer_name'
PLAN_COL                = 'plan_name'
NEGOTIATED_DOLLAR_COL   = 'standard_charge|negotiated_dollar'
METHODOLOGY_COL         = 'standard_charge|methodology'
MIN_COL                 = 'standard_charge|min'
MAX_COL                 = 'standard_charge|max'
BILLING_CLASS_COL       = 'billing_class'
SETTING_COL             = 'setting'
MODIFIER_COL            = 'modifiers'

# Code columns to search for CPT matches
CODE_COLS      = ['code|1', 'code|2', 'code|3', 'code|4']
CODE_TYPE_COLS = ['code|1|type', 'code|2|type', 
                  'code|3|type', 'code|4|type']

# ─────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────

def find_cpt_code(row):
    """Search all four code columns for a 
    HCPCS/CPT code that matches our target list.
    Returns the CPT code if found, None if not."""
    
    for i in range(4):
        code      = row.get(CODE_COLS[i], '').strip()
        code_type = row.get(CODE_TYPE_COLS[i], '').strip()
        
        # HCPCS type includes all CPT codes
        if code_type.upper() == 'HCPCS' and \
           code in TARGET_CPT_CODES:
            return code
    
    return None

def is_dollar_rate(row):
    """Check if this row has a clean dollar 
    negotiated rate we can use directly.
    Also skips rows with zero procedure count."""
    
    # Skip rows where procedure was never 
    # actually performed at this facility
    count = row.get('count', '').strip()
    if count == '0':
        return False
    
    rate = row.get(NEGOTIATED_DOLLAR_COL, '').strip()
    
    if rate == '' or rate is None:
        return False
    
    try:
        float(rate)
        return True
    except ValueError:
        return False

def is_chargemaster_row(row):
    """Check if this is a chargemaster-only row
    with no payer information."""
    
    payer = row.get(PAYER_COL, '').strip()
    return payer == ''

def clean_rate(value):
    """Convert a rate string to a float.
    Returns None if conversion fails."""
    
    if value is None or value.strip() == '':
        return None
    try:
        return round(float(value.strip()), 2)
    except ValueError:
        return None

def get_hospital_name(filepath):
    """Extract hospital name from the first 
    row of the CMS file."""
    
    with open(filepath, 'r', 
              encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        first_row = next(reader)
        return first_row.get(
            'hospital_name', 
            os.path.basename(filepath)
        )

# ─────────────────────────────────────────
# MAIN PARSER FUNCTION
# ─────────────────────────────────────────

def parse_mrf_file(filepath):
    """Parse one CMS MRF CSV file and extract
    all rates for our target CPT codes.
    
    Returns a list of dictionaries, one per
    rate row that matches our criteria."""
    
    results = []
    
    # Track counts for summary reporting
    total_rows        = 0
    cpt_matches       = 0
    chargemaster_rows = 0
    dollar_rate_rows  = 0
    skipped_rows      = 0
    
    print(f"\nParsing: {os.path.basename(filepath)}")
    print("-" * 50)
    
    # Get hospital name from file header
    hospital_name = get_hospital_name(filepath)
    print(f"Hospital: {hospital_name}")
    
    # Open and read the file
    # Skip the first two rows (hospital metadata
    # and attestation) to get to the data
    with open(filepath, 'r', 
              encoding='utf-8-sig') as f:
        
        # Read all lines first so we can skip
        # the metadata rows at the top
        lines = f.readlines()
    
    # The actual column headers are on row 3
    # (index 2) in CMS v3.0.0 format
    # Row 1 = hospital metadata
    # Row 2 = attestation values  
    # Row 3 = column headers
    # Row 4+ = data rows
    
    # Rejoin as a single string starting 
    # from the header row
    data_section = ''.join(lines[2:])
    
    reader = csv.DictReader(
        data_section.splitlines()
    )
    
    for row in reader:
        total_rows += 1
        
        # Step 1: Does this row contain one 
        # of our target CPT codes?
        cpt_code = find_cpt_code(row)
        if cpt_code is None:
            continue
        
        cpt_matches += 1
        
        # Step 2: Is this a chargemaster row?
        # Capture gross and cash rates from it
        if is_chargemaster_row(row):
            chargemaster_rows += 1
            
            gross = clean_rate(
                row.get(GROSS_CHARGE_COL, '')
            )
            cash  = clean_rate(
                row.get(CASH_COL, '')
            )
            
            # Only save if we have at least 
            # a gross charge
            if gross is not None:
                results.append({
                    'hospital':          hospital_name,
                    'cpt_code':          cpt_code,
                    'description':       row.get(
                                           'description',
                                           '').strip(),
                    'billing_class':     row.get(
                                           BILLING_CLASS_COL,
                                           '').strip(),
                    'setting':           row.get(
                                           SETTING_COL,
                                           '').strip(),
                    'modifier':          row.get(
                                           MODIFIER_COL,
                                           '').strip(),
                    'payer':             'chargemaster',
                    'plan':              '',
                    'rate_type':         'chargemaster',
                    'negotiated_rate':   gross,
                    'cash_pay_rate':     cash,
                    'min_rate':          None,
                    'max_rate':          None,
                    'methodology':       'chargemaster',
                })
            continue
        
        # Step 3: Payer-specific row
        # Only keep clean dollar amount rates
        if is_dollar_rate(row):
            dollar_rate_rows += 1
            
            results.append({
                'hospital':        hospital_name,
                'cpt_code':        cpt_code,
                'description':     row.get(
                                     'description',
                                     '').strip(),
                'billing_class':   row.get(
                                     BILLING_CLASS_COL,
                                     '').strip(),
                'setting':         row.get(
                                     SETTING_COL,
                                     '').strip(),
                'modifier':        row.get(
                                     MODIFIER_COL,
                                     '').strip(),
                'payer':           row.get(
                                     PAYER_COL,
                                     '').strip(),
                'plan':            row.get(
                                     PLAN_COL,
                                     '').strip(),
                'rate_type':       'negotiated',
                'negotiated_rate': clean_rate(
                                     row.get(
                                       NEGOTIATED_DOLLAR_COL,
                                       '')),
                'cash_pay_rate':   clean_rate(
                                     row.get(CASH_COL, '')),
                'min_rate':        clean_rate(
                                     row.get(MIN_COL, '')),
                'max_rate':        clean_rate(
                                     row.get(MAX_COL, '')),
                'methodology':     row.get(
                                     METHODOLOGY_COL,
                                     '').strip(),
                                     'median_rate':     clean_rate(
                                     row.get(
                                       'median_amount',
                                       '')),
                'count':           row.get(
                                     'count',
                                     '').strip(),
            })
        else:
            skipped_rows += 1
    
    # Print summary
    print(f"Total rows scanned:      {total_rows:,}")
    print(f"CPT code matches:        {cpt_matches:,}")
    print(f"Chargemaster rows:       {chargemaster_rows:,}")
    print(f"Dollar rate rows:        {dollar_rate_rows:,}")
    print(f"Skipped (no dollar):     {skipped_rows:,}")
    print(f"Results extracted:       {len(results):,}")
    
    return results

# ─────────────────────────────────────────
# OUTPUT FUNCTION
# ─────────────────────────────────────────

def save_results(results, output_path):
    """Save extracted rates to a clean CSV
    that calculate.py can use directly."""
    
    if not results:
        print("No results to save.")
        return
    
    fieldnames = [
        'hospital', 'cpt_code', 'description',
        'billing_class', 'setting', 'modifier',
        'payer', 'plan', 'rate_type',
        'negotiated_rate', 'cash_pay_rate',
        'min_rate', 'max_rate', 'median_rate', 'count','methodology'
    ]
    
    with open(output_path, 'w', 
              newline='', 
              encoding='utf-8') as f:
        writer = csv.DictWriter(
            f, fieldnames=fieldnames
        )
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\nSaved {len(results):,} rows to:")
    print(f"  {output_path}")

# ─────────────────────────────────────────
# POST-PROCESSING
# ─────────────────────────────────────────

def post_process(results):
    """Clean up extracted results:
    1. Deduplicate chargemaster rows
    2. Join cash rates to negotiated rows
    3. Add Medicare index where possible
    """
    
    # Step 1: Build cash rate lookup from
    # chargemaster rows — one per hospital
    # and CPT code, keeping first occurrence
    cash_lookup = {}
    chargemaster_seen = set()
    clean_results = []

    for row in results:
        if row['rate_type'] == 'chargemaster':
            key = (row['hospital'], 
                   row['cpt_code'],
                   row['modifier'])
            
            # Store cash rate for later joining
            if row['cash_pay_rate']:
                cash_key = (row['hospital'],
                            row['cpt_code'])
                if cash_key not in cash_lookup:
                    cash_lookup[cash_key] = \
                        row['cash_pay_rate']
            
            # Keep only first chargemaster row
            # per hospital/CPT/modifier combo
            if key not in chargemaster_seen:
                chargemaster_seen.add(key)
                clean_results.append(row)
        else:
            clean_results.append(row)

    # Step 2: Join cash rates to negotiated rows
    # If no cash rate published, use min_rate
    # as proxy and flag it
    for row in clean_results:
        if row['rate_type'] == 'negotiated':
            cash_key = (row['hospital'],
                        row['cpt_code'])
            if cash_key in cash_lookup:
                row['cash_pay_rate'] = \
                    cash_lookup[cash_key]
            elif row['min_rate']:
                # No cash rate published —
                # use minimum negotiated rate
                # as a conservative proxy
                row['cash_pay_rate'] = \
                    row['min_rate']
                row['methodology'] = \
                    row['methodology'] + \
                    '|cash_rate_estimated'

    print(f"\nPost-processing complete:")
    print(f"  Before: {len(results)} rows")
    print(f"  After:  {len(clean_results)} rows")
    print(f"  Removed {len(results) - len(clean_results)}"
          f" duplicate chargemaster rows")
    
    cash_filled = sum(
        1 for r in clean_results 
        if r['rate_type'] == 'negotiated' 
        and r['cash_pay_rate']
    )
    print(f"  Cash rates joined: {cash_filled} rows")
    
    return clean_results
# ─────────────────────────────────────────
# RUN THE PARSER
# ─────────────────────────────────────────

all_results = []

# Parse both hospital files
files = [
    'data/sutter_santa_rosa.csv',
    'data/sutter_alta_bates.csv',
]

for filepath in files:
    if os.path.exists(filepath):
        results = parse_mrf_file(filepath)
        all_results.extend(results)
    else:
        print(f"File not found: {filepath}")

# Post-process to clean duplicates 
# and join cash rates
all_results = post_process(all_results)

# Save combined results
save_results(
    all_results,
    'data/extracted_rates.csv'
)

# Print a sample of what we extracted
print("\n--- SAMPLE OF EXTRACTED RATES ---")
print(f"Total rates extracted: {len(all_results):,}")
print()

# Show first 10 results
for row in all_results[:10]:
    print(
        f"{row['hospital'][:30]:<30} | "
        f"CPT {row['cpt_code']} | "
        f"{row['payer'][:20]:<20} | "
        f"${row['negotiated_rate']}"
    )