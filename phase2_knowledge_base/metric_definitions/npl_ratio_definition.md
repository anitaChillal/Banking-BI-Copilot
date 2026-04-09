# Governed Metric Definition: Non-Performing Loan Ratio (NPL Ratio)
## Apex Bank — Official KPI Reference
### Version: 2.0 | Effective Date: 2024-01-01 | Owner: Chief Risk Officer

---

## 1. Definition

The Non-Performing Loan (NPL) Ratio measures the proportion of the bank's
total loan portfolio that has been classified as non-performing — i.e. where
the borrower has failed to make scheduled payments for 90 or more days, or
where full repayment is considered unlikely regardless of days past due.
NPL Ratio is the primary indicator of asset quality and credit risk in
the loan portfolio.

---

## 2. Official Formula

```
NPL Ratio (%) = Total NPL Balance
                ───────────────────  × 100
                Total Gross Loans

Net NPL Ratio (%) = (Total NPL Balance − Total Provisions)
                    ──────────────────────────────────────  × 100
                           Total Gross Loans
```

Where:
- **Total NPL Balance** = Sum of outstanding balances of all loans classified
  as non-performing (DPD ≥ 90 or stage 3 under IFRS 9)
- **Total Gross Loans** = Total outstanding loan balances before deducting
  provisions (gross carrying amount)
- **Total Provisions** = Specific provisions held against NPL accounts

---

## 3. NPL Classification Criteria

A loan is classified as Non-Performing when ANY of the following conditions
are met:

### 3.1 Days Past Due (DPD) Criterion
- Retail loans: DPD ≥ 90 days on any material obligation
- Corporate loans: DPD ≥ 90 days on any material obligation
- Credit cards: DPD ≥ 90 days
- Overdrafts: Continuously overdrawn beyond limit for ≥ 90 days

### 3.2 Unlikeliness to Pay (UTP) Criterion
Regardless of DPD, a loan is NPL if:
- Borrower has filed for bankruptcy or insolvency
- Bank has sold the loan at a material credit-related loss
- Bank has consented to distressed restructuring (debt forgiveness)
- Collateral has been repossessed
- Specific provision of 100% has been raised

### 3.3 IFRS 9 Stage Classification
| Stage | Description | NPL Classification |
|---|---|---|
| Stage 1 | 12-month ECL, no significant credit deterioration | Performing |
| Stage 2 | Lifetime ECL, significant credit deterioration | Performing (Watch) |
| Stage 3 | Lifetime ECL, credit-impaired | Non-Performing |

---

## 4. IFRS 9 Staging Thresholds

| DPD Range | Stage | Treatment |
|---|---|---|
| 0–29 days | Stage 1 | 12-month ECL provision |
| 30–89 days | Stage 2 | Lifetime ECL provision, interest continues |
| ≥ 90 days | Stage 3 (NPL) | Lifetime ECL, interest suspended |
| Written off | Off balance sheet | Disclosed in notes |

---

## 5. Provision Coverage Ratio

```
Provision Coverage (%) = Total Specific Provisions
                         ───────────────────────────  × 100
                              Total NPL Balance
```

Minimum required coverage: **60%** for secured loans, **100%** for unsecured loans.

---

## 6. Thresholds and Benchmarks

| Threshold | Value | Action |
|---|---|---|
| Target NPL Ratio | ≤ 2.00% | Green — acceptable |
| Watch level | 2.01% – 3.50% | Amber — enhanced monitoring |
| Alert level | 3.51% – 5.00% | Red — remediation plan required |
| Critical level | > 5.00% | Critical — board escalation |
| WoW change alert | +15 bps | Trigger agent investigation |
| MoM change alert | +30 bps | Trigger CRO briefing |
| YoY change alert | +100 bps | Trigger board notification |

---

## 7. Key Drivers of NPL Movement

### NPL Increase Drivers (negative)
- Macroeconomic deterioration (unemployment, interest rate rises)
- Sector concentration — distress in a specific industry
- Geographic concentration — regional economic shock
- Underwriting standards weakened in prior periods
- Fraud or operational failures
- Natural disasters or force majeure events

### NPL Decrease Drivers (positive)
- Successful loan restructuring and rehabilitation
- Write-offs removing fully provisioned loans from the book
- Loan recoveries and repayments
- Portfolio sale of NPL book
- Improved economic conditions

---

## 8. Segment Decomposition

NPL must be reported at:
- **Product type**: Mortgage, Auto, Personal, Business, Trade Finance, Credit Card
- **Business unit**: Retail, Corporate, SME
- **Vintage**: Year of origination
- **Geography**: Region and country
- **Collateral type**: Secured vs unsecured

---

## 9. Data Sources

| Data Element | Source System | Table | Refresh Frequency |
|---|---|---|---|
| Loan balances | Core Banking | fact.loan_position | Daily |
| DPD | Core Banking | fact.loan_position.days_past_due | Daily |
| Loan status | Core Banking | fact.loan_position.loan_status | Daily |
| Provision amounts | Credit Risk System | fact.loan_position.provision_amount | Daily |
| KPI aggregate | ETL Pipeline | kpi.npl_ratio | Daily 03:00 UTC |

---

## 10. Exclusions

- **Interbank loans**: Excluded from retail/corporate NPL ratio.
  Reported separately as counterparty credit risk.
- **Investment securities**: Credit-impaired securities reported under
  FVOCI/FVTPL impairment, not NPL ratio.
- **Off-balance sheet**: Guarantees and contingent liabilities excluded
  from NPL balance but included in total exposure for capital purposes.
- **Written-off loans**: Removed from NPL balance and gross loans after
  write-off. Maintained in off-balance-sheet register for recovery tracking.

---

## 11. Governance

| Role | Responsibility |
|---|---|
| Chief Risk Officer | Formula owner, classification policy |
| Credit Risk | Daily NPL classification and staging |
| Finance | Provision calculation and P&L impact |
| Collections | NPL remediation and recovery |
| Internal Audit | Quarterly NPL classification review |
| Bedrock Agent | Automated daily validation against this definition |
