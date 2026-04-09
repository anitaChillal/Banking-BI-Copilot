# Governed Metric Definition: CASA Ratio
## Apex Bank — Official KPI Reference
### Version: 2.0 | Effective Date: 2024-01-01 | Owner: Retail Banking

---

## 1. Definition

The CASA Ratio measures the proportion of Current Account and Savings Account
deposits to total deposits. CASA deposits are low-cost or zero-cost funds
that reduce the bank's overall cost of funds and improve NIM. A high CASA
ratio indicates a stable, low-cost deposit franchise.

---

## 2. Official Formula

```
CASA Ratio (%) = (Current Account Balance + Savings Account Balance)
                 ────────────────────────────────────────────────────  × 100
                              Total Deposit Balance
```

Where:
- **Current Account Balance** = Total balances in current/checking accounts
  (typically zero or near-zero interest rate)
- **Savings Account Balance** = Total balances in savings accounts
  (typically low interest rate, below fixed deposit rates)
- **Total Deposit Balance** = All customer deposits including CASA, fixed
  deposits, certificates of deposit, and notice deposits

---

## 3. CASA Product Classification

| Product Type | Classification | Typical Rate |
|---|---|---|
| Current account (individual) | CASA — Current | 0.00% |
| Current account (corporate) | CASA — Current | 0.00% – 0.25% |
| Savings account (regular) | CASA — Saving | 0.50% – 2.00% |
| Savings account (premium) | CASA — Saving | 1.00% – 2.50% |
| Fixed deposit (any tenor) | Non-CASA | 3.00% – 5.50% |
| Certificate of deposit | Non-CASA | 3.50% – 5.00% |
| Notice deposit | Non-CASA | 2.00% – 4.00% |

---

## 4. Thresholds and Benchmarks

| Threshold | Value | Action |
|---|---|---|
| Target CASA Ratio | ≥ 45.00% | Green |
| Watch level | 35.00% – 44.99% | Amber |
| Alert level | 25.00% – 34.99% | Red — funding cost pressure |
| Critical level | < 25.00% | Critical — liquidity risk review |
| WoW change alert | ±50 bps | Trigger agent investigation |
| MoM change alert | ±150 bps | Trigger ALCO briefing |

---

## 5. Key Drivers

### CASA Improvement Drivers
- New current/savings account acquisitions
- Payroll account partnerships with corporates
- Digital banking adoption (higher engagement = higher balances)
- Reduction in fixed deposit rates making CASA more attractive
- Seasonal inflows (bonus season, tax refunds)

### CASA Deterioration Drivers
- Rising interest rates making fixed deposits more attractive
- Competitive pressure from other banks offering higher savings rates
- Account attrition and customer churn
- Seasonal outflows (festive spending, year-end tax payments)
- Corporate clients sweeping balances to money market funds

---

## 6. Data Sources

| Data Element | Source | Table | Refresh |
|---|---|---|---|
| CASA balances | Core Banking | fact.deposit_position | Daily |
| Total deposits | Core Banking | fact.deposit_position | Daily |
| Account counts | Core Banking | fact.deposit_position.number_of_accounts | Daily |
| KPI aggregate | ETL Pipeline | kpi.casa_ratio | Daily 03:00 UTC |

---

## 7. Governance

| Role | Responsibility |
|---|---|
| Retail Banking | Formula owner, product classification |
| ALCO | CASA target setting and monitoring |
| Finance | Reconciliation to balance sheet |
| Bedrock Agent | Automated daily validation |

---
---

# Governed Metric Definition: Return on Equity (ROE) and Return on Assets (ROA)
## Apex Bank — Official KPI Reference
### Version: 2.0 | Effective Date: 2024-01-01 | Owner: Group Finance

---

## 1. Definition

**ROE** measures how efficiently the bank generates profit from shareholders'
equity. **ROA** measures how efficiently the bank uses its total assets to
generate profit. Together they are the primary measures of overall bank
profitability and management efficiency.

