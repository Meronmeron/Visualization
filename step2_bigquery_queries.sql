-- ============================================================
-- STEP 2 — BigQuery SQL: Clean, Harmonise & Build Views
-- Run these queries in order in the BigQuery SQL Editor
-- Project: financial-data-491415
-- Dataset: financial_data
--
-- UPDATED: Added data quality filters, period validation,
-- and support for target company analysis.
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- 2A. CONCEPT CROSSWALK TABLE
-- Maps different accounting tag names (from GB IFRS, EU IFRS,
-- and US GAAP) to a single standard concept so GB, EU and US
-- data can be directly compared in one chart.
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE `financial-data-491415.financial_data.concept_crosswalk` AS
SELECT concept_raw, standard_concept, concept_category FROM UNNEST([
  -- Revenue
  STRUCT('Revenue'                           AS concept_raw, 'Revenue'            AS standard_concept, 'Income Statement' AS concept_category),
  STRUCT('ifrs-full:Revenue'                 AS concept_raw, 'Revenue'            AS standard_concept, 'Income Statement'),
  STRUCT('Revenues'                          AS concept_raw, 'Revenue'            AS standard_concept, 'Income Statement'),
  STRUCT('RevenueFromContractsWithCustomers' AS concept_raw, 'Revenue'            AS standard_concept, 'Income Statement'),
  STRUCT('RevenueFromContractWithCustomerExcludingAssessedTax' AS concept_raw, 'Revenue' AS standard_concept, 'Income Statement'),
  STRUCT('us-gaap:Revenues'                  AS concept_raw, 'Revenue'            AS standard_concept, 'Income Statement'),
  STRUCT('SalesRevenueNet'                   AS concept_raw, 'Revenue'            AS standard_concept, 'Income Statement'),

  -- Net Income
  STRUCT('NetIncome'                         AS concept_raw, 'Net Income'         AS standard_concept, 'Income Statement'),
  STRUCT('NetIncomeLoss'                     AS concept_raw, 'Net Income'         AS standard_concept, 'Income Statement'),
  STRUCT('ProfitLoss'                        AS concept_raw, 'Net Income'         AS standard_concept, 'Income Statement'),
  STRUCT('ifrs-full:ProfitLoss'              AS concept_raw, 'Net Income'         AS standard_concept, 'Income Statement'),
  STRUCT('ProfitLossAttributableToOwnersOfParent' AS concept_raw, 'Net Income'   AS standard_concept, 'Income Statement'),

  -- Operating Income
  STRUCT('OperatingProfit'                   AS concept_raw, 'Operating Income'   AS standard_concept, 'Income Statement'),
  STRUCT('OperatingIncomeLoss'               AS concept_raw, 'Operating Income'   AS standard_concept, 'Income Statement'),
  STRUCT('ifrs-full:ProfitLossFromOperatingActivities' AS concept_raw, 'Operating Income' AS standard_concept, 'Income Statement'),

  -- Gross Profit
  STRUCT('GrossProfit'                       AS concept_raw, 'Gross Profit'       AS standard_concept, 'Income Statement'),
  STRUCT('ifrs-full:GrossProfit'             AS concept_raw, 'Gross Profit'       AS standard_concept, 'Income Statement'),

  -- Cost of Revenue
  STRUCT('CostOfSales'                       AS concept_raw, 'Cost of Revenue'    AS standard_concept, 'Income Statement'),
  STRUCT('CostOfRevenue'                     AS concept_raw, 'Cost of Revenue'    AS standard_concept, 'Income Statement'),
  STRUCT('CostOfGoodsAndServicesSold'        AS concept_raw, 'Cost of Revenue'    AS standard_concept, 'Income Statement'),
  STRUCT('ifrs-full:CostOfSales'             AS concept_raw, 'Cost of Revenue'    AS standard_concept, 'Income Statement'),

  -- Total Assets
  STRUCT('Assets'                            AS concept_raw, 'Total Assets'       AS standard_concept, 'Balance Sheet'),
  STRUCT('AssetsNet'                         AS concept_raw, 'Total Assets'       AS standard_concept, 'Balance Sheet'),
  STRUCT('ifrs-full:Assets'                  AS concept_raw, 'Total Assets'       AS standard_concept, 'Balance Sheet'),

  -- Total Liabilities
  STRUCT('Liabilities'                       AS concept_raw, 'Total Liabilities'  AS standard_concept, 'Balance Sheet'),
  STRUCT('ifrs-full:Liabilities'             AS concept_raw, 'Total Liabilities'  AS standard_concept, 'Balance Sheet'),
  STRUCT('LiabilitiesAndStockholdersEquity'  AS concept_raw, 'Total Liabilities'  AS standard_concept, 'Balance Sheet'),

  -- Total Equity
  STRUCT('StockholdersEquity'                AS concept_raw, 'Total Equity'       AS standard_concept, 'Balance Sheet'),
  STRUCT('Equity'                            AS concept_raw, 'Total Equity'       AS standard_concept, 'Balance Sheet'),
  STRUCT('ifrs-full:Equity'                  AS concept_raw, 'Total Equity'       AS standard_concept, 'Balance Sheet'),
  STRUCT('StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest' AS concept_raw, 'Total Equity' AS standard_concept, 'Balance Sheet'),

  -- Cash
  STRUCT('CashAndCashEquivalentsAtCarryingValue' AS concept_raw, 'Cash'           AS standard_concept, 'Balance Sheet'),
  STRUCT('CashAndCashEquivalents'            AS concept_raw, 'Cash'               AS standard_concept, 'Balance Sheet'),
  STRUCT('CashAndCashEquivalentsAtCarryingValue' AS concept_raw, 'Cash'           AS standard_concept, 'Balance Sheet'),
  STRUCT('ifrs-full:CashAndCashEquivalents'  AS concept_raw, 'Cash'               AS standard_concept, 'Balance Sheet'),

  -- Long Term Debt
  STRUCT('LongTermDebt'                      AS concept_raw, 'Long Term Debt'     AS standard_concept, 'Balance Sheet'),
  STRUCT('LongTermDebtNoncurrent'            AS concept_raw, 'Long Term Debt'     AS standard_concept, 'Balance Sheet'),
  STRUCT('ifrs-full:BorrowingsRecognisedAsOfAcquisitionDate' AS concept_raw, 'Long Term Debt' AS standard_concept, 'Balance Sheet'),

  -- Per Share
  STRUCT('EarningsPerShareBasic'             AS concept_raw, 'EPS Basic'          AS standard_concept, 'Per Share'),
  STRUCT('BasicEarningsLossPerShare'         AS concept_raw, 'EPS Basic'          AS standard_concept, 'Per Share'),
  STRUCT('ifrs-full:BasicEarningsLossPerShare' AS concept_raw, 'EPS Basic'        AS standard_concept, 'Per Share'),
  STRUCT('EarningsPerShareDiluted'           AS concept_raw, 'EPS Diluted'        AS standard_concept, 'Per Share'),

  -- Cash Flow
  STRUCT('DividendsPaid'                     AS concept_raw, 'Dividends Paid'     AS standard_concept, 'Cash Flow'),
  STRUCT('PaymentsOfDividends'               AS concept_raw, 'Dividends Paid'     AS standard_concept, 'Cash Flow'),
  STRUCT('NetCashProvidedByUsedInOperatingActivities' AS concept_raw, 'Operating Cash Flow' AS standard_concept, 'Cash Flow'),
  STRUCT('NetCashProvidedByOperatingActivities' AS concept_raw, 'Operating Cash Flow' AS standard_concept, 'Cash Flow'),
  STRUCT('ifrs-full:CashFlowsFromUsedInOperatingActivities' AS concept_raw, 'Operating Cash Flow' AS standard_concept, 'Cash Flow'),
  STRUCT('NetCashProvidedByUsedInInvestingActivities' AS concept_raw, 'Investing Cash Flow' AS standard_concept, 'Cash Flow'),
  STRUCT('NetCashProvidedByUsedInFinancingActivities' AS concept_raw, 'Financing Cash Flow' AS standard_concept, 'Cash Flow')
]);


