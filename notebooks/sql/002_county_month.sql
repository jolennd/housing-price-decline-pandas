-- Zillow is the spine (LEFT JOIN): a month missing from mortgage_monthly should
-- surface as a NULL mortgage_rate, never as a silently dropped county-month row.
--
-- Dropped first so this is safe to re-run: CREATE TABLE ... AS has no "OR
-- REPLACE" form in Postgres, so "IF NOT EXISTS" alone would silently keep
-- whatever rows this table already had from an earlier run, even after
-- zhvi_monthly or mortgage_monthly changed underneath it.
DROP TABLE IF EXISTS county_month_check;

CREATE TABLE county_month_check AS
SELECT z.county_fips, z.month, z.zhvi, m.mortgage_rate
FROM zhvi_monthly AS z
LEFT JOIN mortgage_monthly AS m ON m.month = z.month;
