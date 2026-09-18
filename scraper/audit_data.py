import json
from collections import Counter
import sys

sys.stdout.reconfigure(encoding="utf-8")


FILE = "data/raw/divar_cars_500.json"


# -----------------------------
# Load data
# -----------------------------
with open(FILE, "r", encoding="utf-8") as f:
    posts = json.load(f)


print("=" * 70)
print("DIVAR DATA AUDIT")
print("=" * 70)

print(f"Total records: {len(posts)}")


# -----------------------------
# Basic fields
# -----------------------------
print("\n" + "=" * 70)
print("BASIC FIELD COMPLETENESS")
print("=" * 70)

fields = [
    "token",
    "title",
    "publish_date",
    "city",
    "district",
    "url",
    "description",
    "data",
]

for field in fields:
    count = sum(
        1 for post in posts
        if post.get(field) not in [None, "", []]
    )

    print(
        f"{field:15} : "
        f"{count:3} / {len(posts)}"
    )


# -----------------------------
# DATA field analysis
# -----------------------------
print("\n" + "=" * 70)
print("DATA FIELD ANALYSIS")
print("=" * 70)

field_counter = Counter()

for post in posts:
    for item in post.get("data", []):
        field_counter[item.get("title")] += 1


for field, count in field_counter.most_common():
    print(f"{field:35} : {count}")


# -----------------------------
# Important car fields
# -----------------------------
important_fields = [
    "برند و مدل",
    "مدل (سال تولید)",
    "کارکرد",
    "قیمت پایه",
    "گیربکس",
    "نوع سوخت",
    "بدنه",
    "وضعیت شاسی‌ها",
    "موتور",
]


print("\n" + "=" * 70)
print("IMPORTANT CAR FIELDS")
print("=" * 70)

for field in important_fields:

    records_with_field = 0
    values = []

    for post in posts:

        for item in post.get("data", []):

            if item.get("title") == field:

                records_with_field += 1
                values.append(item.get("value"))

                break

    print(
        f"{field:25} : "
        f"{records_with_field:3} / {len(posts)}"
    )


# -----------------------------
# Unique brands/models
# -----------------------------
print("\n" + "=" * 70)
print("BRAND / MODEL VALUES")
print("=" * 70)

brand_models = Counter()

for post in posts:

    for item in post.get("data", []):

        if item.get("title") == "برند و مدل":

            value = item.get("value")

            if value:
                brand_models[value] += 1

            break


print(f"Unique brand/model values: {len(brand_models)}")

print("\nTop 30:")

for value, count in brand_models.most_common(30):
    print(f"{count:3}  {value}")


# -----------------------------
# Years
# -----------------------------
print("\n" + "=" * 70)
print("MODEL YEARS")
print("=" * 70)

years = Counter()

for post in posts:

    for item in post.get("data", []):

        if item.get("title") == "مدل (سال تولید)":

            value = item.get("value")

            if value:
                years[value] += 1

            break


print(f"Unique year values: {len(years)}")

for value, count in years.most_common():
    print(f"{count:3}  {value}")


# -----------------------------
# Price availability
# -----------------------------
print("\n" + "=" * 70)
print("PRICE AVAILABILITY")
print("=" * 70)

price_count = 0

for post in posts:

    for item in post.get("data", []):

        if item.get("title") == "قیمت پایه":

            if item.get("value"):
                price_count += 1

            break


print(
    f"Listings with base price: "
    f"{price_count} / {len(posts)}"
)


# -----------------------------
# Mileage availability
# -----------------------------
print("\n" + "=" * 70)
print("MILEAGE AVAILABILITY")
print("=" * 70)

mileage_count = 0

for post in posts:

    for item in post.get("data", []):

        if item.get("title") == "کارکرد":

            if item.get("value"):
                mileage_count += 1

            break


print(
    f"Listings with mileage: "
    f"{mileage_count} / {len(posts)}"
)


# -----------------------------
# Duplicate tokens
# -----------------------------
print("\n" + "=" * 70)
print("DUPLICATE CHECK")
print("=" * 70)

tokens = [post.get("token") for post in posts]

token_counts = Counter(tokens)

duplicates = {
    token: count
    for token, count in token_counts.items()
    if count > 1
}

print(f"Unique tokens: {len(token_counts)}")
print(f"Duplicate tokens: {len(duplicates)}")

if duplicates:
    print("\nDuplicates:")
    for token, count in duplicates.items():
        print(token, count)


print("\n" + "=" * 70)
print("AUDIT FINISHED")
print("=" * 70)