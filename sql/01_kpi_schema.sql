-- =============================================================================
-- Banking BI Copilot — Redshift KPI Schema
-- Phase 1: Data Foundation
-- Database: banking_bi
-- =============================================================================
-- Run order:
--   1. schemas
--   2. dimension tables
--   3. fact tables
--   4. KPI aggregate tables
--   5. views (governed metric definitions)
-- =============================================================================

-- ─────────────────────────────────────────────────────────────────────────────
-- SCHEMAS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS dim   ;
CREATE SCHEMA IF NOT EXISTS fact  ;
CREATE SCHEMA IF NOT EXISTS kpi   ;
CREATE SCHEMA IF NOT EXISTS audit ;

-- ─────────────────────────────────────────────────────────────────────────────
-- DIMENSION TABLES
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dim.date (
    date_key        INTEGER         NOT NULL,
    full_date       DATE            NOT NULL,
    year            SMALLINT        NOT NULL,
    quarter         SMALLINT        NOT NULL,  -- 1..4
    month           SMALLINT        NOT NULL,  -- 1..12
    month_name      VARCHAR(10)     NOT NULL,
    week_of_year    SMALLINT        NOT NULL,
    day_of_week     SMALLINT        NOT NULL,
    is_month_end    BOOLEAN         NOT NULL DEFAULT FALSE,
    is_quarter_end  BOOLEAN         NOT NULL DEFAULT FALSE,
    is_year_end     BOOLEAN         NOT NULL DEFAULT FALSE,
    is_business_day BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (date_key));

CREATE TABLE IF NOT EXISTS dim.business_unit (
    bu_key          SMALLINT        NOT NULL,
    bu_code         VARCHAR(20)     NOT NULL,
    bu_name         VARCHAR(100)    NOT NULL,
    bu_type         VARCHAR(50)     NOT NULL,  -- Retail, Corporate, Treasury, SME
    region          VARCHAR(50)     NOT NULL,
    country         VARCHAR(50)     NOT NULL,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (bu_key));

CREATE TABLE IF NOT EXISTS dim.product (
    product_key     INTEGER         NOT NULL,
    product_code    VARCHAR(30)     NOT NULL,
    product_name    VARCHAR(150)    NOT NULL,
    product_type    VARCHAR(50)     NOT NULL,  -- Loan, Deposit, CASA, Investment
    product_class   VARCHAR(50),               -- Retail, Corporate, SME
    asset_class     VARCHAR(50),               -- e.g. Mortgage, Auto, Personal
    is_interest_bearing BOOLEAN     NOT NULL DEFAULT TRUE,
    PRIMARY KEY (product_key));

CREATE TABLE IF NOT EXISTS dim.customer_segment (
    segment_key     SMALLINT        NOT NULL,
    segment_code    VARCHAR(20)     NOT NULL,
    segment_name    VARCHAR(100)    NOT NULL,  -- Mass, Affluent, HNW, Corporate
    segment_tier    VARCHAR(30)     NOT NULL,
    PRIMARY KEY (segment_key));

-- ─────────────────────────────────────────────────────────────────────────────
-- FACT TABLES
-- ─────────────────────────────────────────────────────────────────────────────

-- Loans & advances (source for NIM, NPL, LCR/NSFR)
CREATE TABLE IF NOT EXISTS fact.loan_position (
    position_id         BIGINT          NOT NULL,
    date_key            INTEGER         NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    product_key         INTEGER         NOT NULL,
    segment_key         SMALLINT        NOT NULL,
    outstanding_balance DECIMAL(18,2)   NOT NULL,
    original_balance    DECIMAL(18,2)   NOT NULL,
    interest_rate       DECIMAL(8,4)    NOT NULL,   -- annualised %
    interest_income     DECIMAL(15,2)   NOT NULL,   -- accrued for period
    days_past_due       SMALLINT        NOT NULL DEFAULT 0,
    loan_status         VARCHAR(20)     NOT NULL,   -- Current, 30DPD, 60DPD, 90DPD, NPL, Written-off
    provision_amount    DECIMAL(15,2)   NOT NULL DEFAULT 0,
    collateral_value    DECIMAL(18,2),
    origination_date_key INTEGER,
    maturity_date_key   INTEGER,
    currency_code       CHAR(3)         NOT NULL DEFAULT 'USD',
    PRIMARY KEY (position_id)
);

