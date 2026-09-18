import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

INPUT_FILE = "data/raw/divar_cars_500.json"
OUTPUT_FILE = "data/raw/divar_cars_structured.json"


# Manual corrections for obvious digit-scale errors identified from comparable listings
MANUAL_PRICE_CORRECTIONS = {
    "gaom_9uQ": {
        "corrected_price": 8_100_000_000,
        "reason": "Manual correction based on comparable listings and apparent digit-scale error."
    }
}


def normalize_digits(text):
    """Convert Persian and Arabic digits to English digits."""
    if text is None:
        return None

    return str(text).translate(
        str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
            "01234567890123456789"
        )
    )


def parse_number(text):
    """Extract the first numeric value from a text field."""
    if not text:
        return None

    text = normalize_digits(text)
    numbers = re.findall(r"\d[\d,]*", text)

    if not numbers:
        return None

    return int(numbers[0].replace(",", ""))


def get_field(data, name):
    """Return the first value matching a field name."""
    for item in data:
        if item["title"] == name:
            return item["value"]

    return None


def parse_year(text):
    """Normalize Jalali/Gregorian year values to a Jalali year."""
    if not text:
        return None

    text = normalize_digits(text)
    years = re.findall(r"\d{4}", text)

    if not years:
        return None

    years = [int(year) for year in years]

    jalali_years = [
        year for year in years
        if 1300 <= year <= 1500
    ]

    gregorian_years = [
        year for year in years
        if 1900 <= year <= 2100
    ]

    if jalali_years:
        return jalali_years[0]

    if gregorian_years:
        return gregorian_years[0] - 621

    return None


def get_price_status(price):
    """Classify price quality without deleting suspicious values."""
    if price is None:
        return "missing"

    if price < 10_000_000:
        return "suspect_low"

    if price > 100_000_000_000:
        return "suspect_high"

    return "valid"


with open(INPUT_FILE, "r", encoding="utf-8") as f:
    records = json.load(f)


output = []

for record in records:

    data = record["data"]

    price_raw = get_field(data, "قیمت پایه")
    original_price = parse_number(price_raw)

    asking_price = original_price
    price_status = get_price_status(original_price)
    price_correction_reason = None

    # Apply manual price correction when a specific listing has been verified
    if record["token"] in MANUAL_PRICE_CORRECTIONS:
        correction = MANUAL_PRICE_CORRECTIONS[record["token"]]

        asking_price = correction["corrected_price"]
        price_status = "manually_corrected"
        price_correction_reason = correction["reason"]

    # Split gearbox type and gearbox condition into separate fields
    gearbox_type = None
    gearbox_condition = None

    for item in data:
        if item["title"] != "گیربکس":
            continue

        value = item["value"]

        if value in ["اتوماتیک", "دنده‌ای"]:
            gearbox_type = value

        elif value in [
            "سالم و پلمپ",
            "تعمیر شده",
            "نیاز به تعمیر جزئی"
        ]:
            gearbox_condition = value

    structured_record = {
        "token": record["token"],
        "title": record["title"],
        "publish_date": record["publish_date"],
        "city": record["city"],
        "district": record["district"],

        "brand_model": get_field(data, "برند و مدل"),

        "year_raw": get_field(data, "مدل (سال تولید)"),
        "year": parse_year(
            get_field(data, "مدل (سال تولید)")
        ),

        "mileage": parse_number(
            get_field(data, "کارکرد")
        ),

        "color": get_field(data, "رنگ"),

        "gearbox_type": gearbox_type,
        "gearbox_condition": gearbox_condition,

        "fuel_type": get_field(data, "نوع سوخت"),

        "engine_condition": get_field(data, "موتور"),

        "chassis_condition": get_field(
            data,
            "وضعیت شاسی‌ها"
        ),

        "body_condition": get_field(
            data,
            "بدنه"
        ),

        "price_raw": price_raw,
        "original_price": original_price,
        "asking_price": asking_price,
        "price_status": price_status,
        "price_correction_reason": price_correction_reason,

        "description": record["description"],
        "url": record["url"],
    }

    output.append(structured_record)


with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(
        output,
        f,
        ensure_ascii=False,
        indent=2
    )


# Print a summary of the resulting dataset
print("=" * 70)
print("STRUCTURED DATASET")
print("=" * 70)

print(f"Records: {len(output)}")

status_counts = {}

for record in output:
    status = record["price_status"]
    status_counts[status] = status_counts.get(status, 0) + 1

print("\nPrice status:")

for status, count in status_counts.items():
    print(f"  {status}: {count}")

manual_corrections = sum(
    1
    for record in output
    if record["price_status"] == "manually_corrected"
)

print(f"\nManual price corrections: {manual_corrections}")

print("\nOutput:")
print(OUTPUT_FILE)