import csv
from collections import defaultdict

rows = list(csv.DictReader(
    open('data/extracted_rates.csv')))

negotiated = [r for r in rows 
              if r['rate_type'] == 'negotiated']

# Missing cash rates
no_cash = [r for r in negotiated 
           if not r['cash_pay_rate']]
print(f"Negotiated rows missing cash rate: {len(no_cash)}")

# Estimated vs real cash rates
estimated = [r for r in negotiated 
             if 'cash_rate_estimated' 
             in r.get('methodology','')]
real_cash = [r for r in negotiated 
             if r['cash_pay_rate'] 
             and 'cash_rate_estimated' 
             not in r.get('methodology','')]
print(f"Real cash rates:      {len(real_cash)}")
print(f"Estimated cash rates: {len(estimated)}")
print()

# Rate comparison — insurance vs cash
print("--- INSURANCE VS CASH COMPARISON ---")
print(f"{'Hospital':<30} {'CPT':<6} "
      f"{'Payer':<12} {'Insured':>10} "
      f"{'Cash':>10} {'Cheaper':>10}")
print("-" * 82)

for r in negotiated:
    if not r['negotiated_rate'] or \
       not r['cash_pay_rate']:
        continue
    neg  = float(r['negotiated_rate'])
    cash = float(r['cash_pay_rate'])
    cheaper = "CASH" if cash < neg \
              else "INSURANCE"
    print(f"{r['hospital'][:30]:<30} "
          f"{r['cpt_code']:<6} "
          f"{r['payer'][:12]:<12} "
          f"${neg:>9,.2f} "
          f"${cash:>9,.2f} "
          f"{cheaper:>10}")