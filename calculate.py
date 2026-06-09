import os
import csv
# ─────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────

def load_data(use_real_data=True):
    """Load procedure data.
    
    If use_real_data=True, loads from the
    extracted MRF data with real hospital rates.
    Falls back to hand-typed seed data if the
    extracted file does not exist.
    """
    
    real_data_path = 'data/extracted_rates.csv'
    seed_data_path = 'data/procedures.csv'
    
    if use_real_data and \
       os.path.exists(real_data_path):
        return load_real_data(real_data_path)
    else:
        print("Using seed data (procedures.csv)")
        with open(seed_data_path, 'r') as f:
            reader = csv.DictReader(f)
            return list(reader)

def load_real_data(filepath):
    """Load and normalize extracted MRF data
    into the structure calculate.py expects."""
    
    rows = []
    
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            
            # Skip chargemaster rows —
            # we only want negotiated rate rows
            if row['rate_type'] != 'negotiated':
                continue
            
            # Skip rows with no negotiated rate
            if not row['negotiated_rate']:
                continue
            
            # Map extracted columns to the
            # structure find_rate() expects
            rows.append({
                'hospital':         row['hospital'],
                'insurer':          row['payer'],
                'plan':             row['plan'],
                'procedure':        row['description'],
                'cpt_code':         row['cpt_code'],
                'chargemaster_rate': '',
                'negotiated_rate':  row['negotiated_rate'],
                'cash_pay_rate':    row['cash_pay_rate'],
                'region':           get_region(
                                      row['hospital']),
                'min_rate':         row['min_rate'],
                'max_rate':         row['max_rate'],
                'methodology':      row['methodology'],
            })
    
    print(f"Loaded {len(rows)} real rates from "
          f"{os.path.basename(filepath)}")
    return rows

def get_region(hospital_name):
    """Map hospital name to California region."""
    
    regions = {
        'Santa Rosa':  'Bay Area',
        'Alta Bates':  'Bay Area',
        'Sutter':      'Bay Area',
        'UCSF':        'Bay Area',
        'Stanford':    'Bay Area',
        'Cedars':      'Los Angeles',
        'Providence':  'Los Angeles',
        'Scripps':     'San Diego',
        'Sharp':       'San Diego',
    }
    
    for keyword, region in regions.items():
        if keyword.lower() in \
           hospital_name.lower():
            return region
    
    return 'California'    


def find_rate(rows, procedure, insurer):
    """Find the negotiated and cash rate for a
    specific procedure and insurer.
    
    Matches on procedure description or CPT code,
    and insurer name (partial match supported).
    Returns the best matching row or None."""
    
    insurer_lower = insurer.lower().strip()
    proc_lower = procedure.lower().strip()
    
    # Try exact match first
    for row in rows:
        row_insurer = row.get(
            'insurer', '').lower().strip()
        row_proc = row.get(
            'procedure', '').lower().strip()
        row_cpt = row.get('cpt_code', '').strip()
        
        insurer_match = insurer_lower in \
                        row_insurer or \
                        row_insurer in insurer_lower
        
        proc_match = proc_lower == row_proc or \
                     proc_lower in row_proc or \
                     row_proc in proc_lower
        
        if insurer_match and proc_match:
            return {
                'hospital':         row.get(
                                      'hospital',''),
                'negotiated_rate':  float(row.get(
                                      'negotiated_rate',
                                      0)),
                'cash_pay_rate':    float(row.get(
                                      'cash_pay_rate',
                                      0)) if row.get(
                                      'cash_pay_rate') 
                                      else None,
                'chargemaster_rate': float(row.get(
                                      'chargemaster_rate',
                                      0)) if row.get(
                                      'chargemaster_rate')
                                      else None,
                'region':           row.get(
                                      'region',''),
                'plan':             row.get(
                                      'plan', ''),
                'min_rate':         row.get(
                                      'min_rate', ''),
                'max_rate':         row.get(
                                      'max_rate', ''),
            }
    
    return None



# ─────────────────────────────────────────
# OOP CALCULATION
# ─────────────────────────────────────────

def calculate_oop(negotiated_rate, deductible_remaining,coinsurance_pct):
    """Calculate patient out of pocket cost after deductible and coinsurance."""

    if deductible_remaining  >= negotiated_rate:
        patient_pays = negotiated_rate
        deductible_used = negotiated_rate
        coinsurance_paid = 0.0

    elif deductible_remaining > 0:
        # Partial deductible then coinsurance
        deductible_used = deductible_remaining
        remainder = negotiated_rate - deductible_remaining
        coinsurance_paid = remainder * (coinsurance_pct / 100)
        patient_pays = deductible_used + coinsurance_paid

    else:
        # Deductible already met - coinsurance only
        deductible_used = 0.0
        coinsurance_paid = negotiated_rate * (coinsurance_pct / 100)
        patient_pays = coinsurance_paid

    return {
        'patient_pays': round(patient_pays, 2),
        'deductible_used': round(deductible_used, 2),
        'coinsurance_paid': round(coinsurance_paid, 2)
    }



