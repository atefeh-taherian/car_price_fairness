import pandas as pd
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parent.parent))

from src.normalize import extract_brand_and_body_style, report_unknown_brands, normalize

BRAND_CONFIG = {
    "brands": ["پژو", "ام وی ام", "بنز", "مرسدس بنز"],
    "aliases": {"مرسدس بنز": "بنز"},
    "body_style_prefixes": ["وانت"],
}


def test_multiword_brand_matched_before_single_token():
    parts = extract_brand_and_body_style("ام وی ام X33 Cross", BRAND_CONFIG)
    assert parts["brand"] == "ام وی ام"
    assert parts["brand_matched"] is True


def test_alias_collapses_to_canonical_brand():
    parts = extract_brand_and_body_style("مرسدس بنز C200", BRAND_CONFIG)
    assert parts["brand"] == "بنز"


def test_pickup_prefix_stripped_and_flagged():
    parts = extract_brand_and_body_style("وانت پژو 405", BRAND_CONFIG)
    assert parts["brand"] == "پژو"
    assert parts["is_pickup"] is True


def test_unknown_brand_falls_back_to_first_token_without_crashing():
    parts = extract_brand_and_body_style("ناشناخته 123 مدل عجیب", BRAND_CONFIG)
    assert parts["brand"] == "ناشناخته"
    assert parts["brand_matched"] is False


def test_report_unknown_brands_flags_unmatched_rows_only():
    df = pd.DataFrame({"brand_model": ["پژو 206", "ناشناخته 123", "پژو 207"]})
    report = report_unknown_brands(df, BRAND_CONFIG)
    assert list(report.index) == ["ناشناخته 123"]
    assert report.iloc[0] == 1


def test_normalize_adds_category_dtype_and_freq_columns():
    df = pd.DataFrame({
        "brand_model": ["پژو 206", "ام وی ام X33"],
        "city": ["تهران", "شیراز"],
        "fuel_type": ["بنزینی", "بنزینی"],
        "Gearbox_type": ["دنده‌ای", "اتوماتیک"],
        "Gearbox_condition": ["سالم", "سالم"],
        "engine_condition": ["سالم", "سالم"],
        "chassis_condition": ["سالم", "سالم"],
        "body_condition": ["بی‌رنگ", "بی‌رنگ"],
        "district": ["۱", "۲"],
        "third_party_insurance": ["۱۲ ماه", None],
    })
    out = normalize(df, BRAND_CONFIG)
    assert str(out["brand"].dtype) == "category"
    assert "brand_freq" in out.columns
    assert out.loc[out["brand_model"] == "پژو 206", "brand"].iloc[0] == "پژو"
