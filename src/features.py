"""
Feature engineering for the price model.
"""
import numpy as np
import pandas as pd

CATEGORICAL_COLS = [
    "brand", "brand_model", "city", "district", "fuel_type",
    "Gearbox_type", "Gearbox_condition", "engine_condition",
    "chassis_condition", "body_condition",
]


def add_derived_features(df: pd.DataFrame, reference_year: int) -> pd.DataFrame:
    df = df.copy()
    df["car_age"] = (reference_year - df["year_gregorian"]).clip(lower=0)
    df["mileage_per_year"] = df["mileage_km"] / df["car_age"].replace(0, 1)
    df["has_insurance_left"] = df["insurance_months_left"].fillna(0) > 0
    return df


def fit_target_encoding(train_df: pd.DataFrame, col: str, target_col: str, smoothing: float = 10.0) -> dict:
    """
    Smoothed target mean encoding, fit on the training split only.
    smoothing controls how much a category's encoding is pulled toward
    the global mean when it has few observations (protects rare
    categories, e.g. a brand_model seen only once or twice, from
    overfitting to a single noisy price).
    """
    global_mean = train_df[target_col].mean()
    stats = train_df.groupby(col)[target_col].agg(["mean", "count"])
    smoothed = (stats["mean"] * stats["count"] + global_mean * smoothing) / (stats["count"] + smoothing)
    mapping = smoothed.to_dict()
    mapping["__global_mean__"] = global_mean
    return mapping


def apply_target_encoding(df: pd.DataFrame, col: str, mapping: dict, new_col: str = None) -> pd.Series:
    global_mean = mapping.get("__global_mean__")
    new_col = new_col or f"{col}_target_enc"
    return df[col].map(mapping).fillna(global_mean).rename(new_col)


def prepare_model_frame(df: pd.DataFrame, categorical_cols=CATEGORICAL_COLS) -> pd.DataFrame:
    """
    Casts categorical columns back to pandas 'category' dtype (lost on a
    CSV round-trip) so LightGBM can use native categorical splits.
    """
    df = df.copy()
    for col in categorical_cols:
        if col in df.columns:
            df[col] = df[col].astype("category")
    return df
