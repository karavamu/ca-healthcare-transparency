
import csv
# open the CSV file and read it into a list

with open('data/procedures.csv','r') as file:
    reader = csv.DictReader(file)
    rows = list(reader)

# print how many rows we have
print(f"Total records: {len(rows)}")

# print every row
print ("\n All records:")
for row in rows:
    print(f"    {row['hospital']}  |  {row['insurer']}  | {row['procedure']}  |  ${row['negotiated_rate']}")

# Question 1 - Cheapest negotiated rate for knee MRI

print ("\nKnee MRI negotiated rates (lowest first):")
knee_mri_rows = [ row for row in rows if row['procedure'] == 'Knee MRI']
knee_mri_sorted = sorted (knee_mri_rows, key=lambda x : float (x['negotiated_rate']))
for row in knee_mri_sorted:
    print(f" {row['hospital']} |  {row['insurer']}  |  ${row['negotiated_rate']}")

# Question 2 - where is the cash pay better than the negotiated rate?
print ("\n Places where the cash pay is cheaper than the insurance:")
for row in rows:
    negotiated = float(row['negotiated_rate'])
    cash =  float(row['cash_pay_rate'])
    if cash < negotiated:
            saving = negotiated - cash
            print(f" {row['hospital']} |  {row['insurer']}  |  ${row['procedure']}  | Insurance: ${negotiated} | Cash: ${cash} | Saving: ${saving:.2f}")

# Question 3 - how inflated is the chargemaster versus the negotiated_rate?
print ("\n  chargemaster rate inflation versus negotiated rate:")
for row in rows:
    chargemaster = float(row['chargemaster_rate'])
    negotiated = float(row['negotiated_rate'])
    inflation = (chargemaster/negotiated)
    print(f" {row['hospital']} |  {row['insurer']}  |  ${row['procedure']}")
    print(f" Chargemaster is {inflation:.1f}x the negotiated rate")

# Question 4 - average negotiated rate by region
print ("\n Average negotiated rate by region")
regions = {}
for row in rows:
    region = row['region']
    rate = float(row['negotiated_rate'])
    if region not in regions:
        regions[region] = []
    regions[region].append(rate)
for region, rates in regions.items():
    average = sum(rates) / len(rates)
    print(f"  {region}: ${average:.2f} average negotiated rate")

