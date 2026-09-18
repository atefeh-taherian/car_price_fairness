"""
Cleaning pipeline for raw Divar car listing data.

Steps:
    1. Deduplicate on `token`
    2. Drop non-passenger-car listings (rentals, trucks, buses, machinery)
    3. Convert Persian digits -> Latin digits
    4. Parse asking_price_raw -> asking_price (int, Toman)
    5. Parse mileage -> int
    6. Normalize year_raw -> year_jalali, year_gregorian (both int)
    7. Light normalization of free-text fields (whitespace, ZWNJ)
    8. Drop placeholder-price rows (pre-order / installment listings)
    9. Correct extreme-price typos (extra trailing zeros), validated
       against same-family comparables
"""
import re

import numpy as np
import pandas as pd

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
LATIN_DIGITS = "0123456789"
DIGIT_MAP = str.maketrans(PERSIAN_DIGITS, LATIN_DIGITS)

RENTAL_PATTERN = re.compile(r"اجاره|رنت|کرایه", re.UNICODE)

NON_PASSENGER_VEHICLE_TYPES = {
    "کامیون یا کامیونت",
    "اتوبوس یا مینی‌بوس",
    "ماشین‌آلات راه‌سازی",
    "خودروی کشاورزی",
    "سایر",
}

# defaults mirror config/config.yaml -- pass overrides explicitly if the
# notebook loads different values from the config file
DEFAULT_PLACEHOLDER_PRICE_THRESHOLD = 100_000_000   # Toman
DEFAULT_EXTREME_HIGH_THRESHOLD = 100_000_000_000    # Toman
DEFAULT_MILEAGE_HIGH_THRESHOLD = 700_000            # km


def fa_to_en_digits(s):
    if pd.isna(s):
        return s
    return str(s).translate(DIGIT_MAP)


def normalize_text(s):
    if pd.isna(s):
        return s
    s = str(s)
    s = s.replace("\u200c", " ")  # ZWNJ -> space
    s = re.sub(r"\s+", " ", s).strip()
    return s


def parse_price(raw):
    if pd.isna(raw):
        return np.nan
    s = fa_to_en_digits(raw)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else np.nan


def parse_mileage(raw):
    if pd.isna(raw):
        return np.nan
    s = fa_to_en_digits(raw)
    digits = re.sub(r"[^\d]", "", s)
    return int(digits) if digits else np.nan


def parse_year(raw):
    """
    year_raw appears in two observed formats:
      '1405 - 2026'  -> jalali=1405, gregorian=2026
      '2026'         -> gregorian only (new / pre-order listings)
    Returns (year_jalali, year_gregorian) as a tuple of nullable ints.
    """
    if pd.isna(raw):
        return (np.nan, np.nan)
    s = fa_to_en_digits(raw)
    nums = re.findall(r"\d{4}", s)
    if len(nums) == 2:
        return (int(nums[0]), int(nums[1]))
    if len(nums) == 1:
        n = int(nums[0])
        if n > 1600:
            return (n - 621, n)
        return (n, n + 621)
    return (np.nan, np.nan)


def is_rental_or_nonpassenger(row):
    if isinstance(row["vehicle_type"], str) and row["vehicle_type"] in NON_PASSENGER_VEHICLE_TYPES:
        return True
    title = row["title"] if isinstance(row["title"], str) else ""
    return bool(RENTAL_PATTERN.search(title))


