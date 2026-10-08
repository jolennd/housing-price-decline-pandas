# Affordability/payment-burden feature

Steps are listed in the order they should be done.

## 1. Record the scope decision

Before writing code, add a short note to `docs/phase0_framing.md` saying the original fixed feature scope (momentum, `MORTGAGE30US` level, rate-of-change, one interaction term) is being extended with one affordability/payment-burden feature, and why (rates act on prices through affordability, per the US Bank article). Record the decision to use the full amortization formula rather than the simple price x rate interaction. The results get documented later in step 12; this step only records the decision, so the change of scope is on paper before any results exist.

Also add a fifth row to `phase0_framing.md`'s existing Success Criteria table (the same table with the Baseline / + rate level / + rate-of-change/interaction / Robustness check rows): a **+ affordability** row, ordered after the existing "+ rate-of-change/interaction" row since this feature is added on top of it, not in place of it. State its target the same way the existing rows do (for example, `ROC-AUC >= step 3 + 0.01, or a stated null result`) before any model sees the feature, for the same reason the project states step 2's and step 3's targets in advance rather than after seeing the result.

## 2. Decide the feature's final form: level vs. change

A dollar payment estimate trends upward with nominal home prices over time, so the same payment level means something different in 2012 than in 2024. In a walk-forward split, later validation folds will sit at payment levels the model never saw in training. Plan to feed the model a change-based version (for example the 12-month % change in estimated payment, or the payment relative to the county's own trailing average) and keep the raw dollar payment only for inspection. Decide this now so the function in step 4 returns the right columns.

## 3. Dependency check

`numpy==2.5.3`, `pandas==3.0.6`, and `scikit-learn==1.9.1` are already pinned in both `requirements.txt` and `requirements.mac.txt`, and the amortization formula only needs pandas arithmetic and the `**` operator, so the feature itself needs nothing new. However, `pytest` is not in either requirements file, and step 5 needs it. Add `pytest` to both requirements files and install it in `.venv`.

## 4. Write the feature function in `features.py`

Implement the full amortization formula with unit conversions (annual rate to monthly, percentage to decimal): payment = P \* r(1+r)^360 / ((1+r)^360 - 1), where r = MORTGAGE30US / 100 / 12. Handle edge cases: a rate of zero (payment = P / 360), missing rate or price values (return NaN, never fill forward silently), and a negative rate (raise an error). Compute it at the monthly level and use the existing `shift_by_calendar_months` and `to_quarter_end` helpers so it follows the same as-of convention as `compute_momentum` and `compute_rate_features`.

Add the new column name(s) to the module-level `FEATURE_COLUMNS` list (not just inside the function), the same way `rate_roc_x_momentum` is already listed there -- this is what makes the feature actually flow through `build_feature_matrix`'s warm-up-drop and column-selection logic, and what `outputs/train_features_meta.json` picks up automatically the next time notebook 07 runs (see step 6).

State an expected sign for the new feature's coefficient in a docstring, the same way `features.py` already states `EXPECTED_INTERACTION_SIGN = "negative"` with the worked-through reasoning above it. The natural hypothesis here is **positive**: a higher estimated payment burden (or a larger increase in it) should raise decline risk, all else equal. Write the reasoning out the same explicit way the interaction term's is written, as its own module-level constant (for example `EXPECTED_AFFORDABILITY_SIGN = "positive"`), so step 10's sign check has a stated target to check against, not an eyeballed one after the fact.

## 5. Create a `tests/` directory with pytest tests

Write the tests right after the function and before wiring it into the notebooks, so a formula bug is caught before any model sees the feature. Include: a test asserting the payment estimate matches a hand-calculated value for a known price and rate; a test for the zero-rate edge case; a test confirming the feature does not use any price or rate value from after the as-of month; and tests for `labels.py` confirming the one-quarter-ahead label alignment.

## 6. Wire it into `07_feature_engineering.ipynb`

Join it onto the existing county-month table and confirm the merge doesn't drop or duplicate rows (row count before and after, and no duplicate county_fips + month pairs). This notebook is also what (re)writes `outputs/train_features_meta.json`, which hardcodes the current `feature_columns` list (currently the six existing features) and `n_rows`/`n_counties`/`positive_rate_pct`. Confirm after running that its `feature_columns` list picked up the new column(s) automatically (from step 4's `FEATURE_COLUMNS` change) and that `n_rows` only shifted by the expected amount (fewer rows if the new feature's own warm-up/history requirement is longer than momentum's 6-month one, unchanged otherwise).

