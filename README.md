# Housing Price Decline Risk

## Business Question

> Which US counties will see their home values fall by 2% or more in the next quarter, and
> how much do mortgage rates add once a county's own price momentum is already known?

This project answers that question with a pipeline built in **pandas**, backed by a
**PostgreSQL** database. Python and pandas download and clean the data, split it in time,
build the validation folds, create the labels and features, fit the models and draw the
plots. PostgreSQL stores the cleaned Zillow and FRED tables and builds the joined
county-month table in SQL, so every table can also be opened and queried in DBeaver.

This project is part of a two-person capstone, built and verified on its own. The
[team repository](https://github.com/michobc205/capstone-housing-risk-team) holds the team's
merged pipeline.

This question is deliberately framed as a _marginal contribution_ question rather than a
share-of-credit question — mortgage-rate movement and price momentum aren't independent
(rate changes influence prices partly through momentum itself), so the analysis measures
what rate adds **on top of** momentum, once momentum's own contribution is already
established.

## Results

- **Price momentum alone predicts next-quarter declines well.** On the held-out test
  period (January 2022 to March 2026), the momentum-only model scores a ROC-AUC of 0.86
  (logistic regression) to 0.88 (XGBoost), and a PR-AUC of 0.46 to 0.51 against a decline
  rate of about 8.5%.
- **The 30-year mortgage rate adds nothing measurable on top of momentum.** Neither the
  rate level nor the rate change and its interaction with momentum improved ROC-AUC by the
  pre-registered 0.01 threshold, and no improvement had a 95% confidence interval clear of
  zero. Both algorithms agree. This is a valid null result, allowed for in the success
  criteria before any model was trained.

Full scores, confidence intervals, and the write-up are in
`notebooks/10_final_evaluation.ipynb` and `outputs/final_evaluation.json`.

## Data Sources

| Source                                                                                             | Grain                                   | What it provides                                                                          |
| -------------------------------------------------------------------------------------------------- | --------------------------------------- | ----------------------------------------------------------------------------------------- |
| Zillow ZHVI (Middle Tier, 33rd-67th percentile, SFR + Condo/Co-op, Smoothed & Seasonally Adjusted) | County, monthly                         | Home value index — builds the price-decline label and momentum features                   |
| FRED `MORTGAGE30US`                                                                                | National, weekly (resampled to monthly) | 30-year fixed mortgage rate — builds rate level, rate-of-change, and interaction features |

Both sources resolve to county FIPS or national scope without a crosswalk file.

Data credits: Zillow Home Value Index (ZHVI), [Zillow Research](https://www.zillow.com/research/data/).
30-Year Fixed Rate Mortgage Average in the United States (`MORTGAGE30US`), Freddie Mac,
retrieved from [FRED](https://fred.stlouisfed.org/series/MORTGAGE30US), Federal Reserve
Bank of St. Louis. Neither dataset is redistributed in this repository; the notebooks
download both directly from the source.

## Project Structure

```
data/         raw and processed data (not tracked in git)
notebooks/    one notebook per phase, numbered 00-11 (see Phase Plan below)
src/          reusable Python helper functions (housing_risk package)
tests/        pytest suite for the housing_risk package
outputs/      exported charts, persisted results, and CV fold definitions
docs/         business framing and planning documentation
db/           SQL schema and (gitignored) data exports
```

## Phase Plan

| Phase                         | What's involved                                                                                              | Notebook(s)                                                                                                                   |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| Phase 0 — Framing             | Business question, field scope, evaluation metric, success criteria                                          | `docs/phase0_framing.md`                                                                                                      |
| Phase 1 — Ingest/clean        | Zillow ingest, FRED ingest, county-FIPS join into `county_month_check`                                       | `01_zillow_ingest_clean.ipynb`, `02_fred_ingest_clean.ipynb`, `02b_fred_resample_sensitivity.ipynb`, `03_join_sql_load.ipynb` |
| Phase 2 — Split               | Chronological train/embargo/test split, expanding-window time series CV                                      | `05_split_cv.ipynb`                                                                                                           |
| Phase 3 — EDA                 | Distributions, lag-correlation analysis (training data only)                                                 | `06_eda.ipynb`                                                                                                                |
| Phase 4 — Feature engineering | Momentum, rate level, rate-of-change, interaction term                                                       | `07_feature_engineering.ipynb`                                                                                                |
| Phase 5 — Modeling            | Baseline (momentum only) → + rate level → + rate-of-change/interaction → robustness check (second algorithm) | `08_modeling_sequence.ipynb`, `09_robustness_second_algo.ipynb`                                                               |
| Phase 6 — Final evaluation    | Marginal AUC deltas on the held-out test set, bootstrap confidence intervals, reverse-causation check        | `10_final_evaluation.ipynb`, `11_reverse_causation_check.ipynb`                                                               |
| Phase 7 — Communication       | Dashboard, repo, slides                                                                                      | _(not started)_                                                                                                               |

`04_teammate_pandas_comparison.ipynb` is a standalone notebook and isn't part of the numbered phase sequence above.

`00_zhvi_smoothing_check.ipynb` also isn't part of the numbered phase sequence -- it's a foundational leakage-safety check (confirms Zillow's ZHVI smoothing filter is trailing, not centered) that the momentum features in Phase 4 depend on, run once rather than tied to a specific phase.

`11_reverse_causation_check.ipynb` tests whether the arrow could point the other way (falling prices prompting lower rates). It finds no evidence of that feedback loop beyond chance within the training period.

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
pip install -r requirements.mac.txt   # macOS/Linux
# pip install -r requirements.txt     # Windows (adds the Windows-only pywinpty)
pip install -e .
```

The last line installs `src/` as an editable package (`housing_risk`), so
notebooks can `from housing_risk.config import get_engine` instead of
redefining the database connection and split/CV cutoff dates in every
notebook.

The notebooks need a local PostgreSQL database. `db/README.md` walks through installing
Postgres.app and creating the database; notebooks 01 and 02 then download the data and
create and fill their own tables. No data files are needed in advance.

Create a `.env` file in the project root (never committed — see `.gitignore`) with:

```
PGHOST=...
PGPORT=5432
PGDATABASE=...
PGUSER=...
PGPASSWORD=...
```

## Running

Run the notebooks in order (00 to 11), or use the Makefile:

```
make notebooks      # runs every notebook in dependency order, stopping at the first failure
make notebook-08    # runs a single notebook by its number
make test           # runs the pytest suite (synthetic data only, no database needed)
```
