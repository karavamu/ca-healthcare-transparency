import csv
# ─────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────
def load_data():
    """Load procedure data from CSV file."""
    with open('data/procedures.csv', 'r') as file:
        reader = csv.DictReader(file)
        return list(reader)


def find_rate(rows, procedure, insurer):
    """Find the negotiated and cash rate for a
    specific procedure and insurer."""
    for row in rows:
        if row['procedure'] == procedure and \
           row['insurer'] == insurer:
            return {
                'hospital': row['hospital'],
                'negotiated_rate': float(row['negotiated_rate']),
                'cash_pay_rate': float(row['cash_pay_rate']),
                'chargemaster_rate': float(row['chargemaster_rate']),
                'region': row['region']
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
    cash_total = rate_info['cash_pay_rate']

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
    print(f"Region:              {rate_info['region']}")

    print(f"\n--- PRICING BREAKDOWN ---")
    print(f"Chargemaster rate:   ${rate_info['chargemaster_rate']:>10,.2f}")
    print(f"Negotiated rate:     ${rate_info['negotiated_rate']:>10,.2f}")
    print(f"Cash pay rate:       ${rate_info['cash_pay_rate']:>10,.2f}")

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
# TEST SCENARIOS
# ─────────────────────────────────────────

# Scenario 1: High deductible, moderate premium
# User has not met deductible yet
get_recommendation(
    procedure='Knee MRI',
    insurer='Blue Shield',
    deductible_remaining=1500,
    coinsurance_pct=20,
    monthly_premium=250,
    expected_procedures=4
)

# Scenario 2: Deductible met, low premium
# User has already met their deductible this year
get_recommendation(
    procedure='Knee MRI',
    insurer='Anthem Blue Cross',
    deductible_remaining=0,
    coinsurance_pct=20,
    monthly_premium=180,
    expected_procedures=6
)

# Scenario 3: Lab work, partial deductible
# User has some deductible remaining
get_recommendation(
    procedure='Lipid Panel',
    insurer='Anthem Blue Cross',
    deductible_remaining=200,
    coinsurance_pct=30,
    monthly_premium=320,
    expected_procedures=3
)