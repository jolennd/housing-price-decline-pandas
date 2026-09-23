-- Run after schema.sql, from this db/ directory, e.g.:
--   psql "$DATABASE_URL" -f schema.sql
--   psql "$DATABASE_URL" -f load.sql
-- \copy runs client-side, so relative paths resolve against the directory
-- psql was launched from -- run psql from inside db/, or use absolute paths.

TRUNCATE zhvi_monthly, county_coverage, mortgage_monthly, county_month;

\copy zhvi_monthly FROM 'data/zhvi_monthly.csv' WITH (FORMAT csv, HEADER true)
\copy county_coverage FROM 'data/county_coverage.csv' WITH (FORMAT csv, HEADER true)
\copy mortgage_monthly FROM 'data/mortgage_monthly.csv' WITH (FORMAT csv, HEADER true)
\copy county_month FROM 'data/county_month.csv' WITH (FORMAT csv, HEADER true)
