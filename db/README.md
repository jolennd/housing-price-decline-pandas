# Local Postgres setup (independent of the bootcamp server)

These tables were converted from the "Housing Price Decline" project's
SQLite database (`data/processed/housing.db` there) so this team project can
load the same data into a **local** Postgres database — one that keeps
working after the bootcamp's shared server goes away. Nothing here touches
the original SQLite file or that project's folder.

Files in this `db/` directory:

- `schema.sql` — Postgres DDL for the 4 tables (converted from that
  project's `sql/001_schema.sql`).
- `data/*.csv` — a full export of each table (`zhvi_monthly`,
  `county_coverage`, `mortgage_monthly`, `county_month`), ~710k rows in the
  two largest.
- `load.sql` — truncates and reloads all 4 tables from the CSVs via `\copy`.

## 1. Install Postgres.app

1. Download from https://postgresapp.com (macOS, native app, no Homebrew or
   Docker needed).
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

## 3. Load the schema and data

Run these from inside this `db/` directory (the `\copy` paths in `load.sql`
are relative to where `psql` is launched):

```bash
cd "michel-capstone-housing-risk-main/db"
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

Expected: zhvi_monthly 709996, county_coverage 3071, mortgage_monthly 665,
county_month 709996.

## 4. Point the project's `.env` at it

Postgres.app's default server has no password and listens on 5432 under
your macOS username. Update (or create) `.env` in the project root
(`michel-capstone-housing-risk-main/.env`, already gitignored):

```
PGHOST=localhost
PGPORT=5432
PGDATABASE=housing_risk
PGUSER=<your macOS username>
PGPASSWORD=
```

## 5. Connect DBeaver to it (new connection, not the bootcamp one)

1. DBeaver → **Database → New Database Connection → PostgreSQL**.
2. Host `localhost`, Port `5432`, Database `housing_risk`, Username your
   macOS username, no password (leave blank) — or set one first with
   `psql housing_risk -c "ALTER USER <you> WITH PASSWORD '...';"` if you'd
   rather not leave it open.
3. Test Connection → Finish. This is a separate connection entry from the
   bootcamp's `ds-sql-playground...rds.amazonaws.com` one already in your
   DBeaver sidebar — both can stay side by side.

This server is entirely local: it keeps working after the bootcamp ends,
with no dependency on the bootcamp's RDS instance.