## 7. Distribution check in `07_feature_engineering.ipynb`

Immediately after computing the feature, run `describe()` and plot a histogram. This shows the scale and shape before the feature reaches a model, and is where you'd catch an unexpected zero or negative rate month, or extreme outliers. Do not scale here; the feature stays in its natural units in `features.py` and notebook 07.

## 8. Check it for leakage and alignment

Confirm the feature only uses price and rate values known as of quarter t and that the one-quarter-ahead label alignment still holds. The tests from step 5 cover this automatically; also spot-check a few counties by hand in notebook 07.

## 9. Collinearity check against the existing features

Still in notebook 07, compute correlations (and optionally VIF) between the new feature and the existing momentum, rate level, rate-of-change, and interaction features. The payment estimate is built from price and rate, so it may largely duplicate what those features already carry. If correlation with an existing feature is very high, note it before modeling, since it will make the logistic regression coefficients unstable and hard to interpret.

## 10. Add it as a fourth step in the existing sequence, not a standalone ablation

`08_modeling_sequence.ipynb` already runs a fixed, cumulative sequence -- `baseline` (momentum only) -> `step2_rate_level` -> `step3_rate_change` (+ rate-of-change and the interaction term) -- scored fold-by-fold with a `Pipeline`-internal `StandardScaler` (fit on each fold's training data only, per the leakage rule already in place), and `outputs/baseline_lock.json` locks the baseline's numbers exactly once so step 2's and step 3's targets can't silently move. The affordability feature should become **`step4_affordability`**, added on top of `step3_rate_change` in `feature_steps`/`step_summaries` in `outputs/modeling_sequence_logreg.json`, in `09_robustness_second_algo.ipynb`'s equivalent structure, and in notebook 08's own markdown/section numbering. Do not re-run or re-lock the baseline or step 2/3 numbers; they stay exactly as already recorded, and step 4 is scored the same fold-by-fold way and compared only against step 3, mirroring Section 8's existing "Success criteria check".

Logistic regression (notebook 08) shows whether the feature has a clean, interpretable linear relationship with the decline label. Add a Section 9-style "sign check" for it, refit on the full usable training-period data exactly as the existing interaction-coefficient sign check is, comparing the fitted sign against `EXPECTED_AFFORDABILITY_SIGN` from step 4 -- a positive fitted coefficient confirms the hypothesis; a negative one is a surprise to report, not adjust away, the same way the interaction term's wrong sign was reported rather than hidden. The tree-based second algorithm (notebook 09, `xgboost`) shows whether the signal holds without assuming linearity and whether it appears as an important split; agreement between the two families is the stronger evidence, per `phase0_framing.md`'s Robustness Check row.

## 11. Score step 4 and check the new Success Criteria row

Score `step4_affordability` on the same cross-validated folds as the other steps, with a bootstrap confidence interval on `delta_step4_vs_step3`, exactly as `delta_step3_vs_step2` is already reported -- a delta whose 95% CI includes zero is "no significant marginal contribution," per the project's existing rule, not rounded to a small positive result. Check the result against the Success Criteria row added in step 1. Persist it into `outputs/modeling_sequence_logreg.json` and `outputs/modeling_sequence_xgboost.json` alongside the existing steps (not a separate one-off file), so the full step-by-step history stays in one place the way it already is for steps 2 and 3.

While reviewing this fold-by-fold comparison, also check collinearity and overfitting: whether `step4_affordability`'s train-vs-validation gap is noticeably wider than `step3_rate_change`'s, and whether the affordability feature's correlation with the existing rate/momentum features (step 9's collinearity check) shows up as coefficient instability here.

## 12. Extend the final evaluation the same way, and document the results

`10_final_evaluation.ipynb` already reports the held-out test set the same cumulative-step way (`final_scores_full_feature_set`, `test_step_scores`, `test_deltas`, `robustness_holds_on_test`). Extend that structure with `step4_affordability`'s test-set score and delta, rather than adding a separate write-up section, so the final evaluation stays one continuous table through all four steps. State the outcome plainly, including if it's a null result, exactly as the project already treats step 3's null result as a valid, reportable answer rather than a failure. Then update `docs/phase0_framing.md` (the new Success Criteria row from step 1, now filled in with the actual result) and the README Status section, completing the scope note from step 1.

## 13. Commit

Commit the feature, tests, notebook changes, outputs, and doc updates together, then push from your own terminal with `git push origin main`.