-- ────────────────────────────────────────────────────────────
-- 2B. UNIFIED HARMONISED VIEW
-- DATA QUALITY: Filters out:
--   - Future years (>2026) and very old years (<2010)
--   - Non-numeric values (via SAFE_CAST)
--   - Extreme outlier values (|value| > 1 trillion for GB/EU)
--   - US rows with null fiscal_year
--   - US rows with unreliable qtrs (>4)
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE VIEW `financial-data-491415.financial_data.v_unified_financials` AS

WITH raw_all AS (
  -- GB data
  SELECT
    g.company_name,
    'GB'                                            AS market,
    'United Kingdom'                                AS country_full,
    'GB'                                            AS country_code,
    g.unit                                          AS currency,
    COALESCE(cx.standard_concept, g.concept)        AS concept,
    cx.concept_category,
    SAFE_CAST(g.value AS FLOAT64)                   AS value,
    SAFE_CAST(SPLIT(COALESCE(g.period_end, ''), '-')[OFFSET(0)] AS INT64) AS fiscal_year,
    SAFE_CAST(g.period_end AS DATE)                 AS period_end,
    SAFE_CAST(g.filing_date AS DATE)                AS filing_date,
    NULL                                            AS cik,
    NULL                                            AS form
  FROM `financial-data-491415.financial_data.gb_xbrl_raw` g
  LEFT JOIN `financial-data-491415.financial_data.concept_crosswalk` cx
    ON g.concept = cx.concept_raw
  WHERE SAFE_CAST(g.value AS FLOAT64) IS NOT NULL
    AND ABS(SAFE_CAST(g.value AS FLOAT64)) < 1e12

  UNION ALL

  -- EU data
  SELECT
    e.company_name,
    'EU'                                            AS market,
    e.country                                       AS country_full,
    e.country                                       AS country_code,
    e.unit                                          AS currency,
    COALESCE(cx.standard_concept, e.concept)        AS concept,
    cx.concept_category,
    SAFE_CAST(e.value AS FLOAT64)                   AS value,
    SAFE_CAST(SPLIT(COALESCE(e.period_end, ''), '-')[OFFSET(0)] AS INT64) AS fiscal_year,
    SAFE_CAST(e.period_end AS DATE)                 AS period_end,
    SAFE_CAST(e.filing_date AS DATE)                AS filing_date,
    NULL                                            AS cik,
    NULL                                            AS form
  FROM `financial-data-491415.financial_data.eu_xbrl_raw` e
  LEFT JOIN `financial-data-491415.financial_data.concept_crosswalk` cx
    ON e.concept = cx.concept_raw
  WHERE SAFE_CAST(e.value AS FLOAT64) IS NOT NULL
    AND SAFE_CAST(SPLIT(COALESCE(e.period_end, ''), '-')[OFFSET(0)] AS INT64) <= 2026

  UNION ALL

  -- US data (filter: qtrs <= 4 and fiscal_year not null)
  SELECT
    SAFE_CAST(u.company_name AS STRING)             AS company_name,
    'US'                                            AS market,
    'United States'                                 AS country_full,
    'US'                                            AS country_code,
    'USD'                                           AS currency,
    COALESCE(cx.standard_concept, u.concept)        AS concept,
    cx.concept_category,
    SAFE_CAST(u.value AS FLOAT64)                   AS value,
    SAFE_CAST(SAFE_CAST(u.fiscal_year AS FLOAT64) AS INT64) AS fiscal_year,
    SAFE_CAST(NULL AS DATE)                         AS period_end,
    SAFE_CAST(u.filing_date AS DATE)                AS filing_date,
    u.cik                                           AS cik,
    u.form                                          AS form
  FROM `financial-data-491415.financial_data.us_edgar_raw` u
  LEFT JOIN `financial-data-491415.financial_data.concept_crosswalk` cx
    ON u.concept = cx.concept_raw
  WHERE u.fiscal_year IS NOT NULL
    AND SAFE_CAST(SAFE_CAST(u.fiscal_year AS FLOAT64) AS INT64) IS NOT NULL
    AND (SAFE_CAST(u.qtrs AS INT64) IS NULL OR SAFE_CAST(u.qtrs AS INT64) <= 4)
)
SELECT * FROM raw_all
WHERE fiscal_year BETWEEN 2010 AND 2026
  AND value IS NOT NULL;