# ─────────────────────────────────────────
# PREMIUM CALCULATION
# ─────────────────────────────────────────

def calculate_premium_context(monthly_premium,expected_procedures,through_insurance_oop, cash_pay_rate):
    """Calculate how the annual premium affects
    the true cost of using insurance."""

    # Annual premium the employee pays
    annual_premium = monthly_premium * 12

    # Share of premium attributable to this one procedure
    # based on how many procedures expected this year
    if expected_procedures > 0:
        premium_per_procedure = annual_premium / expected_procedures
    else:
        premium_per_procedure = 0.0

    # True insurance cost = OOP + your share of annual premium
    true_insurance_cost = through_insurance_oop + premium_per_procedure

    # How much does insurance save per procedure vs cash
    # (before considering premium)
    raw_saving_per_procedure = cash_pay_rate - through_insurance_oop

    # Break even: how many procedures per year do you need
    # for insurance to pay for itself vs paying cash everywhere
    if raw_saving_per_procedure > 0:
        break_even = annual_premium / raw_saving_per_procedure
        break_even_verdict = (
            f"You need {break_even:.1f} procedures/year "
            f"for insurance to pay for itself"
        )
    elif raw_saving_per_procedure == 0:
        break_even = None
        break_even_verdict = (
            "Insurance and cash cost the same per procedure"
        )
    else:
        break_even = None
        break_even_verdict = (
            "Cash is cheaper per procedure — insurance "
            "does not pay for itself on this procedure alone"
        )

    # Annual verdict
    if true_insurance_cost < cash_pay_rate:
        annual_verdict = "INSURANCE wins when premium is factored in"
    else:
        annual_verdict = "CASH wins even after factoring in premium"

    return {
        'annual_premium': round(annual_premium, 2),
        'premium_per_procedure': round(premium_per_procedure, 2),
        'true_insurance_cost': round(true_insurance_cost, 2),
        'raw_saving_per_procedure': round(raw_saving_per_procedure, 2),
        'break_even_verdict': break_even_verdict,
        'annual_verdict': annual_verdict
    }


# ─────────────────────────────────────────
# MAIN RECOMMENDATION FUNCTION
# ─────────────────────────────────────────

def get_recommendation(procedure, insurer,
                        deductible_remaining, coinsurance_pct,
                        monthly_premium, expected_procedures):
    """Main function — takes user inputs and
    returns full cost estimate including premium."""

    # Load data
    rows = load_data()

    # Find rate for this procedure and insurer
    rate_info = find_rate(rows, procedure, insurer)

    if rate_info is None:
        print(f"Sorry - no data found for "
              f"{procedure} with {insurer}")
        return

    # Calculate through-insurance OOP
    oop_result = calculate_oop(
        rate_info['negotiated_rate'],
        deductible_remaining,
        coinsurance_pct
    )

    through_insurance = oop_result['patient_pays']
    cash_total = rate_info['cash_pay_rate'] \
                 if rate_info['cash_pay_rate'] \
                 else rate_info['negotiated_rate']

    # Per-procedure recommendation (ignoring premium)
    if cash_total < through_insurance:
        per_procedure_rec = "PAY CASH - cheaper for this procedure"
        per_procedure_saving = through_insurance - cash_total
    else:
        per_procedure_rec = "USE INSURANCE - cheaper for this procedure"
        per_procedure_saving = cash_total - through_insurance

    # Premium context
    premium_context = calculate_premium_context(
        monthly_premium,
        expected_procedures,
        through_insurance,
        cash_total
    )

    # Print full breakdown
    print(f"\n{'='*55}")
    print(f"COST ESTIMATE: {procedure}")
    print(f"{'='*55}")
    print(f"Hospital:            {rate_info['hospital']}")
    print(f"Insurer:             {insurer}")
    plan = rate_info.get('plan','')
    if plan:
        print(f"Plan:                {plan}")
    print(f"Region:              {rate_info['region']}")
    min_r = rate_info.get('min_rate','')
    max_r = rate_info.get('max_rate','')
    if min_r and max_r:
        print(f"Rate range:          "
              f"${float(min_r):,.2f} "
              f"to ${float(max_r):,.2f} "
              f"across all insurers")

    print(f"\n--- PRICING BREAKDOWN ---")
    # Only show chargemaster if available
    if rate_info['chargemaster_rate']:
        print(f"Chargemaster rate:   "
              f"${rate_info['chargemaster_rate']:>10,.2f}")
    else:
        print(f"Chargemaster rate:   "
              f"{'not published':>10}")
    
    print(f"Negotiated rate:     "
          f"${rate_info['negotiated_rate']:>10,.2f}")
    
    # Only show cash rate if available
    if rate_info['cash_pay_rate']:
        print(f"Cash pay rate:       "
              f"${rate_info['cash_pay_rate']:>10,.2f}")
    else:
        print(f"Cash pay rate:       "
              f"{'not published':>10}")

    print(f"\n--- YOUR PLAN ---")
    print(f"Deductible remaining:  ${deductible_remaining:>8,.2f}")
    print(f"Coinsurance:           {coinsurance_pct:>8}%")
    print(f"Monthly premium:       ${monthly_premium:>8,.2f}")
    print(f"Procedures expected:   {expected_procedures:>8}")

    print(f"\n--- THROUGH INSURANCE (this procedure) ---")
    print(f"Deductible portion:  ${oop_result['deductible_used']:>10,.2f}")
    print(f"Coinsurance portion: ${oop_result['coinsurance_paid']:>10,.2f}")
    print(f"You pay (OOP):       ${through_insurance:>10,.2f}")

    print(f"\n--- CASH PAY (this procedure) ---")
    print(f"You pay:             ${cash_total:>10,.2f}")

    print(f"\n--- PER-PROCEDURE VERDICT ---")
    print(f"  {per_procedure_rec}")
    print(f"  You save: ${per_procedure_saving:,.2f}")

    print(f"\n--- ANNUAL PREMIUM CONTEXT ---")
    print(f"Annual premium:         ${premium_context['annual_premium']:>8,.2f}")
    print(f"Premium per procedure:  ${premium_context['premium_per_procedure']:>8,.2f}")
    print(f"True insurance cost:    ${premium_context['true_insurance_cost']:>8,.2f}")
    print(f"  (OOP + premium share)")
    print(f"Cash pay cost:          ${cash_total:>8,.2f}")
    print(f"")
    print(f"  {premium_context['break_even_verdict']}")
    print(f"  {premium_context['annual_verdict']}")
    print(f"{'='*55}")


