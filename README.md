# County-Level Housing Price Decline Prediction

Neuefische Data Science Bootcamp — Capstone Project

## Business Question

> "Can we predict, one quarter ahead, which US counties will see a housing price decline greater than 2%, and how much predictive power does mortgage-rate movement (30-year fixed rate level and rate-of-change) add once a county's own price momentum is already known?"

This question is deliberately framed as a *marginal contribution* question rather than a share-of-credit question — mortgage-rate movement and price momentum aren't independent (rate changes influence prices partly through momentum itself), so the analysis measures what rate adds **on top of** momentum, once momentum's own contribution is already established.

## Data Sources

| Source | Grain | What it provides |
|---|---|---|
| Zillow ZHVI (Middle Tier, 33rd-67th percentile, SFR + Condo/Co-op, Smoothed & Seasonally Adjusted) | County, monthly | Home value index — builds the price-decline label and momentum features |
| FRED `MORTGAGE30US` | National, weekly (resampled to monthly) | 30-year fixed mortgage rate — builds rate level, rate-of-change, and interaction features |

Both sources resolve to county FIPS or national scope without a crosswalk file.

## Project Structure

```
data/         raw and processed data (not tracked in git)
notebooks/    one notebook per phase, numbered 01-10 (see Phase Plan below)
src/          reusable Python helper functions (housing_risk package)
outputs/      exported charts, persisted results, and CV fold definitions
docs/         business framing and planning documentation
db/           SQL schema and (gitignored) data exports
```

## Phase Plan

| Phase | What's involved | Notebook(s) |
|---|---|---|
| Phase 0 — Framing | Business question, field scope, evaluation metric, success criteria | `docs/phase0_framing.md` |
| Phase 1 — Ingest/clean | Zillow ingest, FRED ingest, county-FIPS join into `county_month_check` | `01_zillow_ingest_clean.ipynb`, `02_fred_ingest_clean.ipynb`, `02b_fred_resample_sensitivity.ipynb`, `03_join_sql_load.ipynb` |
| Phase 2 — Split | Chronological train/embargo/test split, expanding-window time series CV | `05_split_cv.ipynb` |
| Phase 3 — EDA | Distributions, lag-correlation analysis (training data only) | `06_eda.ipynb` |
| Phase 4 — Feature engineering | Momentum, rate level, rate-of-change, interaction term | `07_feature_engineering.ipynb` |
| Phase 5 — Modeling | Baseline (momentum only) → + rate level → + rate-of-change/interaction → robustness check (second algorithm) | `08_modeling_sequence.ipynb`, `09_robustness_second_algo.ipynb` |
| Phase 6 — Final evaluation | Marginal AUC deltas on the held-out test set, bootstrap confidence intervals, final write-up | `10_final_evaluation.ipynb` |
| Phase 7 — Communication | Dashboard, repo, slides | *(not started)* |

`04_teammate_pandas_comparison.ipynb` is a standalone notebook and isn't part of the numbered phase sequence above.

`00_zhvi_smoothing_check.ipynb` also isn't part of the numbered phase sequence -- it's a foundational leakage-safety check (confirms Zillow's ZHVI smoothing filter is trailing, not centered) that the momentum features in Phase 4 depend on, run once rather than tied to a specific phase.

Success criteria, data provenance figures, and the train/test split live in `docs/phase0_framing.md`.

## Status

- ✅ Phase 0 — Framing
- ✅ Phase 1 — Ingest/clean
- ✅ Phase 2 — Split
- ✅ Phase 3 — EDA
- ✅ Phase 4 — Feature engineering
- ✅ Phase 5 — Modeling
- ✅ Phase 6 — Final evaluation
- 🔲 Phase 7 — Communication (not started)

The empirical check confirming Zillow's ZHVI smoothing filter is trailing rather than centered (i.e. that momentum features don't leak future information) has been run against this project's own downloaded data in `notebooks/00_zhvi_smoothing_check.ipynb` — confirmed trailing, not centered. The full numeric result is saved in `outputs/zhvi_smoothing_check.json`.

## Setup

This project uses a plain Python virtual environment (no Anaconda required):

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```
The last line installs `src/` as an editable package (`housing_risk`), so
notebooks can `from housing_risk.config import get_engine` instead of
redefining the database connection and split/CV cutoff dates in every
notebook.

Create a `.env` file in the project root (never committed — see `.gitignore`) with:
```
PGHOST=...
PGPORT=5432
PGDATABASE=...
PGUSER=...
PGPASSWORD=...
```
