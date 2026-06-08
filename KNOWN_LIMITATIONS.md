# Known Limitations and Assumptions

## Current assumptions in calculate.py

### High priority to address
- All providers assumed in-network
- Preventive care exemptions not implemented
- OOP maximum not factored into calculation
- Prior authorization not checked

### Medium priority to address
- Prescription drug costs not included
- Global surgical period not modeled
- Family vs individual deductible not distinguished
- Tiered network cost sharing not implemented

### Lower priority
- Coordination of benefits (dual insurance) not handled
- No Surprises Act protections not modeled

## Notes
Each limitation is documented in the session notes
and will be addressed in later modules as the data
model and calculation engine mature.

## Data quality issues discovered in Module 2

### Cash rate = chargemaster for some procedures
Some hospitals publish the same value for both
gross charge and discounted cash rate columns.
This makes cash appear artificially expensive
for procedures like Knee MRI where the true
discounted cash rate would be lower.
Mitigation: flag when cash_rate = chargemaster_rate

### Colonoscopy cash rate is estimated
Sutter Santa Rosa did not publish a chargemaster
row for colonoscopy. Cash rate is estimated from
the minimum negotiated rate (Medicare Adv rate).
Flagged in methodology column as cash_rate_estimated.

### Lipid panel commercial rates missing
Most commercial insurers use percentage-based
contracts for low-cost lab work rather than
flat dollar amounts. Our parser currently skips
these rows. Only Medicare Advantage rates captured
for CPT 80061.