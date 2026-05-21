---
id: kb-brandx-united-healthcare
type: payer-coverage
title: "BrandX coverage — UnitedHealthcare commercial"
version: 1
owners: ["u:market-access-lead"]
status: approved
last_verified: 2026-05-05
review_cycle: 14
classification: confidential
audience: ["bu:commercial-onco", "bu:market-access"]
residency: ["us"]
coverage_tier: tier2
entities:
  brand: ["brandx"]
  payer: ["united-healthcare"]
  indication: ["nsclc"]
sources:
  - { ref: "https://example.local/uhc/oncology-policy-2026-q2", date: 2026-04-01, kind: external }
confidence: high
---
# BrandX coverage — UnitedHealthcare commercial

## Current Coverage

UnitedHealthcare commercial plans cover BrandX at tier 2 with prior authorization.
PA requires documentation of confirmed MET-exon14 alteration by an approved assay
and prior-line exposure documentation. Step-edit through BrandY is **not** required.

## Recent Policy Changes

- 2026-Q2 oncology policy refresh expanded approved MET assays to include the new
  liquid-biopsy panel from the diagnostic partner.
- The PA renewal cycle was shortened from 12 to 6 months for new starts.

## Field Implications

Provider offices in UHC-heavy markets should be reminded that step-edit is not
required and that the liquid-biopsy assay is now accepted, reducing time-to-treatment
by ~9 days in typical workflows.

## Sources
[^s1]: UHC oncology policy bulletin, Q2 2026.
