import pickle
from pathlib import Path

import numpy as np
import pandas as pd

from src.features import add_derived_features, apply_target_encoding
from src.comparables import find_comparables

NUMERIC_FEATURES = [
    "car_age", "mileage_km", "mileage_per_year", "insurance_months_left",
    "brand_freq", "brand_model_target_enc", "is_pickup",
]
CATEGORICAL_FEATURES = [
    "brand", "city", "fuel_type", "Gearbox_type", "Gearbox_condition",
    "engine_condition", "chassis_condition", "body_condition",
]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def save_artifacts(directory, point_model, q_low_model, q_high_model,
                    brand_model_enc_map: dict, conformal_margin: float,
                    full_df: pd.DataFrame, reference_year: int):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with open(directory / "artifacts.pkl", "wb") as f:
        pickle.dump({
            "point_model": point_model,
            "q_low_model": q_low_model,
            "q_high_model": q_high_model,
            "brand_model_enc_map": brand_model_enc_map,
            "conformal_margin": conformal_margin,
            "full_df": full_df,
            "reference_year": reference_year,
        }, f)


def load_artifacts(directory) -> dict:
    with open(Path(directory) / "artifacts.pkl", "rb") as f:
        return pickle.load(f)


def estimate_price(car: dict, artifacts: dict) -> dict:
    """
    car: dict with brand_model, brand, city, year_gregorian, mileage_km,
         fuel_type, Gearbox_type, Gearbox_condition, engine_condition,
         chassis_condition, body_condition, is_pickup,
         insurance_months_left (optional), asking_price (optional --
         if given, adds market_position to the result).

    Returns: estimated_price, price_range, confidence,
             comparable_vehicles, and (if asking_price was given)
             asking_price + market_position.
    """
    full_df = artifacts["full_df"]
    reference_year = artifacts["reference_year"]

    row = pd.DataFrame([car])
    row = add_derived_features(row, reference_year)
    row["brand_model_target_enc"] = apply_target_encoding(row, "brand_model", artifacts["brand_model_enc_map"])

    brand_freq_map = full_df.set_index("brand")["brand_freq"].to_dict()
    row["brand_freq"] = row["brand"].map(brand_freq_map).fillna(0)

    for col in NUMERIC_FEATURES:
        if col not in row.columns:
            row[col] = 0
        row[col] = row[col].fillna(full_df[col].median() if col in full_df.columns else 0)
    for col in CATEGORICAL_FEATURES:
        row[col] = row[col].astype("category")

    X_row = row[FEATURES]
    est_price = float(np.exp(artifacts["point_model"].predict(X_row)[0]))
    margin = artifacts["conformal_margin"]
    low_log = artifacts["q_low_model"].predict(X_row)[0] - margin
    high_log = artifacts["q_high_model"].predict(X_row)[0] + margin
    low_price, high_price = float(np.exp(low_log)), float(np.exp(high_log))

    comps = find_comparables(full_df, car, k=5)
    n_same_model = (comps["match_level"] == "same_model").sum() if len(comps) else 0

    interval_width_pct = (high_price - low_price) / est_price
    if n_same_model >= 3 and interval_width_pct < 0.5:
        confidence = "High"
    elif n_same_model >= 1 or interval_width_pct < 0.8:
        confidence = "Medium"
    else:
        confidence = "Low"

    result = {
        "estimated_price": round(est_price),
        "price_range": (round(low_price), round(high_price)),
        "confidence": confidence,
        "comparable_vehicles": comps.to_dict("records"),
    }

    if car.get("asking_price") is not None:
        asking = car["asking_price"]
        if asking < low_price:
            position = "Below Market"
        elif asking > high_price:
            position = "Above Market"
        else:
            position = "Fair"
        result["asking_price"] = asking
        result["market_position"] = position

    return result
