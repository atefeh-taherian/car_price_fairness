"""
Normalization pipeline: brand extraction from the free-text `brand_model`
field, plus categorical typing/encoding for downstream modeling.

Design notes
------------
`brand_model` is free text scraped from listing titles/fields, e.g.:
    "Peugeot 206 Tip 2"
    "Toyota Corolla Cross Hybrid 2L"
    "MVM X33 Cross automatic"

Brand extraction matches against the brand list by LONGEST prefix so
multi-word brands aren't cut short. If no known brand matches, the first
token is used as a fallback brand -- this keeps the pipeline from
crashing or silently dropping rows on unseen brands.

`model` / `trim` are NOT split out here: splitting
free text into model + trim reliably needs a much larger override table
per brand and breaks easily on new listings. brand_model is kept as a
single normalized string and left for tree-based models / frequency
encoding to learn from directly.
"""
import re

import numpy as np
import pandas as pd

# All categorical columns are kept as pandas 'category' dtype (native
# support in LightGBM/CatBoost -- the model splits on subsets of
# categories directly, with no false ordinal relationship and no
# dimensionality blow-up). A frequency-encoded numeric column is added
# alongside each one as a fallback for any model without native
# categorical support.

CATEGORICAL_COLS = [
    "brand", "district", "city", "fuel_type", "Gearbox_type",
    "Gearbox_condition", "engine_condition", "chassis_condition",
    "body_condition",
]


def _sorted_brands(brand_config: dict):
    return sorted(set(brand_config["brands"]), key=len, reverse=True)


def find_brand(text: str, brand_config: dict):
    for b in _sorted_brands(brand_config):
        if text.startswith(b):
            return b
    return None


def extract_brand_and_body_style(raw, brand_config: dict):
    """
    Returns (brand, is_pickup, brand_matched).
    brand_matched=False means the brand list did not recognize this text
    and the first token was used as a fallback -- see
    report_unknown_brands() to review these in bulk.
    """
    if not isinstance(raw, str) or not raw.strip():
        return pd.Series({"brand": np.nan, "is_pickup": False, "brand_matched": False})

    text = raw.strip()

    is_pickup = False
    for prefix in brand_config.get("body_style_prefixes", []):
        if text.startswith(prefix):
            is_pickup = True
            text = text[len(prefix):].strip()
            break

    brand = find_brand(text, brand_config)
    if brand is None:
        tokens = text.split()
        fallback_brand = tokens[0] if tokens else np.nan
        return pd.Series({"brand": fallback_brand, "is_pickup": is_pickup, "brand_matched": False})

    aliases = brand_config.get("aliases", {})
    brand = aliases.get(brand, brand)
    return pd.Series({"brand": brand, "is_pickup": is_pickup, "brand_matched": True})


def report_unknown_brands(df: pd.DataFrame, brand_config: dict) -> pd.Series:
    """
    Run this after normalizing new data. Returns value counts of the raw
    brand_model text for rows where no brand in brand_config matched
    (i.e. the fallback path was used) -- these are exactly the entries
    worth reviewing before adding to config/brands.yaml.
    """
    parts = df["brand_model"].apply(lambda x: extract_brand_and_body_style(x, brand_config))
    unmatched = df.loc[~parts["brand_matched"], "brand_model"]
    return unmatched.value_counts()


def parse_insurance_months(raw):
    """'12 months' style field -> int months of third-party insurance left."""
    if pd.isna(raw):
        return np.nan
    s = str(raw).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    m = re.search(r"\d+", s)
    return int(m.group()) if m else np.nan


def normalize(df: pd.DataFrame, brand_config: dict) -> pd.DataFrame:
    """Pure transform: takes the cleaned dataframe + brand config (loaded
    from config/brands.yaml by the caller), returns the normalized +
    typed/encoded dataframe. Does not write any files."""
    df = df.copy()

    parts = df["brand_model"].apply(lambda x: extract_brand_and_body_style(x, brand_config))
    df = pd.concat([df, parts], axis=1)

    df["insurance_months_left"] = df["third_party_insurance"].apply(parse_insurance_months)

    for col in CATEGORICAL_COLS:
        if col in df.columns:
            df[col] = df[col].astype("category")

    for col in CATEGORICAL_COLS:
        if col in df.columns:
            freq = df[col].value_counts(normalize=True)
            df[f"{col}_freq"] = df[col].map(freq)

    return df
