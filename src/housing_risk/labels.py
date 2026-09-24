"""Quarterly decline-label logic: the real, permanent home for the label.

**Supersedes `notebooks/06_eda.ipynb`'s Section 5.** That notebook built an
inline throwaway copy of this exact logic before this module existed (it
says so explicitly, to avoid a circular import between a not-yet-written
`labels.py` and the EDA that needed to test against real labels). This
module is that follow-up: the permanent, importable version every later
notebook should use instead of re-deriving the label.

Method, reproduced exactly from `docs/phase0_framing.md`'s Data Provenance
section: county-level ZHVI, resampled to quarter-end (the last observed
value per quarter, selected directly by `month.dt.month.isin
(QUARTER_END_MONTHS)` -- never `pd.offsets.QuarterBegin`/`QuarterEnd`, which
default to fiscal rather than calendar quarters), positive label defined as
a quarter-over-quarter ZHVI decline greater than 2%
(`pct_change_qoq <= -0.02`).
"""

from __future__ import annotations

import pandas as pd

from housing_risk.config import QUARTER_END_MONTHS, TRAIN_END, EMBARGO_START, EMBARGO_END, TEST_START, TEST_END

REQUIRED_COLUMNS = ("county_fips", "month", "zhvi")
DECLINE_THRESHOLD = -0.02


def build_quarterly_labels(county_month: pd.DataFrame) -> pd.DataFrame:
    """One row per (county_fips, quarter-end month) with `pct_change_qoq`
    and `decline_label` (0/1, int).

    `county_month` needs at least `county_fips`, `month`, `zhvi` columns
    (extra columns, e.g. `mortgage_rate`, are ignored -- this function is
    label-only). Rows are reduced to quarter-end months first, then
    quarter-over-quarter percent change is computed per county
    (`groupby("county_fips")["zhvi"].pct_change()`), and `decline_label =
    1` where that change is `<= -0.02`.

    A county's first quarter-end row has no prior quarter to compare
    against and comes back NaN from `pct_change()` -- an expected edge case
    (dropped here, not filled), not a data-quality problem. Per
    `docs/phase0_framing.md`'s Data Requirement, zero counties should be
    dropped *entirely* by this trim (every county has at least one prior
    quarter-end row) -- asserted below, since this pipeline needs no
    geographic crosswalk and any county dropped outright would indicate an
    implementation error, not a genuine geography mismatch.
    """
    missing = set(REQUIRED_COLUMNS) - set(county_month.columns)
    assert not missing, f"county_month is missing required columns: {sorted(missing)}"

    df = county_month[list(REQUIRED_COLUMNS)].copy()
    df["month"] = pd.to_datetime(df["month"])

    quarter_end = df[df["month"].dt.month.isin(QUARTER_END_MONTHS)].copy()
    quarter_end = quarter_end.sort_values(["county_fips", "month"]).reset_index(drop=True)

    quarter_end["pct_change_qoq"] = quarter_end.groupby("county_fips")["zhvi"].pct_change()
    quarter_end["decline_label"] = (quarter_end["pct_change_qoq"] <= DECLINE_THRESHOLD).astype("Int64")

    n_counties_before = quarter_end["county_fips"].nunique()
    labeled = quarter_end.dropna(subset=["pct_change_qoq"]).copy()
    labeled["decline_label"] = labeled["decline_label"].astype(int)
    n_counties_after = labeled["county_fips"].nunique()

    assert n_counties_after == n_counties_before, (
        f"STOP: {n_counties_before - n_counties_after} counties dropped entirely by the "
        "first-quarter-per-county trim -- docs/phase0_framing.md requires zero counties "
        "dropped (this pipeline needs no geographic crosswalk, so a county disappearing "
        "here means an implementation error, not a genuine geography mismatch)."
    )

    return labeled[["county_fips", "month", "pct_change_qoq", "decline_label"]].reset_index(drop=True)


def positive_rate_by_window(
    labeled: pd.DataFrame,
    month_col: str = "month",
    label_col: str = "decline_label",
) -> dict[str, dict]:
    """Positive rate and row count for the four gated windows in
    `docs/phase0_framing.md`'s Data Provenance table (full history, train,
    embargo, test) -- the exact four grains the Model Validation
    Requirements section's per-window data-quality gate applies to, never a
    single blanket tolerance and never a finer (per-year/per-quarter) grain.
    """
    month = pd.to_datetime(labeled[month_col])
    windows = {
        "full_history": pd.Series(True, index=labeled.index),
        "train": month <= TRAIN_END,
        "embargo": (month >= EMBARGO_START) & (month <= EMBARGO_END),
        "test": (month >= TEST_START) & (month <= TEST_END),
    }
    out: dict[str, dict] = {}
    for name, mask in windows.items():
        rows = labeled.loc[mask]
        n = len(rows)
        rate = float(rows[label_col].mean()) if n else float("nan")
        out[name] = {"rate": rate, "n": n}
    return out
