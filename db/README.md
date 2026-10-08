# Local Postgres setup

The pipeline reads and writes a **local** Postgres database, so it runs
without depending on any shared or hosted server.

Files in this `db/` directory:

- `schema.sql` — Postgres DDL for the 4 tables in the optional CSV load
  below.
- `load.sql` — truncates and reloads those 4 tables from `data/*.csv` via
  `\copy`.
- `data/` — where a local CSV export of the tables goes. The CSVs are
  gitignored and **not included in this repository** (to avoid
  redistributing Zillow's data), so this folder is empty in a fresh clone.

## 1. Install Postgres.app

1. Download from https://postgresapp.com (macOS, native app, no Homebrew or
   Docker needed). Any other local Postgres install (for example Homebrew's)
   works too.
2. Drag it to `/Applications`, open it, click **Initialize** to create a new
   server with a default `postgres` database. It runs in your menu bar and
   starts/stops with one click — no background service to manage.
3. Add the command-line tools to your PATH (Postgres.app shows this exact
   line the first time you open it, or run it yourself):
   ```
   sudo mkdir -p /etc/paths.d && echo /Applications/Postgres.app/Contents/Versions/latest/bin | sudo tee /etc/paths.d/postgresapp
   ```
   Open a new terminal tab afterward so `psql` is on PATH.

## 2. Create the database

```bash
createdb housing_risk
```

## 3. Point the project's `.env` at it

Postgres.app's default server has no password and listens on 5432 under
your macOS username. Update (or create) `.env` in the project root
(`housing-price-decline-pandas/.env`, already gitignored):

```
PGHOST=localhost
PGPORT=5432
PGDATABASE=housing_risk
PGUSER=<your macOS username>
PGPASSWORD=
```

## 4. Fill the database

**Standard path (fresh clone):** leave the database empty and run the
notebooks. Notebooks 01 and 02 download the Zillow and FRED data and create
and fill `zhvi_monthly` and `mortgage_monthly`; notebook 03 builds the
joined `county_month_check` table that every later notebook reads.

**Optional shortcut (only with a local CSV export):** if you have the four
CSVs in `db/data/`, you can load them directly instead. Run these from
inside this `db/` directory (the `\copy` paths in `load.sql` are relative to
where `psql` is launched):

```bash
cd db
psql housing_risk -f schema.sql
psql housing_risk -f load.sql
```

`load.sql` prints nothing on success; verify row counts:

```bash
psql housing_risk -c "SELECT 'zhvi_monthly', count(*) FROM zhvi_monthly
                       UNION ALL SELECT 'county_coverage', count(*) FROM county_coverage
                       UNION ALL SELECT 'mortgage_monthly', count(*) FROM mortgage_monthly
                       UNION ALL SELECT 'county_month', count(*) FROM county_month;"
```

Expected (as of the export): zhvi_monthly 709996, county_coverage 3071,
mortgage_monthly 665, county_month 709996.

This load also creates the reference `county_month` table that notebook 03's
final cross-check compares against. Without it, notebook 03 skips that check
with a message instead of failing.

## 5. Connect DBeaver to it (optional)

1. DBeaver → **Database → New Database Connection → PostgreSQL**.
2. Host `localhost`, Port `5432`, Database `housing_risk`, Username your
   macOS username, no password (leave blank) — or set one first with
   `psql housing_risk -c "ALTER USER <you> WITH PASSWORD '...';"` if you'd
   rather not leave it open.
3. Test Connection → Finish.

This server is entirely local, with no dependency on any hosted database.
