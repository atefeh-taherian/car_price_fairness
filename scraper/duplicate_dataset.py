import json
import sys

sys.stdout.reconfigure(encoding="utf-8")

OLD_FILE = "data/raw/divar_cars_500.json"
NEW_FILE = "data/raw/divar_multi_city_raw.json"
OUTPUT_FILE = "data/raw/divar_cars_raw_unique.json"


def load_json(path):
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


old_records = load_json(OLD_FILE)
new_records = load_json(NEW_FILE)

combined_records = old_records + new_records

unique_records = []
seen_tokens = set()
duplicate_records = []

for record in combined_records:

    token = record.get("token")

    if token in seen_tokens:
        duplicate_records.append(record)
        continue

    seen_tokens.add(token)
    unique_records.append(record)


with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    json.dump(
        unique_records,
        file,
        ensure_ascii=False,
        indent=2
    )


print("=" * 70)
print("DEDUPLICATION FINISHED")
print("=" * 70)

print(f"Old batch: {len(old_records)}")
print(f"New batch: {len(new_records)}")
print(f"Combined records: {len(combined_records)}")
print(f"Unique records: {len(unique_records)}")
print(f"Duplicate records removed: {len(duplicate_records)}")

print(f"\nOutput: {OUTPUT_FILE}")