-- Deposits & liabilities (source for NIM, CASA, LCR/NSFR)
CREATE TABLE IF NOT EXISTS fact.deposit_position (
    position_id         BIGINT          NOT NULL,
    date_key            INTEGER         NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    product_key         INTEGER         NOT NULL,
    segment_key         SMALLINT        NOT NULL,
    deposit_type        VARCHAR(20)     NOT NULL,   -- CASA_Current, CASA_Saving, FD, CD
    balance             DECIMAL(18,2)   NOT NULL,
    interest_expense    DECIMAL(15,2)   NOT NULL,
    interest_rate       DECIMAL(8,4)    NOT NULL,
    number_of_accounts  INTEGER         NOT NULL DEFAULT 1,
    currency_code       CHAR(3)         NOT NULL DEFAULT 'USD',
    PRIMARY KEY (position_id)
);

-- Income statement items (source for Cost-to-Income, ROE/ROA)
CREATE TABLE IF NOT EXISTS fact.income_statement (
    entry_id            BIGINT          NOT NULL,
    date_key            INTEGER         NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    line_item_code      VARCHAR(50)     NOT NULL,
    line_item_name      VARCHAR(150)    NOT NULL,
    category            VARCHAR(50)     NOT NULL,  -- Income, Expense, Provision
    sub_category        VARCHAR(50),               -- NII, Fee, Staff, IT, Credit
    amount              DECIMAL(18,2)   NOT NULL,
    currency_code       CHAR(3)         NOT NULL DEFAULT 'USD',
    PRIMARY KEY (entry_id)
);

-- Balance sheet (source for ROE/ROA, LCR/NSFR capital)
CREATE TABLE IF NOT EXISTS fact.balance_sheet (
    entry_id            BIGINT          NOT NULL,
    date_key            INTEGER         NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    account_code        VARCHAR(50)     NOT NULL,
    account_name        VARCHAR(150)    NOT NULL,
    account_type        VARCHAR(50)     NOT NULL,  -- Asset, Liability, Equity
    sub_type            VARCHAR(50),
    balance             DECIMAL(18,2)   NOT NULL,
    hqla_eligible       BOOLEAN         NOT NULL DEFAULT FALSE,  -- for LCR
    rst_stable          BOOLEAN         NOT NULL DEFAULT FALSE,  -- for NSFR
    currency_code       CHAR(3)         NOT NULL DEFAULT 'USD',
    PRIMARY KEY (entry_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- KPI AGGREGATE TABLES
-- Daily roll-ups pre-computed by Glue; consumed by Bedrock agents
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Net Interest Margin
CREATE TABLE IF NOT EXISTS kpi.net_interest_margin (
    kpi_date            DATE            NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    period_type         VARCHAR(10)     NOT NULL DEFAULT 'Daily',  -- Daily, MTD, QTD, YTD
    total_interest_income  DECIMAL(18,2) NOT NULL,
    total_interest_expense DECIMAL(18,2) NOT NULL,
    net_interest_income    DECIMAL(18,2) NOT NULL,
    average_earning_assets DECIMAL(20,2) NOT NULL,
    nim_pct             DECIMAL(8,4)    NOT NULL,   -- NII / Avg Earning Assets × 100
    nim_wow_bps         SMALLINT,                   -- week-on-week change in basis points
    nim_mom_bps         SMALLINT,
    nim_yoy_bps         SMALLINT,
    nim_ytd_avg_pct     DECIMAL(8,4),
    computed_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kpi_date, bu_key, period_type)
);

-- 2. Non-Performing Loan Ratio
CREATE TABLE IF NOT EXISTS kpi.npl_ratio (
    kpi_date            DATE            NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    product_key         INTEGER         NOT NULL,  -- or -1 for total
    period_type         VARCHAR(10)     NOT NULL DEFAULT 'Daily',
    total_loan_book     DECIMAL(20,2)   NOT NULL,
    npl_balance         DECIMAL(18,2)   NOT NULL,   -- DPD >= 90 days
    npl_ratio_pct       DECIMAL(8,4)    NOT NULL,   -- NPL / Total Loans × 100
    stage_1_balance     DECIMAL(18,2),              -- IFRS 9 staging
    stage_2_balance     DECIMAL(18,2),
    stage_3_balance     DECIMAL(18,2),
    provision_coverage  DECIMAL(8,4),               -- Total Provision / NPL
    npl_wow_bps         SMALLINT,
    npl_mom_bps         SMALLINT,
    npl_yoy_bps         SMALLINT,
    net_npl_ratio_pct   DECIMAL(8,4),               -- after provisions
    computed_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kpi_date, bu_key, product_key, period_type)
);

