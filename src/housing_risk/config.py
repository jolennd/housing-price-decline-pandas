"""Single source of truth for the Postgres connection and the split/CV cutoffs.

Notebooks import from here instead of redefining these constants inline, so a
change to a cutoff date or a connection default only has to happen once.
"""

from __future__ import annotations

import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

# --- Database connection ---
# Reading from environment variables so credentials never land in a notebook.
# An empty DB_PASSWORD is expected/valid for a local Postgres using
# peer/trust auth (e.g. Homebrew's default for the current OS user on
# localhost) -- not asserted against here for that reason.
load_dotenv()  # loads .env from the project root if present; a no-op if the
                # variables are already set in the shell environment.

DB_USER = os.environ.get("PGUSER", "postgres")
DB_PASSWORD = os.environ.get("PGPASSWORD", "")
DB_HOST = os.environ.get("PGHOST", "localhost")
DB_PORT = os.environ.get("PGPORT", "5432")
DB_NAME = os.environ.get("PGDATABASE", "housing_risk")


def get_engine() -> Engine:
    """Build a fresh SQLAlchemy engine from the connection settings above.

    A function rather than a module-level `engine` constant so each notebook
    gets its own engine instance (SQLAlchemy engines aren't meant to be
    shared across separate connections/sessions casually) and so import time
    never itself opens a connection.
    """
    return create_engine(
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )


# --- Split (Train / Embargo / Test) ---
# Cutoffs are fixed and shared by every notebook that touches the split, so
# they can only be defined in one place: here. See notebook 05 for the
# reasoning behind these specific dates.
TRAIN_END = pd.Timestamp("2021-09-30")
EMBARGO_START = pd.Timestamp("2021-10-01")
EMBARGO_END = pd.Timestamp("2021-12-31")
TEST_START = pd.Timestamp("2022-01-01")
TEST_END = pd.Timestamp("2026-03-31")

# --- Expanding-window cross-validation (notebook 05) ---
QUARTER_END_MONTHS = (3, 6, 9, 12)
CV_INITIAL_TRAIN_QUARTERS = 40  # first fold's minimum training window (~10 years)
CV_FOLD_VAL_QUARTERS = 4        # each fold validates on this many trailing quarters (~1 year)