---

## 2. Official Formulas

```
ROE (%) = Net Profit After Tax (NPAT)
          ─────────────────────────────  × 100
            Average Shareholders' Equity


ROA (%) =    Net Profit After Tax (NPAT)
          ─────────────────────────────────  × 100
           Average Total Assets
```

### Annualised Formula (for sub-annual periods)

```
Annualised ROE (%) = (NPAT for period / Days in period) × 365
                     ─────────────────────────────────────────  × 100
                              Average Equity for period
```

---

## 3. Component Definitions

### Net Profit After Tax (NPAT)
- Total operating income (NII + Non-Interest Income)
- Less: Total operating expenses (staff, IT, admin, depreciation)
- Less: Credit impairment charges (provisions)
- Less: Income tax expense
- **Equals: NPAT**

Excludes: Minority interest, discontinued operations, extraordinary items.

### Average Shareholders' Equity
- Average of opening and closing equity for the period
- Includes: Share capital, retained earnings, reserves, OCI reserves
- Excludes: Minority interest (for standalone entity ROE)

### Average Total Assets
- Average of opening and closing total assets for the period
- Includes ALL on-balance-sheet assets (gross, before provisions)

---

## 4. Thresholds and Benchmarks

| Metric | Target | Watch | Alert | Critical |
|---|---|---|---|---|
| ROE | ≥ 15.00% | 10–14.99% | 7–9.99% | < 7.00% |
| ROA | ≥ 1.50% | 1.00–1.49% | 0.70–0.99% | < 0.70% |
| ROE WoW alert | ±20 bps | — | — | — |
| ROA WoW alert | ±5 bps | — | — | — |

---

## 5. Key Drivers

### ROE/ROA Improvement
- NIM expansion (higher lending rates, lower funding costs)
- Non-interest income growth (fees, commissions, trading)
- Cost efficiency improvement (lower CIR)
- Credit quality improvement (lower provisions)
- Tax optimisation

### ROE/ROA Deterioration
- NIM compression
- Revenue decline (lower volumes or rates)
- Cost increases (restructuring, regulatory compliance)
- Higher credit impairment charges
- Capital raise diluting equity without immediate earnings uplift

---

## 6. Data Sources

| Data Element | Source | Table | Refresh |
|---|---|---|---|
| NPAT | Finance System | fact.income_statement | Monthly |
| Equity | Balance Sheet | fact.balance_sheet | Monthly |
| Total Assets | Balance Sheet | fact.balance_sheet | Monthly |
| KPI aggregate | ETL Pipeline | kpi.roe_roa | Daily 03:00 UTC |

---

## 7. Governance

| Role | Responsibility |
|---|---|
| Group Finance | Formula owner, target setting |
| Board/ALCO | ROE target approval |
| Investor Relations | External ROE disclosure |
| Bedrock Agent | Automated validation |

---
---

# Governed Metric Definition: Cost-to-Income Ratio (CIR)
## Apex Bank — Official KPI Reference
### Version: 2.0 | Effective Date: 2024-01-01 | Owner: Group Finance

---

## 1. Definition

The Cost-to-Income Ratio (CIR) measures operating expenses as a proportion
of operating income. It is the primary measure of the bank's operational
efficiency — how much it costs to generate each unit of revenue. A lower CIR
indicates a more efficient bank.

---

## 2. Official Formula

```
CIR (%) = Total Operating Expenses
          ──────────────────────────  × 100
          Total Operating Income
```

Where:
- **Total Operating Income** = Net Interest Income + Non-Interest Income
- **Total Operating Expenses** = Staff costs + IT costs + Administrative costs
  + Depreciation & Amortisation + Other operating expenses

---

## 3. Component Definitions

### Operating Income (Denominator)
| Component | Included |
|---|---|
| Net Interest Income | Yes |
| Net fee and commission income | Yes |
| Net trading income | Yes |
| Other operating income | Yes |
| Provision charges | No — below the line |
| Tax | No — below the line |
| Extraordinary items | No |