# ─────────────────────────────────────────
# TEST SCENARIOS WITH REAL DATA
# ─────────────────────────────────────────

print("\n" + "="*55)
print("RUNNING WITH REAL CALIFORNIA HOSPITAL DATA")
print("="*55)


# ─────────────────────────────────────────
# INTERACTIVE MODE
# ─────────────────────────────────────────

def show_available_options(rows):
    """Show the user what procedures and 
    insurers are in the database."""
    
    procedures = sorted(set(row['procedure'] for row in rows))
    insurers = sorted(set(row['insurer'] for row in rows))
    
    print("\nAvailable procedures:")
    for i, procedure in enumerate(procedures, 1):
        print(f"  {i}. {procedure}")
    
    print("\nAvailable insurers:")
    for i, insurer in enumerate(insurers, 1):
        print(f"  {i}. {insurer}")

def interactive_mode():
    """Ask the user for their inputs and
    return a personalized cost estimate."""
    
    # Load data once
    rows = load_data()
    
    print("\n" + "="*55)
    print("CALIFORNIA HEALTHCARE TRANSPARENCY PROJECT")
    print("="*55)
    print("Let us find the true cost of your procedure.")
    
    # Show what is available
    show_available_options(rows)
    
    # Get user inputs
    print("\n--- YOUR INFORMATION ---")
    
    procedure = input("\nEnter procedure name exactly as shown above: ")
    insurer = input("Enter insurer name exactly as shown above: ")
    
    deductible_remaining = float(input(
        "How much deductible do you have remaining ($): "
    ).replace('$', '').replace(',', '').strip())
    
    coinsurance_raw = input(
        "What is your coinsurance percentage (e.g. 20 for 20%): "
    )
    # Strip % sign if user types it
    coinsurance_pct = float(
        coinsurance_raw.replace('%', '').strip()
    )
    
    monthly_premium = float(input(
        "What is your monthly premium ($): "
    ).replace('$', '').replace(',', '').strip())
    
    expected_procedures = int(input(
        "How many procedures do you expect this year: "
    ))
    
    # Run the calculation with their inputs
    get_recommendation(
        procedure=procedure,
        insurer=insurer,
        deductible_remaining=deductible_remaining,
        coinsurance_pct=coinsurance_pct,
        monthly_premium=monthly_premium,
        expected_procedures=expected_procedures
    )
    
    # Ask if they want to check another procedure
    another = input("\nCheck another procedure? (yes/no): ")
    if another.lower() == 'yes':
        interactive_mode()

# ─────────────────────────────────────────
# CHOOSE MODE: TEST OR INTERACTIVE
# ─────────────────────────────────────────

print("\nWould you like to:")
print("  1. Run test scenarios")
print("  2. Enter your own information")

choice = input("\nEnter 1 or 2: ")

if choice == '1':
    # ── Real data scenarios ──
    get_recommendation(
        procedure='Diagnostic colonoscopy',
        insurer='Anthem',
        deductible_remaining=1500,
        coinsurance_pct=20,
        monthly_premium=250,
        expected_procedures=4
    )
    get_recommendation(
        procedure='Mri jnt of lwr extre w/o dye',
        insurer='Blue Shield',
        deductible_remaining=0,
        coinsurance_pct=20,
        monthly_premium=300,
        expected_procedures=5
    )
    get_recommendation(
        procedure='Mri jnt of lwr extre w/o dye',
        insurer='Health Net',
        deductible_remaining=500,
        coinsurance_pct=30,
        monthly_premium=220,
        expected_procedures=3
    )

elif choice == '2':
    interactive_mode()

else:
    print("Please enter 1 or 2")