import json
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8")

OLD_FILE = "data/raw/divar_cars_500.json"
NEW_FILE = "data/raw/divar_multi_city_raw.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


old_records = load_json(OLD_FILE)
new_records = load_json(NEW_FILE)

records = old_records + new_records


print("=" * 70)
print("COMBINED MULTI-BATCH DATA AUDIT")
print("=" * 70)

print(f"Old batch records: {len(old_records)}")
print(f"New batch records: {len(new_records)}")
print(f"Combined records: {len(records)}")


print("\nCITY DISTRIBUTION")
print("-" * 70)

city_counts = Counter(
    record.get("city")
    for record in records
)

for city, count in city_counts.most_common():
    print(f"{city}: {count}")


print("\nDUPLICATE TOKENS")
print("-" * 70)

token_counts = Counter(
    record.get("token")
    for record in records
)

duplicate_tokens = {
    token: count
    for token, count in token_counts.items()
    if count > 1
}

print(f"Unique tokens: {len(token_counts)}")
print(f"Duplicate tokens: {len(duplicate_tokens)}")
print(
    f"Duplicate records beyond first occurrence: "
    f"{len(records) - len(token_counts)}"
)


print("\nDUPLICATE DETAILS")
print("-" * 70)

for token, count in duplicate_tokens.items():

    print(f"\nToken: {token}")
    print(f"Occurrences: {count}")

    matches = [
        record
        for record in records
        if record.get("token") == token
    ]

    for index, record in enumerate(matches, start=1):

        print(f"  Record {index}")
        print(f"    City: {record.get('city')}")
        print(f"    District: {record.get('district')}")
        print(f"    Title: {record.get('title')}")
        print(f"    Publish date: {record.get('publish_date')}")


print("\nBASIC FIELD COMPLETENESS")
print("-" * 70)

basic_fields = [
    "token",
    "title",
    "publish_date",
    "city",
    "district",
    "url",
    "description",
    "data",
]

for field in basic_fields:

    count = sum(
        1
        for record in records
        if record.get(field) not in [None, "", []]
    )

    print(
        f"{field}: "
        f"{count}/{len(records)} "
        f"({count / len(records) * 100:.1f}%)"
    )


print("\nIMPORTANT VEHICLE FIELDS")
print("-" * 70)

vehicle_fields = [
    "برند و مدل",
    "مدل (سال تولید)",
    "کارکرد",
    "قیمت پایه",
    "گیربکس",
    "نوع سوخت",
    "موتور",
    "وضعیت شاسی‌ها",
    "بدنه",
]


def get_field(data, field_name):

    for item in data:

        if item["title"] == field_name:
            return item["value"]

    return None


for field in vehicle_fields:

    count = sum(
        1
        for record in records
        if get_field(record["data"], field)
    )

    print(
        f"{field}: "
        f"{count}/{len(records)} "
        f"({count / len(records) * 100:.1f}%)"
    )


print("\nBRAND/MODEL DIVERSITY")
print("-" * 70)

brand_models = []

for record in records:

    value = get_field(
        record["data"],
        "برند و مدل"
    )

    if value:
        brand_models.append(value)


brand_model_counts = Counter(brand_models)

print(
    f"Unique brand/model values: "
    f"{len(brand_model_counts)}"
)

print("\nTop 20 brand/model values:")

for value, count in brand_model_counts.most_common(20):
    print(f"{count:4d} | {value}")


print("\nYEAR DISTRIBUTION")
print("-" * 70)

years = []

for record in records:

    value = get_field(
        record["data"],
        "مدل (سال تولید)"
    )

    if value:
        years.append(value)


year_counts = Counter(years)

print(
    f"Unique raw year values: "
    f"{len(year_counts)}"
)

for value, count in year_counts.most_common(20):
    print(f"{count:4d} | {value}")


print("\nPRICE AVAILABILITY")
print("-" * 70)

prices = []

for record in records:

    value = get_field(
        record["data"],
        "قیمت پایه"
    )

    if value:
        prices.append(value)


print(
    f"Records with price: "
    f"{len(prices)}/{len(records)}"
)


print("\nMILEAGE AVAILABILITY")
print("-" * 70)

mileages = []

for record in records:

    value = get_field(
        record["data"],
        "کارکرد"
    )

    if value:
        mileages.append(value)


print(
    f"Records with mileage: "
    f"{len(mileages)}/{len(records)}"
)


print("\n" + "=" * 70)
print("COMBINED AUDIT FINISHED")
print("=" * 70)