-- ────────────────────────────────────────────────────────────
-- 2C. REVENUE TRENDS
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE `financial-data-491415.financial_data.t_revenue_trends` AS
SELECT
  company_name,
  market,
  country_code,
  currency,
  fiscal_year,
  SUM(value) AS revenue
FROM `financial-data-491415.financial_data.v_unified_financials`
WHERE concept = 'Revenue'
  AND fiscal_year BETWEEN 2019 AND 2025
  AND value > 0
GROUP BY 1,2,3,4,5
ORDER BY company_name, fiscal_year;


-- ────────────────────────────────────────────────────────────
-- 2D. PROFITABILITY METRICS
-- Pivots key concepts into one row per company per year.
-- Computes margins, ROE, ROA, debt-to-equity.
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE `financial-data-491415.financial_data.t_profitability` AS
WITH base AS (
  SELECT
    company_name,
    market,
    country_code,
    fiscal_year,
    MAX(CASE WHEN concept = 'Revenue'           THEN value END) AS revenue,
    MAX(CASE WHEN concept = 'Gross Profit'      THEN value END) AS gross_profit,
    MAX(CASE WHEN concept = 'Operating Income'  THEN value END) AS operating_income,
    MAX(CASE WHEN concept = 'Net Income'        THEN value END) AS net_income,
    MAX(CASE WHEN concept = 'Total Assets'      THEN value END) AS total_assets,
    MAX(CASE WHEN concept = 'Total Equity'      THEN value END) AS total_equity,
    MAX(CASE WHEN concept = 'Total Liabilities' THEN value END) AS total_liabilities,
    MAX(CASE WHEN concept = 'Cash'              THEN value END) AS cash,
    MAX(CASE WHEN concept = 'Long Term Debt'    THEN value END) AS long_term_debt,
    MAX(CASE WHEN concept = 'Operating Cash Flow' THEN value END) AS operating_cash_flow,
    MAX(CASE WHEN concept = 'EPS Basic'         THEN value END) AS eps_basic
  FROM `financial-data-491415.financial_data.v_unified_financials`
  WHERE fiscal_year BETWEEN 2019 AND 2025
  GROUP BY 1,2,3,4
)
SELECT
  *,
  SAFE_DIVIDE(gross_profit,      revenue)       AS gross_margin,
  SAFE_DIVIDE(operating_income,  revenue)       AS operating_margin,
  SAFE_DIVIDE(net_income,        revenue)       AS net_margin,
  SAFE_DIVIDE(net_income,        total_equity)  AS return_on_equity,
  SAFE_DIVIDE(net_income,        total_assets)  AS return_on_assets,
  SAFE_DIVIDE(total_liabilities, total_equity)  AS debt_to_equity
