-- ============================================================
-- DATA QUALITY FIXES for BigQuery
-- Project: financial-data-491415
-- Dataset: financial_data
-- 
-- Run BEFORE step2_bigquery_queries.sql to clean the raw data
-- ============================================================


-- ────────────────────────────────────────────────────────────
-- FIX 1: Remove rows with future/invalid years from EU data
-- EU dataset contains rows with period_end years 2029 and 2031.
-- These are clearly data entry errors in XBRL filings.
-- ────────────────────────────────────────────────────────────
DELETE FROM `financial-data-491415.financial_data.eu_xbrl_raw`
WHERE SAFE_CAST(SPLIT(COALESCE(period_end, ''), '-')[OFFSET(0)] AS INT64) > 2026;


-- ────────────────────────────────────────────────────────────
-- FIX 2: Clean non-numeric values from GB data
-- 18,777 rows have non-numeric values (e.g. text descriptions).
-- These break SAFE_CAST and produce NULL financial metrics.
-- We remove rows where value cannot be parsed as a number
-- AND the value is not null (null is handled separately).
-- ────────────────────────────────────────────────────────────
-- (Handled via SAFE_CAST in the view — no deletion needed)


-- ────────────────────────────────────────────────────────────
-- FIX 3: Filter unreliable US data with extreme qtrs values
-- Rows with qtrs > 4 represent multi-year cumulative data or
-- filing errors and should not be treated as single-period data.
-- Keep qtrs IN (0, 1, 2, 3, 4) only.
-- ────────────────────────────────────────────────────────────
DELETE FROM `financial-data-491415.financial_data.us_edgar_raw`
WHERE SAFE_CAST(qtrs AS INT64) > 4;


-- ────────────────────────────────────────────────────────────
-- FIX 4: Remove US rows with null fiscal_year
-- 5% of rows have no fiscal_year. These cannot be placed
-- on a timeline and will cause null aggregation issues.
-- ────────────────────────────────────────────────────────────
-- (Handled via WHERE fiscal_year IS NOT NULL in the view)


-- ────────────────────────────────────────────────────────────
-- FIX 5: Filter extreme outlier values from GB data
-- Values exceeding ±1 trillion are likely data errors
-- (e.g. -85T, 850T found in the data).
-- ────────────────────────────────────────────────────────────
-- (Handled via ABS(value) < 1e12 filter in the unified view)


-- ────────────────────────────────────────────────────────────
-- REBUILD: Recreate all downstream tables after fixes
-- Now run step2_bigquery_queries.sql
-- ────────────────────────────────────────────────────────────
