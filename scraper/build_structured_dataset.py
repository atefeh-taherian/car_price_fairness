import json
import re
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")

INPUT_FILE = "data/raw/divar_cars_raw_unique.json"
OUTPUT_DIR = "data/processed"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "divar_cars_structured.json"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)


FIELD_BRAND_MODEL = "\u0628\u0631\u0646\u062f \u0648 \u0645\u062f\u0644"
FIELD_YEAR = "\u0645\u062f\u0644 (\u0633\u0627\u0644 \u062a\u0648\u0644\u06cc\u062f)"
FIELD_MILEAGE = "\u06a9\u0627\u0631\u06a9\u0631\u062f"
FIELD_COLOR = "\u0631\u0646\u06af"
FIELD_GEARBOX = "\u06af\u06cc\u0631\u0628\u06a9\u0633"
FIELD_FUEL = "\u0646\u0648\u0639 \u0633\u0648\u062e\u062a"
FIELD_ENGINE = "\u0645\u0648\u062a\u0648\u0631"
FIELD_CHASSIS = "\u0648\u0636\u0639\u06cc\u062a \u0634\u0627\u0633\u06cc\u200c\u0647\u0627"
FIELD_BODY = "\u0628\u062f\u0646\u0647"
FIELD_PRICE = "\u0642\u06cc\u0645\u062a \u067e\u0627\u06cc\u0647"


GEARBOX_AUTOMATIC = "\u0627\u062a\u0648\u0645\u0627\u062a\u06cc\u06a9"
GEARBOX_MANUAL = "\u062f\u0646\u062f\u0647\u200c\u0627\u06cc"

GEARBOX_GOOD = "\u0633\u0627\u0644\u0645 \u0648 \u067e\u0644\u0645\u067e"
GEARBOX_REPAIRED = "\u062a\u0639\u0645\u06cc\u0631 \u0634\u062f\u0647"
GEARBOX_MINOR_REPAIR = "\u0646\u06cc\u0627\u0632 \u0628\u0647 \u062a\u0639\u0645\u06cc\u0631 \u062c\u0632\u0626\u06cc"


def normalize_digits(text):
    if text is None:
        return None

    return str(text).translate(
        str.maketrans(
            "\u06f0\u06f1\u06f2\u06f3\u06f4\u06f5\u06f6\u06f7\u06f8\u06f9"
            "\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669",
            "01234567890123456789"
        )
    )


def parse_number(text):
    if not text:
        return None

    text = normalize_digits(text)

    numbers = re.findall(
        r"\d[\d,]*",
        text
    )

    if not numbers:
        return None

    return int(
        numbers[0].replace(",", "")
    )


def get_field(data, field_name):
    for item in data:
        if item.get("title") == field_name:
            return item.get("value")

    return None


def parse_year(text):
    if not text:
        return None

    text = normalize_digits(text)

    years = re.findall(
        r"\d{4}",
        text
    )

    if not years:
        return None

    years = [
        int(year)
        for year in years
    ]

    jalali_years = [
        year
        for year in years
        if 1300 <= year <= 1500
    ]

    gregorian_years = [
        year
        for year in years
        if 1900 <= year <= 2100
    ]

    if jalali_years:
        return jalali_years[0]

    if gregorian_years:
        return gregorian_years[0] - 621

    return None


def parse_publish_date(text):
    if not text:
        return None

    return text


def classify_price(price):
    if price is None:
        return "missing"

    if price < 10_000_000:
        return "suspect_low"

    if price > 100_000_000_000:
        return "suspect_high"

    return "valid"


def extract_gearbox(data):
    gearbox_type = None
    gearbox_condition = None

    for item in data:

        if item.get("title") != FIELD_GEARBOX:
            continue

        value = item.get("value")

        if value in [
            GEARBOX_AUTOMATIC,
            GEARBOX_MANUAL
        ]:
            gearbox_type = value

        elif value in [
            GEARBOX_GOOD,
            GEARBOX_REPAIRED,
            GEARBOX_MINOR_REPAIR
        ]:
            gearbox_condition = value

    return gearbox_type, gearbox_condition


with open(INPUT_FILE, "r", encoding="utf-8") as file:
    records = json.load(file)


structured_records = []


for record in records:

    data = record.get("data", [])

    price_raw = get_field(
        data,
        FIELD_PRICE
    )

    original_price = parse_number(
        price_raw
    )

    gearbox_type, gearbox_condition = extract_gearbox(
        data
    )

    structured_record = {
        "token": record.get("token"),
        "title": record.get("title"),
        "publish_date": parse_publish_date(
            record.get("publish_date")
        ),
        "city": record.get("city"),
        "district": record.get("district"),
        "url": record.get("url"),

        "brand_model": get_field(
            data,
            FIELD_BRAND_MODEL
        ),

        "year_raw": get_field(
            data,
            FIELD_YEAR
        ),

        "year": parse_year(
            get_field(data, FIELD_YEAR)
        ),

        "mileage": parse_number(
            get_field(data, FIELD_MILEAGE)
        ),

        "color": get_field(
            data,
            FIELD_COLOR
        ),

        "gearbox_type": gearbox_type,

        "gearbox_condition": gearbox_condition,

        "fuel_type": get_field(
            data,
            FIELD_FUEL
        ),

        "engine_condition": get_field(
            data,
            FIELD_ENGINE
        ),

        "chassis_condition": get_field(
            data,
            FIELD_CHASSIS
        ),

        "body_condition": get_field(
            data,
            FIELD_BODY
        ),

        "price_raw": price_raw,

        "original_price": original_price,

        "asking_price": original_price,

        "price_status": classify_price(
            original_price
        ),

        "description": record.get(
            "description"
        ),
    }

    structured_records.append(
        structured_record
    )


with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        structured_records,
        file,
        ensure_ascii=False,
        indent=2
    )


print("=" * 70)
print("STRUCTURED DATASET CREATED")
print("=" * 70)

print(
    f"Input records: {len(records)}"
)

print(
    f"Output records: "
    f"{len(structured_records)}"
)


price_status_counts = {}

for record in structured_records:

    status = record["price_status"]

    price_status_counts[status] = (
        price_status_counts.get(status, 0) + 1
    )


print("\nPRICE STATUS")

for status, count in sorted(
    price_status_counts.items()
):
    print(
        f"{status}: {count}"
    )


field_names = [
    "brand_model",
    "year",
    "mileage",
    "gearbox_type",
    "gearbox_condition",
    "fuel_type",
    "engine_condition",
    "chassis_condition",
    "body_condition",
    "asking_price",
]


print("\nFIELD COMPLETENESS")

for field in field_names:

    count = sum(
        1
        for record in structured_records
        if record.get(field) is not None
    )

    percentage = (
        count / len(structured_records) * 100
    )

    print(
        f"{field}: "
        f"{count}/{len(structured_records)} "
        f"({percentage:.1f}%)"
    )


print("\nOUTPUT")
print(OUTPUT_FILE)