-- 3. CASA Ratio
CREATE TABLE IF NOT EXISTS kpi.casa_ratio (
    kpi_date            DATE            NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    period_type         VARCHAR(10)     NOT NULL DEFAULT 'Daily',
    casa_balance        DECIMAL(20,2)   NOT NULL,   -- Current + Savings
    current_acct_balance DECIMAL(20,2)  NOT NULL,
    savings_acct_balance DECIMAL(20,2)  NOT NULL,
    total_deposits      DECIMAL(20,2)   NOT NULL,
    casa_ratio_pct      DECIMAL(8,4)    NOT NULL,   -- CASA / Total Deposits × 100
    number_of_casa_accts INTEGER        NOT NULL,
    casa_avg_balance    DECIMAL(15,2),
    casa_wow_bps        SMALLINT,
    casa_mom_bps        SMALLINT,
    casa_yoy_bps        SMALLINT,
    computed_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kpi_date, bu_key, period_type)
);

-- 4. ROE / ROA
CREATE TABLE IF NOT EXISTS kpi.roe_roa (
    kpi_date            DATE            NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    period_type         VARCHAR(10)     NOT NULL DEFAULT 'Daily',  -- typically MTD/QTD/YTD
    net_profit_after_tax DECIMAL(18,2)  NOT NULL,
    average_equity      DECIMAL(20,2)   NOT NULL,
    average_total_assets DECIMAL(22,2)  NOT NULL,
    roe_pct             DECIMAL(8,4)    NOT NULL,   -- NPAT / Avg Equity × 100
    roa_pct             DECIMAL(8,4)    NOT NULL,   -- NPAT / Avg Total Assets × 100
    roe_annualised_pct  DECIMAL(8,4),
    roa_annualised_pct  DECIMAL(8,4),
    roe_wow_bps         SMALLINT,
    roe_mom_bps         SMALLINT,
    roe_yoy_bps         SMALLINT,
    roa_wow_bps         SMALLINT,
    roa_mom_bps         SMALLINT,
    roa_yoy_bps         SMALLINT,
    computed_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kpi_date, bu_key, period_type)
);

-- 5. Cost-to-Income Ratio
CREATE TABLE IF NOT EXISTS kpi.cost_income_ratio (
    kpi_date            DATE            NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    period_type         VARCHAR(10)     NOT NULL DEFAULT 'MTD',
    total_operating_income  DECIMAL(18,2) NOT NULL,  -- NII + Non-II
    total_operating_expense DECIMAL(18,2) NOT NULL,  -- Staff + Admin + IT + D&A
    staff_costs         DECIMAL(18,2),
    it_costs            DECIMAL(18,2),
    admin_costs         DECIMAL(18,2),
    depreciation_amort  DECIMAL(18,2),
    cir_pct             DECIMAL(8,4)    NOT NULL,   -- Expenses / Income × 100
    cir_wow_bps         SMALLINT,
    cir_mom_bps         SMALLINT,
    cir_yoy_bps         SMALLINT,
    computed_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kpi_date, bu_key, period_type)
);

