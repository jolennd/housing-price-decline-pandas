"""In-scope feature engineering only, per `docs/phase0_framing.md`'s Field Scope.

**Label/feature alignment (fixed 2026-09-24).** `build_feature_matrix` pairs
each quarter-end's features with `decline_label` from the *following*
quarter-end, not the same one. An earlier version merged features and label
on the identical quarter, which meant `momentum_3m` (zhvi(t) vs zhvi(t-3m))
and `decline_label` (zhvi(t) vs zhvi(t-1 quarter), the same three months)
were measuring the same underlying price change -- the model wasn't
forecasting anything, it was being handed a continuous version of the
answer. `docs/phase0_framing.md`'s business question asks to predict "one
quarter ahead": a row's features must reflect only what's knowable as of
its own month, and its label must describe the outcome in the quarter that
follows, never the quarter already baked into the features.

Feature set (fixed, no other Zillow/FRED series or data source in scope):

1. Lagged ZHVI momentum, 1/3/6-month, per county.
2. `mortgage_rate` level (national, shared across counties each month).
3. `mortgage_rate` rate-of-change at the winning lag identified by
   `notebooks/06_eda.ipynb`'s lag-correlation sweep -- read from
   `outputs/eda_summary.json`'s `winning_lag_months` field at runtime
   (`load_rate_roc_lag`), never hardcoded here, so this module always tracks
   whatever notebook 06 actually found rather than a guess baked in twice.
   As of the last run of notebook 06, that winning lag was 12 months, with
   `sign_matches_hypothesis: false` (the correlation was negative, not the
   positive theory predicted). That face-validity flag is not swept under
   the rug here: the feature is still built exactly as EDA found it (this
   project's Field Scope calls for "the winning lag", not "the lag that
   matches theory"), and the mismatch is worth re-checking at the Model 2
   interaction-term sign check downstream.
4. `rate_roc_x_momentum`: the rate-of-change x prior-3-month-momentum
   interaction term, coded as a **plain product**
   (`mortgage_rate_roc * momentum_3m`), not a transformed/sign-flipped
   version of either input.

Expected sign of the interaction coefficient: **negative.**

Reasoning (worked through for this project's own plain-product coding, not
copied from elsewhere): in a logistic model with both main effects present,
the marginal effect of `mortgage_rate_roc` on decline log-odds is
`b + d * momentum_3m`, where `d` is the interaction coefficient. A county
already losing momentum (`momentum_3m` more negative) should be *more*
sensitive to a given rate increase, i.e. that marginal effect should get
*larger* (more positive, more decline risk) as `momentum_3m` decreases.
`d(effect)/d(momentum_3m) = d`, so "effect increases as momentum_3m
decreases" requires `d < 0`. This holds under a plain product regardless of
which lag `mortgage_rate_roc` itself is computed at (point 3 above), since
the sign logic is about the interaction with momentum, not about the
rate-of-change lag choice. A positive fitted coefficient would therefore
contradict the stated theory and should be reported as a surprise, not
treated as a confirmation.
"""

from __future__ import annotations

import json
import os

import pandas as pd

from housing_risk.config import QUARTER_END_MONTHS
from housing_risk.labels import build_quarterly_labels

MOMENTUM_LAGS_MONTHS = (1, 3, 6)
INTERACTION_MOMENTUM_COL = "momentum_3m"
EXPECTED_INTERACTION_SIGN = "negative"

FEATURE_COLUMNS = [
    "momentum_1m",
    "momentum_3m",
    "momentum_6m",
    "mortgage_rate_level",
    "mortgage_rate_roc",
    "rate_roc_x_momentum",
]

_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
EDA_SUMMARY_PATH_DEFAULT = os.path.normpath(
    os.path.join(_MODULE_DIR, "..", "..", "outputs", "eda_summary.json")
)


