# ca-healthcare-transparency
A California Healthcare Transparency app for Android
# California Healthcare Transparency Project

An Android app that helps California residents understand the true cost of medical procedures before they happen.

## What it does
- Shows negotiated rates between hospitals and insurers
- Calculates your actual out-of-pocket cost based on your
  plan design and deductible status
- Compares insurance path vs cash-pay path
- Identifies financial assistance eligibility for
  uninsured patients
- Guides users through provider network verification
  for every step of a medical episode

## Data sources
- CMS Hospital Price Transparency MRF files
- CMS Physician Fee Schedule
- California HCAI facility and discharge data
- Federal Poverty Level tables

## Tech stack
- Python (data pipeline)
- DuckDB + SQLite (data processing and on-device storage)
- Kotlin + Jetpack Compose (Android app)

## Status
Under construction — Module 0 complete.