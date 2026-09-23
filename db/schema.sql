-- Postgres schema for the Housing Price Decline tables, converted from
-- ../../Housing Price Decline/sql/001_schema.sql (SQLite). Column types
-- mapped: SQLite TEXT -> TEXT, REAL -> DOUBLE PRECISION, INTEGER -> INTEGER.
-- Booleans stored as 0/1 in SQLite (has_internal_gap, no_training_presence)
-- are kept as INTEGER here for a byte-for-byte data match; cast to boolean
-- in queries if preferred.

CREATE TABLE IF NOT EXISTS zhvi_monthly (
    county_fips TEXT NOT NULL,
    month       TEXT NOT NULL,
    zhvi        DOUBLE PRECISION,
    region_name TEXT,
    state       TEXT,
    PRIMARY KEY (county_fips, month)
);

CREATE TABLE IF NOT EXISTS county_coverage (
    county_fips          TEXT PRIMARY KEY,
    first_month          TEXT,
    last_month           TEXT,
    n_months             INTEGER,
    n_quarters           INTEGER,
    has_internal_gap     INTEGER,
    n_training_quarters  INTEGER,
    no_training_presence INTEGER
);

CREATE TABLE IF NOT EXISTS mortgage_monthly (
    month         TEXT PRIMARY KEY,
    mortgage_rate DOUBLE PRECISION NOT NULL,
    n_weeks       INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS county_month (
    county_fips   TEXT NOT NULL,
    month         TEXT NOT NULL,
    zhvi          DOUBLE PRECISION,
    mortgage_rate DOUBLE PRECISION,
    PRIMARY KEY (county_fips, month)
);