def load_rate_roc_lag(path: str = EDA_SUMMARY_PATH_DEFAULT) -> int:
    """`winning_lag_months` from `notebooks/06_eda.ipynb`'s persisted EDA
    summary. Raises loudly (rather than silently defaulting to a guessed
    lag) if that notebook hasn't been run yet.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found -- run notebooks/06_eda.ipynb first; it persists "
            "outputs/eda_summary.json with the winning rate-of-change lag "
            "('winning_lag_months') that this module reads."
        )
    with open(path) as fh:
        summary = json.load(fh)
    if "winning_lag_months" not in summary:
        raise KeyError(
            f"{path} has no 'winning_lag_months' key -- rerun notebooks/06_eda.ipynb, "
            "its Section 10 persists this key."
        )
    return int(summary["winning_lag_months"])


def shift_by_calendar_months(
    df: pd.DataFrame,
    value_col: str,
    n: int,
    group_col: str | None = None,
    month_col: str = "month",
) -> pd.Series:
    """`df[value_col]` reindexed `n` calendar months ahead (n>0) or behind
    (n<0) of each row's own `month_col`, optionally within groups of
    `group_col` (e.g. `county_fips`).

    Adapted from `notebooks/06_eda.ipynb`'s `shift_by_calendar_months`
    (Section 4), generalized to operate on a full DataFrame with an
    optional per-group key instead of a single national `pd.Series`, which
    momentum needs (per-county) and the national rate-of-change doesn't
    (`group_col=None`). Uses `PeriodIndex` (month-granularity integer)
    arithmetic rather than `pd.DateOffset`/`pd.Timedelta` on the raw dates,
    for the same reason notebook 06 does: `DateOffset` applied to a
    month-*end* date preserves day-of-month and only clips, so it does not
    reliably land on another month-end (`2020-06-30 - DateOffset(months=1)`
    -> `2020-05-30`, not the real `2020-05-31`). NaN where the shifted
    (group, month) isn't present in `df` -- an internal gap never silently
    pulls in the wrong month's value.
    """
    periods = pd.to_datetime(df[month_col]).dt.to_period("M")
    if group_col is not None:
        key = pd.MultiIndex.from_arrays([df[group_col].to_numpy(), periods.to_numpy()])
        target = pd.MultiIndex.from_arrays([df[group_col].to_numpy(), (periods + n).to_numpy()])
    else:
        key = pd.Index(periods.to_numpy())
        target = pd.Index((periods + n).to_numpy())
    lookup = pd.Series(df[value_col].to_numpy(), index=key)
    lookup = lookup[~lookup.index.duplicated(keep="first")]
    shifted = lookup.reindex(target)
    return pd.Series(shifted.to_numpy(), index=df.index, name=f"{value_col}_shift_{n}")


# --- Synthetic sanity check on shift_by_calendar_months, run at import time,
# mirroring notebook 06's "verify before trusting against real data" practice ---
def _check_shift_by_calendar_months() -> None:
    idx = pd.to_datetime(["2020-04-30", "2020-05-31", "2020-06-30", "2020-07-31"])
    check_df = pd.DataFrame({"month": idx, "value": [1.0, 2.0, 3.0, 4.0]})
    shifted_back_1 = shift_by_calendar_months(check_df, "value", -1)
    assert shifted_back_1.iloc[2] == 2.0, (
        "date-shift bug: 2020-06-30 shifted back 1 month should land on the value at "
        "2020-05-31 (2.0), not misalign to 2020-05-30 and return NaN."
    )
    assert pd.isna(shifted_back_1.iloc[0]), (
        "the earliest row has no value 1 month behind it and should be NaN, not silently filled."
    )


_check_shift_by_calendar_months()


def compute_momentum(county_month: pd.DataFrame) -> pd.DataFrame:
    """`momentum_1m`/`momentum_3m`/`momentum_6m` per (county_fips, month),
    calendar-month lag joins (`shift_by_calendar_months`, never a row-offset
    shift, so a gap in a county's series yields a correctly-NaN lag instead
    of silently pulling in the wrong month's ZHVI).

    Momentum is a fraction, e.g. 0.02 == +2% -- `zhvi(t) / zhvi(t-k) - 1`.
    """
    df = county_month[["county_fips", "month", "zhvi"]].copy()
    df["month"] = pd.to_datetime(df["month"])
    df = df.sort_values(["county_fips", "month"]).reset_index(drop=True)

    out = df[["county_fips", "month"]].copy()
    for k in MOMENTUM_LAGS_MONTHS:
        past_zhvi = shift_by_calendar_months(df, "zhvi", -k, group_col="county_fips")
        out[f"momentum_{k}m"] = df["zhvi"].to_numpy() / past_zhvi.to_numpy() - 1
    return out


def compute_rate_features(
    monthly_rate: pd.DataFrame,
    county_momentum: pd.DataFrame,
    roc_lag_months: int | None = None,
) -> pd.DataFrame:
    """Build `mortgage_rate_level`, `mortgage_rate_roc`, and
    `rate_roc_x_momentum` at county-month grain, merged onto
    `county_momentum`.

    `monthly_rate` (columns `month`, `mortgage_rate`) is a national series
    with no county dimension, taken as an explicit argument rather than
    read from a table directly, so the rate-of-change window can be swept
    or overridden without touching this function. `roc_lag_months` defaults
    to `load_rate_roc_lag()` (notebook 06's winning lag) when not passed.
    Rate level/rate-of-change are computed on `monthly_rate`'s *full*
    history (which starts well before Zillow's coverage) so no rate-side
    warm-up months are lost before the merge -- any row not needed
    downstream is dropped naturally by the merge onto `county_momentum`'s
    (county_fips, month) grain.
    """
    if roc_lag_months is None:
        roc_lag_months = load_rate_roc_lag()

    rate = monthly_rate[["month", "mortgage_rate"]].copy()
    rate["month"] = pd.to_datetime(rate["month"])
    rate = rate.sort_values("month").reset_index(drop=True)

    past_rate = shift_by_calendar_months(rate, "mortgage_rate", -roc_lag_months)
    rate_feat = pd.DataFrame(
        {
            "month": rate["month"],
            "mortgage_rate_level": rate["mortgage_rate"].to_numpy(),
            "mortgage_rate_roc": rate["mortgage_rate"].to_numpy() - past_rate.to_numpy(),
        }
    )

    merged = county_momentum.merge(rate_feat, on="month", how="left")
    merged["rate_roc_x_momentum"] = merged["mortgage_rate_roc"] * merged[INTERACTION_MOMENTUM_COL]
    return merged


def to_quarter_end(df: pd.DataFrame, month_col: str = "month") -> pd.DataFrame:
    """Rows whose `month_col` falls in `QUARTER_END_MONTHS` (Mar/Jun/Sep/Dec)."""
    is_quarter_end = pd.to_datetime(df[month_col]).dt.month.isin(QUARTER_END_MONTHS)
    return df.loc[is_quarter_end].copy()


def build_feature_matrix(
    county_month: pd.DataFrame,
    mortgage_monthly: pd.DataFrame,
    roc_lag_months: int | None = None,
) -> dict:
    """Compose momentum, rate features (level/ROC/interaction), and the real
    decline label (via `housing_risk.labels.build_quarterly_labels`);
    reduce to quarter-end rows; drop rows without a full lag history.

    Per `docs/phase0_framing.md`'s Data Requirement, each county-quarter row
    needs at least 2 quarters (6 months) of prior history to compute
    `momentum_6m`, the longest lag in scope -- the only exclusion this
    pipeline applies, counted and reported (`n_warmup_dropped`) rather than
    silently dropped. A row that also lacks a `decline_label` (no prior
    quarter to compute `pct_change_qoq` from -- `labels.build_quarterly_labels`
    already trims those) is excluded by the inner merge below; the momentum
    warm-up requirement is strictly longer (6 months vs. 1 quarter), so it's
    the binding constraint in practice.

    Returns a dict: `matrix` (columns `county_fips`, `month`,
    `FEATURE_COLUMNS`, `decline_label`), `n_quarter_end_before_label_join`
    (quarter-end feature rows before joining a future-quarter label onto
    them), `n_dropped_no_future_label` (rows dropped because no "one
    quarter later" label exists in the `county_month` passed in -- expected
    at the trailing edge of whatever window was loaded, see the merge step
    below), `n_quarter_end_rows` (rows remaining after that join, before the
    momentum warm-up drop), `n_warmup_dropped`, `roc_lag_months` (the lag
    actually used).
    """
    if roc_lag_months is None:
        roc_lag_months = load_rate_roc_lag()

    momentum = compute_momentum(county_month)
    with_rate = compute_rate_features(mortgage_monthly, momentum, roc_lag_months=roc_lag_months)
    quarterly_features = to_quarter_end(with_rate)
    n_quarter_end_before_label_join = len(quarterly_features)

    label_df = build_quarterly_labels(county_month)

    # Shift each label row back one quarter (3 calendar months) onto the
    # quarter-end its OWN features should have been measured at. label_df's
    # "month" is when the decline is observed (zhvi(month) vs
    # zhvi(month - 1 quarter)); after this shift, "feature_month" is that
    # prior quarter-end -- the row where features are joined from below.
    # PeriodIndex arithmetic, not pd.DateOffset, for the same month-end
    # reason as shift_by_calendar_months above.
    label_df = label_df.copy()
    label_periods = pd.to_datetime(label_df["month"]).dt.to_period("M")
    label_df["feature_month"] = (label_periods - 3).dt.to_timestamp(how="end").dt.floor("D")

    merged = quarterly_features.merge(
        label_df[["county_fips", "feature_month", "decline_label", "month"]].rename(
            columns={"month": "label_month"}
        ),
        left_on=["county_fips", "month"],
        right_on=["county_fips", "feature_month"],
        how="inner",  # a features quarter with no later label (e.g. the last
                       # available quarter in the county_month passed in --
                       # its "one quarter ahead" outcome isn't in the data)
                       # or a label with no earlier features (the first) is
                       # correctly dropped, not filled.
    ).drop(columns=["feature_month"])

    # How many quarter-end rows survived the label join vs. how many quarter-end
    # feature rows existed before it. If `county_month` was loaded only through
    # some cutoff (e.g. notebook 07 loads through TRAIN_END, notebook 10 through
    # TEST_END), the LAST quarter-end in that data has no "one quarter later"
    # label available -- it was never loaded -- so it drops out here. This is a
    # real, expected consequence of predicting one quarter ahead (see this
    # module's docstring), not a bug: distinct from, and in addition to, the
    # momentum warm-up drop counted below.
    n_dropped_no_future_label = n_quarter_end_before_label_join - len(merged)

    # Sanity check: every surviving row's label really does come from exactly
    # one calendar quarter after its own features -- never the same quarter,
    # never two quarters out. label_month was carried through the merge above
    # purely to check this; dropped right after.
    if len(merged):
        # Period subtraction returns a MonthEnd offset object, not a plain
        # int (`pd.Period("2019-12", "M") - pd.Period("2019-09", "M")` is
        # `<3 * MonthEnds>`, not `3`) -- ordinals are compared instead so
        # "one quarter" reliably means "3 months", not an always-false
        # object comparison against `1`.
        features_ordinal = pd.to_datetime(merged["month"]).dt.to_period("M").astype("int64")
        label_ordinal = pd.to_datetime(merged["label_month"]).dt.to_period("M").astype("int64")
        assert (label_ordinal - features_ordinal == 3).all(), (
            "label/feature alignment bug: at least one row's decline_label isn't "
            "exactly one calendar quarter (3 months) after its own features' month."
        )
    merged = merged.drop(columns=["label_month"])

    n_quarter_end_rows = len(merged)
    warmup_mask = merged[FEATURE_COLUMNS].isna().any(axis=1)
    n_warmup_dropped = int(warmup_mask.sum())
    final = merged.loc[~warmup_mask].copy()
    final["decline_label"] = final["decline_label"].astype(int)
    final = final[["county_fips", "month", *FEATURE_COLUMNS, "decline_label"]]
    final = final.sort_values(["county_fips", "month"]).reset_index(drop=True)

    return {
        "matrix": final,
        "n_quarter_end_before_label_join": n_quarter_end_before_label_join,
        "n_dropped_no_future_label": n_dropped_no_future_label,
        "n_quarter_end_rows": n_quarter_end_rows,
        "n_warmup_dropped": n_warmup_dropped,
        "roc_lag_months": roc_lag_months,
    }
