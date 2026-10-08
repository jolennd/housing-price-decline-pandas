# housing-price-decline-pandas -- notebook pipeline
#
# Data lives in a Postgres database (via src/housing_risk/config.py's
# get_engine(), populated by notebooks 01-03), so there is no
# `make data` target here -- ingest is notebooks 01/02/02b, and the
# `county_month_check` table those feed is built and verified by
# notebook 03. Each notebook writes its own inputs for the next one
# (outputs/*.json, outputs/*.csv, data/processed/*.csv), so the
# pipeline's real dependency order is enforced by `make notebooks`
# below, not just by filename numbering.

NBCONVERT := jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800
NOTEBOOK_DIR := notebooks

# 00 runs after 01 because it compares against the smoothed Zillow file that
# 01 downloads; 11 runs last.
NOTEBOOKS := \
	01_zillow_ingest_clean.ipynb \
	00_zhvi_smoothing_check.ipynb \
	02_fred_ingest_clean.ipynb \
	02b_fred_resample_sensitivity.ipynb \
	03_join_sql_load.ipynb \
	04_teammate_pandas_comparison.ipynb \
	05_split_cv.ipynb \
	06_eda.ipynb \
	07_feature_engineering.ipynb \
	08_modeling_sequence.ipynb \
	09_robustness_second_algo.ipynb \
	10_final_evaluation.ipynb \
	11_reverse_causation_check.ipynb

.PHONY: notebooks notebook-% clean-outputs test

# Runs every notebook in dependency order, in-place, stopping immediately
# (and loudly) if any one of them fails -- `jupyter nbconvert --execute`
# raises on a cell error, and `make` stops a `foreach` loop the first time
# a recipe command returns non-zero, so a failed notebook never lets a
# later one run against stale or missing inputs.
notebooks:
	@for nb in $(NOTEBOOKS); do \
		echo "==> Running $(NOTEBOOK_DIR)/$$nb"; \
		$(NBCONVERT) "$(NOTEBOOK_DIR)/$$nb" || { \
			echo "FAILED: $(NOTEBOOK_DIR)/$$nb -- stopping (later notebooks were not run)"; \
			exit 1; \
		}; \
	done
	@echo "All notebooks ran successfully, in order."

# Runs a single notebook by its numeric prefix, e.g. `make notebook-08`.
# Does not enforce that earlier notebooks have already been run -- use
# `make notebooks` for the full, order-enforced pipeline.
notebook-%:
	@nb=$$(ls $(NOTEBOOK_DIR)/$***.ipynb 2>/dev/null | head -1); \
	if [ -z "$$nb" ]; then \
		echo "No notebook found matching $(NOTEBOOK_DIR)/$***.ipynb"; \
		exit 1; \
	fi; \
	$(NBCONVERT) "$$nb"

# Removes this project's persisted intermediate/output files (outputs/*.json,
# outputs/*.csv, data/processed/*.csv) so `make notebooks` can be re-run from
# a clean state. Does not touch data/raw/ (the downloaded source files) or
# the database itself.
clean-outputs:
	rm -f outputs/*.json outputs/*.csv outputs/*.png
	rm -f data/processed/*.csv
	@echo "Cleared outputs/ and data/processed/ (data/raw/ and the database were not touched)."

# Runs the pytest suite in tests/ (config in pyproject.toml). Uses small
# synthetic DataFrames only -- no database, network, or raw data needed.
# `python -m pytest` so it runs under the active .venv's interpreter.
test:
	python -m pytest
