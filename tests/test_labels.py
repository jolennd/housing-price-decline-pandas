"""Tests for housing_risk.labels -- the >2% quarterly decline label."""

from __future__ import annotations

import pandas as pd
import pytest

from housing_risk.config import TEST_START, TRAIN_END
from housing_risk.labels import build_quarterly_labels, positive_rate_by_window
from tests.conftest import COUNTY_RISING, COUNTY_STEP, STEP_MONTH


def test_only_calendar_quarter_end_months(county_month):
    labeled = build_quarterly_labels(county_month)
    assert set(labeled["month"].dt.month) <= {3, 6, 9, 12}


def test_decline_label_hand_checked(county_month):
    labeled = build_quarterly_labels(county_month)
    positives = labeled[labeled["decline_label"] == 1]
    # Exactly one positive: COUNTY_STEP's Sep-2020 quarter, 95/100 - 1 = -5%.
    assert len(positives) == 1
    row = positives.iloc[0]
    assert row["county_fips"] == COUNTY_STEP
    assert row["month"] == STEP_MONTH
    assert row["pct_change_qoq"] == pytest.approx(-0.05)


def test_threshold_boundary():
    # Just under 2% is not a decline; just over 2% is. (An exact -2.00% can't
    # be hit through float division -- 98/100 - 1 == -0.020000000000000018 --
    # so the test brackets the threshold instead of sitting on it.)
    months = pd.to_datetime(["2020-03-31", "2020-06-30", "2020-09-30"])
    df = pd.DataFrame(
        {
            "county_fips": ["X"] * 3,
            "month": months,
            "zhvi": [100.0, 98.1, 98.1 * 0.979],  # -1.9%, then -2.1%
        }
    )
    labeled = build_quarterly_labels(df).set_index("month")
    assert labeled.loc["2020-06-30", "decline_label"] == 0
    assert labeled.loc["2020-09-30", "decline_label"] == 1


def test_first_quarter_dropped_but_no_county_dropped(county_month):
    labeled = build_quarterly_labels(county_month)
    assert set(labeled["county_fips"]) == {COUNTY_RISING, COUNTY_STEP}
    # First quarter-end (2019-03-31) has no prior quarter -> dropped.
    assert labeled["month"].min() == pd.Timestamp("2019-06-30")
    assert labeled["pct_change_qoq"].notna().all()
    # 12 quarter-ends per county (2019Q1-2021Q4), minus the first.
    assert labeled.groupby("county_fips").size().eq(11).all()


def test_missing_required_columns_raises(county_month):
    with pytest.raises(AssertionError, match="missing required columns"):
        build_quarterly_labels(county_month.drop(columns=["zhvi"]))


def test_positive_rate_by_window_uses_config_cutoffs():
    months = pd.to_datetime(["2021-06-30", "2021-09-30", "2021-12-31", "2022-03-31"])
    labeled = pd.DataFrame({"month": months, "decline_label": [1, 0, 1, 1]})
    out = positive_rate_by_window(labeled)
    assert out["full_history"] == {"rate": 0.75, "n": 4}
    assert out["train"]["n"] == int((months <= TRAIN_END).sum())
    assert out["train"]["rate"] == pytest.approx(0.5)
    assert out["embargo"]["n"] == 1  # 2021-12-31 only
    assert out["test"]["n"] == int((months >= TEST_START).sum())
