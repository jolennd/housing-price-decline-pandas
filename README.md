# County-Level Housing Price Decline Prediction

Neuefische Data Science Bootcamp — Capstone Project

## Business Question

> "Can we predict, one quarter ahead, which US counties will see a housing price decline greater than 2%, and how much predictive power does mortgage-rate movement (30-year fixed rate level and rate-of-change) add once a county's own price momentum is already known?"

This question is deliberately framed as a *marginal contribution* question rather than a share-of-credit question — mortgage-rate movement and price momentum aren't independent (rate changes influence prices partly through momentum itself), so the analysis measures what rate adds **on top of** momentum, once momentum's own contribution is already established.

## Data Sources

| Source | Grain | What it provides |
|---|---|---|
| Zillow ZHVI | County, monthly | Home value index — builds the price-decline label and momentum features |
| FRED `MORTGAGE30US` | National, weekly (resampled to monthly) | 30-year fixed mortgage rate — builds rate level, rate-of-change, and interaction features |

Both sources resolve to county FIPS or national scope without a crosswalk file.

## Project Structure

```
data/         raw and processed data (not tracked in git)
notebooks/    one notebook per phase (phase1_zillow_ingest.ipynb, etc.)
src/          reusable Python helper functions
outputs/      exported charts and files
```
## Phase Plan

| Phase | What's involved |
|---|---|
| Phase 0 — Framing | Business question, field scope, evaluation metric, success criteria |
| Phase 1 — Ingest/clean | Zillow + FRED ingest, county-FIPS join, monthly table |
| Feature engineering | Momentum, rate level, rate-of-change, interaction term |
| Phase 2 — EDA | Distributions, lag-correlation analysis |
| Phase 3 — Split | Chronological train/test split, time series CV |
| Phase 6 — Modeling | Baseline (momentum only) → + rate level → + rate-of-change/interaction → robustness check |
| Phase 7 — Evaluation | Marginal AUC deltas, bootstrap confidence intervals |
| Phase 8 — Communication | Streamlit dashboard, repo, slides |

## Status

- ✅ Phase 0 — Framing (complete, see `notebooks/phase0_framing.md`)
- 🔲 Phase 1 — Ingest/clean (not started)
## Setup

This project uses a plain Python virtual environment (no Anaconda required):

```
python -m venv .venv
source .venv/Scripts/activate
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
## Collaboration

Built in parallel with a teammate's own repo — each phase is independently attempted by both, compared, and the better (or merged) version is carried into the shared final repo. Decisions and comparison results are logged as they happen.
