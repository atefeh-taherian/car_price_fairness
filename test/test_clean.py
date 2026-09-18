import pandas as pd
import numpy as np
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from src.clean import clean


def make_raw_row(**overrides):
    row = {
        "token": "tok1",
        "title": "پژو 206 تیپ 2",
        "city": "تهران",
        "district": "منطقه ۱",
        "brand_model": "پژو 206 تیپ 2",
        "year_raw": "۱۳۹۹ - ۲۰۲۰",
        "mileage": "۸۰,۰۰۰",
        "color": "سفید",
        "asking_price_raw": "‏۱,۰۰۰,۰۰۰,۰۰۰ تومان",
        "fuel_type": "بنزینی",
        "vehicle_type": np.nan,
    }
    row.update(overrides)
    return row


def make_raw_df(rows):
    return pd.DataFrame(rows)


def test_dedup_removes_repeated_token():
    df = make_raw_df([make_raw_row(token="a"), make_raw_row(token="a"), make_raw_row(token="b")])
    cleaned, _ = clean(df)
    assert len(cleaned) == 2


def test_rental_listing_is_dropped():
    df = make_raw_df([
        make_raw_row(token="a", title="اجاره خودرو پراید"),
        make_raw_row(token="b", title="فروش پراید صندوق‌دار"),
    ])
    cleaned, _ = clean(df)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["token"] == "b"


def test_non_passenger_vehicle_type_is_dropped():
    df = make_raw_df([
        make_raw_row(token="a", vehicle_type="کامیون یا کامیونت"),
        make_raw_row(token="b", vehicle_type=np.nan),
    ])
    cleaned, _ = clean(df)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["token"] == "b"


def test_placeholder_price_is_dropped_and_quarantined():
    df = make_raw_df([
        make_raw_row(token="a", asking_price_raw="۱۰,۰۰۰ تومان"),   # placeholder
        make_raw_row(token="b", asking_price_raw="۱,۰۰۰,۰۰۰,۰۰۰ تومان"),  # real
    ])
    cleaned, quarantined = clean(df, placeholder_price_threshold=100_000_000)
    assert len(cleaned) == 1
    assert cleaned.iloc[0]["token"] == "b"
    assert len(quarantined) == 1
    assert quarantined.iloc[0]["token"] == "a"


def test_extreme_price_typo_is_corrected_when_comparables_agree():
    # 3 normal-priced Peugeot 206 listings + 1 with 3 extra trailing zeros
    rows = [make_raw_row(token=f"n{i}", asking_price_raw="۱,۰۰۰,۰۰۰,۰۰۰ تومان") for i in range(3)]
    rows.append(make_raw_row(token="typo", asking_price_raw="۱,۰۰۰,۰۰۰,۰۰۰,۰۰۰ تومان"))
    df = make_raw_df(rows)
    cleaned, _ = clean(df, extreme_high_threshold=100_000_000_000)
    typo_row = cleaned[cleaned["token"] == "typo"].iloc[0]
    assert bool(typo_row["price_corrected"]) is True
    assert typo_row["asking_price"] == 1_000_000_000


def test_year_parsing_handles_dual_and_single_formats():
    df = make_raw_df([
        make_raw_row(token="a", year_raw="۱۳۹۹ - ۲۰۲۰"),
        make_raw_row(token="b", year_raw="۲۰۲۶"),
    ])
    cleaned, _ = clean(df)
    row_a = cleaned[cleaned["token"] == "a"].iloc[0]
    row_b = cleaned[cleaned["token"] == "b"].iloc[0]
    assert row_a["year_jalali"] == 1399
    assert row_a["year_gregorian"] == 2020
    assert row_b["year_gregorian"] == 2026
