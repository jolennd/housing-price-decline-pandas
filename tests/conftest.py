"""Shared synthetic fixtures for the test suite.

Every test runs on small, hand-built DataFrames -- never the real Zillow/FRED
data or the Postgres database -- so `make test` is fast, needs no network or
credentials, and each expected value can be checked by hand.
"""

from __future__ import annotations

import pandas as pd
import pytest

COUNTY_RISING = "01001"  # ZHVI rises 1% every month -> never a decline
COUNTY_STEP = "06085"    # ZHVI flat at 100, steps down to 95 in Sep 2020

MONTHS = pd.date_range("2019-01-31", "2021-12-31", freq="ME")
STEP_MONTH = pd.Timestamp("2020-09-30")


@pytest.fixture
def county_month() -> pd.DataFrame:
    """Two counties, Jan 2019 - Dec 2021, month-end dates.

    COUNTY_STEP's only >2% quarterly decline is the quarter ending
    2020-09-30 (95 / 100 - 1 = -5%). Everything else is flat or rising.
    """
    rising = pd.DataFrame(
        {
            "county_fips": COUNTY_RISING,
            "month": MONTHS,
            "zhvi": [100.0 * 1.01**i for i in range(len(MONTHS))],
        }
    )
    step = pd.DataFrame(
        {
            "county_fips": COUNTY_STEP,
            "month": MONTHS,
            "zhvi": [95.0 if m >= STEP_MONTH else 100.0 for m in MONTHS],
        }
    )
    return pd.concat([rising, step], ignore_index=True)


@pytest.fixture
def mortgage_monthly() -> pd.DataFrame:
    """National rate starting a year before the ZHVI data (as the real
    FRED series does), rising 0.1 percentage points per month."""
    months = pd.date_range("2018-01-31", "2021-12-31", freq="ME")
    return pd.DataFrame(
        {"month": months, "mortgage_rate": [3.0 + 0.1 * i for i in range(len(months))]}
    )