### Operating Expenses (Numerator)
| Component | Included | Sub-category |
|---|---|---|
| Staff salaries and wages | Yes | Staff |
| Staff bonuses and incentives | Yes | Staff |
| Staff benefits and pension | Yes | Staff |
| IT infrastructure and licenses | Yes | IT |
| Digital transformation capex amortisation | Yes | IT |
| Premises and occupancy | Yes | Admin |
| Marketing and advertising | Yes | Admin |
| Professional fees | Yes | Admin |
| Regulatory levies | Yes | Admin |
| Depreciation of fixed assets | Yes | D&A |
| Amortisation of intangibles | Yes | D&A |
| Restructuring charges | No — excluded for underlying CIR |
| Goodwill impairment | No — excluded |

---

## 4. Thresholds and Benchmarks

| Threshold | Value | Action |
|---|---|---|
| Target CIR | ≤ 45.00% | Green — efficient |
| Watch level | 45.01% – 55.00% | Amber |
| Alert level | 55.01% – 65.00% | Red — cost programme required |
| Critical level | > 65.00% | Critical — board escalation |
| WoW change alert | ±100 bps | Trigger investigation |
| MoM change alert | ±250 bps | Trigger CFO briefing |

---

## 5. Key Drivers

### CIR Improvement
- Revenue growth (NIM expansion, fee income growth)
- Headcount reduction or productivity improvement
- Branch rationalisation
- IT legacy decommissioning
- Procurement savings

### CIR Deterioration
- Revenue decline (NIM compression, lower volumes)
- Wage inflation
- Increased regulatory compliance costs
- New technology investment (before productivity benefits)
- Restructuring charges (if included)

---

## 6. Data Sources

| Data Element | Source | Table | Refresh |
|---|---|---|---|
| Operating income | Finance System | fact.income_statement | Daily |
| Operating expenses | Finance System | fact.income_statement | Daily |
| Cost breakdown | Finance System | fact.income_statement.sub_category | Daily |
| KPI aggregate | ETL Pipeline | kpi.cost_income_ratio | Daily 03:00 UTC |

---

## 7. Governance

| Role | Responsibility |
|---|---|
| Group Finance | Formula owner, expense categorisation |
| CFO | CIR target and cost programme ownership |
| HR | Staff cost data provision |
| Technology | IT cost data provision |
| Bedrock Agent | Automated daily validation |

---
---

# Governed Metric Definition: Liquidity Coverage Ratio (LCR) and Net Stable Funding Ratio (NSFR)
## Apex Bank — Official KPI Reference
### Version: 2.0 | Effective Date: 2024-01-01 | Owner: Treasury / ALM

---

## 1. Definition

**LCR** measures whether the bank holds sufficient High-Quality Liquid Assets
(HQLA) to survive a 30-day stressed cash outflow scenario as defined by
Basel III. **NSFR** measures whether the bank's long-term assets are funded
by sufficiently stable funding sources over a 1-year horizon. Both are
mandatory regulatory ratios under Basel III.

---

## 2. Official Formulas

```
LCR (%) =         Stock of HQLA
          ──────────────────────────────────  × 100
          Net Cash Outflows over 30-day period


NSFR (%) = Available Stable Funding (ASF)
           ──────────────────────────────  × 100
           Required Stable Funding (RSF)
```

Minimum regulatory requirement: **LCR ≥ 100%**, **NSFR ≥ 100%**

---

## 3. LCR Components

### High-Quality Liquid Assets (HQLA)

| Asset Class | Level | Haircut | Included if |
|---|---|---|---|
| Central bank reserves | Level 1 | 0% | Always |
| Government bonds (0% RW) | Level 1 | 0% | Investment grade sovereign |
| Central bank bills | Level 1 | 0% | Always |
| Government bonds (20% RW) | Level 2A | 15% | Investment grade |
| Covered bonds (AA-) | Level 2A | 15% | Rated AA- or above |
| RMBS (AA) | Level 2B | 25% | Subject to 15% cap |
| Corporate bonds (A-) | Level 2B | 50% | Subject to 15% cap |

