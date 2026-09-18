import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")

INPUT_FILE = "data/raw/divar_cars_500.json"


def get_field(data, field_name):
    for item in data:
        if item["title"] == field_name:
            return item["value"]
    return None


def parse_number(text):
    if not text:
        return None

    # تبدیل ارقام فارسی/عربی به انگلیسی
    trans = str.maketrans(
        "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
        "01234567890123456789"
    )
    text = text.translate(trans)

    numbers = re.findall(r"\d[\d,]*", text)

    if not numbers:
        return None

    return int(numbers[0].replace(",", ""))


with open(INPUT_FILE, "r", encoding="utf-8") as f:
    records = json.load(f)


cars = []

for r in records:
    data = r["data"]

    brand_model = get_field(data, "برند و مدل")
    year = get_field(data, "مدل (سال تولید)")
    mileage = get_field(data, "کارکرد")
    price_raw = get_field(data, "قیمت پایه")

    price = parse_number(price_raw)
    mileage_num = parse_number(mileage)

    if price is None:
        continue

    cars.append({
        "token": r["token"],
        "title": r["title"],
        "brand_model": brand_model,
        "year": year,
        "mileage": mileage_num,
        "price": price,
        "url": r["url"],
    })


print("=" * 100)
print(f"Valid price records: {len(cars)}")
print("=" * 100)

# ارزان‌ترین
print("\nCHEAPEST 30")
print("-" * 100)

for x in sorted(cars, key=lambda z: z["price"])[:30]:
    print(
        f'{x["price"]:>15,} | '
        f'{str(x["brand_model"]):<45} | '
        f'year={str(x["year"]):<18} | '
        f'mileage={str(x["mileage"]):<10} | '
        f'token={x["token"]}'
    )


# گران‌ترین
print("\nMOST EXPENSIVE 30")
print("-" * 100)

for x in sorted(cars, key=lambda z: z["price"], reverse=True)[:30]:
    print(
        f'{x["price"]:>15,} | '
        f'{str(x["brand_model"]):<45} | '
        f'year={str(x["year"]):<18} | '
        f'mileage={str(x["mileage"]):<10} | '
        f'token={x["token"]}'
    )