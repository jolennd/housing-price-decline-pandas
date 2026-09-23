-- Zillow is the spine (LEFT JOIN): a month missing from mortgage_monthly should
-- surface as a NULL mortgage_rate, never as a silently dropped county-month row.
CREATE TABLE IF NOT EXISTS county_month_check AS
SELECT z.county_fips, z.month, z.zhvi, m.mortgage_rate
FROM zhvi_monthly AS z
LEFT JOIN mortgage_monthly AS m ON m.month = z.month;