Level 2 assets capped at 40% of total HQLA.
Level 2B assets capped at 15% of total HQLA.

### Net Cash Outflows (30-day stressed scenario)

**Outflows:**
- Retail deposits: 5% (stable) to 10% (less stable) run-off rate
- Unsecured wholesale funding: 25% – 100% run-off depending on counterparty
- Secured funding: Depends on collateral quality
- Committed credit facilities: 10% – 100% drawdown assumption
- Derivative collateral: Mark-to-market + add-on

**Inflows (capped at 75% of outflows):**
- Scheduled loan repayments from performing loans
- Maturing reverse repos and securities lending
- Trade finance inflows

---

## 4. NSFR Components

### Available Stable Funding (ASF) — Liabilities and Equity

| Funding Source | ASF Factor |
|---|---|
| Regulatory capital (Tier 1 + Tier 2) | 100% |
| Retail deposits > 1 year | 100% |
| Stable retail deposits < 1 year | 95% |
| Less stable retail deposits < 1 year | 90% |
| Wholesale deposits > 1 year | 50% |
| Wholesale deposits < 6 months | 0% |

### Required Stable Funding (RSF) — Assets

| Asset Type | RSF Factor |
|---|---|
| Cash and central bank reserves | 0% |
| Level 1 HQLA (unencumbered) | 5% |
| Level 2A HQLA (unencumbered) | 15% |
| Loans > 1 year to retail/SME | 85% |
| Loans < 1 year to retail | 50% |
| Loans to corporates < 1 year | 50% |
| NPL loans | 100% |
| Fixed assets | 100% |

---

## 5. Thresholds and Benchmarks

| Metric | Regulatory Min | Target | Alert | Critical |
|---|---|---|---|---|
| LCR | 100% | ≥ 130% | 105–119% | < 105% |
| NSFR | 100% | ≥ 115% | 103–109% | < 103% |
| LCR WoW alert | — | — | ±200 bps | — |
| NSFR WoW alert | — | — | ±200 bps | — |

Breaching regulatory minimum triggers immediate regulatory notification
within 24 hours per local banking regulation.

---

## 6. Key Drivers

### LCR Deterioration
- Large unexpected deposit outflows
- HQLA portfolio reduction (used for lending)
- Increase in committed facility drawdowns
- Derivative margin calls

### NSFR Deterioration
- Long-term lending growth funded by short-term wholesale
- CASA ratio decline (less stable retail funding)
- Fixed deposit maturity shortening
- Wholesale funding maturity shortening

---

## 7. Data Sources

| Data Element | Source | Table | Refresh |
|---|---|---|---|
| HQLA balances | Treasury System | fact.balance_sheet (hqla_eligible=true) | Daily |
| Deposit balances and run-off | Core Banking | fact.deposit_position | Daily |
| Loan repayment schedules | Core Banking | fact.loan_position | Daily |
| ASF/RSF factors | Treasury System | fact.balance_sheet (rst_stable) | Daily |
| KPI aggregate | ETL Pipeline | kpi.liquidity_ratios | Daily 03:00 UTC |

---

## 8. Regulatory References

- Basel III: International framework for liquidity risk measurement (BCBS 238)
- Local banking regulation: Liquidity Policy Statement
- Internal: ALCO Liquidity Risk Appetite Statement

---

## 9. Governance

| Role | Responsibility |
|---|---|
| Treasurer / ALM | Formula owner, daily LCR/NSFR monitoring |
| ALCO | Liquidity risk appetite and limit setting |
| Risk Management | Stress scenario calibration |
| Regulatory Reporting | Submission to central bank |
| Bedrock Agent | Automated daily validation against this definition |