-- 6. LCR / NSFR
CREATE TABLE IF NOT EXISTS kpi.liquidity_ratios (
    kpi_date            DATE            NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    period_type         VARCHAR(10)     NOT NULL DEFAULT 'Daily',
    -- LCR components
    hqla_total          DECIMAL(20,2)   NOT NULL,   -- High-Quality Liquid Assets
    hqla_level1         DECIMAL(20,2),
    hqla_level2a        DECIMAL(20,2),
    hqla_level2b        DECIMAL(20,2),
    net_cash_outflows_30d DECIMAL(20,2) NOT NULL,
    lcr_pct             DECIMAL(8,4)    NOT NULL,   -- HQLA / Net Cash Outflows × 100
    lcr_regulatory_min  DECIMAL(8,4)    NOT NULL DEFAULT 100.0,
    lcr_headroom_pct    DECIMAL(8,4),               -- LCR - 100
    -- NSFR components
    available_stable_funding DECIMAL(20,2) NOT NULL,
    required_stable_funding  DECIMAL(20,2) NOT NULL,
    nsfr_pct            DECIMAL(8,4)    NOT NULL,   -- ASF / RSF × 100
    nsfr_regulatory_min DECIMAL(8,4)    NOT NULL DEFAULT 100.0,
    nsfr_headroom_pct   DECIMAL(8,4),
    lcr_wow_bps         SMALLINT,
    lcr_mom_bps         SMALLINT,
    nsfr_wow_bps        SMALLINT,
    nsfr_mom_bps        SMALLINT,
    computed_at         TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (kpi_date, bu_key, period_type)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- KPI MOVEMENT EVENTS — populated when anomaly thresholds are breached
-- Consumed by EventBridge to trigger agent investigation
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS kpi.movement_events (
    event_id            VARCHAR(36)     NOT NULL,   -- UUID
    event_timestamp     TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    kpi_name            VARCHAR(50)     NOT NULL,   -- nim, npl_ratio, casa, roe_roa, cir, lcr_nsfr
    kpi_date            DATE            NOT NULL,
    bu_key              SMALLINT        NOT NULL,
    period_type         VARCHAR(10)     NOT NULL,
    previous_value      DECIMAL(10,4)   NOT NULL,
    current_value       DECIMAL(10,4)   NOT NULL,
    change_bps          SMALLINT        NOT NULL,
    change_pct          DECIMAL(8,4)    NOT NULL,
    threshold_type      VARCHAR(20)     NOT NULL,   -- WoW, MoM, YoY, Absolute
    threshold_breached  DECIMAL(10,4)   NOT NULL,
    severity            VARCHAR(10)     NOT NULL,   -- Low, Medium, High, Critical
    investigation_status VARCHAR(20)    NOT NULL DEFAULT 'Pending',
    agent_session_id    VARCHAR(100),               -- set when agent picks up
    PRIMARY KEY (event_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- GOVERNED METRIC VIEWS — single source of truth for agent validation
-- ─────────────────────────────────────────────────────────────────────────────

CREATE OR REPLACE VIEW kpi.v_nim_latest AS
SELECT
    n.kpi_date,
    b.bu_name,
    b.region,
    n.net_interest_income,
    n.average_earning_assets,
    n.nim_pct,
    n.nim_wow_bps,
    n.nim_mom_bps,
    n.nim_yoy_bps,
    n.nim_ytd_avg_pct
FROM kpi.net_interest_margin n
JOIN dim.business_unit b ON b.bu_key = n.bu_key
WHERE n.period_type = 'Daily'
  AND n.kpi_date = (SELECT MAX(kpi_date) FROM kpi.net_interest_margin WHERE period_type = 'Daily');

CREATE OR REPLACE VIEW kpi.v_npl_latest AS
SELECT
    n.kpi_date,
    b.bu_name,
    b.region,
    p.product_name,
    p.product_type,
    n.total_loan_book,
    n.npl_balance,
    n.npl_ratio_pct,
    n.net_npl_ratio_pct,
    n.provision_coverage,
    n.stage_1_balance,
    n.stage_2_balance,
    n.stage_3_balance,
    n.npl_wow_bps,
    n.npl_mom_bps,
    n.npl_yoy_bps
FROM kpi.npl_ratio n
JOIN dim.business_unit b ON b.bu_key = n.bu_key
LEFT JOIN dim.product p ON p.product_key = n.product_key
WHERE n.period_type = 'Daily'
  AND n.kpi_date = (SELECT MAX(kpi_date) FROM kpi.npl_ratio WHERE period_type = 'Daily');

CREATE OR REPLACE VIEW kpi.v_casa_latest AS
SELECT
    c.kpi_date,
    b.bu_name,
    b.region,
    c.casa_balance,
    c.total_deposits,
    c.casa_ratio_pct,
    c.number_of_casa_accts,
    c.casa_wow_bps,
    c.casa_mom_bps,
    c.casa_yoy_bps
FROM kpi.casa_ratio c
JOIN dim.business_unit b ON b.bu_key = c.bu_key
WHERE c.period_type = 'Daily'
  AND c.kpi_date = (SELECT MAX(kpi_date) FROM kpi.casa_ratio WHERE period_type = 'Daily');

CREATE OR REPLACE VIEW kpi.v_liquidity_latest AS
SELECT
    l.kpi_date,
    b.bu_name,
    b.region,
    l.lcr_pct,
    l.lcr_headroom_pct,
    l.nsfr_pct,
    l.nsfr_headroom_pct,
    l.hqla_total,
    l.net_cash_outflows_30d,
    l.lcr_wow_bps,
    l.lcr_mom_bps,
    l.nsfr_wow_bps,
    l.nsfr_mom_bps
FROM kpi.liquidity_ratios l
JOIN dim.business_unit b ON b.bu_key = l.bu_key
WHERE l.period_type = 'Daily'
  AND l.kpi_date = (SELECT MAX(kpi_date) FROM kpi.liquidity_ratios WHERE period_type = 'Daily');

-- ─────────────────────────────────────────────────────────────────────────────
-- AUDIT LOG
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit.query_log (
    log_id              BIGSERIAL,
    logged_at           TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    principal           VARCHAR(100)    NOT NULL,  -- IAM role or user
    query_hash          VARCHAR(64),
    kpi_accessed        VARCHAR(50),
    rows_returned       INTEGER,
    query_duration_ms   INTEGER,
    source_system       VARCHAR(50),    -- bedrock-agent, glue, analyst-ui
    PRIMARY KEY (log_id)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- GRANT PERMISSIONS
-- ─────────────────────────────────────────────────────────────────────────────

-- Create roles first
CREATE ROLE analysts;
CREATE ROLE agents;
CREATE ROLE auditors;

-- Analyst: read KPI aggregates and views only
GRANT USAGE ON SCHEMA kpi TO analysts;
GRANT SELECT ON ALL TABLES IN SCHEMA kpi TO analysts;

-- Agent: read everything, write movement_events
GRANT USAGE ON SCHEMA dim, fact, kpi TO agents;
GRANT SELECT ON ALL TABLES IN SCHEMA dim TO agents;
GRANT SELECT ON ALL TABLES IN SCHEMA fact TO agents;
GRANT SELECT, INSERT, UPDATE ON kpi.movement_events TO agents;

-- Auditor: read only, all schemas
GRANT USAGE ON SCHEMA dim, fact, kpi, audit TO auditors;
GRANT SELECT ON ALL TABLES IN SCHEMA dim TO auditors;
GRANT SELECT ON ALL TABLES IN SCHEMA fact TO auditors;
GRANT SELECT ON ALL TABLES IN SCHEMA kpi TO auditors;
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO auditors;
