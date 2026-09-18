"""
Comparable-vehicle retrieval for a given target car.

Strategy (matches the EDA finding that ~40% of listings have zero
same-model comparables within a tight window):
    1. Try same brand_model, within a year/mileage window -- tightest,
       most trustworthy comparables.
    2. If fewer than `min_k` found, widen the window once.
    3. If still not enough, fall back to same brand (any model), ranked
       by similarity in year/mileage/price -- looser but still relevant.
    4. If brand-level also has nothing, return whatever same-model rows
       exist (even below min_k) rather than nothing at all.
"""
import numpy as np
import pandas as pd


def _score_similarity(candidates: pd.DataFrame, target: dict) -> pd.Series:
    year_diff = (candidates["year_gregorian"] - target["year_gregorian"]).abs()
    mileage_diff = (candidates["mileage_km"] - target["mileage_km"]).abs() / max(target["mileage_km"], 1)
    # lower is better; weights are a modeling choice, not a fixed law --
    # documented here so it's easy to revisit
    return year_diff * 1.0 + mileage_diff * 5.0


def find_comparables(
    df: pd.DataFrame,
    target: dict,
    k: int = 5,
    year_window: int = 2,
    mileage_pct: float = 0.3,
    min_k: int = 3,
    exclude_token: str = None,
) -> pd.DataFrame:
    pool = df if exclude_token is None else df[df["token"] != exclude_token]

    def _same_model_window(yw, mp):
        same_model = pool[pool["brand_model"] == target["brand_model"]]
        year_ok = (same_model["year_gregorian"] - target["year_gregorian"]).abs() <= yw
        mileage_ok = (same_model["mileage_km"] - target["mileage_km"]).abs() <= mp * max(target["mileage_km"], 1)
        return same_model[year_ok & mileage_ok]

    candidates = _same_model_window(year_window, mileage_pct)
    match_level = "same_model"

    if len(candidates) < min_k:
        candidates = _same_model_window(year_window * 2, mileage_pct * 2)
        match_level = "same_model_wide"

    if len(candidates) < min_k:
        same_brand = pool[(pool["brand"] == target["brand"]) & (pool["brand_model"] != target["brand_model"])]
        if len(same_brand) > 0:
            candidates = same_brand
            match_level = "same_brand"

    if len(candidates) == 0:
        return candidates.assign(match_level=[], similarity_score=[])

    candidates = candidates.copy()
    candidates["similarity_score"] = _score_similarity(candidates, target)
    candidates["match_level"] = match_level
    candidates = candidates.sort_values("similarity_score").head(k)

    return candidates[[
        "token", "brand_model", "year_gregorian", "mileage_km", "city",
        "asking_price", "match_level", "similarity_score",
    ]]