def clean(
    df: pd.DataFrame,
    placeholder_price_threshold: int = DEFAULT_PLACEHOLDER_PRICE_THRESHOLD,
    extreme_high_threshold: int = DEFAULT_EXTREME_HIGH_THRESHOLD,
    mileage_high_threshold: int = DEFAULT_MILEAGE_HIGH_THRESHOLD,
):
    """
    Pure transform: takes the raw dataframe, returns
    (cleaned_df, quarantined_placeholder_df). Does not write any files.
    """
    df = df.copy()
    n0 = len(df)

    # 1. Dedup
    df = df.drop_duplicates(subset="token", keep="first")
    n1 = len(df)

    # 2. Drop rentals / non-passenger vehicles
    drop_mask = df.apply(is_rental_or_nonpassenger, axis=1)
    df = df[~drop_mask]
    n2 = len(df)

    # 3-6. Parse numeric fields
    df["asking_price"] = df["asking_price_raw"].apply(parse_price)
    df["mileage_km"] = df["mileage"].apply(parse_mileage)
    years = df["year_raw"].apply(parse_year)
    df["year_jalali"] = years.apply(lambda t: t[0])
    df["year_gregorian"] = years.apply(lambda t: t[1])

    # 7. Text normalization
    for col in ["brand_model", "title", "city", "district", "color"]:
        df[col] = df[col].apply(normalize_text)

    # Drop rows still missing essential modeling fields
    essential = ["brand_model", "asking_price", "year_gregorian"]
    before = len(df)
    df = df.dropna(subset=essential)
    n3 = len(df)

    # 8. Placeholder-price rows: sellers commonly enter a token value
    #    (1000, 10000, 100000 Toman ...) instead of a real asking price,
    #    typically on pre-order / installment / factory-allocation
    #    listings. These are not Asking Price observations for a used
    #    car and are removed rather than treated as low outliers.
    n_before_placeholder = len(df)
    placeholder_mask = df["asking_price"] < placeholder_price_threshold
    quarantined_placeholder = df[placeholder_mask].copy()
    df = df[~placeholder_mask]
    n4 = len(df)

    # 9. Extreme high-side price correction: cross-checked against the
    #    raw asking_price_raw text -- these are genuine seller typos
    #    (extra trailing zeros), not scraper bugs. The correction
    #    (divide by 1000) is only applied if it lands within a plausible
    #    range of same-family comparables; otherwise the row stays
    #    flagged, not silently altered.
    def family_key(bm):
        if not isinstance(bm, str):
            return ""
        return " ".join(bm.split()[:2])

    df["_family"] = df["brand_model"].apply(family_key)
    family_median = df.groupby("_family")["asking_price"].median()

    df["price_corrected"] = False
    df["price_original_raw"] = np.nan
    extreme_idx = df.index[df["asking_price"] > extreme_high_threshold]
    for idx in extreme_idx:
        fam = df.at[idx, "_family"]
        candidate = df.at[idx, "asking_price"] / 1000
        med = family_median.get(fam, np.nan)
        if pd.notna(med) and med > 0 and (0.2 * med <= candidate <= 5 * med):
            df.at[idx, "price_original_raw"] = df.at[idx, "asking_price"]
            df.at[idx, "asking_price"] = candidate
            df.at[idx, "price_corrected"] = True

    df = df.drop(columns=["_family"])
    df["price_flag_extreme_high"] = (df["asking_price"] > extreme_high_threshold) & (~df["price_corrected"])
    df["mileage_flag_high"] = df["mileage_km"] > mileage_high_threshold

    print("Cleaning summary")
    print(f"  raw rows                          : {n0}")
    print(f"  after dedup                       : {n1}  (-{n0 - n1})")
    print(f"  after rental/non-passenger drop    : {n2}  (-{n1 - n2})")
    print(f"  after essential-field dropna       : {n3}  (-{before - n3})")
    print(f"  after placeholder-price drop (<{placeholder_price_threshold:,}): {n4}  (-{n_before_placeholder - n4})")
    print(f"  extreme-high prices corrected (/1000, comparable-validated): {df['price_corrected'].sum()}")
    print(f"  extreme-high prices still flagged (unresolved)   : {df['price_flag_extreme_high'].sum()}")
    print(f"  mileage outlier flags              : {df['mileage_flag_high'].sum()}")

    return df.reset_index(drop=True), quarantined_placeholder.reset_index(drop=True)
