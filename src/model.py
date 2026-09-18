"""
Modeling: a simple group-median baseline, a LightGBM point-estimate model
on log(price), and two LightGBM quantile models (for a price range /
uncertainty estimate). Pure functions -- fit here, save/load handled by
the caller.
"""
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor


# --------------------------------------------------------------------------
# Baseline: hierarchical group median. No leakage risk since a median is
# not the same as a learned model, but it must still be computed on
# TRAIN ONLY and applied to test, exactly like the target encoding.
# --------------------------------------------------------------------------
def fit_baseline(train_df: pd.DataFrame, price_col: str = "asking_price") -> dict:
    global_median = train_df[price_col].median()
    by_brand_model = train_df.groupby("brand_model")[price_col].median()
    by_brand = train_df.groupby("brand")[price_col].median()
    return {
        "global_median": global_median,
        "by_brand_model": by_brand_model.to_dict(),
        "by_brand": by_brand.to_dict(),
    }


def predict_baseline(df: pd.DataFrame, baseline: dict) -> np.ndarray:
    preds = []
    for _, row in df.iterrows():
        if row["brand_model"] in baseline["by_brand_model"]:
            preds.append(baseline["by_brand_model"][row["brand_model"]])
        elif row["brand"] in baseline["by_brand"]:
            preds.append(baseline["by_brand"][row["brand"]])
        else:
            preds.append(baseline["global_median"])
    return np.array(preds)


# --------------------------------------------------------------------------
# Main point-estimate model: LightGBM on log(price), native categoricals.
# --------------------------------------------------------------------------
def train_point_model(X_train: pd.DataFrame, y_log_train: pd.Series, categorical_cols) -> LGBMRegressor:
    model = LGBMRegressor(
        n_estimators=400,
        learning_rate=0.03,
        num_leaves=31,
        min_child_samples=10,   # small dataset -- avoid overfitting to tiny leaves
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X_train, y_log_train, categorical_feature=categorical_cols)
    return model


# --------------------------------------------------------------------------
# Quantile models: give a price RANGE (e.g. 10th-90th percentile of
# log-price), which converts to a Confidence-style uncertainty estimate.
# --------------------------------------------------------------------------
def train_quantile_model(X_train: pd.DataFrame, y_log_train: pd.Series, categorical_cols, alpha: float) -> LGBMRegressor:
    model = LGBMRegressor(
        n_estimators=400,
        learning_rate=0.03,
        num_leaves=15,          # shallower than the point model -- quantile
        min_child_samples=15,   # regression is noisier on a small dataset
        subsample=0.8,
        colsample_bytree=0.8,
        objective="quantile",
        alpha=alpha,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X_train, y_log_train, categorical_feature=categorical_cols)
    return model


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Metrics on the ORIGINAL price scale (Toman), not log scale --
    log-scale error metrics are hard to interpret for a business user."""
    err = y_pred - y_true
    abs_pct_err = np.abs(err) / y_true
    return {
        "MAE": float(np.mean(np.abs(err))),
        "RMSE": float(np.sqrt(np.mean(err ** 2))),
        "MAPE": float(np.mean(abs_pct_err) * 100),
        "median_APE": float(np.median(abs_pct_err) * 100),
        "within_10pct": float(np.mean(abs_pct_err <= 0.10) * 100),
        "within_20pct": float(np.mean(abs_pct_err <= 0.20) * 100),
    }


def evaluate_by_price_segment(y_true: np.ndarray, y_pred: np.ndarray, n_segments: int = 4) -> pd.DataFrame:
    """
    Same metrics as evaluate(), broken out by price quartile (or
    n_segments-tile). Aggregate MAE/RMSE/MAPE are dominated by whichever
    segment has the largest absolute prices -- this shows whether the
    model is actually reliable across the price range or only in the
    common/mid segment, which the aggregate numbers alone hide.
    """
    labels = [f"Q{i+1}" for i in range(n_segments)]
    segment = pd.qcut(y_true, n_segments, labels=labels, duplicates="drop")
    rows = []
    for seg in pd.Categorical(segment).categories:
        mask = segment == seg
        if mask.sum() == 0:
            continue
        m = evaluate(y_true[mask], y_pred[mask])
        m["segment"] = seg
        m["n"] = int(mask.sum())
        m["price_range"] = f"{y_true[mask].min():,.0f} - {y_true[mask].max():,.0f}"
        rows.append(m)
    cols = ["segment", "n", "price_range", "MAE", "RMSE", "MAPE", "median_APE", "within_10pct", "within_20pct"]
    return pd.DataFrame(rows)[cols]


# --------------------------------------------------------------------------
# Conformalized Quantile Regression (CQR): calibrates the [low, high]
# interval from train_quantile_model() so its *empirical* coverage on
# unseen data actually matches the target (e.g. 80%), instead of trusting
# the quantile models' own (often miscalibrated, especially on a small
# dataset) notion of the 10th/90th percentile.
#
# Must be fit on a CALIBRATION set that the quantile models were NOT
# trained on, and that is separate from the final test set used for
# reporting -- otherwise the "calibrated" coverage is just as leaked/
# optimistic as the uncalibrated one was.
# --------------------------------------------------------------------------
def fit_conformal_margin(y_true_log: np.ndarray, low_pred_log: np.ndarray, high_pred_log: np.ndarray,
                          target_coverage: float = 0.8) -> float:
    """
    All three arrays are on the LOG-price scale (same scale the quantile
    models were trained on). Returns a single additive margin (in log
    space) to widen [low, high] by on both sides.
    """
    conformity_scores = np.maximum(low_pred_log - y_true_log, y_true_log - high_pred_log)
    n = len(conformity_scores)
    # finite-sample-corrected quantile level (standard CQR correction)
    q_level = min(1.0, np.ceil((n + 1) * target_coverage) / n)
    margin = np.quantile(conformity_scores, q_level)
    return float(margin)


def apply_conformal_margin(low_pred_log: np.ndarray, high_pred_log: np.ndarray, margin: float):
    return low_pred_log - margin, high_pred_log + margin