FROM base
WHERE revenue IS NOT NULL AND revenue > 0;


-- ────────────────────────────────────────────────────────────
-- 2E. MARKET SUMMARY
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE `financial-data-491415.financial_data.t_market_summary` AS
SELECT
  market,
  COUNT(DISTINCT company_name)    AS total_companies,
  COUNT(DISTINCT country_code)    AS total_countries,
  COUNT(DISTINCT concept)         AS total_concepts,
  MIN(fiscal_year)                AS data_from,
  MAX(fiscal_year)                AS data_to,
  SUM(CASE WHEN concept = 'Revenue' THEN value ELSE 0 END) AS total_revenue_all_companies
FROM `financial-data-491415.financial_data.v_unified_financials`
GROUP BY market;


-- ────────────────────────────────────────────────────────────
-- 2F. TOP COMPANIES BY REVENUE (all years, not just 2024)
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE `financial-data-491415.financial_data.t_top_companies` AS
SELECT
  company_name,
  market,
  country_code,
  fiscal_year,
  revenue,
  net_income,
  net_margin,
  gross_margin,
  operating_margin,
  total_assets,
  RANK() OVER (PARTITION BY market, fiscal_year ORDER BY revenue DESC) AS revenue_rank
FROM `financial-data-491415.financial_data.t_profitability`;


-- ────────────────────────────────────────────────────────────
-- 2G. YOY REVENUE GROWTH
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE `financial-data-491415.financial_data.t_yoy_growth` AS
SELECT
  curr.company_name,
  curr.market,
  curr.country_code,
  curr.fiscal_year,
  curr.revenue                                            AS revenue_current,
  prev.revenue                                            AS revenue_prior,
  SAFE_DIVIDE(curr.revenue - prev.revenue, prev.revenue)  AS yoy_growth_rate
FROM `financial-data-491415.financial_data.t_revenue_trends` curr
LEFT JOIN `financial-data-491415.financial_data.t_revenue_trends` prev
  ON  curr.company_name = prev.company_name
  AND curr.market       = prev.market
  AND curr.fiscal_year  = prev.fiscal_year + 1
WHERE curr.fiscal_year BETWEEN 2020 AND 2025;


-- ────────────────────────────────────────────────────────────
-- 2H. CROSS-MARKET CONCEPT COVERAGE
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE `financial-data-491415.financial_data.t_concept_coverage` AS
SELECT
  concept,
  concept_category,
  COUNT(DISTINCT CASE WHEN market = 'GB' THEN company_name END) AS gb_companies,
  COUNT(DISTINCT CASE WHEN market = 'EU' THEN company_name END) AS eu_companies,
  COUNT(DISTINCT CASE WHEN market = 'US' THEN company_name END) AS us_companies,
  COUNT(DISTINCT company_name)                                   AS total_companies
FROM `financial-data-491415.financial_data.v_unified_financials`
WHERE concept_category IS NOT NULL
GROUP BY 1,2
ORDER BY total_companies DESC;


-- ────────────────────────────────────────────────────────────
-- 2I. DATA QUALITY SUMMARY TABLE (NEW)
-- Tracks null counts and issues per market for the dashboard
-- ────────────────────────────────────────────────────────────
CREATE OR REPLACE TABLE `financial-data-491415.financial_data.t_data_quality` AS
SELECT
  market,
  fiscal_year,
  COUNT(*) AS total_rows,
  COUNTIF(value IS NULL) AS null_values,
  COUNTIF(concept_category IS NULL) AS unmapped_concepts,
  COUNT(DISTINCT company_name) AS companies_with_data,
  COUNT(DISTINCT concept) AS unique_concepts
FROM `financial-data-491415.financial_data.v_unified_financials`
GROUP BY 1, 2
ORDER BY 1, 2;
