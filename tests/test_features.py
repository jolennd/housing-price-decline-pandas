"""Tests for housing_risk.features.

The most important ones encode the invariants that past bugs broke:
labels come from exactly one quarter after the features (the 2026-09-24
leakage fix), and changing future data never changes past features.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from housing_risk.features import (
    FEATURE_COLUMNS,
    build_feature_matrix,
    compute_momentum,
    compute_rate_features,
    load_rate_roc_lag,
    shift_by_calendar_months,
)
from tests.conftest import COUNTY_RISING, COUNTY_STEP

ROC_LAG = 3  # passed explicitly so tests never depend on outputs/eda_summary.json


# --- shift_by_calendar_months -------------------------------------------------

def test_shift_lands_on_true_month_end():
    df = pd.DataFrame(
        {"month": pd.to_datetime(["2020-01-31", "2020-02-29", "2020-03-31"]), "v": [1.0, 2.0, 3.0]}
    )
    shifted = shift_by_calendar_months(df, "v", -1)
    assert pd.isna(shifted.iloc[0])
    assert shifted.iloc[1:].tolist() == [1.0, 2.0]


def test_shift_stays_within_group_and_gap_gives_nan():
    df = pd.DataFrame(
        {
            "g": ["A", "A", "B", "B"],
            # B is missing 2020-02, so its March value has no 1-month-back value.
            "month": pd.to_datetime(["2020-01-31", "2020-02-29", "2020-01-31", "2020-03-31"]),
            "v": [1.0, 2.0, 10.0, 30.0],
        }
    )
    shifted = shift_by_calendar_months(df, "v", -1, group_col="g")
    assert pd.isna(shifted.iloc[0])
    assert shifted.iloc[1] == 1.0          # A's Feb -> A's Jan, never B's
    assert pd.isna(shifted.iloc[2])
    assert pd.isna(shifted.iloc[3])        # gap -> NaN, not B's Jan value


# --- compute_momentum ---------------------------------------------------------

def test_momentum_values(county_month):
    mom = compute_momentum(county_month).set_index(["county_fips", "month"])
    rising = mom.loc[COUNTY_RISING]
    row = rising.loc["2020-06-30"]
    assert row["momentum_1m"] == pytest.approx(0.01)
    assert row["momentum_3m"] == pytest.approx(1.01**3 - 1)
    assert row["momentum_6m"] == pytest.approx(1.01**6 - 1)
    # 6-month momentum needs 6 prior months: first valid month is 2019-07-31.
    assert rising["momentum_6m"].first_valid_index() == pd.Timestamp("2019-07-31")


# --- compute_rate_features ----------------------------------------------------

def test_rate_features(county_month, mortgage_monthly):
    mom = compute_momentum(county_month)
    out = compute_rate_features(mortgage_monthly, mom, roc_lag_months=ROC_LAG)
    assert len(out) == len(mom)  # left merge onto county-months: no rows added or lost
    row = out[(out["county_fips"] == COUNTY_RISING) & (out["month"] == "2019-01-31")].iloc[0]
    # 2019-01 is index 12 of the rate series (starts 2018-01): 3.0 + 1.2 = 4.2.
    assert row["mortgage_rate_level"] == pytest.approx(4.2)
    # ROC uses rate history from BEFORE the ZHVI data starts (2018-10).
    assert row["mortgage_rate_roc"] == pytest.approx(0.1 * ROC_LAG)
    valid = out.dropna(subset=["mortgage_rate_roc", "momentum_3m"])
    np.testing.assert_allclose(
        valid["rate_roc_x_momentum"], valid["mortgage_rate_roc"] * valid["momentum_3m"]
    )


# --- build_feature_matrix -----------------------------------------------------

@pytest.fixture
def result(county_month, mortgage_monthly):
    return build_feature_matrix(county_month, mortgage_monthly, roc_lag_months=ROC_LAG)


def test_matrix_shape_and_row_accounting(result):
    m = result["matrix"]
    assert list(m.columns) == ["county_fips", "month", *FEATURE_COLUMNS, "decline_label"]
    assert m[FEATURE_COLUMNS].notna().all().all()
    assert not m.duplicated(["county_fips", "month"]).any()
    # Per county: 12 quarter-ends; the last (2021-12) has no next-quarter label;
    # 2019-03 and 2019-06 lack 6 months of momentum history.
    assert result["n_quarter_end_before_label_join"] == 24
    assert result["n_dropped_no_future_label"] == 2
    assert result["n_warmup_dropped"] == 4
    assert len(m) == 18
    assert set(m["county_fips"]) == {COUNTY_RISING, COUNTY_STEP}
    assert result["roc_lag_months"] == ROC_LAG


def test_label_is_one_quarter_ahead(result):
    m = result["matrix"]
    positives = m[m["decline_label"] == 1]
    # The drop is observed at 2020-09-30, so it must be the label of the row
    # whose FEATURES are from 2020-06-30 -- not the 2020-09-30 row itself.
    assert len(positives) == 1
    assert positives.iloc[0]["county_fips"] == COUNTY_STEP
    assert positives.iloc[0]["month"] == pd.Timestamp("2020-06-30")
    # And at 2020-06-30 the features show no hint of the coming drop.
    assert positives.iloc[0]["momentum_3m"] == pytest.approx(0.0)


def test_future_data_never_changes_past_features(county_month, mortgage_monthly, result):
    cutoff = pd.Timestamp("2020-06-30")
    cm = county_month.copy()
    cm.loc[cm["month"] > cutoff, "zhvi"] *= 0.5
    mm = mortgage_monthly.copy()
    mm.loc[mm["month"] > cutoff, "mortgage_rate"] += 5.0
    perturbed = build_feature_matrix(cm, mm, roc_lag_months=ROC_LAG)["matrix"]

    def past(df):
        return df[df["month"] <= cutoff].set_index(["county_fips", "month"])[FEATURE_COLUMNS]

    pd.testing.assert_frame_equal(past(result["matrix"]), past(perturbed))


# --- load_rate_roc_lag --------------------------------------------------------

def test_load_rate_roc_lag_reads_file(tmp_path):
    path = tmp_path / "eda_summary.json"
    path.write_text(json.dumps({"winning_lag_months": 12}))
    assert load_rate_roc_lag(str(path)) == 12


def test_load_rate_roc_lag_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match="06_eda"):
        load_rate_roc_lag(str(tmp_path / "nope.json"))


def test_load_rate_roc_lag_missing_key(tmp_path):
    path = tmp_path / "eda_summary.json"
    path.write_text(json.dumps({}))
    with pytest.raises(KeyError):
        load_rate_roc_lag(str(path))
